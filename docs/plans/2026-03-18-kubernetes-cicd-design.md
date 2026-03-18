# Kubernetes CI/CD Design

## Goal

Deploy `@Adarkwa_Study_Bot` to a VPS-hosted Kubernetes cluster with a push-to-deploy flow:

- every push to `main` or `master` runs CI
- successful pushes build and publish a container image to GitHub Container Registry
- GitHub Actions deploys the new image to the cluster using a kubeconfig stored in GitHub Secrets
- application secrets live in GitHub Secrets and are synchronized into Kubernetes during deploy

## Chosen Approach

Use `GitHub Actions + GHCR + kubeconfig deploy + Cloudflare Tunnel to ClusterIP`.

This keeps the cluster simple and avoids introducing Argo CD, Flux, or Sealed Secrets in the first production slice. It also matches the current Kubernetes manifests and lets the team keep GitHub as the source of truth for both releases and secrets.

## Architecture

### Release Flow

1. A push reaches `main` or `master`.
2. GitHub Actions runs tests.
3. If tests pass, GitHub Actions builds the Docker image and pushes immutable tags to GHCR.
4. GitHub Actions connects to the VPS Kubernetes cluster using `KUBE_CONFIG_B64`.
5. The workflow applies the namespace, ConfigMap, Service, HPAs, and Deployments.
6. The workflow recreates the Kubernetes `Secret` from GitHub Secrets.
7. The workflow updates the web and worker deployments to the new image tag.
8. The workflow runs an Alembic migration job for the same image tag.
9. The workflow waits for rollout success.

### Secret Model

GitHub Secrets are the operational source of truth. During deployment, the workflow generates the Kubernetes secret object and applies it to the cluster. This means secrets are not committed to the repo and do not need to be manually managed on the VPS.

### Networking Model

- The app remains a `ClusterIP` service inside the cluster.
- A named Cloudflare Tunnel on the VPS or in-cluster forwards the public hostname to the internal webhook service.
- Telegram points at the Cloudflare-backed webhook URL.

## Manifest Strategy

- Add a namespace manifest for `adarkwa-study-bot`.
- Keep non-secret configuration in a committed ConfigMap.
- Remove committed secret values from `k8s/config.yaml`.
- Use deployment manifests with a stable image placeholder, then update the image during deployment.
- Keep the migration job as a template manifest with placeholders for image and job name, rendered in CI.

## GitHub Secrets

Required:

- `KUBE_CONFIG_B64`
- `WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
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

## Tradeoffs

### Why not Sealed Secrets now?

They improve cluster-side secret handling, but they add a controller and more operational setup. GitHub-secret-driven apply is enough for the first production release.

### Why not Argo CD now?

GitOps is attractive later, but it adds another control plane before the team has a stable production baseline. GitHub Actions deploys are a better fit for the first slice.

## Success Criteria

- A push to `main` or `master` automatically deploys a new version.
- The cluster receives the correct image tag and environment secrets.
- Web and worker roll independently but from the same image.
- Migrations run automatically during deploy.
- The setup is documented well enough to bootstrap a new cluster without guesswork.
