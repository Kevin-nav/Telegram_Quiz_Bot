#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-adarkwa-study-bot}"
IMAGE_REPO="${IMAGE_REPO:-ghcr.io/owner/adarkwa-study-bot}"
ADMIN_IMAGE_REPO="${ADMIN_IMAGE_REPO:-ghcr.io/owner/adarkwa-study-bot-admin}"
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
ADMIN_DEPLOYMENT="${ADMIN_DEPLOYMENT:-adarkwa-bot-admin}"
MIGRATION_PREFIX="${MIGRATION_PREFIX:-adarkwa-bot-migrate}"
ENABLE_HPA="${ENABLE_HPA:-false}"
DEFAULT_WEBHOOK_REPLICAS="${DEFAULT_WEBHOOK_REPLICAS:-1}"
DEFAULT_WORKER_REPLICAS="${DEFAULT_WORKER_REPLICAS:-1}"
DEFAULT_ADMIN_REPLICAS="${DEFAULT_ADMIN_REPLICAS:-1}"

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

release_sha="$(git -C "${WORKTREE_DIR}" rev-parse HEAD)"
backend_release_image="${IMAGE_REPO}:${release_sha}"
admin_release_image="${ADMIN_IMAGE_REPO}:${release_sha}"

resolve_digest_or_skip() {
  local image_ref="$1"
  local image_label="$2"
  local output_var="$3"
  local digest
  if ! digest="$(crane digest "${image_ref}" 2>/dev/null)"; then
    echo "release image for ${image_label} is not available yet: ${image_ref}"
    echo "waiting for GitHub Actions to publish all images for ${release_sha}"
    exit 0
  fi
  printf -v "${output_var}" '%s' "${digest}"
}

resolve_digest_or_skip "${backend_release_image}" "backend" backend_digest
resolve_digest_or_skip "${admin_release_image}" "admin" admin_digest
immutable_backend_image="${IMAGE_REPO}@${backend_digest}"
immutable_admin_image="${ADMIN_IMAGE_REPO}@${admin_digest}"

last_deployed_file="${STATE_DIR}/last-deployed-sha"
last_failed_file="${STATE_DIR}/last-failed-sha"
last_backend_digest_file="${STATE_DIR}/last-deployed-backend-digest"
last_admin_digest_file="${STATE_DIR}/last-deployed-admin-digest"
if [[ -f "${last_deployed_file}" ]] && [[ "$(cat "${last_deployed_file}")" == "${release_sha}" ]]; then
  rm -f "${last_failed_file}"
  echo "already deployed release ${release_sha}"
  exit 0
fi

current_webhook_image="$(kubectl get deployment "${WEBHOOK_DEPLOYMENT}" --namespace "${NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)"
current_worker_image="$(kubectl get deployment "${WORKER_DEPLOYMENT}" --namespace "${NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)"
current_admin_image="$(kubectl get deployment "${ADMIN_DEPLOYMENT}" --namespace "${NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)"
if [[ "${current_webhook_image}" == "${immutable_backend_image}" && "${current_worker_image}" == "${immutable_backend_image}" && "${current_admin_image}" == "${immutable_admin_image}" ]]; then
  if kubectl rollout status "deployment/${WEBHOOK_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=5s >/dev/null \
    && kubectl rollout status "deployment/${WORKER_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=5s >/dev/null \
    && kubectl rollout status "deployment/${ADMIN_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=5s >/dev/null; then
    printf '%s' "${release_sha}" > "${last_deployed_file}"
    printf '%s' "${backend_digest}" > "${last_backend_digest_file}"
    printf '%s' "${admin_digest}" > "${last_admin_digest_file}"
    rm -f "${last_failed_file}"
    echo "deployment already healthy at release ${release_sha}"
    exit 0
  fi
fi

if [[ -f "${last_failed_file}" ]] && [[ "$(cat "${last_failed_file}")" == "${release_sha}" ]]; then
  echo "skipping automatic retry for previously failed release ${release_sha}"
  echo "delete ${last_failed_file} to retry manually after fixing the underlying issue"
  exit 0
fi

mark_failed_release() {
  printf '%s' "${release_sha}" > "${last_failed_file}"
}

deployment_manifest="${RENDER_DIR}/deployment.yaml"
admin_deployment_manifest="${RENDER_DIR}/admin-deployment.yaml"
migration_manifest="${RENDER_DIR}/migration-job.yaml"
migration_job_name="${MIGRATION_PREFIX}-$(date +%Y%m%d%H%M%S)-${backend_digest#sha256:}"
migration_job_name="${migration_job_name:0:63}"

sed "s|__IMAGE__|${immutable_backend_image}|g" \
  "${WORKTREE_DIR}/k8s/deployment.yaml" > "${deployment_manifest}"

sed "s|__ADMIN_IMAGE__|${immutable_admin_image}|g" \
  "${WORKTREE_DIR}/k8s/admin-deployment.yaml" > "${admin_deployment_manifest}"

sed \
  -e "s|__IMAGE__|${immutable_backend_image}|g" \
  -e "s|__MIGRATION_JOB_NAME__|${migration_job_name}|g" \
  "${WORKTREE_DIR}/k8s/migration-job.yaml" > "${migration_manifest}"

kubectl apply -f "${WORKTREE_DIR}/k8s/namespace.yaml"
kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/config.yaml"
kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/service.yaml"
kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/admin-service.yaml"
if [[ -f "${WORKTREE_DIR}/k8s/ingress.yaml" ]]; then
  kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/ingress.yaml"
fi
if [[ -f "${WORKTREE_DIR}/k8s/hpa.yaml" && "${ENABLE_HPA}" == "true" ]]; then
  kubectl apply --namespace "${NAMESPACE}" -f "${WORKTREE_DIR}/k8s/hpa.yaml"
elif [[ -f "${WORKTREE_DIR}/k8s/hpa.yaml" ]]; then
  kubectl delete --namespace "${NAMESPACE}" --ignore-not-found -f "${WORKTREE_DIR}/k8s/hpa.yaml"
fi

kubectl apply --namespace "${NAMESPACE}" -f "${migration_manifest}"
if ! kubectl wait \
  --namespace "${NAMESPACE}" \
  --for=condition=complete \
  "job/${migration_job_name}" \
  --timeout=300s; then
  mark_failed_release
  kubectl logs --namespace "${NAMESPACE}" "job/${migration_job_name}" || true
  exit 1
fi

kubectl apply --namespace "${NAMESPACE}" -f "${deployment_manifest}"
kubectl apply --namespace "${NAMESPACE}" -f "${admin_deployment_manifest}"
if [[ "${ENABLE_HPA}" != "true" ]]; then
  kubectl scale "deployment/${WEBHOOK_DEPLOYMENT}" --namespace "${NAMESPACE}" --replicas="${DEFAULT_WEBHOOK_REPLICAS}"
  kubectl scale "deployment/${WORKER_DEPLOYMENT}" --namespace "${NAMESPACE}" --replicas="${DEFAULT_WORKER_REPLICAS}"
  kubectl scale "deployment/${ADMIN_DEPLOYMENT}" --namespace "${NAMESPACE}" --replicas="${DEFAULT_ADMIN_REPLICAS}"
fi
if ! kubectl rollout status "deployment/${WEBHOOK_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=300s; then
  mark_failed_release
  exit 1
fi
if ! kubectl rollout status "deployment/${WORKER_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=300s; then
  mark_failed_release
  exit 1
fi
if ! kubectl rollout status "deployment/${ADMIN_DEPLOYMENT}" --namespace "${NAMESPACE}" --timeout=300s; then
  mark_failed_release
  exit 1
fi

printf '%s' "${release_sha}" > "${last_deployed_file}"
printf '%s' "${backend_digest}" > "${last_backend_digest_file}"
printf '%s' "${admin_digest}" > "${last_admin_digest_file}"
rm -f "${last_failed_file}"
echo "deployed release ${release_sha}"
echo "backend image ${immutable_backend_image}"
echo "admin image ${immutable_admin_image}"
