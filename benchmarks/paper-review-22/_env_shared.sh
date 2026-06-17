#!/usr/bin/env bash
# benchmarks/paper-review-22/_env_shared.sh
# Shared env logic for paper-review-22 benchmark.
#
# Responsibility: prepare container filesystem only.
# - Recreate container via bench_force_recreate (setup job tore it down)
# - Stage wiki fixtures into the wiki vault (~/.openclaw/wiki/main/)
# - Stage full-text papers / baked wiki into the vault
# - Link benchmarks/ into sub-agent workspaces
# - Pre-create runtime dirs
# qa.jsonl is read by run_bench.py on the host — no need to stage it.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
log() { printf '\n[paper-review-22.env] %s\n' "$*"; }

# Source the runtime env file (produced by env_setup.sh) to get helper
# functions (bench_force_recreate, bench_container_cli, …) and exported
# variables (BENCH_CONTAINER, BENCH_MOUNT, BENCH_COMPOSE_PROJECT, …).
# The setup job tore down the initial container, so the bench job MUST
# call bench_force_recreate to bring up a fresh one.
if [[ -n "${BENCH_ENV_FILE:-}" && -f "${BENCH_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${BENCH_ENV_FILE}"
  log "sourced runtime env; calling bench_force_recreate"
  bench_force_recreate
else
  echo "[paper-review-22.env][FATAL] BENCH_ENV_FILE=${BENCH_ENV_FILE:-<unset>} not found or missing; cannot proceed" >&2
  exit 1
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

# ── 2. Link benchmarks/ into sub-agent workspaces for path resolution ──
log "linking benchmarks/ into sub-agent workspaces"
bench_container_cli exec "${BENCH_CONTAINER}" bash -lc \
  "for ws in workspace/extract workspace/critic workspace/design workspace/spec workspace/audit; do
     mkdir -p '${BENCH_MOUNT}/\${ws}'
     rm -f '${BENCH_MOUNT}/\${ws}/benchmarks'
     ln -s '${BENCH_MOUNT}/benchmarks' '${BENCH_MOUNT}/\${ws}/benchmarks'
   done"

# ── 3. Pre-create runtime dirs the gateway needs ────────────────────
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

# ── 4. Output directories ──
log "ensuring output dirs"
bench_container_cli exec "${BENCH_CONTAINER}" mkdir -p "${BENCH_MOUNT}/workspace/extract/outputs/bench-${BENCH_RUN_ID:-local}"

log "env ready"
