#!/usr/bin/env bash
# benchmarks/paper-review-22/env.sh
# Paper-review-22 benchmark (full set — for local testing; CI uses shards).
# qa.jsonl is read by run_bench.py on the host — no need to stage it.
set -euo pipefail

: "${BENCH_CONTAINER:?must be exported by env_setup.sh}"
: "${BENCH_MOUNT:?must be exported by env_setup.sh}"
: "${BENCH_RUN_ID:=local}"

HERE="$(cd "$(dirname "$0")" && pwd)"

# Delegate to shared env.
# shellcheck disable=SC1090
. "${HERE}/_env_shared.sh"

# >>> bake_wiki: stage baked wiki/main (managed by benchmarks/_common/bake_wiki.sh) >>>
# Replaced on every bake_wiki.sh run; hand-edits inside the markers will be lost.
if declare -F bench_container_cli >/dev/null 2>&1 && [[ -n "${BENCH_CONTAINER:-}" && -n "${BENCH_MOUNT:-}" ]]; then
  _bake_wiki_src="$(cd "$(dirname "$0")" && pwd)/wiki/main"
  if [[ -d "${_bake_wiki_src}" ]]; then
    printf '
[bake_wiki] staging baked wiki/main -> %s/wiki/main
' "${BENCH_MOUNT}"
    bench_container_cli exec "${BENCH_CONTAINER}" rm -rf "${BENCH_MOUNT}/wiki/main"
    bench_container_cli exec "${BENCH_CONTAINER}" mkdir -p "${BENCH_MOUNT}/wiki"
    bench_container_cli cp "${_bake_wiki_src}" "${BENCH_CONTAINER}:${BENCH_MOUNT}/wiki"
    bench_container_cli exec "${BENCH_CONTAINER}" chown -R 1000:1000 "${BENCH_MOUNT}/wiki/main" 2>/dev/null || true
  else
    printf '
[bake_wiki] no baked wiki/main at %s; skipping stage
' "${_bake_wiki_src}" >&2
  fi
fi
# <<< bake_wiki: stage baked wiki/main <<<
