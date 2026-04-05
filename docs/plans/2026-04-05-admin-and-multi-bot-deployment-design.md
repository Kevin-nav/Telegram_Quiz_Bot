# Admin And Multi-Bot Deployment Design

## Goal

Deploy the current two-bot backend and the `admin/` Next.js frontend from GitHub Actions to the existing VPS/K3s environment with one repeatable production flow, one Cloudflare Tunnel, and separate public hostnames for Telegram traffic and the staff admin UI.

## Approved Production Shape

- The FastAPI backend remains one shared runtime for both Telegram bots: `tanjah` and `adarkwa`.
- The webhook/backend public hostname stays separate from the admin hostname.
- The admin frontend is published at `admin-tgbot.sankoslides.com`.
- The same Cloudflare Tunnel publishes both hostnames.
- The browser should talk to one origin for admin usage: `admin-tgbot.sankoslides.com`.
- Admin login remains application-level auth only. No Cloudflare Access layer is added.
- GitHub Actions builds and publishes images. The VPS pulls and deploys them locally.

## Existing Repo Context

The repo already has:

- a backend Docker image at the repo root
- GitHub Actions workflows for backend CI and backend image publishing
- K3s manifests for the backend webhook and worker
- a VPS deploy agent under `ops/deploy/`
- production docs centered on one backend image and one public bot hostname
- a Next.js admin app in `admin/` with `output: "standalone"`

What is missing:

- an admin production image
- admin Kubernetes deployment and service manifests
- ingress rules for the admin hostname
- coordinated release handling for two images from one commit
- operator documentation for the admin rollout path

## Architecture

### 1. Runtime Topology

Production should run three long-lived workloads inside the same K3s namespace:

- backend webhook deployment
- backend worker deployment
- admin frontend deployment

The backend image remains responsible for:

- Telegram webhooks for both bots
- `/admin/*` API routes
- migrations
- background jobs

The admin image is responsible only for serving the Next.js UI.

### 2. Public Hostnames And Traffic Routing

Use two public hostnames on the same Cloudflare Tunnel:

- `tg-bot-tanjah.sankoslides.com` -> backend ingress/service
- `admin-tgbot.sankoslides.com` -> admin ingress/service plus backend admin API paths

The admin hostname should stay single-origin in the browser. The cleanest place to proxy admin API traffic is the Kubernetes ingress layer, not the frontend code.

Recommended routing on `admin-tgbot.sankoslides.com`:

- `/admin` and `/admin/*` -> backend FastAPI service
- all other paths -> admin Next.js service

That keeps:

- session cookies host-local to the admin hostname
- browser requests same-origin
- CORS unnecessary in production for the admin hostname
- backend bot/webhook traffic isolated from human admin browsing

Local development can keep the current split:

- admin on `localhost:3000`
- backend on `localhost:8000`
- `NEXT_PUBLIC_ADMIN_API_BASE_URL=http://localhost:8000`

### 3. Image Strategy

Publish two GHCR images from the same commit:

- `ghcr.io/<owner>/adarkwa-study-bot:<git-sha>`
- `ghcr.io/<owner>/adarkwa-study-bot:latest`
- `ghcr.io/<owner>/adarkwa-study-bot-admin:<git-sha>`
- `ghcr.io/<owner>/adarkwa-study-bot-admin:latest`

The current backend image name should stay unchanged to avoid unnecessary VPS churn. The admin frontend gets a new dedicated image repository.

### 4. Release Coordination

Once two images exist, the VPS should stop treating one moving `latest` digest as the whole release. The deploy agent should instead deploy by Git commit SHA from `origin/main`.

Recommended deploy-agent flow:

1. fetch `origin/main`
2. resolve `release_sha = git rev-parse origin/main`
3. resolve backend image `ghcr.io/<owner>/adarkwa-study-bot:${release_sha}`
4. resolve admin image `ghcr.io/<owner>/adarkwa-study-bot-admin:${release_sha}`
5. convert both to immutable digests
6. render manifests with both digests
7. run migrations
8. roll out backend webhook, backend worker, and admin deployments
9. record the last deployed commit SHA and digests

This avoids partial releases where one `latest` tag updates before the other.

### 5. Admin Frontend Container Shape

The admin app should use a dedicated multi-stage Docker build:

- builder installs `admin/package*.json`
- builder runs `npm ci`
- builder runs `npm run build`
- runtime copies Next standalone output plus static assets
- runtime starts `node server.js`

The image should expose port `3000`.

Production env for the admin container should prefer:

- `PORT=3000`
- `HOSTNAME=0.0.0.0`
- `NEXT_PUBLIC_ADMIN_API_BASE_URL=` empty, because ingress provides same-origin routing

### 6. Kubernetes Layout

Add separate manifests for the admin frontend rather than overloading the backend deployment file.

Recommended objects:

- `Deployment/adarkwa-bot-admin`
- `Service/adarkwa-bot-admin-service`
- admin host ingress rules inside `k8s/ingress.yaml`

The backend manifests stay responsible for:

- `Deployment/adarkwa-bot-webhook`
- `Deployment/adarkwa-bot-worker`
- `Service/adarkwa-bot-service`
- migration job

The ingress should contain both hosts and explicit path precedence for the admin hostname so `/admin/*` reaches FastAPI and everything else reaches Next.js.

### 7. GitHub Actions Responsibilities

GitHub Actions should:

- run backend tests
- run admin lint/build validation
- build and publish backend and admin images together on `main`
- include both image names and digests in the workflow summary

GitHub should still not:

- hold kubeconfig
- talk directly to the cluster
- create runtime Kubernetes secrets

### 8. VPS Deploy Agent Responsibilities

The existing deploy agent should remain the single production entrypoint, but it needs to understand the admin deployment too.

It should:

- fetch the repo
- resolve the release SHA from `origin/main`
- resolve both image digests from GHCR
- apply namespace, config, services, and ingress
- render and run the migration job with the backend image digest
- render and apply backend and admin deployments
- wait for webhook, worker, and admin rollout success
- record `last-deployed-sha`
- record `last-failed-sha`

The same `systemd` timer model remains correct.

### 9. Secrets And Runtime Configuration

Backend runtime secrets remain in Kubernetes.

Backend secret examples:

- `TELEGRAM_BOT_TOKEN` or `TANJAH_BOT_TOKEN`
- `ADARKWA_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET` or `TANJAH_WEBHOOK_SECRET`
- `ADARKWA_WEBHOOK_SECRET`

Backend non-secret config examples:

- `ADMIN_ALLOWED_ORIGINS`
- `ADMIN_SESSION_COOKIE_DOMAIN`

Admin frontend should need little or no secret configuration in production if ingress does the proxying. A minimal config map is enough unless later features introduce server-side secrets.

Recommended production values:

- `ADMIN_ALLOWED_ORIGINS=https://admin-tgbot.sankoslides.com`
- `ADMIN_SESSION_COOKIE_DOMAIN=` empty
- `NEXT_PUBLIC_ADMIN_API_BASE_URL=` empty in the admin deployment

Leaving `ADMIN_SESSION_COOKIE_DOMAIN` empty keeps the admin cookie scoped to `admin-tgbot.sankoslides.com`, which is safer and avoids unnecessary cross-subdomain sharing.

### 10. Tunnel Configuration

One Cloudflare Tunnel can publish multiple hostnames by mapping each hostname to a local service. For this setup, keep the tunnel on the VPS host and point both hostnames at the Traefik listener on `http://localhost:80`.

The hostname split is then handled by Kubernetes ingress:

- bot host -> backend service
- admin host -> backend `/admin/*` paths and admin frontend `/`

### 11. Bootstrap And First Deploy Order

For a fresh environment, the safe order is:

1. deploy manifests and services
2. run `alembic upgrade head`
3. run `python scripts/bootstrap_admin.py --email <admin-email>`
4. wait for backend webhook, worker, and admin deployments to become healthy
5. sign in at `https://admin-tgbot.sankoslides.com`
6. complete the forced password change if prompted
7. verify both bot webhooks are configured against the backend hostname

### 12. Verification Strategy

Backend verification:

- targeted pytest suite
- migration job success
- webhook and worker rollout status
- `/health`, `/health/live`, and `/health/ready`

Admin verification:

- `npm run lint`
- `npm run build`
- admin deployment readiness
- browser sign-in flow through `admin-tgbot.sankoslides.com`
- same-origin `/admin/auth/me` request success

Operational verification:

- both tunnel hostnames resolve through the same tunnel
- backend hostname returns bot health
- admin hostname serves Next.js pages
- admin hostname proxies `/admin/*` to FastAPI

## Tradeoffs

### Recommended Choice: Ingress-Level Same-Origin Proxy

Pros:

- simpler cookie behavior
- simpler browser security model
- no production CORS dependency for admin
- no frontend-only proxy code path to maintain

Cons:

- ingress rules become slightly more complex

### Rejected Choice: Direct Browser Calls From Admin Host To Backend Host

Pros:

- fewer ingress rules

Cons:

- cross-origin cookies are more fragile
- production behavior depends on CORS and cookie-domain correctness
- harder to reason about login/session failures

## Rollout Order

1. Add admin image build and admin CI validation.
2. Add admin deployment/service and multi-host ingress rules.
3. Extend deploy agent from one-image digest polling to release-SHA deployment.
4. Update docs and env examples.
5. Run first full deploy on VPS.
6. Verify admin login and both bot webhooks.
