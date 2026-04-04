# Deployment Setup Guide

This guide covers the recommended production deployment shape for `@Adarkwa_Study_Bot`:

- GitHub Actions for CI and image publishing
- GitHub Container Registry for images
- K3s on a VPS for runtime
- Kubernetes for the webhook, worker, and migration job
- Cloudflare Tunnel for the Telegram webhook hostname
- a pull-based deploy agent on the VPS

The deployment flow is:

1. Push to `main`
2. GitHub Actions runs tests
3. GitHub Actions builds and pushes the image to GHCR
4. The VPS deploy agent detects the new `latest` digest
5. The VPS applies Kubernetes manifests locally
6. The VPS runs database migrations
7. The VPS rolls out the webhook and worker deployments

For the shared admin UI, keep the first-deploy sequence explicit:

1. run database migrations
2. bootstrap the first super-admin
3. deploy the backend web process
4. deploy or serve the admin frontend
5. sign in through the shared admin URL and complete the forced password change if prompted

## 0. Production Incident And Target Shape

The March 21, 2026 rollout incident exposed an unsafe production dependency chain:

1. `main` was pushed.
2. Image publishing to GHCR succeeded.
3. The deploy timer started a rollout.
4. New webhook and worker pods exhausted or were rejected by the request-metered Redis tier.
5. Webhook readiness failed and Telegram saw `503`.
6. Without a failed-digest guard, the timer would retry the same digest again on later ticks.

The target production shape keeps K3s, Cloudflare Tunnel, and pull-based GHCR deployment the same, but replaces hosted metered Redis with a VPS-local Redis-compatible service:

- prefer `valkey-server` on Ubuntu 24.04
- use `redis-server` if Valkey is not packaged
- secure it with password auth and persistence
- reach it from pods through the VPS private IP recorded in `REDIS_URL`

Production defaults stay conservative:

- `1` webhook replica
- `1` worker replica
- HPA disabled unless `ENABLE_HPA=true`

## 0.1. Current Working Production State

The deployment model described in this repo is no longer a planned target. It is the current intended production state:

- GitHub Actions publishes GHCR images from `main`
- the VPS deploy timer pulls and deploys the new digest
- `cloudflared` on the VPS points to `http://localhost:80`
- Traefik ingress routes `tg-bot-tanjah.sankoslides.com` to `adarkwa-bot-service`
- Kubernetes webhook and worker deployments run with conservative defaults
- Redis is a VPS-local `valkey-server` instance, not Upstash or another request-capped tier

The currently known working VPS-private endpoint is:

```text
10.226.0.2:6379
```

That value should be treated as an environment fact, not a repo constant. If the VPS address changes later, update:

- Valkey `bind`
- Kubernetes secret `REDIS_URL`
- any runbooks that mention the old IP

## 1. What Gets Deployed

The repo contains:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `k8s/namespace.yaml`
- `k8s/config.yaml`
- `k8s/deployment.yaml`
- `k8s/service.yaml`
- `k8s/ingress.yaml`
- `k8s/hpa.yaml`
- `k8s/migration-job.yaml`
- `ops/deploy/adarkwa-bot-deploy.sh`
- `ops/deploy/adarkwa-bot-deploy.service`
- `ops/deploy/adarkwa-bot-deploy.timer`

At deploy time:

- `k8s/config.yaml` provides non-secret runtime values
- the Kubernetes secret already present in the cluster supplies runtime secrets
- the VPS deploy script renders the deployment and migration job with the exact image digest to deploy
- production defaults keep one webhook and one worker replica on a single VPS unless you explicitly enable HPA

## 2. GitHub Setup

### 2.1. GitHub Actions Role

GitHub Actions is responsible for:

- running tests
- building the production image
- publishing immutable and tracking tags to GHCR

GitHub Actions is not responsible for:

- storing kubeconfig
- connecting directly to the cluster
- creating runtime Kubernetes secrets

### 2.2. GHCR Images

The workflow publishes:

```text
ghcr.io/<github-owner>/adarkwa-study-bot:<git-sha>
ghcr.io/<github-owner>/adarkwa-study-bot:latest
```

The VPS deploy agent watches `:latest` and deploys the underlying digest.

### 2.3. GitHub Secrets

For this deployment model, GitHub does not need `KUBE_CONFIG_B64`.

The default `GITHUB_TOKEN` is sufficient for the workflow to push the image package as long as workflow package write permissions remain enabled.

If you later add signing, notifications, or release promotion steps, those may require extra GitHub secrets, but runtime app secrets should stay off GitHub for production deployment.

## 3. VPS and Kubernetes Setup

### 3.1. Minimum VPS Shape

Recommended minimum:

- 2 vCPU
- 4 GB RAM
- Ubuntu 24.04 LTS

### 3.2. Kubernetes Requirements

Your VPS-hosted K3s cluster should have:

- working local `kubectl` access
- outbound access to GitHub, GHCR, Cloudflare, Telegram, and Neon
- the `adarkwa-study-bot` namespace
- an application secret created from the VPS
- network reachability from pods to the VPS-local Redis listener

### 3.3. Kubernetes Secrets

Create `adarkwa-bot-secret` from the VPS with values such as:

- `TELEGRAM_BOT_TOKEN` or `TANJAH_BOT_TOKEN`
- `ADARKWA_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET` or `TANJAH_WEBHOOK_SECRET`
- `ADARKWA_WEBHOOK_SECRET`
- optional Sentry and R2 settings

Do not regenerate these secrets from GitHub Actions on every deploy.

For the Redis cutover, the Kubernetes secret should use the VPS-local endpoint directly, for example:

```text
REDIS_URL=redis://:<strong-password>@10.0.0.5:6379/0
```

Use the VPS private IP unless you have already set up a different stable host alias for the cluster.

When only Redis changes, prefer patching just `REDIS_URL` instead of recreating the full secret.

For the shared admin UI, also configure:

- `ADMIN_ALLOWED_ORIGINS`
- `ADMIN_SESSION_COOKIE_DOMAIN`

These are non-secret runtime values and can live in `k8s/config.yaml` or the deploy-agent env file depending on your rollout shape.

### 3.4. Image Pull Strategy

Recommended:

- keep GHCR private
- create a read-only package token
- store it only on the VPS
- create a Kubernetes `docker-registry` pull secret once

If the package is public, the cluster pull secret becomes optional.

## 4. Cloudflare and Domain Setup

### 4.1. Recommended Production Shape

Use:

- a named Cloudflare Tunnel
- your real production hostname
- the VPS-local Traefik listener as the tunnel target

Recommended Cloudflare Tunnel target for a host-level `cloudflared` service:

```text
http://localhost:80
```

Recommended webhook base URL:

```text
https://tg-bot-tanjah.sankoslides.com
```

### 4.2. Why This Shape

- Telegram gets a stable HTTPS endpoint
- the app remains internal to the cluster
- Traefik on K3s handles hostname routing through `k8s/ingress.yaml`
- the VPS does not need a public node port for this bot

## 5. Deploy Agent Model

The VPS deploy agent runs as a `systemd` one-shot service plus timer.

Responsibilities:

- check the digest for `ghcr.io/<owner>/adarkwa-study-bot:latest`
- refresh a dedicated checkout at `origin/main`
- render the deployment and migration manifests with the immutable image digest
- apply namespace, config, and service manifests
- run the migration job
- wait for the migration job to complete
- apply the deployment manifest
- wait for webhook and worker rollout success
- record the last deployed digest locally
- stop automatically retrying the same failed digest on every timer tick

Why this is preferred:

- no self-hosted runner to maintain
- no public Kubernetes API
- no cluster credentials in GitHub
- migration-before-rollout stays explicit and easy to debug
- a failed rollout does not create endless migration/redeploy loops for the same image

## 6. First Deployment Checklist

1. Harden the VPS and enable `ufw`.
2. Install K3s and confirm `kubectl get nodes` works locally.
3. Install `cloudflared` with your tunnel token.
4. Clone the repo into the dedicated deploy directory.
5. Create the Kubernetes runtime secret from the VPS.
6. Create the GHCR pull secret if the image package is private.
7. Install and verify VPS-local `valkey-server` or `redis-server`.
8. Install `crane`, the deploy script, and the `systemd` timer.
9. Leave `ENABLE_HPA=false` unless you have verified Redis and VPS headroom.
10. Push to `main`.
11. Confirm the new image is published and deployed.

## 7. Ongoing Deployment Flow

Normal production deployment:

1. push changes to `main`
2. GitHub runs tests and publishes the image
3. the VPS timer detects the new digest
4. the VPS performs the deployment locally

Useful commands:

```bash
systemctl status adarkwa-bot-deploy.timer
systemctl status adarkwa-bot-deploy.service
journalctl -u adarkwa-bot-deploy.service -n 100 --no-pager
kubectl rollout status deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-worker -n adarkwa-study-bot
kubectl logs job/<migration-job-name> -n adarkwa-study-bot
curl -s "https://api.telegram.org/bot<token>/getWebhookInfo"
```

Optional helper:

```bash
./scripts/production_smoke_check.sh
```

The helper auto-loads `/etc/adarkwa-study-bot/deploy.env` when present and falls back to the `adarkwa-bot-secret` Kubernetes secret for `TELEGRAM_BOT_TOKEN`, so operators can run it directly on the VPS after the normal deployment setup.

Useful production recovery commands when only Redis or webhook state needs correction:

```bash
kubectl patch secret adarkwa-bot-secret -n adarkwa-study-bot --type merge -p '{"stringData":{"REDIS_URL":"redis://:<strong-password>@10.226.0.2:6379/0"}}'
kubectl rollout restart deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout restart deployment/adarkwa-bot-worker -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-worker -n adarkwa-study-bot
```

## 8. Security Notes

Recommended baseline:

- no public inbound access to Kubernetes API port `6443`
- no kubeconfig stored in GitHub Secrets
- SSH keys only
- disabled password authentication
- GHCR read-only token stored on the VPS only
- runtime app secrets stored in Kubernetes, created from the VPS

## 9. Capacity Notes

This bot currently treats Redis as a critical runtime dependency for:

- ARQ job queueing
- idempotency
- hot state

Do not use a request-capped or free Redis tier for production if you want reliable auto-deployments and stable bot uptime. Use a VPS-local Redis-compatible service with persistence and password auth.

## 10. Troubleshooting

### The deploy timer does not update

Check:

- `systemctl status adarkwa-bot-deploy.timer`
- `journalctl -u adarkwa-bot-deploy.service`
- whether the GHCR token is valid
- whether `/opt/adarkwa-study-bot-deploy/state/last-failed-digest` exists for the current image

Manual recovery commands:

```bash
sudo rm -f /opt/adarkwa-study-bot-deploy/state/last-failed-digest
sudo systemctl start adarkwa-bot-deploy.service
kubectl scale deployment/adarkwa-bot-webhook deployment/adarkwa-bot-worker \
  --namespace adarkwa-study-bot \
  --replicas=1
```

### The cluster cannot pull the image

Check:

- whether the GHCR package is private or public
- whether `ghcr-pull-secret` exists
- whether the namespace service account references the image pull secret

### The migration job fails

Check:

- `DATABASE_URL`
- database reachability from the VPS
- Alembic logs from the migration job

### The webhook is unreachable

Check:

- `systemctl status cloudflared`
- the Cloudflare route target
- the Kubernetes service and webhook pod health
- whether VPS-local Redis is reachable from the pod and accepting authenticated connections

### Post-deploy Smoke Checks

Run these after any production rollout:

```bash
crane digest ghcr.io/<github-owner>/adarkwa-study-bot:latest
cat /opt/adarkwa-study-bot-deploy/state/last-deployed-digest
kubectl get pods -n adarkwa-study-bot
kubectl logs -n adarkwa-study-bot deployment/adarkwa-bot-webhook --tail=100
./scripts/production_smoke_check.sh
curl -s "https://api.telegram.org/bot<token>/getWebhookInfo"
```

Interpretation notes:

- `pending_update_count=0` is a stronger health signal than an old `last_error_message`
- Telegram may continue to show a historical `503` or `502` even after the bot is healthy again
- if `/health` is `200`, pods are `Running`, and Telegram traffic works, the old message is stale noise rather than current failure

## 11. Recommended Order of Operations

If you want the cleanest production path, do this in order:

1. harden the VPS
2. install K3s
3. install Cloudflare Tunnel
4. create the Kubernetes runtime secret
5. create the GHCR pull secret
6. install the local deploy agent
7. install and verify VPS-local Redis or Valkey
8. update the `adarkwa-bot-secret` `REDIS_URL`
9. push to `main`
10. verify rollout

For the admin platform specifically:

1. run `alembic upgrade head`
2. run `python scripts/bootstrap_admin.py --email <admin-email>`
3. verify the backend serves `/admin/*`
4. verify the admin frontend points at the backend origin through `NEXT_PUBLIC_ADMIN_API_BASE_URL`
5. verify `ADMIN_ALLOWED_ORIGINS` includes the frontend origin
6. set `ADMIN_SESSION_COOKIE_DOMAIN` only when you need cross-subdomain cookie sharing

## 12. Operator Change Matrix

Use this when deciding whether a change belongs in GitHub, Kubernetes, Cloudflare, or the VPS itself.

Repo-only changes:

- application code
- tests
- deployment manifests already consumed by the deploy script
- docs

VPS changes:

- Valkey installation or password rotation
- `/etc/adarkwa-study-bot/deploy.env`
- `cloudflared` service token rotation
- `/usr/local/bin/adarkwa-bot-deploy.sh` refresh after deploy-script changes

Kubernetes secret changes:

- `TELEGRAM_BOT_TOKEN` or `TANJAH_BOT_TOKEN`
- `ADARKWA_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_SECRET` or `TANJAH_WEBHOOK_SECRET`
- `ADARKWA_WEBHOOK_SECRET`
- R2 credentials

Cloudflare changes:

- tunnel token
- public hostname
- tunnel origin target

One important rule:

- a push to `main` is enough for normal code deployments
- a push to `main` is not enough for runtime secret changes or VPS service changes
