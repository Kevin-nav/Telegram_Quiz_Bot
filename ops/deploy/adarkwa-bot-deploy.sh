#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-adarkwa-study-bot}"
IMAGE_REPO="${IMAGE_REPO:-ghcr.io/owner/adarkwa-study-bot}"
TRACKING_TAG="${TRACKING_TAG:-latest}"
REPO_URL="${REPO_URL:-https://github.com/OWNER/Adarkwa_Study_Bot.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/adarkwa-study-bot-deploy}"
WORKTREE_DIR="${WORKTREE_DIR:-${DEPLOY_ROOT}/repo}"
STATE_DIR="${STATE_DIR:-${DEPLOY_ROOT}/state}"
RENDER_DIR="${RENDER_DIR:-${DEPLOY_ROOT}/rendered}"
GHCR_USERNAME="${GHCR_USERNAME:-}"
GHCR_TOKEN_FILE="${GHCR_TOKEN_FILE:-}"
WEBHOOK_DEPLOYMENT="${WEBHOOK_DEPLOYMENT:-adarkwa-bot-webhook}"
WORKER_DEPLOYMENT="${WORKER_DEPLOYMENT:-adarkwa-bot-worker}"
MIGRATION_PREFIX="${MIGRATION_PREFIX:-adarkwa-bot-migrate}"

require_binary() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required binary: $1" >&2
    exit 1
  fi
}

require_binary git
require_binary kubectl
require_binary sed
require_binary crane

mkdir -p "${STATE_DIR}" "${RENDER_DIR}"

if [[ ! -d "${WORKTREE_DIR}/.git" ]]; then
  git clone --branch "${REPO_BRANCH}" --single-branch "${REPO_URL}" "${WORKTREE_DIR}"
else
  git -C "${WORKTREE_DIR}" fetch origin "${REPO_BRANCH}" --depth 1
  git -C "${WORKTREE_DIR}" checkout -f "origin/${REPO_BRANCH}"
fi

if [[ -n "${GHCR_USERNAME}" && -n "${GHCR_TOKEN_FILE}" ]]; then
  if [[ ! -f "${GHCR_TOKEN_FILE}" ]]; then
    echo "GHCR token file not found: ${GHCR_TOKEN_FILE}" >&2
    exit 1
  fi
  crane auth login ghcr.io \
    --username "${GHCR_USERNAME}" \
    --password "$(tr -d '\r\n' < "${GHCR_TOKEN_FILE}")" >/dev/null
fi

target_image="${IMAGE_REPO}:${TRACKING_TAG}"
target_digest="$(crane digest "${target_image}")"
immutable_image="${IMAGE_REPO}@${target_digest}"

last_deployed_file="${STATE_DIR}/last-deployed-digest"
if [[ -f "${last_deployed_file}" ]] && [[ "$(cat "${last_deployed_file}")" == "${target_digest}" ]]; then
  echo "already deployed ${immutable_image}"
  exit 0
fi

deployment_manifest="${RENDER_DIR}/deployment.yaml"
migration_manifest="${RENDER_DIR}/migration-job.yaml"
migration_job_name="${MIGRATION_PREFIX}-$(date +%Y%m%d%H%M%S)-${target_digest#sha256:}"
migration_job_name="${migration_job_name:0:63}"

sed "s|__IMAGE__|${immutable_image}|g" \
  "${WORKTREE_DIR}/k8s/deployment.yaml" > "${deployment_manifest}"

sed \
  -e "s|__IMAGE__|${immutable_image}|g" \
  -e "s|__MIGRATION_JOB_NAME__|${migration_job_name}|g" \
  "${WORKTREE_DIR}/k8s/migration-job.yaml" > "${migration_manifest}"

kubectl apply -f "${WORKTREE_DIR}/k8s/namespace.yaml"
kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/config.yaml"
kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/service.yaml"
if [[ -f "${WORKTREE_DIR}/k8s/ingress.yaml" ]]; then
  kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/ingress.yaml"
fi
if [[ -f "${WORKTREE_DIR}/k8s/hpa.yaml" ]]; then
  kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/hpa.yaml"
fi

kubectl apply --namespace "${NAMESPACE}" -f "${migration_manifest}"
if ! kubectl wait \
  --namespace "${NAMESPACE}" \
  --for=condition=complete \
  "job/${migration_job_name}" \
  --timeout=300s; then
  kubectl logs --namespace "${NAMESPACE}" "job/${migration_job_name}" || true
  exit 1
fi

kubectl apply --namespace "${NAMESPACE}" -f "${deployment_manifest}"
kubectl rollout status "deployment/${WEBHOOK_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=300s
kubectl rollout status "deployment/${WORKER_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=300s

printf '%s' "${target_digest}" > "${last_deployed_file}"
echo "deployed ${immutable_image}"
