# benchmarks/_common

Shared CI/CD infrastructure for all benchmarks under `benchmarks/`.

## Files

| File | Purpose |
| --- | --- |
| `qa_schema.json` | JSON Schema for `qa.jsonl` (one QA per line). |
| `env_setup.sh` | Unified pre-benchmark env: pull `acautomata/openclaw-docker-cn-im` image, `docker compose up`, rsync the repo into the container, run health check. |
| `run_local_benchmark.sh` | Local single-benchmark runner. Boots the CI-like container env, runs one `env.sh` + `metrics.py`, and supports Docker or Apple's `container` CLI. |
| `judge.py` | Reusable scoring library: `judge_with_rules` (rule-based), plus `judge_prompt` + `judge_parse` (LLM score via the dedicated `judge` agent). Imported by every benchmark's `metrics.py`. |
| `report_pr.py` | Collects every benchmark's `bench-report.json`, renders a Markdown table, posts (or updates) a single PR comment via `gh pr comment`. |
| `README.md` | This file. |

## Protocol (what CI does, what benchmarks must do)

1. CI runs `bash benchmarks/_common/env_setup.sh` once. This:
   - Reads `docker/.env.bench` (created by CI from repo secrets).
   - Runs `docker compose -f docker/docker-compose.bench.yml up -d`.
   - Mounts the current repo at `/home/node/.openclaw` inside the container.
   - Waits for `openclaw health` to return ready (up to 2 min).
   - Runs one smoke turn: `openclaw agent --agent main --message "ping" --local --json`.
   - Exports `BENCH_CONTAINER=openclaw-bench` and `BENCH_MOUNT=/home/node/.openclaw`.

2. For each benchmark directory in `BENCH_TARGETS` (default: all 6):
   - `bash benchmarks/<name>/env.sh` writes fixtures into `$BENCH_MOUNT` (i.e. the mounted repo). May restart only the gateway service, never the whole stack.
   - `python3 benchmarks/<name>/metrics.py` iterates `qa.jsonl`, calls the agent through `openclaw agent --local --json`, scores, and writes `bench-report.json`.

3. CI runs `python3 benchmarks/_common/report_pr.py` once at the end. This script:
   - Reads every `bench-report.json` under `bench-results/`.
   - Renders a Markdown table (benchmark, qa_count, passed, pass_rate, avg_score, delta vs base).
   - Calls `gh pr comment --body-file -` (or `gh api .../issues/<n>/comments` to upsert on the same hidden marker).

## Running one benchmark locally

```bash
# Set LLM_API_KEY in docker/.env.bench first, then run exactly one benchmark.
benchmarks/_common/run_local_benchmark.sh idea-generate-1

# Runtime selection: auto (default), docker, or Apple's `container` CLI.
benchmarks/_common/run_local_benchmark.sh --runtime docker idea-generate-1
benchmarks/_common/run_local_benchmark.sh --runtime container idea-generate-1
```

## What a benchmark directory MUST export

Required files (see CLAUDE.md "Benchmark Constraints" for the policy):

```
benchmarks/<name>/
├── env.sh            # POSIX shell. Receives $BENCH_CONTAINER $BENCH_MOUNT $BENCH_RUN_ID.
├── metrics.py        # Python 3.10+. Receives $BENCH_QA_PATH $BENCH_ARTIFACTS_DIR $BENCH_REPORT_PATH.
├── qa.jsonl          # One QA per line, conformant with qa_schema.json.
├── spec.md           # Human-readable spec (existing).
└── (existing files)  # fixtures, materials, seed files, etc.
```

Exit codes:
- `env.sh`: 0 on success, non-0 on setup failure (CI fails the workflow).
- `metrics.py`: always 0. Failures are recorded in `bench-report.json` (the `passed` count drops, the workflow still runs `report_pr.py`).

## Adding a new benchmark

1. Create `benchmarks/<name>/{env.sh,metrics.py,qa.jsonl}`.
2. Add `<name>` to the `BENCH_TARGETS` list in `.github/workflows/benchmark.yml`.
3. Open a PR. The CI workflow will pick it up automatically.

See CLAUDE.md "Benchmark Constraints" for the full rules.
