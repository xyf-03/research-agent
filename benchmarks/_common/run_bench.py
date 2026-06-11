#!/usr/bin/env python3
"""benchmarks/_common/run_bench.py

Generic driver for any benchmark directory that follows the unified interface
(env.sh + qa.jsonl + metrics.py).

**CI policy: every benchmark task calls only the `main` agent.** The main agent is
responsible for deciding how to handle each task, including delegating to the
appropriate sub-agent via `sessions_spawn` when needed. The separate CI scoring
step may directly invoke the dedicated `reviewer` agent for `judge: "agent"`.

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


# ---------------------------------------------------------------------------
# Session log extraction (DEBUG mode)
# ---------------------------------------------------------------------------
# When BENCH_DEBUG=1, after each QA run we extract the full session JSONL
# transcript for the main agent AND every sub-agent it spawned.  These are
# copied out of the container into bench-debug/<bench>/<qa_id>/sessions/ so
# the CI debug artifact upload includes them.  We also print a condensed
# human-readable summary in the CI logs inside ::group:: blocks.

_AGENT_IDS = ("main", "orchestrate", "ingest", "curate", "extract", "critic",
              "design", "spec", "audit", "ideate", "judge", "reviewer")

_SESSION_MOUNT = "/home/node/.openclaw"


def _agent_id_from_session_key(session_key: str) -> str:
    """Best-effort extraction of the agent id from a session key.

    Session keys look like ``agent:main:bench-...`` or
    ``agent:main:subagent:curate:bench-...``.  The agent id is the token
    immediately following ``subagent:`` for spawned sessions, otherwise the
    second colon-delimited token.
    """
    parts = session_key.split(":")
    try:
        sub_idx = parts.index("subagent")
        return parts[sub_idx + 1]
    except (ValueError, IndexError):
        pass
    # Not a subagent key — the agent id is the second token.
    if len(parts) >= 2:
        return parts[1]
    return "main"


def _container_cat(container: str, path: str) -> str | None:
    """Read a text file from inside *container*, returning its contents or None."""
    try:
        proc = subprocess.run(
            ["docker", "exec", container, "cat", path],
            capture_output=True, text=True, timeout=15,
        )
        if proc.returncode == 0:
            return proc.stdout
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def _sqlite_string_literal(value: str) -> str:
    """Return *value* as a safely escaped SQLite string literal."""
    return "'" + value.replace("'", "''") + "'"


def _container_find_session_jsonl(container: str, agent_id: str,
                                  session_id: str) -> str | None:
    """Return the container-side path to a session JSONL file, or None."""
    candidate = f"{_SESSION_MOUNT}/agents/{agent_id}/sessions/{session_id}.jsonl"
    try:
        proc = subprocess.run(
            ["docker", "exec", container, "test", "-f", candidate],
            capture_output=True, timeout=5,
        )
        if proc.returncode == 0:
            return candidate
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def _print_session_summary(session_path: str, label: str) -> None:
    """Print the **complete** session transcript in CI logs.

    Output is wrapped in a GitHub Actions ``::group::`` block.  The full raw
    JSONL content is printed — no truncation — so that every tool call, tool
    result, and model turn is visible in the CI DEBUG logs.
    """
    print(f"::group::📋 Session: {label}")
    try:
        raw_text = Path(session_path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"(cannot read session file: {e})")
        print("::endgroup::")
        return

    lines = raw_text.splitlines()

    # Print a structured turn-by-turn summary first, then the raw JSONL.
    turn_count = 0
    tool_count = 0
    for raw_line in lines:
        try:
            evt = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        etype = evt.get("type", "")
        if etype == "message":
            role = evt.get("role", "?")
            content = evt.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type", "")
                    if btype == "tool_use":
                        tool_count += 1
                        name = block.get("name", "?")
                        inp = json.dumps(block.get("input", {}), ensure_ascii=False)
                        print(f"  [{role}] 🔧 tool_call #{tool_count}: {name}")
                        print(f"         input: {inp}")
                    elif btype == "tool_result":
                        out = block.get("content", "")
                        if isinstance(out, list):
                            out = " ".join(
                                c.get("text", "") if isinstance(c, dict) else str(c)
                                for c in out
                            )
                        out = str(out)
                        print(f"  [{role}] 📄 tool_result #{tool_count}:")
                        print(f"         {out}")
                    elif btype == "text":
                        txt = block.get("text", "")
                        print(f"  [{role}] 💬 {txt}")
            elif isinstance(content, str) and content.strip():
                print(f"  [{role}] {content}")
            turn_count += 1
        elif etype == "session":
            print(f"  [meta] model={evt.get('model', '?')} "
                  f"sessionId={evt.get('sessionId', '?')} "
                  f"spawnedBy={evt.get('spawnedBy', '-')}")
        elif etype == "thinking_level_change":
            print(f"  [meta] thinking_level={evt.get('thinkingLevel', '?')}")
        elif etype == "model_change":
            print(f"  [meta] model → {evt.get('model', '?')}")

    print(f"  ── {turn_count} message turns, {tool_count} tool calls ──")
    print("::endgroup::")

    # Also print the full raw JSONL in a separate group for forensic analysis.
    print(f"::group::📋 Raw JSONL: {label}")
    print(raw_text)
    print("::endgroup::")


def _extract_qa_sessions(container: str, session_key: str,
                         debug_dir: Path) -> int:
    """Extract all session JSONL transcripts related to *session_key*.

    Copies the main agent's session JSONL and every child session JSONL
    (discovered via SQLite ``subagent_runs`` and fallback ``sessions.json``
    scanning) into ``<debug_dir>/sessions/``.  Also prints condensed
    summaries in CI logs.

    Returns the number of session files extracted (0 on failure).
    """
    sessions_out = debug_dir / "sessions"
    sessions_out.mkdir(parents=True, exist_ok=True)

    extracted = 0

    # ---- 1. Main agent session -------------------------------------------
    main_sessions_json = _container_cat(
        container, f"{_SESSION_MOUNT}/agents/main/sessions/sessions.json"
    )
    main_index: dict[str, dict] = {}
    if main_sessions_json:
        try:
            main_index = json.loads(main_sessions_json)
        except json.JSONDecodeError:
            print("[sessions] warning: could not parse main sessions.json", file=sys.stderr)

    main_entry = main_index.get(session_key, {})
    main_session_id = main_entry.get("sessionId", "")
    if main_session_id:
        src = _container_find_session_jsonl(container, "main", main_session_id)
        if src:
            dst = sessions_out / f"main-{main_session_id}.jsonl"
            try:
                subprocess.run(
                    ["docker", "cp", f"{container}:{src}", str(dst)],
                    capture_output=True, timeout=15,
                )
                if dst.exists():
                    _print_session_summary(str(dst), f"main ({session_key})")
                    extracted += 1
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"[sessions] warning: docker cp main session failed: {e}", file=sys.stderr)
    else:
        print(f"[sessions] warning: main session key {session_key!r} not found "
              f"in sessions.json", file=sys.stderr)

    # ---- 2. Discover descendant sessions via SQLite ----------------------
    child_keys: list[tuple[str, str]] = []  # (session_key, agent_id)
    seen_session_keys: set[str] = {session_key}

    def add_child_session(child_key: str, agent_id: str) -> bool:
        """Remember one descendant session if we have not seen it before."""
        if not child_key or child_key in seen_session_keys:
            return False
        if not agent_id or agent_id not in _AGENT_IDS:
            agent_id = _agent_id_from_session_key(child_key)
        child_keys.append((child_key, agent_id))
        seen_session_keys.add(child_key)
        return True

    try:
        query = (
            "WITH RECURSIVE descendants(child_session_key, workspace_dir) AS ("
            "  SELECT child_session_key, workspace_dir FROM subagent_runs"
            "  WHERE controller_session_key = "
            f"{_sqlite_string_literal(session_key)}"
            "  UNION"
            "  SELECT runs.child_session_key, runs.workspace_dir"
            "  FROM subagent_runs AS runs"
            "  JOIN descendants AS prev"
            "    ON runs.controller_session_key = prev.child_session_key"
            ") "
            "SELECT child_session_key, workspace_dir FROM descendants"
        )
        proc = subprocess.run(
            ["docker", "exec", container, "sqlite3", "-readonly",
             f"{_SESSION_MOUNT}/state/openclaw.sqlite", query],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.strip().splitlines():
                parts = line.split("|", 1)
                child_key = parts[0].strip()
                ws_dir = parts[1].strip() if len(parts) > 1 else ""
                # workspace_dir is like /home/node/.openclaw/workspace/curate
                # → agent sessions live at /home/node/.openclaw/agents/curate/sessions/
                agent_id = "main"
                if ws_dir:
                    ws_rel = ws_dir.replace(f"{_SESSION_MOUNT}/workspace/", "")
                    if ws_rel and ws_rel != ws_dir:
                        agent_id = ws_rel.split("/")[0]
                add_child_session(child_key, agent_id)
        elif proc.returncode != 0:
            print(
                "[sessions] warning: SQLite child-session query failed: "
                f"{(proc.stderr or proc.stdout).strip()}",
                file=sys.stderr,
            )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"[sessions] warning: SQLite child-session query failed: {e}", file=sys.stderr)

    # ---- 3. Fallback: scan all agent sessions.json for spawnedBy ---------
    # Always run the fallback as an augmentation path.  Some session indexes
    # have spawnedBy links that are absent from SQLite, and nested sub-agents
    # may be spawned by a direct child rather than by the original main session.
    agent_session_indexes: dict[str, dict[str, dict]] = {}
    for agent_id in _AGENT_IDS:
        agent_sessions = _container_cat(
            container, f"{_SESSION_MOUNT}/agents/{agent_id}/sessions/sessions.json"
        )
        if not agent_sessions:
            continue
        try:
            agent_session_indexes[agent_id] = json.loads(agent_sessions)
        except json.JSONDecodeError:
            continue

    pending_parent_keys = list(seen_session_keys)
    scanned_parent_keys: set[str] = set()
    while pending_parent_keys:
        parent_key = pending_parent_keys.pop(0)
        if parent_key in scanned_parent_keys:
            continue
        scanned_parent_keys.add(parent_key)
        for agent_id, agent_index in agent_session_indexes.items():
            for key, entry in agent_index.items():
                if entry.get("spawnedBy") == parent_key:
                    if add_child_session(key, agent_id):
                        pending_parent_keys.append(key)

    # ---- 4. Copy child session JSONLs ------------------------------------
    # Also snapshot each agent's sessions.json so we have the cross-reference.
    seen_agents: set[str] = set()
    for child_key, agent_id in child_keys:
        seen_agents.add(agent_id)
        # Find the sessionId by reading that agent's sessions.json.
        agent_sessions_json = _container_cat(
            container, f"{_SESSION_MOUNT}/agents/{agent_id}/sessions/sessions.json"
        )
        child_entry: dict = {}
        if agent_sessions_json:
            try:
                child_entry = json.loads(agent_sessions_json).get(child_key, {})
            except json.JSONDecodeError:
                pass
        child_session_id = child_entry.get("sessionId", "")
        if not child_session_id:
            continue
        src = _container_find_session_jsonl(container, agent_id, child_session_id)
        if not src:
            continue
        dst = sessions_out / f"{agent_id}-{child_session_id}.jsonl"
        try:
            subprocess.run(
                ["docker", "cp", f"{container}:{src}", str(dst)],
                capture_output=True, timeout=15,
            )
            if dst.exists():
                _print_session_summary(str(dst), f"{agent_id} ({child_key})")
                extracted += 1
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"[sessions] warning: docker cp child session failed: {e}", file=sys.stderr)

    # ---- 5. Snapshot sessions.json for each involved agent ----------------
    for agent_id in seen_agents:
        src = f"{_SESSION_MOUNT}/agents/{agent_id}/sessions/sessions.json"
        dst = sessions_out / f"{agent_id}-sessions.json"
        try:
            subprocess.run(
                ["docker", "cp", f"{container}:{src}", str(dst)],
                capture_output=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass
    # Always snapshot main sessions.json.
    main_src = f"{_SESSION_MOUNT}/agents/main/sessions/sessions.json"
    main_dst = sessions_out / "main-sessions.json"
    if not (main_dst).exists():
        try:
            subprocess.run(
                ["docker", "cp", f"{container}:{main_src}", str(main_dst)],
                capture_output=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    if extracted == 0:
        print(f"[sessions] no session JSONL files extracted for {session_key}", file=sys.stderr)
    else:
        print(f"[sessions] extracted {extracted} session JSONL(s) for {session_key} "
              f"→ {sessions_out.resolve()}", file=sys.stderr)
    return extracted


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
for agent_id in main orchestrate ingest curate extract critic design spec audit ideate judge reviewer; do
  mkdir -p "${BENCH_MOUNT}/agents/${agent_id}/sessions"
done
for path in \
  "${BENCH_MOUNT}/agents" \
  "${BENCH_MOUNT}/workspace" \
  "${BENCH_MOUNT}/workspace"/* \
  "${BENCH_MOUNT}/wiki" \
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
    """Invoke `agent_id` (pinned to `main` by CI contract) with the QA prompt.

    Returns (cleaned_agent_text, session_key, raw_artifacts). The third
    tuple element is a dict with the unredacted raw stdout / stderr / prompt
    / cmd, useful for BENCH_DEBUG=1 dumps and for future re-runs.
    With --json, openclaw writes the structured reply to stdout and all
    diagnostics to stderr, so we capture them separately and only look at
    the JSON payload[].text fields for the actual agent answer.
    """
    prompt = qa["question"]
    if qa.get("input_material"):
        material = qa["input_material"]
        if isinstance(material, dict):
            material = material.get("content") or Path(material["path"]).read_text(encoding="utf-8")
        prompt = f"{material}\n\n---\n\n{prompt}"
    # Use a never-reused key so every QA starts from an empty conversation.
    # OpenClaw documents --session-key as the explicit session selector; there
    # is no separate "new session" flag for `openclaw agent`, so freshness comes
    # from making the key unique per QA attempt.
    session_key = f"agent:{agent_id}:bench-{run_id}-{qa['qa_id']}-{uuid.uuid4().hex}"
    # Propagate the LLM provider credentials into the container. Without
    # these the embedded openclaw agent cannot reach the model.
    cmd = [
        "docker", "exec", "-i",
        "-e", "MINIMAX_API_KEY", "-e", "MINIMAX_BASE_URL",
        container, "openclaw", "agent",
        "--agent", agent_id, "--message", prompt, "--json", "--local",
        "--session-key", session_key,
        "--timeout", str(qa.get("timeout_seconds", 1800)),
    ]
    if model:
        cmd += ["--model", model]
    # Per-QA wall-clock cap. The QA may set `timeout_seconds` (per-call budget
    # for the embedded openclaw agent) and `wall_clock_seconds` (overall cap
    # for the docker exec cycle). The cap protects CI from a single hung
    # test blocking the whole run: when the cap fires we set timed_out=True
    # so downstream code can short-circuit judging and mark the QA failed.
    timeout = int(qa.get("timeout_seconds", 1800))
    wall_clock_cap = int(qa.get("wall_clock_seconds",
                                int(os.environ.get("BENCH_MAX_QA_WALL_CLOCK", max(timeout + 120, 600)))))
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=wall_clock_cap)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        returncode = proc.returncode
    except subprocess.TimeoutExpired as e:
        # The docker exec itself hung past the wall-clock cap. Kill the
        # container-side process (best-effort) so the next QA can start on a
        # healthy container, then preserve whatever partial output we got.
        print(f"[{qa['qa_id']}] wall-clock cap hit after {wall_clock_cap}s; "
              f"killing docker exec and marking QA timed_out",
              file=sys.stderr)
        try:
            subprocess.run(["docker", "exec", container, "pkill", "-f",
                            "openclaw agent"], capture_output=True, timeout=10)
        except Exception:
            pass
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
    2. If stdout is empty or unparsable as a whole, try to find a JSON
       object embedded in stdout (some openclaw builds prepend diagnostic
       lines like "- Canonicalized N orphaned session key(s) ..." to the
       JSON payload, which makes json.loads(stdout) raise). The fallback
       scans for the first '{' that starts a top-level object and
       attempts to parse from there.
    3. If stdout is empty or has no parseable JSON, fall back to stderr,
       but run the diagnostic-stripping pass first -- when context-engine
       plugin fails, openclaw writes ~2kB of `[context-engine] ... [diagnostic] ...`
       noise to stderr and no real agent text appears.
    4. If after stripping nothing usable remains, return a sentinel
       "(no agent response — only diagnostic output)" so downstream
       judges and the report get a clear signal instead of 2kB of noise.
    """
    if stdout.strip():
        data = _try_parse_json(stdout)
        if data is not None:
            extracted = _text_from_json(data)
            if extracted is not None:
                return extracted
        # Whole stdout didn't parse -- try to find a JSON object embedded
        # after diagnostic noise (some openclaw builds emit session
        # canonicalization messages before the JSON payload).
        embedded = _extract_embedded_json(stdout)
        if embedded is not None:
            extracted = _text_from_json(_try_parse_json(embedded))
            if extracted is not None:
                return extracted
        # Last resort: return the cleaned noise text so the judge sees
        # whatever non-JSON content was in stdout.
        return _strip_diagnostics(stdout)

    # Fallback: stderr.  Strip diagnostic noise and return what remains.
    cleaned_stderr = _strip_diagnostics(stderr)
    if not cleaned_stderr.strip():
        return "(no agent response — only diagnostic output)"
    return cleaned_stderr


def _try_parse_json(text: str) -> object | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_embedded_json(text: str) -> str | None:
    """Find the first top-level JSON object embedded in text.

    Scans for the first '{' that is the start of a balanced top-level
    object (string-aware), then returns the substring from there. Used
    to recover from openclaw builds that prepend non-JSON diagnostic
    lines to the JSON payload.
    """
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        in_str = False
        escape = False
        for j in range(i, len(text)):
            c = text[j]
            if in_str:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[i : j + 1]
                        if _try_parse_json(candidate) is not None:
                            return candidate
                        break
    return None


def _text_from_json(data: object) -> str | None:
    """Pull the concatenated payloads[].text out of an `openclaw agent --json` reply."""
    if not isinstance(data, dict):
        return None
    payloads = data.get("payloads")
    if isinstance(payloads, list) and payloads:
        texts = [p.get("text", "") for p in payloads if isinstance(p, dict)]
        joined = "\n".join(t for t in texts if t)
        if joined.strip():
            return joined
    # Some embedded-fallback responses nest under "result.payloads".
    result = data.get("result")
    if isinstance(result, dict):
        payloads = result.get("payloads")
        if isinstance(payloads, list) and payloads:
            texts = [p.get("text", "") for p in payloads if isinstance(p, dict)]
            joined = "\n".join(t for t in texts if t)
            if joined.strip():
                return joined
    return None


def main(bench_name: str, agent_id: str | None = None) -> int:
    """Run a benchmark. `agent_id` is the CI-side task caller; the contract forces
    this to `main`. The main agent decides how to handle each QA (including
    whether to delegate to sub-agents). The separate CI scoring path may call
    reviewer directly."""
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
        f"got agent_id={agent_id!r}."
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
            _debug_echo("qa_start", f"id={qa['qa_id']} judge={qa.get('judge')}")
            t0 = time.time()
            answer, session_key, raw = run_agent(container, agent_id, qa, run_id, model,
                                                  debug_dir=qa_debug_dir)
            elapsed = time.time() - t0
            mode = qa.get("judge", "rules")
            if raw.get("timed_out"):
                # Wall-clock cap fired. Skip scoring entirely and mark the QA
                # failed so the benchmark continues with the remaining tests
                # instead of stalling on a hung judge.
                verdict = {
                    "score": 0.0,
                    "pass": False,
                    "rationale": (
                        f"timed out after {elapsed:.0f}s (wall-clock cap); "
                        f"agent did not produce a reply within the budget"
                    ),
                }
            else:
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
                # Extract the full session transcript (main + all spawned sub-agents)
                # from the container. Best-effort: failures log a warning and continue.
                try:
                    _extract_qa_sessions(container, session_key, qa_debug_dir)
                except Exception as exc:
                    print(f"[sessions] warning: session extraction failed for "
                          f"{session_key}: {exc}", file=sys.stderr)
            _debug_echo("qa_done", f"id={qa['qa_id']} score={verdict.get('score', 0):.3f} "
                        f"pass={verdict.get('pass', False)} elapsed={elapsed:.1f}s "
                        f"returncode={raw.get('returncode')} timed_out={raw.get('timed_out')} "
                        f"stdout_bytes={len(raw.get('stdout', ''))} "
                        f"stderr_bytes={len(raw.get('stderr', ''))} "
                        f"agent_text_chars={len(answer or '')}")
            # Print summary line to stderr for quick scanning in CI logs.
            # Then emit the full agent answer inside a GitHub Actions log group
            # so it's fully visible without truncation.  `::group::` / `::endgroup::`
            # are rendered as collapsible sections by GitHub Actions.
            head = (answer or "").replace("\n", "\\n")[:200]
            print(f"  [{qa['qa_id']}] score={verdict.get('score', 0):.3f} "
                  f"pass={verdict.get('pass', False)} "
                  f"len(answer)={len(answer or '')} head={head!r}",
                  file=sys.stderr)
            group_title = (f"QA {qa['qa_id']} — agent reply "
                           f"(score={verdict.get('score', 0):.2f}, "
                           f"pass={verdict.get('pass', False)}, "
                           f"{len(answer or '')} chars)")
            print(f"::group::{group_title}")
            print(answer or "(no agent response)")
            # When the agent CLI fails (non-zero exit), surface raw stderr
            # so the CI logs show what went wrong instead of just the
            # stripped sentinel.
            if raw.get("returncode", 0) != 0 and raw.get("stderr", "").strip():
                print("")
                print("--- raw agent stderr (exit={}) ---".format(raw.get("returncode")))
                print(raw["stderr"].strip()[:8000])
            print("::endgroup::")
            result_entry = {
                "qa_id": qa["qa_id"], "task_type": qa.get("task_type"),
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
