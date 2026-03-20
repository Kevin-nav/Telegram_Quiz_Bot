# VPS Pull-Based Deployment Design

## Goal

Deploy `@Adarkwa_Study_Bot` to a VPS-hosted K3s cluster with automatic deployments from `main` while minimizing long-term maintenance and avoiding cluster credentials in GitHub.

## Chosen Approach

Use `GitHub Actions + GHCR + pull-based deployment on the VPS + Cloudflare Tunnel to the in-cluster service`.

This keeps the Kubernetes API private, avoids a self-hosted GitHub runner, and keeps GitHub responsible only for CI and image publishing.

## Architecture

### Release Flow

1. A push reaches `main`.
2. GitHub Actions runs the test suite.
3. If tests pass, GitHub Actions builds and publishes:
   - `ghcr.io/<owner>/adarkwa-study-bot:<git-sha>`
   - `ghcr.io/<owner>/adarkwa-study-bot:latest`
4. A small deploy agent on the VPS polls GHCR for the digest behind `:latest`.
5. When the digest changes, the VPS deploy agent:
   - refreshes a dedicated checkout of the repo at `origin/main`
   - renders the deployment and migration manifests with the exact image digest
   - applies namespace and non-secret config
   - runs the migration job
   - rolls out the webhook and worker deployments
   - records the deployed digest locally

### Secret Model

- Runtime secrets live on the VPS and in Kubernetes, not in GitHub Actions.
- GitHub only needs package publishing permissions.
- If GHCR remains private, the VPS and cluster receive a read-only GHCR credential during bootstrap.

### Networking Model

- The app remains a `ClusterIP` service.
- Cloudflare Tunnel publishes the Telegram webhook hostname.
- The tunnel forwards traffic to:
  - `http://adarkwa-bot-service.adarkwa-study-bot.svc.cluster.local:80`
- The Kubernetes API does not need to be reachable from the public internet.

## Why This Over Alternatives

### Compared With Push Deploy via Kubeconfig

- avoids storing cluster credentials in GitHub
- avoids exposing the Kubernetes API to GitHub-hosted runners
- reduces blast radius if a GitHub secret is leaked

### Compared With a Self-Hosted Runner

- avoids runner patching, lifecycle management, and hardening work
- keeps deployment authority on the VPS without adding another long-running control plane

### Compared With Argo CD or Flux

- fewer controllers and lower operational overhead for a single bot on one VPS
- enough control to enforce migration-before-rollout behavior
- easy upgrade path later if stronger audit and GitOps workflows become necessary

## Operational Decisions

- Keep `cloudflared` as a host-level `systemd` service first.
- Use a `systemd` timer plus a shell deploy script for the VPS agent.
- Prefer immutable image digests for actual Kubernetes rollouts.
- Keep Kubernetes secrets stable across deploys and update them only when values change.
- Keep auto-deploys tied to `main` only.

## Success Criteria

- A push to `main` triggers a test-then-build pipeline automatically.
- The VPS deploys new images automatically without GitHub holding kubeconfig credentials.
- Cloudflare continues routing the Telegram hostname to the in-cluster service.
- Migrations run before rollout and block deployment if they fail.
- The setup is documented with bootstrap steps, operational checks, and recovery guidance.
