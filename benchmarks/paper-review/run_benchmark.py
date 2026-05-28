#!/usr/bin/env python3
"""
Benchmark runner for paper-review agent.

Usage:
  python run_benchmark.py              Run all test cases
  python run_benchmark.py --no-skip    Re-run even if output exists
  python run_benchmark.py --start-from seed-003  Resume from specific test

Workflow:
  run_tests() -> Feed each QA to agent, save to results/<test_id>/
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional
from config import (
    load_seed_qa, load_full_benchmark, save_json, load_json,
    run_agent, run_id,
    RESULTS_DIR, BENCHMARK_DIR,
    SEED_FILE, FULL_BENCHMARK_FILE, WORKSPACE_DIR,
)


# ── Output file collection ────────────────────────────────────────────
def _collect_output_files(run_dir: Path) -> str:
    """Find markdown files the agent created in benchmark/ subdirectories.
    Reads files created/modified in the last 10 minutes under benchmark/wiki/
    and other subdirs, excluding system dirs like results/ and materials/."""
    import time as _time
    now = _time.time()
    cutoff = now - 600  # last 10 minutes
    exclude_dirs = {"results", "materials", "__pycache__", ".git"}

    collected = []
    for root, dirs, files in os.walk(str(BENCHMARK_DIR)):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        basename = os.path.basename(root)
        if basename in exclude_dirs:
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


# ── Pipeline stages ─────────────────────────────────────────────────

def run_tests(skip_existing: bool = True, start_from: Optional[str] = None) -> str:
    """Run all test cases, saving agent outputs. Returns run_id."""
    if FULL_BENCHMARK_FILE.exists():
        test_cases = load_full_benchmark()
        print(f"Using full benchmark: {len(test_cases)} cases")
    else:
        test_cases = load_seed_qa()
        print(f"Using seed benchmark: {len(test_cases)} cases")

    rid = run_id()
    print(f"Run ID: {rid}")

    results = []
    started = (start_from is None)

    for i, tc in enumerate(test_cases):
        test_id = tc["id"]

        if not started:
            if test_id == start_from:
                started = True
            else:
                print(f"  [{i+1}/{len(test_cases)}] {test_id} — SKIP (before start_from)")
                continue

        run_dir = RESULTS_DIR / test_id
        raw_path = run_dir / "raw_output.json"

        if skip_existing and raw_path.exists():
            print(f"  [{i+1}/{len(test_cases)}] {test_id} — SKIP (exists)")
            results.append({"test_id": test_id, "run_id": rid, "test_case": tc})
            continue

        print(f"  [{i+1}/{len(test_cases)}] {test_id}: {tc['title'][:60]}",
              end=" ", flush=True)

        message = f"{tc.get('input_material', '')}\n\n---\n\n{tc.get('question', '')}"
        result = run_agent(message=message, timeout=300)
        status = "OK" if result["success"] else "FAIL"
        print(f"{status} ({result['elapsed_ms']}ms)")

        # Collect agent file outputs — agent saves results to files in benchmark/
        file_outputs = _collect_output_files(run_dir)
        stdout = result.get("stdout", "")
        full_output = stdout
        if file_outputs:
            full_output += "\n\n--- AGENT FILE OUTPUTS ---\n" + file_outputs

        raw_output = {
            "test_id": test_id, "run_id": rid,
            "timestamp": run_id(), "test_case": tc,
            "message": message, "result": result,
            "file_outputs_collected": bool(file_outputs),
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        save_json(raw_output, raw_path)
        (run_dir / "agent_output.txt").write_text(full_output, encoding="utf-8")
        results.append(raw_output)
        time.sleep(2)

    save_json({"run_id": rid, "count": len(results),
               "ids": [r["test_id"] for r in results]},
              RESULTS_DIR / f"run_index_{rid}.json")
    print(f"\nDone. {len(results)} tests. Results in {RESULTS_DIR}")
    return rid


# ── CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Paper-Review Agent Benchmark Runner")
    parser.add_argument("--no-skip", action="store_true", help="Re-run even if output exists")
    parser.add_argument("--start-from", type=str, help="Start from specific test ID")
    args = parser.parse_args()

    run_tests(skip_existing=not args.no_skip, start_from=args.start_from)
