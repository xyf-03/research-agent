#!/usr/bin/env python3
"""Unit tests for the agent-judge path in run_bench.py / judge.py.

Covers the fix for the "agent as judge" timeout/flakiness found in CI run
27690800218: the judge is now a standalone ``openclaw agent --agent judge --local``
subprocess (decoupled from the main-QA send→watch→logs machinery) whose CLI reply
is parsed straight into a 0..1 number, bounded by ``_JUDGE_TIMEOUT``.

These exercise the pure parsing helpers (no container, no subprocess), so they
run anywhere.
Run: ``python3 -m pytest benchmarks/_common/test_run_bench.py`` (or directly).
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import judge  # noqa: E402
from run_bench import _JUDGE_TIMEOUT  # noqa: E402


# --- judge score parsing (the direct "parse CLI return as number" path) -----

def test_parse_bare_decimal():
    assert judge._parse_judge_score("0.42") == 0.42


def test_parse_json_score():
    assert judge._parse_judge_score('{"score": 0.8}') == 0.8


def test_parse_integer_score():
    assert judge._parse_judge_score("1") == 1.0
    assert judge._parse_judge_score("0") == 0.0


def test_parse_empty_returns_none():
    # Empty reply / heartbeat ack → no number → caller raises JudgeScoreParseError.
    assert judge._parse_judge_score("") is None
    assert judge._parse_judge_score("HEARTBEAT_OK") is None


def test_parse_clamps_to_unit_interval():
    qa = {"pass_threshold": 0.5}
    v = judge.judge_parse("0.9", qa, "answer", strict=True)
    assert v["score"] == 0.9 and v["pass"] is True
    v = judge.judge_parse("1.0", qa, "answer", strict=True)
    assert v["score"] == 1.0


def test_strict_parse_raises_on_non_numeric():
    qa = {"pass_threshold": 0.5}
    try:
        judge.judge_parse("not a number", qa, "answer", strict=True)
    except judge.JudgeScoreParseError:
        return
    raise AssertionError("expected JudgeScoreParseError")


def test_strict_parse_raises_on_heartbeat_ack():
    # The flaky reply observed in CI (paper-review-1/s3-cherrypick). A standalone
    # judge call surfaces it as a score-0 QA via JudgeScoreParseError rather than
    # silently degrading.
    qa = {"pass_threshold": 0.5}
    try:
        judge.judge_parse("HEARTBEAT_OK", qa, "answer", strict=True)
    except judge.JudgeScoreParseError:
        return
    raise AssertionError("expected JudgeScoreParseError")


# --- timeout bound ----------------------------------------------------------

def test_judge_timeout_is_bounded():
    # Regression guard: the agent-judge ceiling was 600s (the "timeout" point).
    # It must now be a sane sub-10-minute bound.
    assert _JUDGE_TIMEOUT <= 300, _JUDGE_TIMEOUT


if __name__ == "__main__":
    # Allow ``python3 test_run_bench.py`` without pytest.
    import traceback
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception:
                failures += 1
                print(f"FAIL  {name}")
                traceback.print_exc()
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)



if __name__ == "__main__":
    # Allow ``python3 test_run_bench.py`` without pytest.
    import traceback
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception:
                failures += 1
                print(f"FAIL  {name}")
                traceback.print_exc()
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
