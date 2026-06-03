#!/usr/bin/env python3
"""benchmarks/_common/run_bench.py

Generic driver for any benchmark directory that follows the unified interface
(env.sh + qa.jsonl + metrics.py).

**CI policy: every benchmark task calls only the `main` agent.** The main agent is
responsible for delegating to the appropriate sub-agent via `sessions_spawn`.
Each QA's `target_agent` field names the sub-agent main should spawn; if
absent, main runs the task itself. The separate CI scoring step may directly
invoke the dedicated `reviewer` agent for `judge: "agent"`.

Per-benchmark `metrics.py` becomes a 6-line shim:

    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_common"))
    from run_bench import main
    main("paper-review")
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

# Allow `python3 -m` and direct invocation both.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from judge import judge_with_agent, judge_with_rules  # noqa: E402
else:
    from .judge import judge_with_agent, judge_with_rules  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Debug-mode helper
# ---------------------------------------------------------------------------
#
# BENCH_DEBUG=1 makes run_bench.py dump the raw, unredacted artifacts from
# every `openclaw agent` call to a per-benchmark debug directory (default
# `bench-debug/<bench>/<qa_id>/`) so the CI logs and uploaded artifacts
# contain the *raw* full stdout, the full stderr, the wrapped prompt we
# actually sent, the extracted agent text, and the judge's input/output.
# Without this we only print a 200-char head of the cleaned text, which
# makes it impossible to diagnose failures caused by JSON parse errors,
# sub-agent routing bugs, sandbox errors, etc.

DEBUG = os.environ.get("BENCH_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")


def _debug_dir(bench: str, qa_id: str | None = None) -> Path | None:
    if not DEBUG:
        return None
    base = Path(os.environ.get("BENCH_DEBUG_DIR", ROOT / "bench-debug"))
    d = base / bench
    if qa_id:
        d = d / qa_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _debug_write(path: Path, content: str | bytes) -> None:
    """Write a debug artifact. content may be str (utf-8) or bytes."""
    try:
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    except OSError as e:
        print(f"[debug] failed to write {path}: {e}", file=sys.stderr)


def _debug_echo(label: str, value: object) -> None:
    """Echo a short, structured marker to stderr so DEBUG shows up inline in CI logs."""
    if not DEBUG:
        return
    if isinstance(value, str) and len(value) > 200:
        value = value[:200] + f"... <truncated, {len(value)} chars total>"
    print(f"[DEBUG] {label}: {value!r}", file=sys.stderr)


def _debug_banner(bench: str) -> None:
    """Print a one-line startup banner so DEBUG mode is visible from the first log line."""
    if not DEBUG:
        return
    artifacts = Path(os.environ.get("BENCH_DEBUG_DIR", ROOT / "bench-debug")) / bench
    print(f"[DEBUG] BENCH_DEBUG=1 — full raw artifacts per QA will be written to "
          f"{artifacts.resolve()}", file=sys.stderr)


def repair_container_permissions(container: str) -> None:
    """Make benchmark-created runtime files writable by OpenClaw's node user.

    The benchmark env.sh scripts stage fixtures with `docker exec` / `docker cp`,
    which creates root-owned files in the mounted ~/.openclaw tree. OpenClaw
    stores per-agent sessions at ~/.openclaw/agents/<agentId>/sessions/*.jsonl
    and the gateway/embedded agents write them as uid 1000 in the benchmark
    image, so repair ownership before sending benchmark turns.
    """
    mount = os.environ.get("BENCH_MOUNT", "/home/node/.openclaw")
    script = r'''
set -e
: "${BENCH_MOUNT:=/home/node/.openclaw}"
for agent_id in main autoresearch paper-review idea-generate reviewer; do
  mkdir -p "${BENCH_MOUNT}/agents/${agent_id}/sessions"
done
for path in \
  "${BENCH_MOUNT}/agents" \
  "${BENCH_MOUNT}/workspace" \
  "${BENCH_MOUNT}"/workspace-* \
  "${BENCH_MOUNT}/logs" \
  "${BENCH_MOUNT}/qmd" \
  "${BENCH_MOUNT}/tasks"
do
  [ -e "$path" ] || continue
  chown -R 1000:1000 "$path" 2>/dev/null || true
  chmod -R u+rwX,g+rwX "$path" 2>/dev/null || true
done
'''
    proc = subprocess.run(
        ["docker", "exec", "-e", f"BENCH_MOUNT={mount}", container, "bash", "-lc", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        print(
            f"[bench] warning: permission repair failed for {container}: "
            f"{(proc.stderr or proc.stdout).strip()}",
            file=sys.stderr,
        )


def load_qa(path: Path) -> list[dict]:
    qas: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        qa = json.loads(line)
        qa.setdefault("qa_id", f"qa-{i:03d}")
        qa.setdefault("agent", qa.get("agent") or "main")
        qa.setdefault("pass_threshold", 0.5)
        qa.setdefault("weight", 1.0)
        qa.setdefault("judge", "rules")
        qas.append(qa)
    return qas


def run_agent(container: str, agent_id: str, qa: dict, run_id: str,
              model: str | None, debug_dir: Path | None = None) -> tuple[str, str, dict]:
    """Always invokes `agent_id` (which the CI contract pins to `main`).
    If the QA carries a `target_agent` field, the prompt is wrapped so main
    delegates to that sub-agent via sessions_spawn and returns the sub-agent's
    final answer.

    Returns (cleaned_agent_text, session_key, raw_artifacts). The third
    tuple element is a dict with the unredacted raw stdout / stderr / prompt
    / cmd, useful for BENCH_DEBUG=1 dumps and for future re-runs.
    With --json, openclaw writes the structured reply to stdout and all
    diagnostics to stderr, so we capture them separately and only look at
    the JSON payload[].text fields for the actual agent answer.
    """
    target = qa.get("target_agent")
    prompt = qa["question"]
    if qa.get("input_material"):
        material = qa["input_material"]
        if isinstance(material, dict):
            material = material.get("content") or Path(material["path"]).read_text(encoding="utf-8")
        prompt = f"{material}\n\n---\n\n{prompt}"
    if target and target != agent_id:
        prompt = (
            f"[BENCHMARK DIRECTIVE — read carefully]\n"
            f"This task must be executed by the `{target}` sub-agent.\n"
            f"Step 1: Call sessions_spawn to delegate:\n"
            f"  sessions_spawn(agentId=\"{target}\", task=<the full task below>, "
            f"mode=\"run\", context=\"isolated\", "
            f"runTimeoutSeconds={qa.get('timeout_seconds', 1800)})\n"
            f"Step 2: IMMEDIATELY call sessions_yield() — this ends your turn and "
            f"blocks until the sub-agent finishes. The sub-agent result will arrive "
            f"as your next incoming message. Do NOT poll or guess when it finishes.\n"
            f"sessions_spawn is non-blocking (returns a runId immediately). "
            f"sessions_yield is the ONLY correct way to wait for the result.\n"
            f"After the sub-agent completes, run the `reviewer` agent to audit "
            f"the sub-agent's final reply against this benchmark directive, the "
            f"full task, expected artifacts, gold_answer, and rubric below. "
            f"If reviewer returns FAIL, use sessions_send(sessionKey=<same sessionKey>, "
            f"message=<reviewer fix prompt>) to send its fix prompt back to the SAME "
            f"sub-agent session and wait for the repaired answer, then run "
            f"reviewer again. Do not start a new `{target}` session for fixes. "
            f"Skip this extra review loop only when the target sub-agent itself "
            f"is `reviewer`.\n"
            f"Then return the reviewer-passed sub-agent final reply as your only output.\n"
            f"Do NOT return a runId, pending status, or 'wait for completion' "
            f"message.\n"
            f"Do NOT solve the task yourself. Do NOT add commentary. Return the "
            f"sub-agent's reply verbatim after it has passed reviewer.\n\n"
            f"BENCHMARK GOLD_ANSWER: {json.dumps(qa.get('gold_answer'), ensure_ascii=False)}\n"
            f"BENCHMARK RUBRIC: {qa.get('rubric') or '(none)'}\n"
            f"BENCHMARK EXPECTED_ARTIFACTS: {json.dumps(qa.get('expected_artifacts'), ensure_ascii=False)}\n\n"
            f"---\n\n{prompt}"
        )
    # Use a never-reused key so every QA starts from an empty conversation.
    # OpenClaw documents --session-key as the explicit session selector; there
    # is no separate "new session" flag for `openclaw agent`, so freshness comes
    # from making the key unique per QA attempt.
    session_key = f"agent:{agent_id}:bench-{run_id}-{qa['qa_id']}-{uuid.uuid4().hex}"
    # Propagate the LLM provider credentials into the container. Without
    # these the embedded openclaw agent cannot reach the model.
    cmd = [
        "docker", "exec", "-i",
        "-e", "DEEPSEEK_API_KEY", "-e", "DEEPSEEK_BASE_URL",
        container, "openclaw", "agent",
        "--agent", agent_id, "--message", prompt, "--json", "--local",
        "--session-key", session_key,
        "--timeout", str(qa.get("timeout_seconds", 1800)),
    ]
    if model:
        cmd += ["--model", model]
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=qa.get("timeout_seconds", 1800) + 60)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        returncode = proc.returncode
    except subprocess.TimeoutExpired as e:
        # Preserve whatever partial output we got, but mark the failure.
        stdout = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
        stderr = e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")
        returncode = -1
        timed_out = True
    # Per docs.openclaw.ai/tools/agent-send: with --json, the structured
    # payload (including payloads[].text = the agent's reply) is on stdout;
    # diagnostics, context-engine warnings, and lane errors all go to stderr.
    # We deliberately keep them separate and only return the agent text.
    agent_text = _extract_agent_text(stdout, stderr)
    raw = {
        "cmd": cmd,
        "prompt": prompt,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": returncode,
        "timed_out": timed_out,
        "session_key": session_key,
        "agent_text": agent_text,
    }
    if debug_dir is not None:
        _debug_write(debug_dir / "00_prompt.txt", prompt)
        _debug_write(debug_dir / "01_cmd.json", json.dumps(cmd, ensure_ascii=False, indent=2))
        _debug_write(debug_dir / "02_stdout.txt", stdout)
        _debug_write(debug_dir / "03_stderr.txt", stderr)
        _debug_write(debug_dir / "04_agent_text.txt", agent_text)
        meta = {
            "qa_id": qa.get("qa_id"),
            "session_key": session_key,
            "returncode": returncode,
            "timed_out": timed_out,
            "stdout_bytes": len(stdout.encode("utf-8")),
            "stderr_bytes": len(stderr.encode("utf-8")),
            "agent_text_chars": len(agent_text),
        }
        _debug_write(debug_dir / "05_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    return (agent_text, session_key, raw)


# Lines we know are diagnostic noise from openclaw, not the agent's answer.
_NOISE_PREFIXES = (
    "[diagnostic]",
    "[context-engine]",
    "[gateway]",
    "[plugins]",
    "[secrets]",
    "[heartbeat]",
    "[ws]",
    "[memory-core]",
    "[memory-wiki]",
    "[memory-qmd]",
    "[qmd]",
    "[sandbox]",
    "[auth]",
    "[lanes]",
    "[tools]",
    "[model-fallback",
    "[model-errors]",
    "[secrets-ref]",
    "[secrets-store]",
    "[secrets-warning]",
    "[fallback]",
    "[init]",
    "[post-init]",
    "[config]",
    "[bridge]",
    "[obsidian]",
    "[vault]",
    "[wiki]",
    "[router]",
    "[worker]",
    "[spawn]",
    "[retry]",
    "[loop]",
    "Config health-state write failed",
    "=== ",
    "初始化",
    "配置",
    "启动",
    "挂载",
    "检测",
    "ℹ️",
    "已",
    "正在",
    "整体",
    "上下文",
    "最大",
    "API",
    "Base",
    "Gateway",
    "沙箱",
    "插件",
    "允许",
    "当前",
    "目标",
    "开放",
)

# Regex matching a *whole* log/diagnostic line that has a `[tag]` prefix and
# no real agent content.  Used as a second pass after prefix matching.
_BRACKET_TAG_RE = re.compile(r"^\s*\[(?P<tag>[a-zA-Z0-9_.-]+)\]\s*(?P<rest>.*)$")

# Diagnostic lines that look like free-form English status text, not
# agent prose.  Anything matching one of these is dropped.
_NOISE_SUBSTRINGS = (
    "Context engine ",
    "quarantining it for this process",
    "falling back to default engine",
    "Context engine \"",
    "failed during resolve: not registered",
    "failed to start",
    "lane task error",
    "Traceback (most recent call last)",
    "TypeError:",
    "RuntimeError:",
    "Error response from daemon",
    "EACCES:",
    "ENOENT:",
    "openclaw configuration is invalid",
    "secret reference is unresolved",
    "no API key found for provider",
    "Authentication failed",
    "401 Unauthorized",
    "403 Forbidden",
    "Sandbox mode requires Docker",
    "Cannot connect to the Docker daemon",
    "Is the docker daemon running?",
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_diagnostics(text: str) -> str:
    """Drop lines that look like openclaw stderr leakage from a non-JSON reply.

    Passes:
    1. ANSI escape removal + trim.
    2. Drop lines that start with any known noise prefix.
    3. Drop lines that match a `[tag] ...` diagnostic shape.
    4. Drop lines whose body contains a known noise substring.
    5. Keep everything else.
    """
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = _ANSI_RE.sub("", line).strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in _NOISE_PREFIXES):
            continue
        if _BRACKET_TAG_RE.match(stripped):
            # Looks like a `[foo] ...` log line.  Only keep if the tag is
            # clearly NOT in our diagnostic tag list.  For safety, drop ALL
            # bracketed-tag lines; real agent text never starts with `[tag]`.
            continue
        if any(sub in stripped for sub in _NOISE_SUBSTRINGS):
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def _extract_agent_text(stdout: str, stderr: str) -> str:
    """Pick the agent's final text out of an `openclaw agent --json` reply.

    Strategy:
    1. Try to parse stdout as JSON. The docs document shape:
         {"payloads": [{"text": "...", "mediaUrl": null}, ...], "meta": {...}}
       We concatenate every payloads[].text (the agent may emit multiple
       text parts) and return that.
    2. If stdout is empty or unparsable, fall back to stderr, but run
       the diagnostic-stripping pass first -- when context-engine plugin
       fails, openclaw writes ~2kB of `[context-engine] ... [diagnostic] ...`
       noise to stderr and no real agent text appears.
    3. If after stripping nothing usable remains, return a sentinel
       "(no agent response — only diagnostic output)" so downstream
       judges and the report get a clear signal instead of 2kB of noise.
    """
    if stdout.strip():
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return _strip_diagnostics(stdout)

        # Common shape: top-level "payloads" list.
        if isinstance(data, dict):
            payloads = data.get("payloads")
            if isinstance(payloads, list) and payloads:
                texts = [p.get("text", "") for p in payloads if isinstance(p, dict)]
                joined = "\n".join(t for t in texts if t)
                if joined.strip():
                    return _strip_diagnostics(joined)
            # Some embedded-fallback responses nest under "result.payloads".
            result = data.get("result")
            if isinstance(result, dict):
                payloads = result.get("payloads")
                if isinstance(payloads, list) and payloads:
                    texts = [p.get("text", "") for p in payloads if isinstance(p, dict)]
                    joined = "\n".join(t for t in texts if t)
                    if joined.strip():
                        return _strip_diagnostics(joined)

    # Fallback: stderr.  Strip diagnostic noise and return what remains.
    cleaned_stderr = _strip_diagnostics(stderr)
    if not cleaned_stderr.strip():
        return "(no agent response — only diagnostic output)"
    return cleaned_stderr


def main(bench_name: str, agent_id: str | None = None) -> int:
    """Run a benchmark. `agent_id` is the CI-side task caller; the contract forces
    this to `main`. Per-QA sub-agent routing goes through `target_agent`; the
    separate CI scoring path may call reviewer directly."""
    qa_path = Path(os.environ.get("BENCH_QA_PATH", ROOT / "benchmarks" / bench_name / "qa.jsonl"))
    report_path = Path(os.environ.get("BENCH_REPORT_PATH",
                                       ROOT / "benchmarks" / bench_name / "bench-report.json"))
    container = os.environ.get("BENCH_CONTAINER", "")
    run_id = os.environ.get("BENCH_RUN_ID", f"local-{int(time.time())}")
    model = os.environ.get("BENCH_MODEL")
    # Hard policy: CI only ever calls `main`. Sub-agents are reached through
    # main's sessions_spawn, never directly.
    agent_id = agent_id or os.environ.get("BENCH_AGENT") or "main"
    assert agent_id == "main", (
        f"CI policy violation: benchmarks may only target the `main` agent, "
        f"got agent_id={agent_id!r}. Set `target_agent` on the QA to route "
        f"through sessions_spawn instead."
    )

    if not container:
        print(f"[{bench_name}] BENCH_CONTAINER not set; skipping agent calls (dry-run).", file=sys.stderr)
        # Still emit a stub report so PR comment machinery has something to read.
        report = {"benchmark": bench_name, "agent": agent_id, "run_id": run_id,
                  "model": model or "default", "total": 0, "passed": 0,
                  "pass_rate": 0.0, "avg_score": 0.0, "results": [],
                  "skipped": "no container"}
    else:
        repair_container_permissions(container)
        qas = load_qa(qa_path)
        results: list[dict] = []
        _debug_banner(bench_name)
        for qa in qas:
            qa_debug_dir = _debug_dir(bench_name, qa["qa_id"])
            _debug_echo("qa_start", f"id={qa['qa_id']} target={qa.get('target_agent')} judge={qa.get('judge')}")
            t0 = time.time()
            answer, session_key, raw = run_agent(container, agent_id, qa, run_id, model,
                                                  debug_dir=qa_debug_dir)
            elapsed = time.time() - t0
            mode = qa.get("judge", "rules")
            # LLM judge directly invokes the dedicated reviewer agent. The
            # main-agent-only policy above applies to each benchmark task, not
            # to this separate CI scoring step.
            verdict = (judge_with_agent(qa, answer, agent_id="reviewer", model=model,
                                        container=container)
                       if mode == "agent" else judge_with_rules(answer, qa))
            # Dump judge artifacts when DEBUG is on.
            if qa_debug_dir is not None:
                _debug_write(qa_debug_dir / "06_verdict.json", json.dumps(verdict, ensure_ascii=False, indent=2))
                _debug_write(qa_debug_dir / "07_answer_full.txt", answer or "")
                _debug_write(qa_debug_dir / "08_qa.json", json.dumps(qa, ensure_ascii=False, indent=2))
            _debug_echo("qa_done", f"id={qa['qa_id']} score={verdict.get('score', 0):.3f} "
                        f"pass={verdict.get('pass', False)} elapsed={elapsed:.1f}s "
                        f"returncode={raw.get('returncode')} timed_out={raw.get('timed_out')} "
                        f"stdout_bytes={len(raw.get('stdout', ''))} "
                        f"stderr_bytes={len(raw.get('stderr', ''))} "
                        f"agent_text_chars={len(answer or '')}")
            # Surface the first 200 chars of the agent's reply so
            # zero-score failures are easy to diagnose from CI logs.
            head = (answer or "").replace("\n", "\\n")[:200]
            print(f"  [{qa['qa_id']}] score={verdict.get('score', 0):.3f} "
                  f"pass={verdict.get('pass', False)} "
                  f"len(answer)={len(answer or '')} head={head!r}",
                  file=sys.stderr)
            result_entry = {
                "qa_id": qa["qa_id"], "task_type": qa.get("task_type"),
                "target_agent": qa.get("target_agent"),
                "weight": qa.get("weight", 1.0),
                "score": verdict.get("score", 0.0), "pass": verdict.get("pass", False),
                "rationale": verdict.get("rationale", ""),
                "elapsed_seconds": round(elapsed, 1),
                "session_key": session_key, "raw_output": answer[:2000],
            }
            if DEBUG:
                result_entry["debug"] = {
                    "returncode": raw.get("returncode"),
                    "timed_out": raw.get("timed_out"),
                    "stdout_len": len(raw.get("stdout", "")),
                    "stderr_len": len(raw.get("stderr", "")),
                    "agent_text_len": len(answer or ""),
                }
            results.append(result_entry)
        weight_total = sum(r["weight"] for r in results) or 1.0
        weighted = sum(r["score"] * r["weight"] for r in results) / weight_total
        passed = sum(1 for r in results if r["pass"])
        report = {
            "benchmark": bench_name, "agent": agent_id, "run_id": run_id,
            "model": model or "default", "total": len(results), "passed": passed,
            "pass_rate": passed / len(results) if results else 0.0,
            "avg_score": round(weighted, 4), "results": results,
        }
    if DEBUG:
        report["debug"] = {
            "mode": "BENCH_DEBUG=1",
            "artifacts_dir": str((Path(os.environ.get("BENCH_DEBUG_DIR", ROOT / "bench-debug")) / bench_name).resolve()),
        }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    results_dir = Path(os.environ.get("BENCH_RESULTS_DIR", ROOT / "bench-results"))
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{bench_name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{bench_name}] {report['passed']}/{report['total']} passed, avg_score={report['avg_score']:.3f}")
    if DEBUG:
        print(f"[DEBUG] {bench_name} artifacts: {report['debug']['artifacts_dir']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: run_bench.py <bench_name>", file=sys.stderr)
        sys.exit(2)
    bench = sys.argv[1]
    sys.exit(main(bench))
