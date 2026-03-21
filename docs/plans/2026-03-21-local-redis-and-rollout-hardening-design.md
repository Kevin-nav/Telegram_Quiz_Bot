# Local Redis And Rollout Hardening Design

## Incident Summary

Production instability on March 21, 2026 came from treating a request-metered Redis tier as if it were a durable queue and hot-state store. The observed failure chain was:

1. A push to `main` published a new GHCR image successfully.
2. The VPS deploy timer started a rollout for the new digest.
3. New webhook and worker pods exhausted or were rejected by the external Redis tier during startup.
4. Webhook readiness failed and Telegram started receiving `503` responses.
5. Without a failed-digest guard, the timer would keep retrying the same broken digest on later ticks.

## Target Production Shape

Production keeps the current K3s-on-VPS architecture, Cloudflare Tunnel, and pull-based GHCR deployment model. The Redis dependency moves onto the VPS itself and must be a local Redis-compatible service:

- prefer `valkey-server` on Ubuntu 24.04 when the package is available
- fall back to `redis-server` if Valkey is not packaged for the target image
- expose the service on the VPS private IP so K3s workloads can reach it
- require password authentication and persistence

Request-metered or free hosted Redis tiers are not acceptable for this bot because Redis carries:

- ARQ queue traffic
- Telegram webhook idempotency
- active quiz and profile hot state
- rollout-time startup checks

## Runtime Footprint

The default production footprint stays intentionally conservative:

- `1` webhook replica
- `1` worker replica
- HPA disabled unless `ENABLE_HPA=true`

Autoscaling should stay off until Redis capacity, bot behavior, and VPS headroom are measured with real traffic.

## Rollout Safety Model

The webhook application should not crash the process just because Redis or ARQ is unavailable during startup. Instead:

- startup logs the Redis or ARQ failure clearly
- the process remains alive in a degraded state
- `/health/ready` reports degraded readiness and returns `503`
- `/webhook` rejects traffic with `503` while the runtime is degraded
- shutdown avoids acting on uninitialized Telegram application state

The deploy timer remains responsible for refusing automatic retries of a digest that has already failed rollout, so `main` pushes do not create a same-digest failure loop.
