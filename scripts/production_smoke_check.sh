#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-/etc/adarkwa-study-bot/deploy.env}"

if [[ -f "${DEPLOY_ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${DEPLOY_ENV_FILE}"
  set +a
fi

NAMESPACE="${NAMESPACE:-adarkwa-study-bot}"
IMAGE_REPO="${IMAGE_REPO:-ghcr.io/<github-owner>/adarkwa-study-bot}"
STATE_DIR="${STATE_DIR:-/opt/adarkwa-study-bot-deploy/state}"
WEBHOOK_DEPLOYMENT="${WEBHOOK_DEPLOYMENT:-adarkwa-bot-webhook}"
WORKER_DEPLOYMENT="${WORKER_DEPLOYMENT:-adarkwa-bot-worker}"

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  TELEGRAM_BOT_TOKEN="$(
    kubectl get secret adarkwa-bot-secret \
      -n "${NAMESPACE}" \
      -o jsonpath='{.data.TELEGRAM_BOT_TOKEN}' | base64 -d
  )"
fi

if [[ -z "${IMAGE_REPO}" || "${IMAGE_REPO}" == "ghcr.io/<github-owner>/adarkwa-study-bot" ]]; then
  echo "IMAGE_REPO is not configured. Set it in ${DEPLOY_ENV_FILE} or export IMAGE_REPO." >&2
  exit 1
fi

echo "GHCR latest digest"
crane digest "${IMAGE_REPO}:latest"
echo

echo "Last deployed digest"
cat "${STATE_DIR}/last-deployed-digest"
echo

echo "Telegram webhook info"
curl -fsS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
echo
echo

echo "Pod readiness"
kubectl get pods -n "${NAMESPACE}"
echo

echo "Webhook rollout status"
kubectl rollout status "deployment/${WEBHOOK_DEPLOYMENT}" -n "${NAMESPACE}" --timeout=60s
echo

echo "Worker rollout status"
kubectl rollout status "deployment/${WORKER_DEPLOYMENT}" -n "${NAMESPACE}" --timeout=60s
echo

echo "Recent webhook logs"
kubectl logs -n "${NAMESPACE}" "deployment/${WEBHOOK_DEPLOYMENT}" --tail=100
echo

echo "Redis connectivity from webhook pod"
kubectl exec -n "${NAMESPACE}" "deployment/${WEBHOOK_DEPLOYMENT}" -- python - <<'PY'
import asyncio
import os
import redis.asyncio as redis

async def main():
    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        print(await client.ping())
    finally:
        await client.aclose()

asyncio.run(main())
PY
