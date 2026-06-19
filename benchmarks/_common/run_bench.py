#!/usr/bin/env python3
"""benchmarks/_common/run_bench.py

Generic driver for any benchmark directory that follows the unified interface
(env.sh + qa.jsonl + metrics.py).

**CI policy: every benchmark task calls only the `main` agent.** The main agent is
responsible for deciding how to handle each task, including delegating to the
appropriate sub-agent via `sessions_spawn` when needed.

Each QA uses the PRD three-step flow (deterministic, independent of how `main`
chooses to wait for its sub-agents):

  1. ``openclaw agent --message <QA>`` delivers the question. ``main`` is free to
     yield / spawn / sleep — we no longer append a sleep-wait suffix and no longer
     rely on the CLI staying blocked.
  2. A **watcher** polls ``openclaw tasks --json`` for the run's tasks:
       * any task ``timed_out``  → abort the whole benchmark immediately;
       * all tasks ``succeeded`` → the run is complete.
  3. ``openclaw logs --expect-final --json`` yields the agent's true final
     delivered answer; its ``message`` field is what we judge.

The CI scoring step (``judge: "agent"``) fires the dedicated ``judge`` agent as a
standalone ``openclaw agent --agent judge --local`` subprocess (separate from the
send→watch→logs flow — judges never spawn sub-agents) and parses its CLI reply
straight into a 0..1 score; see :func:`_run_judge`.

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
    from judge import judge_parse, judge_prompt, judge_with_rules, JudgeScoreParseError  # noqa: E402
else:
    from .judge import judge_parse, judge_prompt, judge_with_rules, JudgeScoreParseError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent


def _container_cli() -> str:
    """Return the container runtime CLI used for benchmark exec/cp calls."""
    cli = os.environ.get("BENCH_CONTAINER_CLI") or os.environ.get("BENCH_CONTAINER_RUNTIME") or "docker"
    return "docker" if cli == "auto" else cli


def _container_exec_cmd(container: str, *args: str, interactive: bool = False,
                        env: list[str] | None = None) -> list[str]:
    cmd = [_container_cli(), "exec"]
    if interactive:
        cmd.append("-i")
    for item in env or []:
        cmd.extend(["-e", item])
    cmd.append(container)
    cmd.extend(args)
    return cmd


def _container_cp_cmd(src: str, dst: str) -> list[str]:
    return [_container_cli(), "cp", src, dst]


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

_AGENT_IDS = ("main", "ingest", "curate", "extract", "critic",
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
            _container_exec_cmd(container, "cat", path),
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
            _container_exec_cmd(container, "test", "-f", candidate),
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
                    _container_cp_cmd(f"{container}:{src}", str(dst)),
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
            _container_exec_cmd(container, "sqlite3", "-readonly",
                                f"{_SESSION_MOUNT}/state/openclaw.sqlite", query),
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
                _container_cp_cmd(f"{container}:{src}", str(dst)),
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
                _container_cp_cmd(f"{container}:{src}", str(dst)),
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
                _container_cp_cmd(f"{container}:{main_src}", str(main_dst)),
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


# ---------------------------------------------------------------------------
# Answer-QA execution: send → watch tasks → collect final via logs (see PRD)
# ---------------------------------------------------------------------------
#
# The old single-phase synchronous approach appended a "sleep-wait" suffix to
# every QA so the `openclaw agent` CLI stayed blocked until every spawned
# sub-agent returned. That was fragile: when main yielded early
# (sessions_yield right after sessions_spawn) the CLI returned a short interim
# and the sub-agent deliverable never reached the judge.
#
# The PRD flow is deterministic regardless of how main waits:
#   1. `openclaw agent --message <QA>` delivers the question (no sleep suffix).
#   2. A watcher polls `openclaw tasks --json` — all-succeeded → done, any
#      timed_out → abort the benchmark.
#   3. `openclaw logs --expect-final --json` → its `message` is the final answer.
#
# The `judge` agent is called as its own standalone subprocess
# (`openclaw agent --agent judge --local`), decoupled from this send→watch→logs
# flow, with a number-only prompt whose reply is parsed straight into a score;
# see `_run_judge`.


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
for agent_id in main ingest curate extract critic design spec audit ideate judge reviewer; do
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
        _container_exec_cmd(container, "bash", "-lc", script,
                            env=[f"BENCH_MOUNT={mount}"]),
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


def _run_agent_once(container: str, agent_id: str, prompt: str, session_key: str,
                    model: str | None = None, timeout: int = 180,
                    debug_dir: Path | None = None, debug_prefix: str = "") -> dict:
    """One synchronous ``openclaw agent`` call via the gateway.

    Routed through the gateway (NOT ``--local`` embedded) so the run is tracked
    as a durable task: the PRD task-watcher in :func:`run_agent` polls
    ``openclaw tasks`` for it, and ``openclaw logs --expect-final`` can read its
    final answer. Embedded ``--local`` runs do not register tasks, which would
    leave the watcher with nothing to observe.

    Blocks until the agent's turn ends, so a single-turn agent (e.g. ``judge``)
    returns its reply directly in the CLI stdout. For the answer QA, main may end
    its turn early (before spawned sub-agents finish); the watcher +
    ``logs --expect-final`` handle that. Bounded by ``timeout`` (passed to
    openclaw as ``--timeout``) plus a 30s subprocess grace; a hung agent is
    killed and flagged ``timed_out`` so the run continues.
    """
    cmd = _container_exec_cmd(
        container, "openclaw", "agent",
        "--agent", agent_id, "--message", prompt, "--json",
        "--session-key", session_key,
        "--timeout", str(timeout),
        interactive=True,
        env=["LLM_API_KEY", "LLM_BASE_URL"],
    )
    # NOTE: we deliberately do NOT pass --model here. env_setup.sh patches the
    # gateway's configured default model to LLM_MODEL, so the agent already runs
    # on the intended model. Passing --model makes the gateway treat it as a
    # per-call *override*, which it gates behind the agent's model allow-list —
    # and that check is flaky ("Model override ... is not allowed for agent
    # main"). Embedded --local used to bypass it; gateway mode does not.
    _ = model  # accepted for API stability; the gateway default is used instead.
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
        stdout, stderr = proc.stdout or "", proc.stderr or ""
        returncode = proc.returncode
    except subprocess.TimeoutExpired as e:
        print(f"[agent] {session_key}: wall-clock cap hit after {timeout + 30}s; "
              f"killing docker exec", file=sys.stderr)
        try:
            subprocess.run(_container_exec_cmd(container, "pkill", "-f", "openclaw agent"),
                           capture_output=True, timeout=10)
        except Exception:
            pass
        stdout = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
        stderr = e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")
        returncode = -1
        timed_out = True
    if debug_dir is not None:
        _debug_write(debug_dir / f"{debug_prefix}01_cmd.json",
                     json.dumps(cmd, ensure_ascii=False, indent=2))
        _debug_write(debug_dir / f"{debug_prefix}02_stdout.txt", stdout)
        _debug_write(debug_dir / f"{debug_prefix}03_stderr.txt", stderr)
    return {"cmd": cmd, "stdout": stdout, "stderr": stderr,
            "returncode": returncode, "timed_out": timed_out,
            "session_key": session_key}


def _build_qa_prompt(qa: dict) -> str:
    """Build the prompt for a QA (material prefix + question). No sleep suffix."""
    prompt = qa["question"]
    if qa.get("input_material"):
        material = qa["input_material"]
        if isinstance(material, dict):
            material = material.get("content") or Path(material["path"]).read_text(encoding="utf-8")
        prompt = f"{material}\n\n---\n\n{prompt}"
    return prompt


# Terminal task statuses in the openclaw task store.
_TERMINAL_STATUSES = ("succeeded", "failed", "timed_out", "cancelled", "lost")

# Seconds between task-store polls while watching a run.
_POLL_INTERVAL = 5


class BenchmarkTimedOut(Exception):
    """A task in the watched run hit ``timed_out`` — abort the whole benchmark."""


def _openclaw_json(container: str, args: list[str], timeout: int = 30) -> object | None:
    """Run ``openclaw <args>`` in *container* and parse its JSON stdout.

    Returns the parsed object, or None on failure (non-zero / unparseable / error).
    """
    cmd = _container_exec_cmd(container, "openclaw", *args, interactive=True)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[tasks] openclaw {' '.join(args)} failed: {exc}", file=sys.stderr)
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        if proc.stderr.strip():
            print(f"[tasks] openclaw {' '.join(args)} stderr: {proc.stderr.strip()[:300]}",
                  file=sys.stderr)
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _snapshot_run_ids(container: str) -> set[str]:
    """Return every runId currently in the task store."""
    data = _openclaw_json(container, ["tasks", "--json"])
    if not isinstance(data, dict):
        return set()
    return {t.get("runId") for t in data.get("tasks", []) if t.get("runId")}


def _discover_run_id(container: str, before: set[str]) -> str | None:
    """Return the runId created since *before* (the QA we just sent).

    In a sequential benchmark the only new run is ours; if several appear we
    pick the first. Returns None if discovery fails (caller degrades to a
    logs-only wait).
    """
    data = _openclaw_json(container, ["tasks", "--json"])
    if not isinstance(data, dict):
        return None
    for task in data.get("tasks", []):
        rid = task.get("runId")
        if rid and rid not in before:
            return rid
    return None


def _run_task_statuses(container: str, run_id: str) -> list[str]:
    """Status of every task belonging to *run_id* (empty if unknown)."""
    data = _openclaw_json(container, ["tasks", "--json"])
    if not isinstance(data, dict):
        return []
    return [t.get("status", "") for t in data.get("tasks", [])
            if t.get("runId") == run_id]


# Console-output patterns that look like a top-level log line (type=log, no
# subsystem) but are NOT the agent's reply — they're emitted by the openclaw
# CLI/runtime via console.log and end up in the file-log tail alongside real
# agent output. The "last non-subsystem log line" heuristic gets fooled by
# whichever of these happens to land at the bottom of the 250 KB tail window;
# in CI run 27686228379/job 81885739532, QA-006 picked up
# "Registered plugin command: /voice (plugin: talk-voice)" instead of the
# 4253-char idea-cards reply that came earlier.
_LOG_NOISE_PREFIXES = (
    "Registered plugin command:",  # plugin manifest registration on CLI boot
    "[tools] read failed",         # filesystem-tool diagnostic
    "tools: read failed",          # same diagnostic, alternative format
    "[plugins] ",                  # generic plugin lifecycle messages
    "[context-engine] ",           # context-engine plugin diagnostics
)


def _is_log_noise(message: str) -> bool:
    """True if *message* matches a known non-agent-reply console.log noise pattern.

    Used by :func:`_extract_final_from_logs` to skip CLI/plugin diagnostics
    that share the same JSON shape as a real agent reply (``type=log``, no
    ``subsystem``) but are not the agent's final answer.
    """
    stripped = message.lstrip()
    return any(stripped.startswith(p) for p in _LOG_NOISE_PREFIXES)


def _extract_final_from_logs(stdout: str) -> str:
    """Pull the agent's final answer out of ``openclaw logs --json`` stdout.

    The stream interleaves the real reply with gateway internals and CLI
    console output:

      * ``{"type":"log", "subsystem":"gateway/ws", "message":"{\\"subsystem\\":...} ..."}``
        — gateway/websocket diagnostics (the bulk of the output);
      * ``{"type":"meta", ...}``  — a header line (file/cursor/size);
      * ``{"type":"notice", "message":"Log tail truncated (increase --max-bytes)."}``
        — appended when the tail exceeded ``--max-bytes``.
      * ``{"type":"log", ...}`` with no ``subsystem`` and a ``console.log``
        ``method`` — the agent's textual reply, but ALSO the CLI's plugin
        registration banner ("Registered plugin command: /pair …") and a
        handful of tool-failure diagnostics that share the same shape.

    The agent's actual reply is the **last** ``type == "log"`` line that
    carries no ``subsystem`` and does not match any of the
    :data:`_LOG_NOISE_PREFIXES` — those are CLI/plugin console output that
    happens to look like agent text. Returns "" if no usable line is found.
    """
    last = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") != "log":
            continue
        if "subsystem" in evt:  # gateway internal (gateway/ws, plugins, …)
            continue
        msg = evt.get("message")
        if not isinstance(msg, str) or not msg.strip():
            continue
        if _is_log_noise(msg):
            continue
        last = msg
    return last


def _collect_final_via_logs(container: str, timeout_ms: int = 120_000,
                            debug_dir: Path | None = None) -> str:
    """Read the agent's final delivered answer via ``openclaw logs --expect-final``.

    Called after the task watcher confirms the run completed (PRD step 3).
    ``--expect-final`` waits for the agent's final response; we then parse the
    emitted JSON log lines with :func:`_extract_final_from_logs` to recover the
    real reply (skipping gateway/websocket noise and the truncation footer).
    Uses the gateway's default ``--limit`` / ``--max-bytes`` — passing values
    above the gateway schema cap makes the call fail outright. Returns "" if
    nothing is captured.
    """
    cmd = _container_exec_cmd(container, "openclaw", "logs",
                              "--expect-final", "--json",
                              "--timeout", str(timeout_ms))
    try:
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True,
                              timeout=timeout_ms / 1000 + 30)
    except subprocess.TimeoutExpired:
        print("[logs] openclaw logs --expect-final hung; returning empty", file=sys.stderr)
        return ""
    if debug_dir is not None:
        _debug_write(debug_dir / "l_01_logs_stdout.txt", proc.stdout or "")
        _debug_write(debug_dir / "l_02_logs_stderr.txt", proc.stderr or "")
    return _extract_final_from_logs(proc.stdout or "")


def run_agent(container: str, agent_id: str, qa: dict, run_id: str,
              model: str | None, debug_dir: Path | None = None) -> tuple[str, str, dict]:
    """Run one benchmark QA via the PRD send→watch→logs flow.

    1. Snapshot existing run ids, then deliver the QA with ``openclaw agent``
       (no sleep suffix); main may yield early — that is fine.
    2. Discover the run id created by this QA.
    3. **Watcher** — poll ``openclaw tasks --json`` for the run's task statuses:
         * any task terminal-but-not-succeeded (``timed_out`` / ``cancelled`` /
           ``failed`` / ``lost``) → abort the whole benchmark;
         * every task ``succeeded`` → the run is complete;
         * otherwise (``running`` / ``queued`` / …) → keep waiting.
       There is no wall-clock bailout for a run that is still progressing: we
       wait until it reaches ``all-succeeded`` or a terminal failure. The only
       abort here besides a terminal failure is when NO task is ever visible for
       the run (task store unreachable / discovery failed) for a grace period.
    4. ``openclaw logs --expect-final --json`` → :func:`_extract_final_from_logs`
       recovers the agent's final reply (the last ``type:"log"`` line with no
       ``subsystem``, skipping gateway/ws noise + the truncation footer).

    Returns ``(answer, session_key, raw)``. Raises :class:`BenchmarkTimedOut`
    if any task in the run ends in a terminal failure, the synchronous *send*
    itself hangs past budget, or ``logs --expect-final`` fails to produce a
    final answer (any of these aborts the whole benchmark — there is no
    fallback to the synchronous send's interim payload).
    """
    prompt = _build_qa_prompt(qa)
    # Unique key per QA attempt so every run starts from an empty conversation.
    session_key = f"agent:{agent_id}:bench-{run_id}-{qa['qa_id']}-{uuid.uuid4().hex}"
    timeout = int(qa.get("timeout_seconds", 180))
    if debug_dir is not None:
        _debug_write(debug_dir / "00_prompt.txt", prompt)

    # 1. snapshot run ids, then deliver the QA.
    before_ids = _snapshot_run_ids(container)
    res = _run_agent_once(container, agent_id, prompt, session_key, model,
                          timeout=timeout, debug_dir=debug_dir, debug_prefix="s_")

    # 2. identify the run created by this QA.
    run_id_found = _discover_run_id(container, before_ids)
    if debug_dir is not None:
        _debug_write(debug_dir / "s_06_run_id.txt", run_id_found or "(not found)")

    # 3. watcher: wait for all-succeeded, or abort on timed_out / cancelled.
    #    A hung synchronous send is itself a benchmark abort — we cannot trust
    #    that the run will ever complete, and we must not silently fall through
    #    to whatever partial text the CLI managed to print.
    # Any terminal non-success status (timed_out/cancelled/failed/lost) aborts
    # the benchmark: the spec lists timed_out/cancelled; failed/lost are the
    # same category (terminal failure that will never reach all-succeeded) and
    # must be treated identically or the watcher would hang forever on them.
    _FAIL_STATUSES = ("timed_out", "cancelled", "failed", "lost")
    if res.get("timed_out"):
        raise BenchmarkTimedOut(
            f"QA {qa.get('qa_id')}: synchronous send hung past "
            f"{timeout}s budget (run {run_id_found or '?'})")
    rid = run_id_found
    no_status_streak = 0
    # Polls with no visible task before we conclude the store is unreachable.
    grace_polls = max(1, 120 // max(1, _POLL_INTERVAL))
    while True:
        if rid is None:
            rid = _discover_run_id(container, before_ids)  # may register late
        statuses = _run_task_statuses(container, rid) if rid else []
        if statuses:
            no_status_streak = 0
            if any(s in _FAIL_STATUSES for s in statuses):
                bad = sorted({s for s in statuses if s in _FAIL_STATUSES})
                raise BenchmarkTimedOut(
                    f"QA {qa.get('qa_id')} run {rid or '?'}: "
                    f"a task hit {bad}")
            if all(s == "succeeded" for s in statuses):
                break
        else:
            no_status_streak += 1
            if no_status_streak >= grace_polls:
                raise BenchmarkTimedOut(
                    f"QA {qa.get('qa_id')}: no tasks visible for run "
                    f"{rid or '?'} after {grace_polls * _POLL_INTERVAL}s — "
                    f"task store unreachable or run id not found")
        time.sleep(_POLL_INTERVAL)

    # 4. read the final answer from logs --expect-final (last JSON object).
    #    Empty answer here is a hard abort: the contract is that every
    #    succeeded run produces a final-message log line, so an empty result
    #    means either logs.tail failed (e.g. invalid params) or the run did
    #    not actually deliver a final answer. Either way we must NOT silently
    #    substitute the synchronous send's interim payload — that just hides
    #    a real failure behind whatever stub the agent yielded mid-flight.
    answer = _collect_final_via_logs(container, timeout_ms=120_000, debug_dir=debug_dir)
    if not answer:
        raise BenchmarkTimedOut(
            f"QA {qa.get('qa_id')} run {run_id_found or '?'}: "
            f"openclaw logs --expect-final returned no agent reply "
            f"(see l_01_logs_stdout.txt / l_02_logs_stderr.txt)")

    if debug_dir is not None:
        _debug_write(debug_dir / "04_agent_text.txt", answer)
        _debug_write(debug_dir / "05_meta.json", json.dumps({
            "qa_id": qa.get("qa_id"), "session_key": session_key,
            "run_id_found": run_id_found,
            "returncode": res["returncode"], "send_timed_out": res["timed_out"],
            "answer_chars": len(answer),
        }, ensure_ascii=False, indent=2))

    raw = {**res, "prompt": prompt, "agent_text": answer,
           "run_id": run_id_found}
    return (answer, session_key, raw)


# A working judge turn returns a bare 0..1 score in ~8s. The old 600s ceiling was
# the "agent as judge" timeout point — a single score should never need 10 min, so
# bound it hard. (Observed in CI run 27690800218: agent-judge calls that succeed
# finish in seconds; the 600s cap only ever masked a hung/flaky judge.)
_JUDGE_TIMEOUT = 180


def _run_judge(container: str, qa: dict, answer: str, run_id: str,
               model: str | None, debug_dir: Path | None = None) -> dict:
    """LLM-judge a candidate *answer* with a standalone, direct call to ``judge``.

    Deliberately decoupled from the main-QA machinery: this does **not** reuse
    :func:`_run_agent_once` (gateway-routed, task-tracked, watched). The judge is
    a single-turn scoring call, so it is fired as its own subprocess —
    ``openclaw agent --agent judge --message <judge_prompt> --local`` — and the
    CLI's reply is parsed straight into a 0..1 number.

    Why ``--local`` (embedded) and not the gateway: embedded mode skips gateway
    task registration and the watcher entirely, which is exactly right for a
    judge that never spawns sub-agents. It also keeps the judge off the gateway's
    session/heartbeat path that intermittently made it answer ``HEARTBEAT_OK``
    instead of scoring (CI 27690800218, paper-review-1/s3-cherrypick).

    The prompt mandates a bare numeric score, so the reply is parsed directly as
    a number (:func:`judge.judge_parse`, ``strict=True``). A non-numeric reply —
    or a timeout / CLI failure — raises :class:`judge.JudgeScoreParseError`, which
    the caller records as score 0 rather than silently degrading to rule scoring.
    """
    prompt = judge_prompt(qa, answer)
    session_key = (f"agent:judge:bench-judge-{run_id}-{qa['qa_id']}-"
                   f"{uuid.uuid4().hex}")
    cmd = _container_exec_cmd(
        container, "openclaw", "agent",
        "--agent", "judge", "--message", prompt,
        "--json", "--local",
        "--session-key", session_key,
        "--timeout", str(_JUDGE_TIMEOUT),
        interactive=True,
        env=["LLM_API_KEY", "LLM_BASE_URL"],
    )
    # NOTE: we deliberately do NOT pass --model. The judge runs on the configured
    # default model (LLM_MODEL); a per-call --model override is gated behind the
    # agent model allow-list and is flaky, so leave it off.
    _ = model  # accepted for API symmetry with run_agent; unused.
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=_JUDGE_TIMEOUT + 30)
        stdout, stderr = proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        raise JudgeScoreParseError(
            f"judge agent timed out after {_JUDGE_TIMEOUT}s (run {run_id})")
    if debug_dir is not None:
        _debug_write(debug_dir / "j_01_cmd.json",
                     json.dumps(cmd, ensure_ascii=False, indent=2))
        _debug_write(debug_dir / "j_02_stdout.txt", stdout)
        _debug_write(debug_dir / "j_03_stderr.txt", stderr)
    # The prompt forces a bare number; pull the agent text out of the --json
    # reply and parse it directly as the score.
    text = _extract_agent_text(stdout, stderr)
    if debug_dir is not None:
        _debug_write(debug_dir / "j_04_judge_text.txt", text)
    return judge_parse(text, qa, answer, strict=True)


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
    this to `main`. Each QA uses the PRD send→watch→logs flow: the QA is sent to
    `main` (which may spawn sub-agents internally), a watcher polls
    `openclaw tasks` until the run is complete or any task hits `timed_out`, and
    the final answer is read from `openclaw logs --expect-final`. If any task in a
    run is `timed_out` the benchmark aborts immediately (partial report written).
    The `judge: "agent"` scoring step uses the dedicated `judge` agent via one
    synchronous call."""
    qa_path = Path(os.environ.get("BENCH_QA_PATH", ROOT / "benchmarks" / bench_name / "qa.jsonl"))
    report_path = Path(os.environ.get("BENCH_REPORT_PATH",
                                       ROOT / "benchmarks" / bench_name / "bench-report.json"))
    container = os.environ.get("BENCH_CONTAINER", "")
    run_id = os.environ.get("BENCH_RUN_ID", f"local-{int(time.time())}")
    model = os.environ.get("LLM_MODEL") or os.environ.get("BENCH_MODEL")
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
        aborted: str | None = None
        _debug_banner(bench_name)
        for qa in qas:
            qa_debug_dir = _debug_dir(bench_name, qa["qa_id"])
            _debug_echo("qa_start", f"id={qa['qa_id']} judge={qa.get('judge')}")
            t0 = time.time()
            try:
                answer, session_key, raw = run_agent(container, agent_id, qa, run_id, model,
                                                      debug_dir=qa_debug_dir)
            except BenchmarkTimedOut as exc:
                # PRD: any task `timed_out` → abort the whole benchmark. Record
                # this QA as failed, write the partial report, and stop.
                elapsed = time.time() - t0
                print(f"[{bench_name}] ABORT (timed_out): {exc} — "
                      f"stopping benchmark per PRD.", file=sys.stderr)
                results.append({
                    "qa_id": qa["qa_id"], "task_type": qa.get("task_type"),
                    "weight": qa.get("weight", 1.0), "score": 0.0, "pass": False,
                    "rationale": f"aborted: a task hit timed_out ({exc})",
                    "elapsed_seconds": round(elapsed, 1),
                    "session_key": "", "raw_output": "",
                })
                aborted = "timed_out"
                break
            elapsed = time.time() - t0
            mode = qa.get("judge", "rules")
            if mode == "agent":
                # Direct synchronous call to the dedicated `judge` agent; the
                # number-only prompt + strict parse raises JudgeScoreParseError
                # on any non-numeric reply. Surface that as an explicit failed
                # QA (score 0) rather than silently degrading to rule scoring.
                try:
                    verdict = _run_judge(container, qa, answer, run_id, model,
                                         debug_dir=qa_debug_dir)
                except JudgeScoreParseError as jexc:
                    verdict = {
                        "score": 0.0,
                        "pass": False,
                        "rationale": f"judge did not return a numeric score: {jexc}",
                    }
            else:
                verdict = judge_with_rules(answer, qa)
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
        if aborted:
            report["aborted"] = aborted
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
