#!/usr/bin/env bash
# benchmarks/paper-review-22/env.sh
# Self-contained benchmark env script.
#
# Responsibility: prepare container filesystem only.
# - Stage wiki fixtures into the wiki vault (~/.openclaw/wiki/main/)
# - Stage full-text papers / baked wiki into the vault
# - Copy syntheses into workspace for sandbox compat
# - Link benchmarks/ into sub-agent workspaces
# - Pre-create runtime dirs
# qa.jsonl is read by run_bench.py on the host — no need to stage it.
set -euo pipefail

: "${BENCH_CONTAINER:?must be exported by env_setup.sh}"
: "${BENCH_MOUNT:?must be exported by env_setup.sh}"
: "${BENCH_RUN_ID:=local}"

HERE="$(cd "$(dirname "$0")" && pwd)"
log() { printf '\n[paper-review-22.env] %s\n' "$*"; }

# Container already booted by env_setup.sh (called by run_local_benchmark.sh
# before env.sh). Skip bench_force_recreate to avoid double-rebuild on Windows.
if [[ -n "${BENCH_ENV_FILE:-}" && -f "${BENCH_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${BENCH_ENV_FILE}"
fi
log "container ready (env_setup.sh); skipping force recreate"
if ! declare -F bench_container_cli >/dev/null; then
  bench_container_cli() {
    local cli="${BENCH_CONTAINER_CLI:-${BENCH_CONTAINER_RUNTIME:-docker}}"
    [[ "${cli}" == "auto" ]] && cli=docker
    "${cli}" "$@"
  }
fi

# ── 1. Stage wiki fixtures into the wiki vault ─────────────────────
# openclaw.json configures memory-wiki vault at ~/.openclaw/wiki/main.
# QA prompts reference wiki files via this vault path.
WIKI_VAULT="${BENCH_MOUNT}/wiki/main"
MATERIALS_SRC="${HERE}/materials"

if [[ -d "${MATERIALS_SRC}" ]]; then
  log "staging wiki materials -> ${WIKI_VAULT}"
  bench_container_cli exec "${BENCH_CONTAINER}" mkdir -p "${WIKI_VAULT}"

  # Wiki entries
  if [[ -d "${MATERIALS_SRC}/wiki" ]]; then
    for f in "${MATERIALS_SRC}/wiki"/*; do
      [[ -f "$f" ]] || continue
      bench_container_cli cp "$f" "${BENCH_CONTAINER}:${WIKI_VAULT}/$(basename "$f")"
    done
  fi

  # Full-text papers
  for f in "${MATERIALS_SRC}"/*; do
    [[ -f "$f" ]] || continue
    bench_container_cli cp "$f" "${BENCH_CONTAINER}:${WIKI_VAULT}/$(basename "$f")"
  done
  log "staged materials into wiki vault"
fi

# ── 2. Stage baked wiki/main (managed by benchmarks/_common/bake_wiki.sh) ──
_bake_wiki_src="${HERE}/wiki/main"
if [[ -d "${_bake_wiki_src}" ]]; then
  log "staging baked wiki/main -> ${BENCH_MOUNT}/wiki/main"
  bench_container_cli exec "${BENCH_CONTAINER}" rm -rf "${BENCH_MOUNT}/wiki/main"
  bench_container_cli exec "${BENCH_CONTAINER}" mkdir -p "${BENCH_MOUNT}/wiki"
  bench_container_cli cp "${_bake_wiki_src}" "${BENCH_CONTAINER}:${BENCH_MOUNT}/wiki"
  bench_container_cli exec "${BENCH_CONTAINER}" chown -R 1000:1000 "${BENCH_MOUNT}/wiki/main" 2>/dev/null || true
else
  log "no baked wiki/main at ${_bake_wiki_src}; skipping stage"
fi

# ── 3. Link benchmarks/ into sub-agent workspaces for path resolution ──
log "linking benchmarks/ into sub-agent workspaces"
bench_container_cli exec "${BENCH_CONTAINER}" bash -lc \
  "for ws in workspace/extract workspace/critic workspace/design workspace/spec workspace/audit; do
     mkdir -p '${BENCH_MOUNT}/\${ws}'
     rm -f '${BENCH_MOUNT}/\${ws}/benchmarks'
     ln -s '${BENCH_MOUNT}/benchmarks' '${BENCH_MOUNT}/\${ws}/benchmarks'
   done"

# ── 4. Pre-create runtime dirs the gateway needs ────────────────────
# On Windows Docker Desktop bind mounts, chown inside the container is
# silently ignored (NTFS has no Unix ownership). The gateway process runs
# as uid 1000 and fails to mkdir logs/, devices/, agents/*/agent/ with
# EACCES. Pre-creating these dirs with permissive mode avoids the crash.
log "pre-creating gateway runtime dirs (Windows bind-mount compat)"
bench_container_cli exec "${BENCH_CONTAINER}" bash -lc "
  set -e
  for d in logs devices; do
    mkdir -p '${BENCH_MOUNT}/\${d}' && chmod 777 '${BENCH_MOUNT}/\${d}' || true
  done
  for id in main ingest curate extract critic design spec audit ideate judge reviewer; do
    mkdir -p '${BENCH_MOUNT}/agents/\${id}/agent' && chmod -R 777 '${BENCH_MOUNT}/agents/\${id}' || true
  done
"

# ── 5. Output directories ──
log "ensuring output dirs"
bench_container_cli exec "${BENCH_CONTAINER}" mkdir -p "${BENCH_MOUNT}/workspace/extract/outputs/bench-${BENCH_RUN_ID}"

log "env ready"
