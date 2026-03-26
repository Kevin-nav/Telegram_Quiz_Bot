# VPS Setup Instructions

These instructions set up a secure, low-maintenance production deployment for `@Adarkwa_Study_Bot` on a single Ubuntu 24.04 VPS using:

- `k3s` for Kubernetes
- `cloudflared` as a host-level tunnel service
- GHCR for images
- a local `systemd` timer that pulls and deploys the latest tested `main` image

This setup is intentionally pull-based:

- GitHub builds and publishes the image
- the VPS deploys it locally
- GitHub never needs your Kubernetes kubeconfig

The March 21, 2026 production incident showed that request-metered hosted Redis is not a safe fit for this bot. Production should run Redis locally on the VPS and let pods connect to it over the VPS private IP.

## Current Production State

As of March 24, 2026, the intended production shape is:

- `cloudflared` runs on the VPS host and forwards the public bot hostname to `http://localhost:80`
- K3s Traefik ingress routes `tg-bot-tanjah.sankoslides.com` to `adarkwa-bot-service`
- production Redis is VPS-local `valkey-server`
- pods reach Valkey through the VPS private IP in `REDIS_URL`
- the deploy timer is enabled and the deploy script records `last-deployed-digest` and `last-failed-digest`
- production defaults stay conservative:
  - `ENABLE_HPA=false`
  - `1` webhook replica
  - `1` worker replica

The currently known working VPS private IP is `10.226.0.2`. If the VPS network changes later, update:

- Valkey `bind`
- Kubernetes secret `REDIS_URL`
- any operator notes that mention the old private IP

Do not point a host-level `cloudflared` service at `*.svc.cluster.local`. The working production route is `cloudflared -> localhost:80 -> Traefik ingress -> adarkwa-bot-service`.

## 1. Harden the VPS First

SSH into the VPS and run:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw unattended-upgrades ca-certificates
sudo dpkg-reconfigure -plow unattended-upgrades
```

Recommended hardening:

- use SSH keys only
- disable root SSH login
- disable password authentication
- create a non-root sudo user for operations

Example SSH hardening:

```bash
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

Configure the firewall:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

Do not expose Kubernetes API port `6443` publicly.

## 2. Install K3s

Install K3s:

```bash
curl -sfL https://get.k3s.io | sh -
```

Verify the cluster:

```bash
sudo k3s kubectl get nodes
```

Prepare local `kubectl` access for your admin user:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown "$(id -u)":"$(id -g)" ~/.kube/config
chmod 600 ~/.kube/config
kubectl get nodes
```

If you do not need autoscaling immediately, you can skip enabling or depending on the included HPA manifest.

## 3. Install Cloudflared

Install `cloudflared` on the VPS:

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

Install the named tunnel service using your token:

```bash
sudo cloudflared service install <YOUR_TUNNEL_TOKEN>
sudo systemctl enable cloudflared
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
```

Your Cloudflare route should point at the local Traefik listener on the VPS:

```text
http://localhost:80
```

Do not point a host-level `cloudflared` service directly at `*.svc.cluster.local`. That DNS name only works inside Kubernetes.

Set the bot webhook base URL to your Cloudflare hostname, for example:

```text
https://tg-bot-tanjah.sankoslides.com
```

## 4. Install Local Redis Or Valkey

Prefer `valkey-server` on Ubuntu 24.04 when the package is available. If it is not available in your configured apt sources, install `redis-server` instead.

Install the package:

```bash
if apt-cache show valkey-server >/dev/null 2>&1; then
  sudo apt install -y valkey-server
  REDIS_SERVICE=valkey-server
  REDIS_CONF=/etc/valkey/valkey.conf
  REDIS_DATA_DIR=/var/lib/valkey
else
  sudo apt install -y redis-server
  REDIS_SERVICE=redis-server
  REDIS_CONF=/etc/redis/redis.conf
  REDIS_DATA_DIR=/var/lib/redis
fi
```

Bind the service so the VPS itself and K3s pods can reach it through the VPS private IP. Replace `10.0.0.5` with your actual private address. The current known production value is `10.226.0.2`.

```bash
sudo sed -i 's/^bind .*/bind 127.0.0.1 10.0.0.5/' "${REDIS_CONF}"
sudo sed -i 's/^protected-mode .*/protected-mode yes/' "${REDIS_CONF}"
sudo sed -i 's/^# requirepass .*/requirepass <STRONG_REDIS_PASSWORD>/' "${REDIS_CONF}"
```

Enable append-only persistence:

```bash
sudo sed -i 's/^appendonly .*/appendonly yes/' "${REDIS_CONF}"
sudo sed -i 's/^appendfsync .*/appendfsync everysec/' "${REDIS_CONF}"
sudo systemctl enable "${REDIS_SERVICE}"
sudo systemctl restart "${REDIS_SERVICE}"
sudo systemctl status "${REDIS_SERVICE}"
```

Verify locally on the VPS:

```bash
valkey-cli -h 127.0.0.1 -a '<STRONG_REDIS_PASSWORD>' ping
valkey-cli -h 10.0.0.5 -a '<STRONG_REDIS_PASSWORD>' info memory
```

If `valkey-cli` is not installed in your image, install the compatibility package:

```bash
sudo apt install -y valkey-redis-compat
```

Operational commands:

```bash
sudo systemctl restart "${REDIS_SERVICE}"
sudo systemctl status "${REDIS_SERVICE}"
valkey-cli -h 127.0.0.1 -a '<STRONG_REDIS_PASSWORD>' info memory
valkey-cli -h 127.0.0.1 -a '<STRONG_REDIS_PASSWORD>' info persistence
sudo ls -lh "${REDIS_DATA_DIR}"
```

Alert conditions that matter:

- Redis stops accepting authenticated connections
- memory use approaches the VPS limit
- AOF or RDB persistence stops updating
- webhook readiness degrades because Redis ping fails

Back up persistence files before risky maintenance:

```bash
sudo tar -czf "/var/backups/adarkwa-redis-$(date +%F-%H%M%S).tar.gz" "${REDIS_DATA_DIR}"
```

## 5. Prepare a Dedicated Deploy Checkout

Create a dedicated deployment workspace:

```bash
sudo mkdir -p /opt/adarkwa-study-bot-deploy
sudo chown "$USER":"$USER" /opt/adarkwa-study-bot-deploy
cd /opt/adarkwa-study-bot-deploy
git clone --branch main --single-branch https://github.com/Kevin-nav/Telegram_Quiz_Bot.git repo
```

This checkout is only for deployment automation. Do not use your personal development checkout for the timer-driven deploy process.

## 6. Create Kubernetes Runtime Secrets from the VPS

Create the namespace first:

```bash
kubectl apply -f /opt/adarkwa-study-bot-deploy/repo/k8s/namespace.yaml
```

Create the application secret directly from the VPS:

```bash
kubectl create secret generic adarkwa-bot-secret \
  --namespace adarkwa-study-bot \
  --from-literal=TELEGRAM_BOT_TOKEN='<YOUR_TELEGRAM_BOT_TOKEN>' \
  --from-literal=DATABASE_URL='<YOUR_DATABASE_URL>' \
  --from-literal=REDIS_URL='redis://:<STRONG_REDIS_PASSWORD>@10.0.0.5:6379/0' \
  --from-literal=WEBHOOK_URL='https://tg-bot-tanjah.sankoslides.com' \
  --from-literal=WEBHOOK_SECRET='<YOUR_WEBHOOK_SECRET>' \
  --from-literal=SENTRY_DSN='' \
  --from-literal=R2_ACCOUNT_ID='' \
  --from-literal=R2_ACCESS_KEY_ID='' \
  --from-literal=R2_SECRET_ACCESS_KEY='' \
  --from-literal=R2_BUCKET_NAME='' \
  --from-literal=R2_PUBLIC_BASE_URL='' \
  --dry-run=client \
  -o yaml | kubectl apply -f -
```

You only need to rerun this when secret values change.

Use the VPS private IP directly in `REDIS_URL` unless you have already created a stable host alias that every pod resolves the same way.

If you are only rotating or fixing Redis, you do not need to recreate the whole secret. Patch just `REDIS_URL`:

```bash
kubectl patch secret adarkwa-bot-secret \
  -n adarkwa-study-bot \
  --type merge \
  -p '{"stringData":{"REDIS_URL":"redis://:<STRONG_REDIS_PASSWORD>@10.0.0.5:6379/0"}}'
```

## 7. Prepare GHCR Pull Access

Recommended:

- keep the GHCR package private
- create a fine-grained GitHub token with read-only package access
- store that token on the VPS only

Create a token file:

```bash
sudo mkdir -p /etc/adarkwa-study-bot
printf '%s' '<YOUR_GHCR_READ_TOKEN>' | sudo tee /etc/adarkwa-study-bot/ghcr-token >/dev/null
sudo chmod 600 /etc/adarkwa-study-bot/ghcr-token
```

Create the Kubernetes image pull secret:

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace adarkwa-study-bot \
  --docker-server ghcr.io \
  --docker-username '<YOUR_GITHUB_USERNAME>' \
  --docker-password "$(sudo cat /etc/adarkwa-study-bot/ghcr-token)" \
  --dry-run=client \
  -o yaml | kubectl apply -f -

kubectl patch serviceaccount default \
  --namespace adarkwa-study-bot \
  --type merge \
  --patch '{"imagePullSecrets":[{"name":"ghcr-pull-secret"}]}'
```

If you later make the GHCR package public, this pull secret becomes optional.

## 8. Install the Local Deploy Agent

The deploy agent polls GHCR for the digest behind `:latest`, then deploys locally with `kubectl`.

Install the required registry helper:

```bash
CRANE_VERSION=v0.20.3
curl -fsSL "https://github.com/google/go-containerregistry/releases/download/${CRANE_VERSION}/go-containerregistry_Linux_x86_64.tar.gz" \
  | sudo tar -xz -C /usr/local/bin crane
crane version
```

Copy the deploy assets from the repo:

```bash
sudo cp /opt/adarkwa-study-bot-deploy/repo/ops/deploy/adarkwa-bot-deploy.sh /usr/local/bin/adarkwa-bot-deploy.sh
sudo chmod 755 /usr/local/bin/adarkwa-bot-deploy.sh
sudo cp /opt/adarkwa-study-bot-deploy/repo/ops/deploy/adarkwa-bot-deploy.service /etc/systemd/system/adarkwa-bot-deploy.service
sudo cp /opt/adarkwa-study-bot-deploy/repo/ops/deploy/adarkwa-bot-deploy.timer /etc/systemd/system/adarkwa-bot-deploy.timer
```

Create the deploy environment file:

```bash
sudo tee /etc/adarkwa-study-bot/deploy.env >/dev/null <<'EOF'
NAMESPACE=adarkwa-study-bot
IMAGE_REPO=ghcr.io/<github-owner>/adarkwa-study-bot
TRACKING_TAG=latest
REPO_URL=<YOUR_REPO_CLONE_URL>
REPO_BRANCH=main
DEPLOY_ROOT=/opt/adarkwa-study-bot-deploy
WORKTREE_DIR=/opt/adarkwa-study-bot-deploy/repo
STATE_DIR=/opt/adarkwa-study-bot-deploy/state
RENDER_DIR=/opt/adarkwa-study-bot-deploy/rendered
GHCR_USERNAME=<YOUR_GITHUB_USERNAME>
GHCR_TOKEN_FILE=/etc/adarkwa-study-bot/ghcr-token
WEBHOOK_DEPLOYMENT=adarkwa-bot-webhook
WORKER_DEPLOYMENT=adarkwa-bot-worker
MIGRATION_PREFIX=adarkwa-bot-migrate
ENABLE_HPA=false
EOF
```

Enable and start the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now adarkwa-bot-deploy.timer
sudo systemctl start adarkwa-bot-deploy.service
```

Ensure the ingress exists so Traefik can route the public hostname to the bot service:

```bash
kubectl apply -f /opt/adarkwa-study-bot-deploy/repo/k8s/ingress.yaml
kubectl get ingress -n adarkwa-study-bot
```

## 9. Cut Over To The VPS-local Redis Endpoint

Use this exact order:

1. Install `valkey-server` or `redis-server`.
2. Verify the service is healthy on the VPS with `redis-cli`.
3. Update the Kubernetes secret so `REDIS_URL` points at the VPS private IP.
4. Restart the deployment service.
5. Verify webhook and worker readiness.
6. Confirm Telegram still reports the correct webhook URL.

Example cutover commands:

```bash
kubectl create secret generic adarkwa-bot-secret \
  --namespace adarkwa-study-bot \
  --from-literal=TELEGRAM_BOT_TOKEN='<YOUR_TELEGRAM_BOT_TOKEN>' \
  --from-literal=DATABASE_URL='<YOUR_DATABASE_URL>' \
  --from-literal=REDIS_URL='redis://:<STRONG_REDIS_PASSWORD>@10.0.0.5:6379/0' \
  --from-literal=WEBHOOK_URL='https://tg-bot-tanjah.sankoslides.com' \
  --from-literal=WEBHOOK_SECRET='<YOUR_WEBHOOK_SECRET>' \
  --dry-run=client -o yaml | kubectl apply -f -

sudo systemctl start adarkwa-bot-deploy.service
kubectl rollout status deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-worker -n adarkwa-study-bot
curl -s "https://api.telegram.org/bot<token>/getWebhookInfo"
```

For the current production setup, a direct rollout restart is enough after a `REDIS_URL` patch:

```bash
kubectl rollout restart deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout restart deployment/adarkwa-bot-worker -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-worker -n adarkwa-study-bot
```

If the rollout has already marked the digest as failed, clear the guard and rerun:

```bash
sudo rm -f /opt/adarkwa-study-bot-deploy/state/last-failed-digest
sudo systemctl start adarkwa-bot-deploy.service
```

## 10. Update GitHub Actions Secrets

You no longer need `KUBE_CONFIG_B64` for production deployments.

GitHub only needs enough access to build and publish images to GHCR. For this repo, the workflow can use the default `GITHUB_TOKEN`.

Do not store these runtime app secrets in GitHub just for deployment:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET`

Keep them on the VPS and in Kubernetes instead.

## 11. Trigger the First Deployment

Push a change to `main`.

GitHub Actions will:

1. run tests
2. build the image
3. push:
   - `ghcr.io/<owner>/adarkwa-study-bot:<git-sha>`
   - `ghcr.io/<owner>/adarkwa-study-bot:latest`

The VPS timer will notice the new `latest` digest and deploy it automatically within a few minutes.

If you want to trigger immediately:

```bash
sudo systemctl start adarkwa-bot-deploy.service
```

## 12. Verify Everything

Check the tunnel:

```bash
sudo systemctl status cloudflared
```

Check the deploy timer:

```bash
systemctl status adarkwa-bot-deploy.timer
systemctl status adarkwa-bot-deploy.service
journalctl -u adarkwa-bot-deploy.service -n 100 --no-pager
```

Check Kubernetes:

```bash
kubectl get pods -n adarkwa-study-bot
kubectl get jobs -n adarkwa-study-bot
kubectl get svc -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-worker -n adarkwa-study-bot
kubectl logs -n adarkwa-study-bot deployment/adarkwa-bot-webhook --tail=100
```

Check the public webhook URL:

```bash
curl -I https://tg-bot-tanjah.sankoslides.com/health
curl -s "https://api.telegram.org/bot<token>/getWebhookInfo"
```

Notes:

- `last_error_message` in `getWebhookInfo` can be historical even after recovery
- if Telegram is responding normally and `pending_update_count` is `0`, an old `503` message alone does not prove the bot is still broken

Verify pod-to-Redis connectivity from inside Kubernetes:

```bash
kubectl exec -n adarkwa-study-bot deployment/adarkwa-bot-webhook -- python - <<'PY'
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
```

## 13. Ongoing Maintenance

Normal deploy flow:

1. push to `main`
2. GitHub publishes the image
3. VPS deploys it automatically

Routine maintenance stays small:

- rotate the GHCR read token if needed
- update Kubernetes secret values only when app secrets change
- occasionally update `cloudflared`, K3s, and system packages

Operational defaults in this repo intentionally keep production conservative on one VPS:

- one webhook replica
- one worker replica
- HPA disabled unless you explicitly set `ENABLE_HPA=true`
- failed digests are not retried forever by the timer

For a compact post-deploy checklist, you can also run:

```bash
/opt/adarkwa-study-bot-deploy/repo/scripts/production_smoke_check.sh
```

The script loads `/etc/adarkwa-study-bot/deploy.env` automatically when available and reads `TELEGRAM_BOT_TOKEN` from the `adarkwa-bot-secret` Kubernetes secret if you have not exported it in the shell.

## 14. What Actually Requires Changes

Use this as the operator decision table.

Change `main` only:

- normal application code changes
- tests
- manifests already tracked by the deploy script

Change the VPS and then restart workloads:

- Valkey password rotation
- VPS private IP change
- `REDIS_URL` cutover or correction
- Cloudflare tunnel token rotation
- `/etc/adarkwa-study-bot/deploy.env` changes

Change Kubernetes secret only:

- Telegram token rotation
- database URL rotation
- Redis password or host change
- webhook secret rotation
- R2 key rotation

Change Cloudflare only:

- tunnel token rotation
- public hostname changes
- tunnel origin target changes

Current expected steady state after any healthy rollout:

- `kubectl get pods -n adarkwa-study-bot` shows `1/1 Running` for webhook and worker
- `curl -I https://tg-bot-tanjah.sankoslides.com/health` returns `200`
- `getWebhookInfo` shows `https://tg-bot-tanjah.sankoslides.com/webhook`

You do not need:

- a self-hosted GitHub runner
- a public Kubernetes API
- kubeconfig secrets in GitHub Actions
