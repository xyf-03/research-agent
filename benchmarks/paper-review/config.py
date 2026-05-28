"""
Benchmark shared configuration for paper-review agent testing.

- Auto-detect openclaw.cmd path
- run_agent() with --local mode (no gateway dependency)
- UTF-8 subprocess handling for Windows
- DeepSeek API with key auto-detection from auth-profiles.json
"""

import json
import os
import shutil
import subprocess
import time
from typing import Optional, Union

import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
BENCHMARK_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCHMARK_DIR.parent.parent                # repo root
RESULTS_DIR = BENCHMARK_DIR / "results"
SEED_FILE = BENCHMARK_DIR / "seed_qa.json"
FULL_BENCHMARK_FILE = BENCHMARK_DIR / "full_benchmark.json"

AGENT_ID = "paper-review"

# ── openclaw CLI detection ──────────────────────────────────────────
def _find_openclaw_exe() -> str:
    for name in ["openclaw.cmd", "openclaw"]:
        found = shutil.which(name)
        if found:
            return found

    candidates = [
        r"E:\npm-global\openclaw.cmd",
        os.path.expandvars(r"%APPDATA%\npm\openclaw.cmd"),
    ]
    for path in candidates:
        if path and Path(path).exists():
            return path

    raise FileNotFoundError(
        "Cannot find openclaw executable. Set OPENCLAW_EXE env variable."
    )

OPENCLAW_EXE = os.environ.get("OPENCLAW_EXE") or _find_openclaw_exe()
print(f"[config] openclaw: {OPENCLAW_EXE}")

# ── Agent invocation ────────────────────────────────────────────────
def run_agent(
    message: str = "",
    session_id: Optional[str] = None,
    timeout: int = 300,
) -> dict:
    """Run paper-review agent in --local mode. Returns {success, stdout, stderr, rc, session_id, elapsed_ms}."""
    if session_id is None:
        import uuid
        session_id = f"bench-{uuid.uuid4().hex[:8]}"

    cmd = [
        "cmd", "/c", OPENCLAW_EXE,
        "agent", "--local",
        "--agent", AGENT_ID,
        "--session-id", session_id,
        "--json",
        "--message", message,
    ]

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": f"Timeout {timeout}s",
                "rc": -1, "session_id": session_id,
                "elapsed_ms": int(timeout * 1000), "error": "timeout"}

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    stdout = proc.stdout.strip() if proc.stdout else ""
    stderr = proc.stderr.strip() if proc.stderr else ""

    ok = proc.returncode == 0
    if not ok and stdout:
        try:
            json.loads(stdout)
            ok = True
        except json.JSONDecodeError:
            pass

    return {"success": ok, "stdout": stdout, "stderr": stderr,
            "rc": proc.returncode, "session_id": session_id, "elapsed_ms": elapsed_ms}


# ── DeepSeek API ────────────────────────────────────────────────────
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

def _find_deepseek_key() -> str:
    env_key = os.environ.get("DEEPSEEK_API_KEY")
    if env_key:
        return env_key

    auth_files = [
        Path(r"E:\openclaw-data\.openclaw\agents\main\agent\auth-profiles.json"),
        REPO_ROOT / "auth-profiles.json",
    ]
    for af in auth_files:
        if af.exists():
            try:
                data = json.loads(af.read_text(encoding="utf-8"))
                for pid, profile in data.get("profiles", {}).items():
                    if "deepseek" in pid.lower():
                        key = profile.get("key", "")
                        if key:
                            return key
            except Exception:
                pass

    raise RuntimeError("Cannot find DeepSeek API key. Set DEEPSEEK_API_KEY or add to auth-profiles.json.")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or _find_deepseek_key()
print("[config] DeepSeek key: found")

def chat_llm(system: str, user: str, model: str = DEEPSEEK_MODEL, timeout: int = 120, max_tokens: int = 4096) -> str:
    resp = requests.post(DEEPSEEK_API_URL,
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": model,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}],
              "temperature": 0.1, "max_tokens": max_tokens},
        timeout=timeout)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ── JSON helpers ────────────────────────────────────────────────────
def load_json(path: Path) -> Union[dict, list]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run_id() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y%m%d-%H%M%S")


# ── Benchmark helpers ───────────────────────────────────────────────
def load_seed_qa() -> list:
    return load_json(SEED_FILE)

def load_full_benchmark() -> list:
    return load_json(FULL_BENCHMARK_FILE)

def load_test_cases() -> list:
    """Prefer full benchmark, fall back to seed."""
    if FULL_BENCHMARK_FILE.exists():
        return load_full_benchmark()
    return load_seed_qa()

CAPABILITY_TO_SKILL = {
    "wiki-extraction": "wiki-organizer",
    "experiment-extraction": "experiment-extractor",
    "problem-analysis": "problem-analyzer",
    "validation-design": "validation-designer",
    "codex-generation": "codex-prompt-generator",
    "missing-info": "wiki-organizer",
    "stage-boundary": "experiment-extractor",
    "fact-inference-distinction": "problem-analyzer",
}


def find_test_case(test_id: str) -> Optional[dict]:
    """Find a test case by ID across seed and full benchmark files."""
    for f in [SEED_FILE, FULL_BENCHMARK_FILE]:
        if f.exists():
            for tc in load_json(f):
                if tc["id"] == test_id:
                    return tc
    return None
