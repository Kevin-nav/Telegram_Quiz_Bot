# Kubernetes CI/CD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a GitHub-driven CI/CD pipeline that tests, builds, pushes, and deploys `@Adarkwa_Study_Bot` to a VPS-hosted Kubernetes cluster.

**Architecture:** GitHub Actions runs CI, publishes the application image to GHCR, and deploys it to the Kubernetes cluster using a kubeconfig stored in GitHub Secrets. Kubernetes resources stay mostly static in the repo, while GitHub Actions renders and applies secrets and the migration job at deploy time.

**Tech Stack:** GitHub Actions, GHCR, Docker, Kubernetes, kubectl, FastAPI, ARQ, Alembic

---

### Task 1: Normalize Kubernetes base manifests

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\namespace.yaml`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\config.yaml`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\deployment.yaml`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\migration-job.yaml`

**Step 1: Write the failing expectation**

Expected behavior:
- No committed Kubernetes Secret data remains in repo manifests.
- Namespace can be applied before the rest of the resources.
- Deployments can be updated to a specific GHCR image during CI.

**Step 2: Implement the base manifest changes**

- Add namespace manifest for `adarkwa-study-bot`
- convert `config.yaml` into ConfigMap-only config
- replace image comments with an explicit GHCR placeholder
- make the migration job renderable via image/job placeholders

**Step 3: Validate the manifest structure**

Run:

```bash
rg "kind: Secret|base64_encoded" k8s
```

Expected: no committed runtime secret values remain in `k8s/`.

### Task 2: Add GitHub Actions CI

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\.github\workflows\ci.yml`

**Step 1: Write the failing expectation**

Expected behavior:
- pushes and pull requests run tests automatically
- the Python environment is set up reproducibly

**Step 2: Implement the workflow**

- install Python
- install project dependencies and `pytest`
- run `python -m pytest tests -q`

**Step 3: Verify syntax mentally and by local file review**

Expected: valid GitHub Actions YAML with no repo-specific secrets required for CI.

### Task 3: Add GitHub Actions deploy workflow

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\.github\workflows\deploy.yml`

**Step 1: Write the failing expectation**

Expected behavior:
- a push to `main` or `master` deploys automatically
- the image is published to GHCR
- kubectl applies manifests and updates the image
- migrations run before rollout completion

**Step 2: Implement the workflow**

- log into GHCR
- build and push image tags
- set kubeconfig from `KUBE_CONFIG_B64`
- apply namespace/config/service/hpa/deployments
- create/update the application secret from GitHub Secrets
- optionally create a GHCR image pull secret
- render and run the migration job
- set deployment images and wait for rollout

**Step 3: Review secret handling**

Expected: no sensitive values are echoed, and optional secrets resolve to empty strings safely.

### Task 4: Document the operational setup

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\README.md`

**Step 1: Write the failing expectation**

Expected behavior:
- a maintainer can bootstrap GitHub Secrets and the cluster from README instructions

**Step 2: Implement the docs**

- add deployment architecture summary
- add GitHub Secrets checklist
- add first-time cluster bootstrap steps
- add Cloudflare Tunnel recommendation for the webhook hostname

**Step 3: Review for gaps**

Expected: no hidden manual steps remain beyond cluster creation and tunnel provisioning.

### Task 5: Validate the slice

**Files:**
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\.github\workflows\ci.yml`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\.github\workflows\deploy.yml`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\deployment.yaml`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\README.md`

**Step 1: Run targeted checks**

Run:

```bash
python -m pytest tests -q
```

Expected: existing tests remain green.

**Step 2: Inspect generated workflow assumptions**

Run:

```bash
rg "KUBE_CONFIG_B64|GHCR_PULL_TOKEN|TELEGRAM_BOT_TOKEN|workflow_dispatch" .github README.md k8s
```

Expected: the workflow and docs reference the same deployment contract.
