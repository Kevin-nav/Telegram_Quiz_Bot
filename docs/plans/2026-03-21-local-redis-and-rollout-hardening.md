# Local Redis And Rollout Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current request-metered production Redis dependency with a VPS-local Redis/Valkey setup and harden rollout behavior so pushes to `main` no longer destabilize the Telegram bot.

**Architecture:** K3s stays on the VPS with Cloudflare Tunnel and pull-based GHCR deployment unchanged. Redis moves from Upstash to a VPS-local Redis-compatible service such as Valkey, and the application startup path is hardened so webhook pods do not fail catastrophically or cause repeated rollout storms when Redis is unavailable or degraded.

**Tech Stack:** K3s, Kubernetes manifests, Valkey or Redis, systemd, Bash, FastAPI, ARQ, Python, GHCR

---

### Task 1: Document the root-cause findings and target production shape

**Files:**
- Create: `docs/plans/2026-03-21-local-redis-and-rollout-hardening-design.md`
- Modify: `docs/deployment_setup.md`
- Modify: `docs/vps_setup_instructions.md`

**Step 1: Capture the production incident summary**

- Document the observed failure chain:
  - push to `main`
  - image publish succeeds
  - rollout starts
  - webhook and worker pods hit Redis request-cap exhaustion
  - readiness/startup fails
  - Telegram receives `503`
  - the deploy timer keeps retrying the same digest unless guarded

**Step 2: Document the target Redis topology**

- Specify that production should use a VPS-local Redis-compatible server.
- Prefer `valkey-server` if available on Ubuntu 24.04, otherwise `redis-server`.
- State that request-metered/free Redis tiers are not acceptable for this bot’s queue and hot-state workload.

**Step 3: Document the target runtime footprint**

- Document the intended conservative defaults:
  - `1` webhook replica
  - `1` worker replica
  - HPA disabled by default
- Explain that autoscaling should only be re-enabled after Redis capacity and application behavior are measured under load.

**Step 4: Review**

Run:

```bash
git diff -- docs/deployment_setup.md docs/vps_setup_instructions.md docs/plans/2026-03-21-local-redis-and-rollout-hardening-design.md
```

Expected:

- the docs explicitly describe the Redis capacity incident and the new local-Redis production shape

### Task 2: Add VPS-local Redis bootstrap and operations docs

**Files:**
- Modify: `docs/vps_setup_instructions.md`
- Modify: `docs/deployment_setup.md`
- Modify: `README.md`

**Step 1: Add local Redis install instructions**

- Add Ubuntu commands for installing either Valkey or Redis.
- Include:
  - package installation
  - enabling the service
  - bind/listen configuration for K3s workloads
  - password/auth configuration
  - persistence configuration

**Step 2: Add production connection guidance**

- Document the target `REDIS_URL` format for Kubernetes secrets.
- Clarify whether pods will reach Redis through:
  - the VPS private IP, or
  - a host alias/static endpoint chosen for the cluster

**Step 3: Add verification commands**

- Include commands to verify:
  - local Redis is reachable
  - Kubernetes pods can connect to Redis
  - webhook and worker pods start successfully after the cutover

**Step 4: Add maintenance guidance**

- Document:
  - how to restart Redis
  - how to inspect memory usage
  - how to back up AOF/RDB files
  - what alert conditions matter

**Step 5: Review**

Run:

```bash
git diff -- README.md docs/deployment_setup.md docs/vps_setup_instructions.md
```

Expected:

- the docs are implementation-ready for a VPS-local Redis deployment

### Task 3: Make Redis startup failure behavior safer in the app

**Files:**
- Modify: `src/app/bootstrap.py`
- Modify: `src/tasks/arq_client.py`
- Modify: `src/api/health.py`
- Test: `tests/test_bootstrap.py`
- Test: `tests/test_webhook.py`

**Step 1: Write failing tests for degraded Redis startup**

- Add tests that cover:
  - web startup behavior when ARQ Redis initialization fails
  - readiness reporting when Redis is unavailable
  - webhook app lifecycle avoiding destructive behavior during partial startup

**Step 2: Run targeted tests to confirm failure**

Run:

```bash
pytest tests/test_bootstrap.py tests/test_webhook.py -q
```

Expected:

- tests fail because startup currently treats Redis/ARQ initialization too rigidly for safe rollout behavior

**Step 3: Implement minimal safe-start behavior**

- Adjust startup code so the application:
  - logs Redis startup failures clearly
  - does not create undefined partial state
  - surfaces degraded readiness correctly
- Keep the webhook registration logic coherent with the actual runtime state.

**Step 4: Run targeted tests again**

Run:

```bash
pytest tests/test_bootstrap.py tests/test_webhook.py -q
```

Expected:

- tests pass

**Step 5: Commit**

```bash
git add src/app/bootstrap.py src/tasks/arq_client.py src/api/health.py tests/test_bootstrap.py tests/test_webhook.py
git commit -m "fix: harden startup behavior when redis is unavailable"
```

### Task 4: Add Kubernetes and deploy-script support for local Redis cutover

**Files:**
- Modify: `k8s/deployment.yaml`
- Modify: `k8s/config.yaml`
- Modify: `ops/deploy/adarkwa-bot-deploy.sh`
- Modify: `docs/vps_setup_instructions.md`

**Step 1: Identify how pods will resolve the VPS-local Redis endpoint**

- Choose one documented approach and implement it consistently:
  - use the VPS private IP directly in `REDIS_URL`
  - or add a stable host alias/endpoint strategy if needed

**Step 2: Ensure deploy-time behavior stays conservative**

- Keep one webhook and one worker as defaults.
- Keep HPA disabled unless `ENABLE_HPA=true`.
- Ensure the deploy script still refuses repeated automatic retries for a failed digest.

**Step 3: Add explicit Redis cutover instructions**

- Document the exact order:
  - install Redis/Valkey
  - confirm service health
  - update Kubernetes secret `REDIS_URL`
  - restart rollout
  - verify readiness and Telegram webhook behavior

**Step 4: Review**

Run:

```bash
git diff -- k8s/deployment.yaml k8s/config.yaml ops/deploy/adarkwa-bot-deploy.sh docs/vps_setup_instructions.md
```

Expected:

- runtime defaults remain conservative and Redis cutover instructions are precise

### Task 5: Add production smoke checks for rollout safety

**Files:**
- Modify: `docs/deployment_setup.md`
- Modify: `docs/vps_setup_instructions.md`
- Optionally create: `scripts/production_smoke_check.sh`

**Step 1: Define smoke-check commands**

- Include post-deploy commands for:
  - GHCR latest digest
  - last deployed digest
  - webhook URL from Telegram `getWebhookInfo`
  - pod readiness
  - recent webhook logs
  - Redis connectivity

**Step 2: Add a manual recovery section**

- Document exact commands for:
  - clearing `last-failed-digest`
  - rerunning the deploy service
  - manually setting the Telegram webhook if needed
  - scaling deployments down to `1` if someone changed them

**Step 3: Review**

Run:

```bash
git diff -- docs/deployment_setup.md docs/vps_setup_instructions.md scripts/production_smoke_check.sh
```

Expected:

- the handoff includes an operational verification checklist and a recovery path

### Task 6: Validate the final handoff package

**Files:**
- Review only

**Step 1: Inspect the final diff**

Run:

```bash
git diff -- README.md docs/deployment_setup.md docs/vps_setup_instructions.md docs/plans/2026-03-21-local-redis-and-rollout-hardening-design.md k8s/deployment.yaml k8s/config.yaml ops/deploy/adarkwa-bot-deploy.sh src/app/bootstrap.py src/tasks/arq_client.py src/api/health.py tests/test_bootstrap.py tests/test_webhook.py
```

Expected:

- the plan, docs, and code changes all describe the same production model

**Step 2: Record the required production verification commands**

Run after implementation:

```bash
kubectl get pods -n adarkwa-study-bot
kubectl logs -n adarkwa-study-bot deployment/adarkwa-bot-webhook --tail=100
curl -s "https://api.telegram.org/bot<token>/getWebhookInfo"
systemctl status adarkwa-bot-deploy.timer
```

Expected:

- webhook pods are healthy
- Telegram webhook URL is populated
- the deploy timer is active
- there is no same-digest failure loop
