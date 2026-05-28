#!/usr/bin/env python3
"""
Run a single benchmark test case by ID.

Usage: python run_single.py <test-id>
       python run_single.py seed-002
       python run_single.py seed-002 --timeout 600
"""

import json
import os
import sys
from pathlib import Path
from config import (
    run_agent, save_json, find_test_case,
    RESULTS_DIR, BENCHMARK_DIR, WORKSPACE_DIR, run_id,
)


def _collect_output_files() -> str:
    """Find markdown files the agent created in benchmark/ subdirectories."""
    import time as _time
    now = _time.time()
    cutoff = now - 600
    exclude_dirs = {"results", "materials", "__pycache__", ".git"}
    collected = []
    for root, dirs, files in os.walk(str(BENCHMARK_DIR)):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        if os.path.basename(root) in exclude_dirs:
            continue
        for f in files:
            if f.endswith(".md"):
                fpath = Path(root) / f
                try:
                    mtime = os.path.getmtime(str(fpath))
                    if mtime >= cutoff:
                        content = fpath.read_text(encoding="utf-8")
                        rel = fpath.relative_to(WORKSPACE_DIR)
                        collected.append(f"[FILE: {rel}]\n{content}")
                except Exception:
                    pass
    return "\n\n".join(collected)


def run_single(test_id: str, timeout: int = 300):
    tc = find_test_case(test_id)
    if tc is None:
        print(f"ERROR: Test case '{test_id}' not found")
        sys.exit(1)

    print(f"Running: [{tc['id']}] {tc['title']}")
    print(f"  Skill: {tc.get('skill')}")
    print(f"  Capability: {tc.get('capability')}\n")

    message = f"{tc.get('input_material', '')}\n\n---\n\n{tc.get('question', '')}"
    print(f"Message ({len(message)} chars):\n{message[:300]}...\n")

    result = run_agent(message=message, timeout=timeout)

    run_dir = RESULTS_DIR / test_id
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_output = {
        "test_id": test_id,
        "timestamp": run_id(),
        "test_case": tc,
        "message": message,
        "result": result,
    }
    save_json(raw_output, run_dir / "raw_output.json")

    # Collect agent file outputs + stdout for judging
    stdout = result.get("stdout", "")
    file_outputs = _collect_output_files()
    full_output = stdout
    if file_outputs:
        full_output += "\n\n--- AGENT FILE OUTPUTS ---\n" + file_outputs
    (run_dir / "agent_output.txt").write_text(full_output, encoding="utf-8")

    print(f"{'='*60}")
    print(f"Session: {result['session_id']}")
    print(f"Success:  {result['success']}")
    print(f"Elapsed:  {result['elapsed_ms']}ms")
    print(f"RC:       {result['rc']}\n")

    stdout = result.get("stdout", "")
    if stdout:
        print("--- Agent stdout ---")
        try:
            print(json.dumps(json.loads(stdout), ensure_ascii=False, indent=2))
        except (json.JSONDecodeError, UnicodeEncodeError):
            # Truncate to avoid terminal encoding issues (esp. Windows GBK)
            try:
                print(stdout[:4000])
            except UnicodeEncodeError:
                print(stdout.encode("ascii", errors="replace").decode("ascii")[:4000])
    else:
        print("(no stdout)")

    if result.get("stderr"):
        print(f"\n--- Agent stderr ---\n{result['stderr'][:2000]}")

    print(f"\nOutput saved to: {run_dir}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run single benchmark test")
    parser.add_argument("test_id", help="Test case ID (e.g. seed-002)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")
    args = parser.parse_args()
    run_single(args.test_id, timeout=args.timeout)
