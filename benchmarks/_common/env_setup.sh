#!/usr/bin/env bash
# benchmarks/_common/env_setup.sh
#
# Unified pre-benchmark env. Boots a minimal openclaw-docker-cn-im container,
# mounts/copies the current repo at /home/node/.openclaw, waits for the gateway
# to become ready, and exports helper functions for per-benchmark env.sh files.
#
# Supported container runtimes:
#   BENCH_CONTAINER_RUNTIME=docker     Use Docker + docker compose (CI default).
#   BENCH_CONTAINER_RUNTIME=container  Use Apple's `container` CLI (no compose).
#   BENCH_CONTAINER_RUNTIME=auto       Prefer a running Docker daemon, else container.
#
# Required env (set by CI, docker/.env.bench, or the caller):
#   LLM_API_KEY         -- LLM provider key (fail-fast if missing)
#   LLM_BASE_URL        -- optional, defaults to https://api.minimaxi.com/anthropic
#   LLM_MODEL           -- optional, defaults to minimax/MiniMax-M2.7
#   BENCH_RUN_ID            -- used as the session key prefix and compose/project name
#   BENCH_COMPOSE_FILE      -- optional, defaults to docker/docker-compose.bench.yml
#   BENCH_OPENCLAW_IMAGE    -- optional, overrides the image tag
#
# Exported after success:
#   BENCH_CONTAINER         -- running container name/id
#   BENCH_CONTAINER_RUNTIME -- docker | container
#   BENCH_CONTAINER_CLI     -- docker | container
#   BENCH_MOUNT             -- /home/node/.openclaw
#   BENCH_OPENCLAW          -- openclaw (path to CLI inside the container)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOCAL_ENV_FILE="${BENCH_LOCAL_ENV_FILE:-${ROOT}/docker/.env.bench}"

log() { printf '\n[env_setup] %s\n' "$*"; }
die() { printf '\n[env_setup][FATAL] %s\n' "$*" >&2; exit 1; }

# Local runs commonly keep credentials in docker/.env.bench. CI injects the
# same values through the process environment, so this is a no-op there.
if [[ -f "${LOCAL_ENV_FILE}" ]]; then
  log "loading ${LOCAL_ENV_FILE}"
  set -a
  # shellcheck disable=SC1090
  . "${LOCAL_ENV_FILE}"
  set +a
fi

# 0. Secrets check
if [[ -z "${LLM_API_KEY:-}" ]]; then
  die "LLM_API_KEY is not set. Export it or put it in docker/.env.bench, then re-run."
fi
: "${LLM_BASE_URL:=https://api.minimaxi.com/anthropic}"
export LLM_BASE_URL
: "${LLM_MODEL:=minimax/MiniMax-M2.7}"
export LLM_MODEL

COMPOSE_FILE="${BENCH_COMPOSE_FILE:-${ROOT}/docker/docker-compose.bench.yml}"
IMAGE="${BENCH_OPENCLAW_IMAGE:-${OPENCLAW_IMAGE:-acautomata/openclaw-docker-cn-im:latest}}"
RUN_ID="${BENCH_RUN_ID:-local-$$}"
COMPOSE_PROJECT="openclaw-bench-${RUN_ID}"
SAFE_RUN_ID="$(printf '%s' "${RUN_ID}" | tr -c 'A-Za-z0-9_.-' '-')"
CONTAINER_NAME="${BENCH_CONTAINER_NAME:-openclaw-bench-${SAFE_RUN_ID}}"
ENV_DIR="${ROOT}/.bench-runtime"
ENV_FILE="${ENV_DIR}/.env.bench"

select_container_runtime() {
  local requested="${BENCH_CONTAINER_RUNTIME:-${BENCH_CONTAINER_CLI:-auto}}"
  case "${requested}" in
    auto|"")
      if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        printf 'docker\n'
      elif command -v container >/dev/null 2>&1; then
        printf 'container\n'
      else
        return 1
      fi
      ;;
    docker|container)
      printf '%s\n' "${requested}"
      ;;
    *)
      return 2
      ;;
  esac
}

CONTAINER_RUNTIME="$(select_container_runtime)" || {
  case "${BENCH_CONTAINER_RUNTIME:-${BENCH_CONTAINER_CLI:-auto}}" in
    auto|"") die "neither a running Docker daemon nor Apple's container CLI is available" ;;
    *) die "unsupported BENCH_CONTAINER_RUNTIME/BENCH_CONTAINER_CLI='${BENCH_CONTAINER_RUNTIME:-${BENCH_CONTAINER_CLI:-}}' (expected docker, container, or auto)" ;;
  esac
}
CONTAINER_CLI="${BENCH_CONTAINER_CLI:-${CONTAINER_RUNTIME}}"
command -v "${CONTAINER_CLI}" >/dev/null 2>&1 || die "container CLI '${CONTAINER_CLI}' not found in PATH"

export BENCH_ROOT="${ROOT}"
export BENCH_COMPOSE_FILE="${COMPOSE_FILE}"
export BENCH_COMPOSE_ENV_FILE="${ENV_FILE}"
export BENCH_OPENCLAW_IMAGE_RESOLVED="${IMAGE}"
export BENCH_CONTAINER_RUNTIME="${CONTAINER_RUNTIME}"
export BENCH_CONTAINER_CLI="${CONTAINER_CLI}"
export BENCH_COMPOSE_PROJECT="${COMPOSE_PROJECT}"
export BENCH_CONTAINER_NAME="${CONTAINER_NAME}"
export BENCH_DATA_DIR="${ENV_DIR}/openclaw-data"

bench_container_cli() {
  "${BENCH_CONTAINER_CLI}" "$@"
}

bench_image_pull() {
  local image="$1"
  case "${BENCH_CONTAINER_RUNTIME}" in
    docker) bench_container_cli pull "${image}" ;;
    container) bench_container_cli image pull "${image}" ;;
    *) echo "[bench_image_pull][FATAL] unsupported runtime ${BENCH_CONTAINER_RUNTIME}" >&2; return 64 ;;
  esac
}

bench_logs_tail() {
  local container="$1"
  local lines="${2:-200}"
  case "${BENCH_CONTAINER_RUNTIME}" in
    docker) bench_container_cli logs --tail "${lines}" "${container}" ;;
    container) bench_container_cli logs -n "${lines}" "${container}" ;;
    *) echo "[bench_logs_tail][FATAL] unsupported runtime ${BENCH_CONTAINER_RUNTIME}" >&2; return 64 ;;
  esac
}

bench_is_running() {
  local container="$1"
  case "${BENCH_CONTAINER_RUNTIME}" in
    docker)
      [[ "$(bench_container_cli inspect --format '{{.State.Running}}' "${container}" 2>/dev/null || true)" == "true" ]]
      ;;
    container)
      bench_container_cli exec "${container}" true >/dev/null 2>&1
      ;;
    *)
      return 1
      ;;
  esac
}

bench_running_state() {
  local container="$1"
  case "${BENCH_CONTAINER_RUNTIME}" in
    docker)
      bench_container_cli inspect --format '{{.State.Running}}|{{.State.Status}}' "${container}" 2>/dev/null || true
      ;;
    container)
      if bench_is_running "${container}"; then
        printf 'true|running\n'
      elif bench_container_cli inspect "${container}" >/dev/null 2>&1; then
        printf 'false|stopped\n'
      else
        printf 'missing|missing\n'
      fi
      ;;
  esac
}

bench_ensure_running() {
  local container="$1"
  local context="${2:-container check}"
  if bench_is_running "${container}"; then
    return 0
  fi
  local state
  state="$(bench_running_state "${container}")"
  echo "[bench_ensure_running] ${container} not running during ${context}; state=${state}; dumping logs:" >&2
  bench_logs_tail "${container}" 200 >&2 || true
  echo "[bench_ensure_running] attempting start ${container}" >&2
  bench_container_cli start "${container}" >/dev/null 2>&1 || true
  sleep 2
  if bench_is_running "${container}"; then
    return 0
  fi
  state="$(bench_running_state "${container}")"
  echo "[bench_ensure_running][FATAL] ${container} still not running after start; state=${state}; dumping logs:" >&2
  bench_logs_tail "${container}" 200 >&2 || true
  return 1
}

bench_runtime_up() {
  [[ -n "${BENCH_COMPOSE_ENV_FILE:-}" ]] || { echo "[bench_runtime_up][FATAL] BENCH_COMPOSE_ENV_FILE not set" >&2; return 64; }
  set -a
  # shellcheck disable=SC1090
  . "${BENCH_COMPOSE_ENV_FILE}"
  set +a
  : "${OPENCLAW_DATA_DIR:=${BENCH_DATA_DIR}}"
  mkdir -p "${OPENCLAW_DATA_DIR}"

  case "${BENCH_CONTAINER_RUNTIME}" in
    docker)
      bench_container_cli compose --project-name "${BENCH_COMPOSE_PROJECT}" \
        -f "${BENCH_COMPOSE_FILE}" --env-file "${BENCH_COMPOSE_ENV_FILE}" \
        up -d --force-recreate openclaw-bench
      local new_container
      new_container="$(bench_container_cli ps --filter "label=com.docker.compose.project=${BENCH_COMPOSE_PROJECT}" \
        --format '{{.Names}}' | head -n1)"
      [[ -n "${new_container}" ]] || { echo "[bench_runtime_up][FATAL] no docker compose container found for ${BENCH_COMPOSE_PROJECT}" >&2; return 1; }
      export BENCH_CONTAINER="${new_container}"
      ;;
    container)
      local name="${BENCH_CONTAINER_NAME}"
      bench_container_cli rm --force "${name}" >/dev/null 2>&1 || true
      bench_container_cli run \
        --detach \
        --name "${name}" \
        --env-file "${BENCH_COMPOSE_ENV_FILE}" \
        --env TZ=Asia/Shanghai \
        --env HOME=/home/node \
        --env TERM=xterm-256color \
        --env NODE_ENV=production \
        --env LANG=en_US.UTF-8 \
        --env LANGUAGE=en_US:en \
        --env LC_ALL=en_US.UTF-8 \
        --env SYNC_EXTENSIONS_MODE=none \
        --env LLM_API_KEY \
        --env LLM_BASE_URL \
        --env OPENCLAW_GATEWAY_BIND=loopback \
        --env OPENCLAW_GATEWAY_MODE=local \
        --env OPENCLAW_GATEWAY_ALLOW_INSECURE_AUTH=true \
        --env GATEWAY_TOKEN="${GATEWAY_TOKEN:-bench-only-not-a-real-token}" \
        --user "${OPENCLAW_RUN_USER:-0:0}" \
        --init \
        "${BENCH_OPENCLAW_IMAGE_RESOLVED}"
      export BENCH_CONTAINER="${name}"
      ;;
    *)
      echo "[bench_runtime_up][FATAL] unsupported runtime ${BENCH_CONTAINER_RUNTIME}" >&2
      return 64
      ;;
  esac
}

bench_patch_openclaw_json_file() {
  local openclaw_json_path="$1"
  local llm_model="${LLM_MODEL:-minimax/MiniMax-M2.7}"
  OPENCLAW_JSON_PATH="${openclaw_json_path}" \
  LLM_MODEL="${llm_model}" \
  LLM_BASE_URL="${LLM_BASE_URL:-}" \
  python3 - <<'PY'
import json, os, pathlib
p = pathlib.Path(os.environ["OPENCLAW_JSON_PATH"])
data = json.loads(p.read_text(encoding="utf-8"))
llm_model = os.environ.get("LLM_MODEL", "")
if "/" not in llm_model:
    raise SystemExit(
        "LLM_MODEL must be in 'provider/model' form (e.g. minimax/MiniMax-M2.7), got: %r" % llm_model
    )
_provider, _model_id = llm_model.split("/", 1)
prov = data.setdefault("models", {}).setdefault("providers", {}).setdefault(_provider, {})
prov["apiKey"] = {"source": "env", "provider": "default", "id": "LLM_API_KEY"}
custom_base = os.environ.get("LLM_BASE_URL", "")
default_base = "https://api.minimaxi.com/anthropic"
if custom_base and custom_base != default_base:
    prov["baseUrl"] = custom_base
    print(f"patched models.providers.{_provider}.baseUrl -> {custom_base}")
default_prov = data.get("models", {}).get("providers", {}).pop("default", None)
if default_prov is not None:
    print("removed models.providers.default overlay (not needed for bench)")
_template = prov.get("models", [{}])[0] if prov.get("models") else {}
_new_model = dict(_template)
_new_model["id"] = _model_id
_new_model["name"] = _model_id
prov["models"] = [_new_model]
data.setdefault("agents", {}).setdefault("defaults", {})["model"] = {
    "primary": f"{_provider}/{_model_id}", "fallbacks": []
}
print(f"patched models.providers.{_provider}.models -> [{_model_id}]")
print(f"patched agents.defaults.model.primary -> {_provider}/{_model_id}")
defaults = data.setdefault("agents", {}).setdefault("defaults", {})
defaults["sandbox"] = {"mode": "off"}
defaults["elevatedDefault"] = "full"
data.setdefault("tools", {}).setdefault("exec", {})["mode"] = "full"
# Disable the file-tool workspace confinement so spawned sub-agents can write
# scratch/output files outside their own workspace root (e.g. when a sub-agent
# writes into the controller's workspace). The benchmark container is isolated
# (loopback, no channels, disposable), so this is safe here.
data.setdefault("tools", {}).setdefault("fs", {})["workspaceOnly"] = False
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"patched models.providers.{_provider}.apiKey -> SecretRef(LLM_API_KEY)")
print("patched agents.defaults.sandbox.mode -> off")
print("patched agents.defaults.elevatedDefault -> full")
print("patched tools.exec.mode -> full (no-approval)")
print("patched tools.fs.workspaceOnly -> false")
PY
}

bench_tar_repo() {
  local root="$1"
  tar --exclude='.git' --exclude='.github' --exclude='.env' \
      --exclude='*.sqlite*' --exclude='qmd' --exclude='logs' \
      --exclude='tasks' --exclude='credentials' --exclude='cron' \
      --exclude='devices' --exclude='identity' --exclude='feishu' \
      --exclude='extensions' --exclude='qqbot' --exclude='.openclaw' \
      --exclude='.dreams' --exclude='dreaming' --exclude='.bench-runtime' \
      --exclude='bench-results' \
      -C "${root}" -cf - .
}

bench_reapply_setup() {
  local container="${1:-${BENCH_CONTAINER:-}}"
  [[ -n "${container}" ]] || { echo "[bench_reapply_setup][FATAL] no container" >&2; return 64; }
  local root="${BENCH_ROOT}"
  if [[ "${BENCH_CONTAINER_RUNTIME}" == "docker" ]]; then
    local data_dir="${BENCH_DATA_DIR:?}"
    echo "[bench_reapply_setup] stage repo into ${data_dir} (bind mount for ${container})"
    bench_container_cli stop "${container}" >/dev/null 2>&1 || true
    mkdir -p "${data_dir}"
    chown -R "$(id -u):$(id -g)" "${data_dir}" 2>/dev/null || sudo chown -R "$(id -u):$(id -g)" "${data_dir}" 2>/dev/null || true
    chmod -R u+rwX "${data_dir}" 2>/dev/null || true
    find "${data_dir}" -mindepth 1 -delete 2>/dev/null || true
    bench_tar_repo "${root}" | tar -xf - -C "${data_dir}"
    echo "[bench_reapply_setup] creating agent session dirs"
    for agent_id in main ingest curate extract critic design spec audit ideate judge reviewer; do
      mkdir -p "${data_dir}/agents/${agent_id}/sessions"
    done
    echo "[bench_reapply_setup] chown ${data_dir} -> 1000:1000"
    chown -R 1000:1000 "${data_dir}" 2>/dev/null || true
    echo "[bench_reapply_setup] patching openclaw.json (SecretRef)"
    bench_patch_openclaw_json_file "${data_dir}/openclaw.json"
    chown 1000:1000 "${data_dir}/openclaw.json" 2>/dev/null || true
    echo "[bench_reapply_setup] starting ${container} after host-side staging"
    bench_container_cli start "${container}" >/dev/null
    return 0
  fi
  bench_ensure_running "${container}" "bench_reapply_setup start"
  echo "[bench_reapply_setup] copy repo into ${container}:/home/node/.openclaw"
  bench_container_cli exec "${container}" bash -lc '
    set -e
    cd /home/node/.openclaw
    find . -mindepth 1 -delete 2>/dev/null || true
  '
  bench_ensure_running "${container}" "before repo tar extract"
  bench_tar_repo "${root}" | \
    bench_container_cli exec -i "${container}" tar -xf - -C /home/node/.openclaw
  echo "[bench_reapply_setup] creating agent session dirs"
  bench_container_cli exec "${container}" bash -lc '
    set -e
    for agent_id in main ingest curate extract critic design spec audit ideate judge reviewer; do
      mkdir -p "/home/node/.openclaw/agents/${agent_id}/sessions"
    done
  '
  echo "[bench_reapply_setup] chown /home/node/.openclaw -> 1000:1000"
  bench_container_cli exec "${container}" chown -R 1000:1000 /home/node/.openclaw || true
  echo "[bench_reapply_setup] patching openclaw.json (SecretRef)"
  # Pass LLM_MODEL into the container. Honor the env_setup.sh default so an
  # empty LLM_MODEL (e.g. when the CI secret isn't configured) still
  # produces a valid provider/model, matching the comment at the top of
  # this file: "LLM_MODEL -- optional, defaults to minimax/MiniMax-M2.7".
  local llm_model="${LLM_MODEL:-minimax/MiniMax-M2.7}"
  bench_container_cli exec -e "LLM_MODEL=${llm_model}" "${container}" python3 -c '
import json, os, pathlib
p = pathlib.Path("/home/node/.openclaw/openclaw.json")
data = json.loads(p.read_text(encoding="utf-8"))
# Resolve target provider + model id from LLM_MODEL, following the
# `provider/model` convention used by ~/.openclaw/openclaw.json: the prefix
# "AA" of "AA/BB" becomes models.providers.AA and "BB" the model id.
# LLM_MODEL must contain a slash; a bare model name is rejected.
llm_model = os.environ.get("LLM_MODEL", "")
if "/" not in llm_model:
    raise SystemExit(
        "LLM_MODEL must be in 'provider/model' form (e.g. minimax/MiniMax-M2.7), got: %r" % llm_model
    )
_provider, _model_id = llm_model.split("/", 1)
prov = data.setdefault("models", {}).setdefault("providers", {}).setdefault(_provider, {})
prov["apiKey"] = {"source": "env", "provider": "default", "id": "LLM_API_KEY"}
custom_base = os.environ.get("LLM_BASE_URL", "")
default_base = "https://api.minimaxi.com/anthropic"
if custom_base and custom_base != default_base:
    prov["baseUrl"] = custom_base
    print(f"patched models.providers.{_provider}.baseUrl -> {custom_base}")
default_prov = data.get("models", {}).get("providers", {}).pop("default", None)
if default_prov is not None:
    print("removed models.providers.default overlay (not needed for bench)")
# Repoint the provider model list to LLM_MODEL so the bench is not pinned
# to MiniMax-M2.7.
_template = prov.get("models", [{}])[0] if prov.get("models") else {}
_new_model = dict(_template)
_new_model["id"] = _model_id
_new_model["name"] = _model_id
prov["models"] = [_new_model]
data.setdefault("agents", {}).setdefault("defaults", {})["model"] = {
    "primary": f"{_provider}/{_model_id}", "fallbacks": []
}
print(f"patched models.providers.{_provider}.models -> [{_model_id}]")
print(f"patched agents.defaults.model.primary -> {_provider}/{_model_id}")
# Sandbox mode requires Docker-in-Docker which is not available in CI/local bench containers.
agents = data.setdefault("agents", {})
defaults = agents.setdefault("defaults", {})
defaults["sandbox"] = {"mode": "off"}
# YOLO mode: auto-approve all tool calls so benchmark runs never stall on prompts.
defaults["elevatedDefault"] = "full"
tools = data.setdefault("tools", {})
tools.setdefault("exec", {})["mode"] = "full"
# Disable file-tool workspace confinement so sub-agents can write outside their
# own workspace root (see docker-branch patch for rationale).
tools.setdefault("fs", {})["workspaceOnly"] = False
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"patched models.providers.{_provider}.apiKey -> SecretRef(LLM_API_KEY)")
print("patched agents.defaults.sandbox.mode -> off")
print("patched agents.defaults.elevatedDefault -> full")
print("patched tools.fs.workspaceOnly -> false")
print("patched tools.exec.mode -> full (no-approval)")
'
  bench_container_cli exec "${container}" chown 1000:1000 /home/node/.openclaw/openclaw.json
}

bench_wait_ready() {
  local container="${1:-${BENCH_CONTAINER:-}}"
  [[ -n "${container}" ]] || { echo "[bench_wait_ready][FATAL] no container" >&2; return 64; }
  echo "[bench_wait_ready] waiting for ${container} to come up and gateway to be ready"
  for i in $(seq 1 90); do
    if bench_is_running "${container}"; then
      if bench_logs_tail "${container}" 200 2>&1 | grep -qE 'http server listening|starting channels and sidecars|\[gateway\] ready|heartbeat.*started'; then
        echo "[bench_wait_ready] ${container} is up and gateway is ready after ${i} polls"
        return 0
      fi
    else
      local running
      running="$(bench_running_state "${container}")"
      case "${running}" in
        false\|exited|false\|dead|false\|stopped|false\|removing|missing\|missing)
          echo "[bench_wait_ready][FATAL] container ${container} state=${running}; dumping logs:" >&2
          bench_logs_tail "${container}" 200 >&2 || true
          return 1
          ;;
      esac
    fi
    sleep 2
  done
  echo "[bench_wait_ready][FATAL] gateway not ready in 180s" >&2
  bench_logs_tail "${container}" 200 >&2 || true
  return 1
}

bench_force_recreate() {
  if [[ -z "${BENCH_COMPOSE_PROJECT:-}" || -z "${BENCH_COMPOSE_ENV_FILE:-}" ]]; then
    echo "[bench_force_recreate][FATAL] BENCH_COMPOSE_PROJECT / BENCH_COMPOSE_ENV_FILE not set" >&2
    return 64
  fi
  echo "[bench_force_recreate] bringing up openclaw-bench --force-recreate (runtime=${BENCH_CONTAINER_RUNTIME}, project=${BENCH_COMPOSE_PROJECT})"
  bench_runtime_up
  if ! bench_is_running "${BENCH_CONTAINER}"; then
    echo "[bench_force_recreate] container ${BENCH_CONTAINER} not running after bench_runtime_up; dumping logs:" >&2
    bench_logs_tail "${BENCH_CONTAINER}" 200 >&2 || true
    echo "[bench_force_recreate] attempting start" >&2
    bench_container_cli start "${BENCH_CONTAINER}" >/dev/null 2>&1 || true
  fi
  bench_reapply_setup "${BENCH_CONTAINER}"
  bench_wait_ready "${BENCH_CONTAINER}"
}

bench_teardown() {
  case "${BENCH_CONTAINER_RUNTIME}" in
    docker)
      if [[ -n "${BENCH_COMPOSE_PROJECT:-}" ]]; then
        bench_container_cli compose --project-name "${BENCH_COMPOSE_PROJECT}" \
          -f "${BENCH_COMPOSE_FILE}" --env-file "${BENCH_COMPOSE_ENV_FILE}" \
          down -v --remove-orphans
      fi
      ;;
    container)
      if [[ -n "${BENCH_CONTAINER:-${BENCH_CONTAINER_NAME:-}}" ]]; then
        bench_container_cli rm --force "${BENCH_CONTAINER:-${BENCH_CONTAINER_NAME}}" >/dev/null 2>&1 || true
      fi
      ;;
  esac
}

# 1. Build a temporary .env the compose/container runner can read.
mkdir -p "${ENV_DIR}"
log "writing ${ENV_FILE}"
cat >"${ENV_FILE}" <<EOF
# Auto-generated by benchmarks/_common/env_setup.sh (run id=${RUN_ID})
OPENCLAW_IMAGE=${IMAGE}
OPENCLAW_DATA_DIR=${ENV_DIR}/openclaw-data
OPENCLAW_RUN_USER=0:0
DOCKER_BIND=${DOCKER_BIND:-127.0.0.1}
OPENCLAW_GATEWAY_PORT=${OPENCLAW_GATEWAY_PORT:-18789}
OPENCLAW_GATEWAY_BIND=loopback
TZ=Asia/Shanghai
SYNC_OPENCLAW_CONFIG=false
SYNC_EXTENSIONS_ON_START=false
SYNC_MODEL_CONFIG=false
MODEL_ID=${LLM_MODEL}
PRIMARY_MODEL=${LLM_MODEL}
BASE_URL=${LLM_BASE_URL}
API_PROTOCOL=anthropic
CONTEXT_WINDOW=200000
MAX_TOKENS=8192
DM_POLICY=disabled
GROUP_POLICY=disabled
ALLOW_FROM=
OPENCLAW_WORKSPACE_ROOT=/home/node/.openclaw
OPENCLAW_PLUGINS_ENABLED=false
EOF
mkdir -p "${BENCH_DATA_DIR}"

# 2a. Pre-seed the data directory with a minimally-valid openclaw.json so
#     the gateway starts clean before the repo is copied in.
log "pre-seeding openclaw.json in data dir to avoid gateway config errors"
cat >"${BENCH_DATA_DIR}/openclaw.json" <<'PRESEEDEOF'
{
  "gateway": {"mode": "local", "bind": "loopback", "port": 18789, "auth": {"mode": "token"}},
  "models": {
    "mode": "merge",
    "providers": {
      "minimax": {
        "baseUrl": "https://api.minimaxi.com/anthropic",
        "api": "anthropic-messages",
        "authHeader": true,
        "apiKey": {"source": "env", "provider": "default", "id": "LLM_API_KEY"}
      }
    }
  }
}
PRESEEDEOF

# 2b. Pull the image (idempotent).
log "using runtime=${BENCH_CONTAINER_RUNTIME} cli=${BENCH_CONTAINER_CLI}"
log "pulling ${IMAGE}"
bench_image_pull "${IMAGE}" >/dev/null

# 3. Bring up the gateway service.
log "bringing up container (project=${COMPOSE_PROJECT}, --force-recreate)"
bench_runtime_up
CONTAINER="${BENCH_CONTAINER}"
log "container: ${CONTAINER}"

# Defensive: docker compose up -d --force-recreate occasionally leaves the
# container in created / exited state when the host daemon is under load.
# bench_reapply_setup would then fail with "container is not running".
if ! bench_is_running "${CONTAINER}"; then
  echo "[env_setup] container ${CONTAINER} not running after bench_runtime_up; dumping logs:" >&2
  bench_logs_tail "${CONTAINER}" 200 >&2 || true
  echo "[env_setup] attempting start" >&2
  bench_container_cli start "${CONTAINER}" >/dev/null 2>&1 || true
fi

# 4. Copy the repo into /home/node/.openclaw and patch bench settings.
log "copy repo into ${CONTAINER}:/home/node/.openclaw"
bench_reapply_setup "${CONTAINER}"
log "repo copied into container"
log "SecretRef patch applied via bench_reapply_setup"

# 5. Wait for the openclaw container to start and the gateway to become ready.
bench_wait_ready "${CONTAINER}"

# 6. Export the contract for downstream env.sh scripts and subsequent CI steps.
export BENCH_CONTAINER="${CONTAINER}"
export BENCH_MOUNT="/home/node/.openclaw"
export BENCH_OPENCLAW="openclaw"
export BENCH_ENV_FILE="${ENV_DIR}/bench-runtime-env.sh"

# Drop a sourceable env file for subsequent workflow steps / local runner.
EXPORT_FILE="${BENCH_ENV_FILE}"
{
  cat <<EOF
# Auto-sourced by .github/workflows/benchmark.yml, local runners, and benchmark env.sh files.
export BENCH_ROOT='${BENCH_ROOT}'
export BENCH_CONTAINER='${CONTAINER}'
export BENCH_CONTAINER_NAME='${BENCH_CONTAINER_NAME}'
export BENCH_CONTAINER_RUNTIME='${BENCH_CONTAINER_RUNTIME}'
export BENCH_CONTAINER_CLI='${BENCH_CONTAINER_CLI}'
export BENCH_MOUNT='/home/node/.openclaw'
export BENCH_OPENCLAW='openclaw'
export BENCH_COMPOSE_PROJECT='${BENCH_COMPOSE_PROJECT}'
export BENCH_COMPOSE_FILE='${BENCH_COMPOSE_FILE}'
export BENCH_COMPOSE_ENV_FILE='${BENCH_COMPOSE_ENV_FILE}'
export BENCH_DATA_DIR='${BENCH_DATA_DIR}'
export BENCH_OPENCLAW_IMAGE_RESOLVED='${BENCH_OPENCLAW_IMAGE_RESOLVED}'
export BENCH_ENV_FILE='${EXPORT_FILE}'
EOF
  declare -f bench_container_cli
  declare -f bench_image_pull
  declare -f bench_logs_tail
  declare -f bench_is_running
  declare -f bench_running_state
  declare -f bench_ensure_running
  declare -f bench_patch_openclaw_json_file
  declare -f bench_tar_repo
  declare -f bench_runtime_up
  declare -f bench_reapply_setup
  declare -f bench_wait_ready
  declare -f bench_force_recreate
  declare -f bench_teardown
} >"${EXPORT_FILE}"

# Surface the file path so the workflow can source it without re-deriving.
if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "BENCH_ENV_FILE=${EXPORT_FILE}" >> "${GITHUB_ENV}"
  echo "BENCH_CONTAINER=${CONTAINER}" >> "${GITHUB_ENV}"
  echo "BENCH_CONTAINER_RUNTIME=${BENCH_CONTAINER_RUNTIME}" >> "${GITHUB_ENV}"
  echo "BENCH_CONTAINER_CLI=${BENCH_CONTAINER_CLI}" >> "${GITHUB_ENV}"
  echo "BENCH_MOUNT=/home/node/.openclaw" >> "${GITHUB_ENV}"
  echo "BENCH_COMPOSE_PROJECT=${COMPOSE_PROJECT}" >> "${GITHUB_ENV}"
fi

log "ready: runtime=${BENCH_CONTAINER_RUNTIME} container=${BENCH_CONTAINER} mount=${BENCH_MOUNT} data_dir=${BENCH_DATA_DIR}"
log "runtime env file: ${EXPORT_FILE}"
