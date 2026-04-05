# Admin And Multi-Bot Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy the shared two-bot backend and the standalone admin frontend from GitHub Actions to the current VPS/K3s stack with one repeatable pull-based rollout path.

**Architecture:** Keep the existing backend image and pull-based VPS deploy model, add a dedicated admin image and admin deployment, and route `admin-tgbot.sankoslides.com` through ingress so `/admin/*` hits FastAPI while all other paths hit Next.js. Update the deploy agent to deploy both images by the `origin/main` commit SHA instead of treating one floating `latest` digest as the whole release.

**Tech Stack:** GitHub Actions, GHCR, Docker, Next.js standalone output, FastAPI, K3s, Traefik ingress, Cloudflare Tunnel, systemd.

---

### Task 1: Add Admin Production Container Assets

**Files:**
- Create: `admin/Dockerfile`
- Create: `admin/.dockerignore`
- Create: `admin/.env.example`
- Modify: `admin/package.json`
- Test: `admin/package-lock.json`

**Step 1: Verify current admin build works locally**

Run:

```bash
cd admin
npm ci
npm run lint
npm run build
```

Expected: lint and build pass before containerization changes.

**Step 2: Add the admin Docker build**

Implement a multi-stage Dockerfile that:

- installs dependencies with `npm ci`
- builds the Next.js app with `output: "standalone"`
- copies `.next/standalone`, `.next/static`, and `public` into a minimal runtime image
- starts `node server.js`
- exposes port `3000`

Add `.dockerignore` so `node_modules`, `.next`, and local env files are not copied into the build context.

Add `admin/.env.example` documenting:

- `NEXT_PUBLIC_ADMIN_API_BASE_URL=http://localhost:8000` for local split-origin development

**Step 3: Verify the admin image locally**

Run:

```bash
docker build -f admin/Dockerfile -t adarkwa-study-bot-admin:local admin
```

Expected: image build succeeds.

**Step 4: Commit**

```bash
git add admin/Dockerfile admin/.dockerignore admin/.env.example admin/package.json admin/package-lock.json
git commit -m "build: add admin production container"
```

---

### Task 2: Extend CI To Validate Backend And Admin Together

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Update CI jobs**

Add admin validation alongside backend tests:

- backend Python setup and pytest
- Node setup scoped to `admin/`
- `npm ci`
- `npm run lint`
- `npm run build`

Prefer separate jobs so failures identify whether the backend or admin broke.

**Step 2: Verify workflow syntax locally by inspection**

Check that:

- paths are repo-root correct
- Node version is explicit
- cache scope for `admin/package-lock.json` is correct

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: validate admin frontend in pull requests"
```

---

### Task 3: Publish Backend And Admin Images From One Deploy Workflow

**Files:**
- Modify: `.github/workflows/deploy.yml`

**Step 1: Update deploy workflow design**

Keep the `main` push trigger and production environment, but publish two images in one workflow:

- `ghcr.io/<owner>/adarkwa-study-bot`
- `ghcr.io/<owner>/adarkwa-study-bot-admin`

Both should receive:

- `<git-sha>` tag
- `latest` tag

Use the existing `GITHUB_TOKEN` and `packages: write` permission.

**Step 2: Include admin build context**

Build the backend image from:

```bash
context: .
file: ./Dockerfile
```

Build the admin image from:

```bash
context: ./admin
file: ./admin/Dockerfile
```

**Step 3: Update workflow summary**

Publish both image repositories and both digests in the job summary.

**Step 4: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "build: publish backend and admin images"
```

---

### Task 4: Add Admin Kubernetes Manifests And Multi-Host Ingress Routing

**Files:**
- Create: `k8s/admin-deployment.yaml`
- Create: `k8s/admin-service.yaml`
- Modify: `k8s/ingress.yaml`
- Modify: `k8s/config.yaml`

**Step 1: Add admin deployment and service**

Create:

- `Deployment/adarkwa-bot-admin`
- `Service/adarkwa-bot-admin-service`

Admin deployment requirements:

- image placeholder such as `__ADMIN_IMAGE__`
- container port `3000`
- readiness and liveness checks suitable for Next.js
- config values:
  - `PORT=3000`
  - `HOSTNAME=0.0.0.0`
  - `NEXT_PUBLIC_ADMIN_API_BASE_URL=` empty

**Step 2: Update ingress**

Keep the bot hostname rule for the backend.

Add admin hostname rules so:

- host `admin-tgbot.sankoslides.com` and path `/admin` or `/admin/*` route to `adarkwa-bot-service`
- host `admin-tgbot.sankoslides.com` and path `/` route to `adarkwa-bot-admin-service`

Ensure path matching is explicit enough that `/admin/*` does not fall through to the Next.js service.

**Step 3: Update runtime config**

Set production admin backend config to:

- `ADMIN_ALLOWED_ORIGINS=https://admin-tgbot.sankoslides.com`
- `ADMIN_SESSION_COOKIE_DOMAIN=` empty unless a real cross-subdomain requirement appears later

**Step 4: Commit**

```bash
git add k8s/admin-deployment.yaml k8s/admin-service.yaml k8s/ingress.yaml k8s/config.yaml
git commit -m "deploy: add admin k8s manifests and ingress routing"
```

---

### Task 5: Extend The VPS Deploy Agent To Handle Two Images By Release SHA

**Files:**
- Modify: `ops/deploy/adarkwa-bot-deploy.sh`
- Modify: `ops/deploy/adarkwa-bot-deploy.service`
- Modify: `ops/deploy/adarkwa-bot-deploy.timer`

**Step 1: Change release coordination**

Replace the single-image `latest` digest trigger with commit-SHA release resolution:

- fetch `origin/main`
- compute `release_sha`
- resolve backend image `IMAGE_REPO:${release_sha}`
- resolve admin image `ADMIN_IMAGE_REPO:${release_sha}`
- resolve both digests with `crane digest`

Track rollout state using:

- `last-deployed-sha`
- `last-failed-sha`

Retain failed-release guard behavior.

**Step 2: Render separate manifests**

Render:

- backend deployment manifest with `__IMAGE__`
- admin deployment manifest with `__ADMIN_IMAGE__`
- migration job with backend image only

Apply:

- namespace
- config
- backend service
- admin service
- ingress
- migration job
- backend deployment
- admin deployment

Wait for rollout success of:

- backend webhook
- backend worker
- admin deployment

**Step 3: Extend deploy env contract**

Update the deploy script to read new env values such as:

- `ADMIN_IMAGE_REPO`
- `ADMIN_DEPLOYMENT`

Leave the existing backend variables intact to minimize VPS churn.

**Step 4: Commit**

```bash
git add ops/deploy/adarkwa-bot-deploy.sh ops/deploy/adarkwa-bot-deploy.service ops/deploy/adarkwa-bot-deploy.timer
git commit -m "deploy: roll out backend and admin by release sha"
```

---

### Task 6: Update README And Operator Docs For The New Production Shape

**Files:**
- Modify: `README.md`
- Modify: `docs/deployment_setup.md`
- Modify: `docs/vps_setup_instructions.md`
- Modify: `.env.example`

**Step 1: Update operator-facing architecture docs**

Document:

- backend host versus admin host
- one Cloudflare Tunnel serving both hostnames
- ingress-level same-origin proxy on the admin host
- two-image GHCR publishing model
- release-SHA deploy behavior on the VPS

**Step 2: Update VPS instructions**

Add:

- Cloudflare hostname rule for `admin-tgbot.sankoslides.com`
- admin deployment/service verification commands
- deploy env example including `ADMIN_IMAGE_REPO` and `ADMIN_DEPLOYMENT`
- first admin rollout verification steps

**Step 3: Update env docs**

Clarify:

- local dev keeps `NEXT_PUBLIC_ADMIN_API_BASE_URL=http://localhost:8000`
- production admin deployment should leave `NEXT_PUBLIC_ADMIN_API_BASE_URL` empty
- `ADMIN_SESSION_COOKIE_DOMAIN` should stay empty for host-only admin cookies

**Step 4: Commit**

```bash
git add README.md docs/deployment_setup.md docs/vps_setup_instructions.md .env.example
git commit -m "docs: document admin and multi-host deployment flow"
```

---

### Task 7: Verify The Full Deployment Path

**Files:**
- No planned source edits unless verification exposes bugs.

**Step 1: Run local validation**

Run:

```bash
python -m pytest tests -q
cd admin && npm run lint
cd admin && npm run build
```

**Step 2: Push to a branch and inspect Actions results**

Verify:

- CI validates backend and admin
- deploy workflow publishes both images on `main`
- workflow summary includes both digests

**Step 3: Verify VPS rollout**

Run on the VPS:

```bash
systemctl status adarkwa-bot-deploy.timer
systemctl status adarkwa-bot-deploy.service
journalctl -u adarkwa-bot-deploy.service -n 100 --no-pager
kubectl rollout status deployment/adarkwa-bot-webhook -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-worker -n adarkwa-study-bot
kubectl rollout status deployment/adarkwa-bot-admin -n adarkwa-study-bot
```

**Step 4: Verify public routing**

Check:

- `https://tg-bot-tanjah.sankoslides.com/health`
- `https://admin-tgbot.sankoslides.com/login`
- `https://admin-tgbot.sankoslides.com/admin/auth/me` returns `401` before login
- sign in through the admin UI
- confirm the browser uses the admin hostname for admin API calls

**Step 5: Commit**

Commit only any follow-up fixes discovered during verification.

---

## Execution Notes

- Keep the backend image name unchanged.
- Add the admin image as a new GHCR repository.
- Prefer ingress-level proxying over frontend rewrites or cross-origin browser calls.
- Do not add kubeconfig or runtime secrets to GitHub Actions.
- Do not set `ADMIN_SESSION_COOKIE_DOMAIN` in production unless there is a deliberate need to share cookies across subdomains.
