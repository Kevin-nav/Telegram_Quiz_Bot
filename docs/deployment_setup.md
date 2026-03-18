# Deployment Setup Guide

This guide covers the full production deployment setup for `@Adarkwa_Study_Bot` on a VPS-hosted Kubernetes cluster with:

- GitHub Actions for CI/CD
- GitHub Container Registry for images
- GitHub Secrets as the source of truth for runtime secrets
- Kubernetes for the web app, worker, and migrations
- Cloudflare Tunnel and your own domain for the Telegram webhook

The deployment flow is:

1. Push to `main` or `master`
2. GitHub Actions runs tests
3. GitHub Actions builds and pushes the Docker image to GHCR
4. GitHub Actions applies config and secrets to Kubernetes
5. GitHub Actions runs database migrations
6. GitHub Actions rolls out the web and worker deployments

## 1. What Gets Deployed

The repo now contains:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `k8s/namespace.yaml`
- `k8s/config.yaml`
- `k8s/deployment.yaml`
- `k8s/service.yaml`
- `k8s/hpa.yaml`
- `k8s/migration-job.yaml`

At deploy time:

- `k8s/config.yaml` provides non-secret runtime values
- GitHub Actions creates `adarkwa-bot-secret` in Kubernetes from GitHub Secrets
- the deployment manifest is rendered with the exact image tag for the commit being deployed

## 2. GitHub Setup

### 2.1. Repository Secrets

Add these secrets in GitHub:

GitHub repository -> `Settings` -> `Secrets and variables` -> `Actions`

Required:

- `KUBE_CONFIG_B64`
- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET`

Optional:

- `SENTRY_DSN`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_PUBLIC_BASE_URL`
- `GHCR_PULL_USERNAME`
- `GHCR_PULL_TOKEN`

### 2.2. GitHub Container Registry

The workflow publishes images to:

```text
ghcr.io/<github-owner>/adarkwa-study-bot:<git-sha>
ghcr.io/<github-owner>/adarkwa-study-bot:latest
```

You have two choices:

1. Make the GHCR package public
2. Keep the GHCR package private and supply:
   - `GHCR_PULL_USERNAME`
   - `GHCR_PULL_TOKEN`

If the package is private, the deploy workflow creates a Kubernetes docker-registry pull secret and patches the default service account in the namespace to use it.

### 2.3. Kubeconfig Secret

`KUBE_CONFIG_B64` must be the base64-encoded kubeconfig for your target cluster.

Linux/macOS:

```bash
base64 -w 0 ~/.kube/config
```

PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$HOME\.kube\config"))
```

Paste the resulting single-line value into the GitHub secret.

### 2.4. Workflow Permissions

The deploy workflow uses:

- repository read access
- package write access for GHCR

No extra GitHub App or cloud IAM integration is required for this setup because the cluster is accessed using the kubeconfig secret.

## 3. VPS and Kubernetes Setup

### 3.1. Minimum Cluster Requirements

Your VPS-hosted Kubernetes cluster should have:

- a working Kubernetes control plane
- DNS/network access to Neon, Redis, Telegram, GitHub, and Cloudflare
- outbound HTTPS access
- enough resources for:
  - 2 web replicas
  - 2 worker replicas
  - 1 migration job during deploy

Recommended minimum:

- 2 vCPU
- 4 GB RAM

### 3.2. Kubernetes Requirements

Make sure the cluster has:

- `kubectl` access working from your admin machine
- metrics-server installed if you want the included HPA resources to function correctly

The workflow creates the namespace automatically, so you do not need to create `adarkwa-study-bot` by hand unless you want to inspect it before first deploy.

### 3.3. Image Pull Strategy

If GHCR is public:

- no cluster-side image pull secret is required

If GHCR is private:

- add `GHCR_PULL_USERNAME`
- add `GHCR_PULL_TOKEN`
- the deploy workflow will create/update the `ghcr-pull-secret` Kubernetes secret automatically

### 3.4. Database and Redis

Before first deploy, confirm:

- the Neon/Postgres database exists
- the Redis instance exists
- both are reachable from the VPS cluster region
- the connection strings are correct and production-ready

For best latency:

- place the VPS, Redis, and database in the same region where possible

## 4. Cloudflare and Domain Setup

### 4.1. Why This Matters

For Telegram webhooks, a stable HTTPS endpoint is required. Quick/free local tunnels are fine for testing, but production should use:

- your own domain
- a named Cloudflare Tunnel

### 4.2. Recommended Production Shape

Use one of these:

1. Cloudflare Tunnel running in-cluster or on the VPS, targeting your Kubernetes ingress/service path
2. An ingress controller on the cluster, with Cloudflare proxying the public hostname to it

The important outcome is:

- Telegram sees a stable HTTPS URL
- that URL forwards to the `adarkwa-bot-service` webhook path

### 4.3. Webhook URL Secret

Set `WEBHOOK_URL` in GitHub Secrets to the public HTTPS base URL for the bot, for example:

```text
https://bot.yourdomain.com
```

The application will use this when registering the Telegram webhook.

## 5. First Deployment Checklist

### Step 1: Confirm local cluster access

Run locally:

```bash
kubectl get nodes
```

Expected:

- your VPS cluster responds successfully

### Step 2: Base64-encode kubeconfig

Generate `KUBE_CONFIG_B64` and add it to GitHub Secrets.

### Step 3: Add all required GitHub secrets

Do not skip:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET`

### Step 4: Decide on GHCR visibility

Choose one:

- public package
- private package with `GHCR_PULL_USERNAME` and `GHCR_PULL_TOKEN`

### Step 5: Push to `main` or `master`

The workflow will:

- test
- build
- push image
- apply namespace/config/secrets
- run migration
- roll out web and worker

### Step 6: Verify rollout

Run:

```bash
kubectl get pods -n adarkwa-study-bot
kubectl get jobs -n adarkwa-study-bot
kubectl get svc -n adarkwa-study-bot
```

Expected:

- web pods running
- worker pods running
- migration job completed
- service present

## 6. Ongoing Deployment Flow

After first setup, normal deployment is simple:

1. push changes to `main` or `master`
2. GitHub Actions deploys automatically
3. verify rollout in the Actions tab and with `kubectl rollout status`

Useful commands:

```bash
kubectl rollout status deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-worker -n adarkwa-study-bot
kubectl logs deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl logs deployment/adarkwa-bot-worker -n adarkwa-study-bot
```

## 7. Troubleshooting

### GitHub Actions deploy fails before cluster access

Check:

- `KUBE_CONFIG_B64` is valid
- the kubeconfig points at the correct cluster
- the cluster is reachable from GitHub-hosted runners

### Pods cannot pull image

Check:

- GHCR package visibility
- `GHCR_PULL_USERNAME`
- `GHCR_PULL_TOKEN`
- whether `ghcr-pull-secret` exists in namespace `adarkwa-study-bot`

### Migration job fails

Check:

- `DATABASE_URL`
- database reachability from the cluster
- Alembic state and logs

View logs:

```bash
kubectl logs job/<migration-job-name> -n adarkwa-study-bot
```

### Webhook registers but Telegram feels slow

Check:

- Redis and database region placement
- Cloudflare tunnel placement
- whether the app is still routing through a local/dev tunnel

Production performance will be much better with:

- VPS-hosted web app
- same-region Redis
- same-region database
- named Cloudflare Tunnel

## 8. Recommended Order of Operations

If you want the cleanest setup path, do this in order:

1. prepare the VPS Kubernetes cluster
2. verify `kubectl` access locally
3. set up the real domain and Cloudflare Tunnel
4. add GitHub Secrets
5. choose GHCR public or private
6. push to `main` or `master`
7. verify rollout
8. update Telegram webhook if needed by redeploying with the final `WEBHOOK_URL`
