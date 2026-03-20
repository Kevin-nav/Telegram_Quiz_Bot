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
- outbound access to GitHub, GHCR, Cloudflare, Telegram, Neon, and Redis
- the `adarkwa-study-bot` namespace
- an application secret created from the VPS

### 3.3. Kubernetes Secrets

Create `adarkwa-bot-secret` from the VPS with values such as:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET`
- optional Sentry and R2 settings

Do not regenerate these secrets from GitHub Actions on every deploy.

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
- the in-cluster service DNS name as the tunnel target

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

Why this is preferred:

- no self-hosted runner to maintain
- no public Kubernetes API
- no cluster credentials in GitHub
- migration-before-rollout stays explicit and easy to debug

## 6. First Deployment Checklist

1. Harden the VPS and enable `ufw`.
2. Install K3s and confirm `kubectl get nodes` works locally.
3. Install `cloudflared` with your tunnel token.
4. Clone the repo into the dedicated deploy directory.
5. Create the Kubernetes runtime secret from the VPS.
6. Create the GHCR pull secret if the image package is private.
7. Install `crane`, the deploy script, and the `systemd` timer.
8. Push to `main`.
9. Confirm the new image is published and deployed.

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
```

## 8. Security Notes

Recommended baseline:

- no public inbound access to Kubernetes API port `6443`
- no kubeconfig stored in GitHub Secrets
- SSH keys only
- disabled password authentication
- GHCR read-only token stored on the VPS only
- runtime app secrets stored in Kubernetes, created from the VPS

## 9. Troubleshooting

### The deploy timer does not update

Check:

- `systemctl status adarkwa-bot-deploy.timer`
- `journalctl -u adarkwa-bot-deploy.service`
- whether the GHCR token is valid

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

## 10. Recommended Order of Operations

If you want the cleanest production path, do this in order:

1. harden the VPS
2. install K3s
3. install Cloudflare Tunnel
4. create the Kubernetes runtime secret
5. create the GHCR pull secret
6. install the local deploy agent
7. push to `main`
8. verify rollout
