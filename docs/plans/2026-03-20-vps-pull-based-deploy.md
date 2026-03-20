# VPS Pull-Based Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the GitHub kubeconfig push-deploy model with a pull-based VPS deployment flow that keeps cluster credentials off GitHub.

**Architecture:** GitHub Actions runs tests and publishes immutable container images to GHCR on `main`. A `systemd` timer on the VPS polls GHCR, refreshes a dedicated repo checkout, applies Kubernetes manifests locally, runs migrations, and rolls out the webhook and worker deployments using the exact published image digest.

**Tech Stack:** GitHub Actions, GHCR, K3s, Kubernetes manifests, Cloudflare Tunnel, `systemd`, Bash

---

### Task 1: Update the GitHub deploy workflow to build and publish only

**Files:**
- Modify: `.github/workflows/deploy.yml`

**Step 1: Remove cluster access steps**

- Delete kubeconfig decoding, `kubectl` setup, namespace apply, secret apply, migration, and rollout steps.
- Keep the workflow focused on CI gating and image publishing.

**Step 2: Restrict automatic deploy publishing to `main`**

- Ensure the workflow only auto-runs on pushes to `main`.
- Keep `workflow_dispatch` for manual rebuilds if needed.

**Step 3: Publish immutable and tracking tags**

- Keep SHA-tag publishing.
- Keep `latest` as the tracked production tag for the VPS poller.

**Step 4: Add a lightweight deployment summary**

- Emit the final image references in the workflow summary or logs so the operator can verify what was published.

**Step 5: Review**

Run:

```bash
git diff -- .github/workflows/deploy.yml
```

Expected:

- no Kubernetes access steps remain
- workflow still builds and pushes GHCR images

### Task 2: Add reusable VPS deploy automation assets

**Files:**
- Create: `ops/deploy/adarkwa-bot-deploy.sh`
- Create: `ops/deploy/adarkwa-bot-deploy.service`
- Create: `ops/deploy/adarkwa-bot-deploy.timer`

**Step 1: Add the deploy script**

- Write a Bash script that:
  - polls the GHCR digest for `:latest`
  - clones or refreshes a dedicated `origin/main` checkout
  - renders Kubernetes manifests with an immutable image reference
  - runs the migration job
  - waits for migration success
  - applies the deployment
  - waits for rollout success
  - records the deployed digest locally

**Step 2: Add service and timer units**

- Create a one-shot `systemd` service for the script.
- Create a timer that runs every few minutes with reasonable jitter.

**Step 3: Review**

Run:

```bash
git diff -- ops/deploy
```

Expected:

- deploy assets exist and reference the bot namespace, image repo, and manifest paths consistently

### Task 3: Rewrite VPS bootstrap instructions

**Files:**
- Modify: `docs/vps_setup_instructions.md`

**Step 1: Replace kubeconfig-based GitHub deployment guidance**

- Remove instructions for exposing the K3s API and generating `KUBE_CONFIG_B64`.

**Step 2: Document the secure bootstrap path**

- Include:
  - base VPS hardening
  - K3s installation
  - Cloudflared installation with the existing token model
  - repo checkout for deployment manifests
  - Kubernetes secret creation from the VPS
  - GHCR read-only credential setup
  - deploy script and `systemd` timer installation

**Step 3: Add verification commands**

- Include checks for `systemctl`, `kubectl`, tunnel health, and rollout state.

### Task 4: Rewrite the general production deployment guide

**Files:**
- Modify: `docs/deployment_setup.md`
- Modify: `README.md`

**Step 1: Update the deployment model**

- Replace GitHub-to-cluster wording with the pull-based VPS model.

**Step 2: Update secret guidance**

- Remove `KUBE_CONFIG_B64`.
- Clarify which secrets stay in GitHub and which stay on the VPS/cluster.

**Step 3: Update operational flow**

- Document the new normal flow:
  - push to `main`
  - image publish
  - VPS timer-driven deployment

**Step 4: Review**

Run:

```bash
git diff -- README.md docs/deployment_setup.md docs/vps_setup_instructions.md
```

Expected:

- docs consistently describe a pull-based deploy model
- Cloudflare routing still targets the in-cluster service

### Task 5: Validate the final change set

**Files:**
- Review only

**Step 1: Inspect the overall diff**

Run:

```bash
git diff -- .github/workflows/deploy.yml README.md docs/deployment_setup.md docs/vps_setup_instructions.md ops/deploy
```

Expected:

- workflow, docs, and VPS assets all describe the same deployment flow

**Step 2: Confirm no stale kubeconfig requirements remain**

Run:

```bash
rg "KUBE_CONFIG_B64|kubectl cluster-info|self-hosted runner|port 6443" README.md docs .github/workflows/deploy.yml
```

Expected:

- no production guidance depends on GitHub-held kubeconfig access
