# Neon To K8s Postgres Migration Design

## Goal

Move the bot from the current Neon-hosted PostgreSQL database to a PostgreSQL instance running inside the existing K3s cluster with very little user-visible downtime, explicit rollback points, and durable backups stored outside the node.

## Current Context

The current production shape is:

- one single-node K3s cluster on the VPS
- one webhook deployment, one worker deployment, and one admin deployment
- `local-path` as the only Kubernetes storage class
- one `DATABASE_URL` consumed by the FastAPI app, ARQ worker, and Alembic migration job
- Neon as the current system-of-record PostgreSQL database
- Redis on the VPS private network for queues, idempotency, and hot state

Live production inspection on `2026-04-12` showed:

- the active Neon database is about `26 MB`
- the largest tables are still modest in size
- the cluster has no existing in-cluster PostgreSQL workload
- the node has about `5.5 GB` free disk on `/`
- the cluster is single-node, so local persistence is not enough on its own for durability

These facts make a logical-replication or dual-write design unnecessary for the initial migration. The lower-risk design is a short, controlled cutover with queued writes.

## Approved Migration Shape

### 1. Target Database Topology

Run a single PostgreSQL `17` instance inside the `adarkwa-study-bot` namespace using:

- one `StatefulSet`
- one PVC on the `local-path` storage class
- one internal `Service`
- one Kubernetes secret for database credentials
- readiness and liveness probes
- conservative resource requests and limits

The cluster is single-node, so high availability inside Kubernetes is out of scope for this phase. The immediate goal is controlled ownership of the database workload plus durable off-node backups.

### 2. Backup Model

Durability must come from two layers:

- the live database files on the PVC
- external backups stored in R2

The first backup system should be simple and explicit:

- scheduled logical backups via `pg_dump -Fc`
- backups uploaded to R2 with timestamped object keys
- per-backup metadata containing timestamp, PostgreSQL version, Alembic revision, file size, and checksum
- a documented restore path into a scratch database
- a restore rehearsal step before production cutover

Point-in-time recovery via WAL archiving can be added later, but it should not block the first migration. The initial requirement is durable, proven snapshot backups outside the node.

### 3. Cutover Strategy

The approved cutover model is a short maintenance window with queued writes.

This avoids dual-write complexity while still preventing user-facing breakage:

- webhook pods continue accepting Telegram requests and return `200`
- incoming work is queued into Redis/ARQ
- worker processing is paused briefly during the final sync
- queued jobs resume only after the app is switched to the new database

To make this safe, the application should support a temporary queue-only maintenance mode where the webhook path never performs inline work that could touch the database directly.

### 4. Why Dual-Write And Logical Replication Were Rejected

Dual-write was rejected because it introduces:

- application complexity
- risk of divergence between sources
- harder rollback conditions
- a larger testing surface area

Logical replication was rejected for phase one because:

- the source database is very small
- the target cluster is simple and single-node
- the extra complexity does not buy enough risk reduction here

The migration should optimize for correctness and reversibility, not theoretical zero downtime.

## Architecture Changes

### 1. Application Controls

The app should gain explicit operational controls for migration and maintenance:

- `APP_MODE=normal|queue_only`
- queue-only webhook behavior that always enqueues updates
- worker scale-down during the final sync window
- optional health/readiness reporting that exposes the current app mode

In `queue_only` mode:

- the webhook accepts valid requests
- updates are claimed for idempotency
- every update is routed to ARQ
- no inline Telegram handling is allowed

This ensures writes are deferred rather than partially processed during cutover.

### 2. Database Verification Tooling

The repo should contain scripts to compare the source and target databases before cutover:

- table row counts for all user tables
- spot-checks for high-value tables such as `users`, `user_bot_profiles`, `question_attempts`, `student_question_srs`, and `analytics_events`
- Alembic head revision check on both sides
- target smoke check using the real application against the target database

The migration is allowed to proceed only if all verification gates pass.

### 3. Kubernetes Database Assets

The repo should gain Kubernetes manifests for:

- PostgreSQL secret template
- PostgreSQL service
- PostgreSQL stateful set
- PVC
- backup CronJob
- ad-hoc backup Job template
- optional restore Job template for rehearsals

The manifests should remain simple enough for a single VPS and should not assume a PostgreSQL operator or advanced CSI features.

### 4. Deployment Integration

The current deploy agent already supports:

- applying manifests
- running a migration job
- rolling the webhook, worker, and admin deployments

The migration should extend this model rather than replace it. The database cutover should be operationally expressed as:

1. provision the in-cluster Postgres
2. run Alembic against it
3. restore verified data into it
4. patch `DATABASE_URL`
5. run the normal migration job
6. roll the app

This keeps the existing deployment model recognizable and debuggable.

## Migration Phases

### Phase 1: Prepare The Target Database

- add in-cluster PostgreSQL manifests
- create the database secret and service
- provision the PVC-backed database
- run Alembic to the current head on the new database
- verify the database is reachable and healthy

### Phase 2: Add Safety Controls And Tooling

- add queue-only webhook mode
- add database comparison scripts
- add backup upload scripts and scheduled backups
- add restore rehearsal tooling
- add docs for snapshot, restore, and cutover

### Phase 3: Dry Runs

- take a fresh Neon backup
- restore it into the in-cluster Postgres
- run comparison scripts
- run application smoke checks against the restored target
- rehearse the operator runbook end-to-end

At least one dry run should happen before the real cutover.

### Phase 4: Production Cutover

The production cutover sequence should be:

1. confirm the latest scheduled backup to R2 exists and is readable
2. enable `APP_MODE=queue_only`
3. roll the webhook deployment
4. scale the worker deployment to `0`
5. take the final Neon logical backup
6. upload the final backup to R2 and record its checksum
7. restore that backup into the in-cluster Postgres
8. run verification scripts
9. patch `DATABASE_URL` to the in-cluster Postgres
10. run the normal Alembic migration job against the new database
11. roll the webhook deployment on the new database
12. verify `/health/ready`
13. scale the worker back to `1`
14. allow the queued backlog to drain into the new database
15. switch `APP_MODE` back to `normal`

### Phase 5: Post-Cutover Observation

For an observation window, Neon should remain untouched as the rollback source while the new database proves stable.

During this window:

- keep scheduled backups running
- monitor worker errors and queue depth
- compare key table counts periodically
- do not decommission Neon immediately

## Verification Gates

The cutover may proceed only if all of the following are true:

- the final backup was uploaded successfully to R2
- the backup checksum matches the local artifact
- the target database is on the expected Alembic head
- row counts match across all expected user tables
- key-table spot checks match
- the webhook deployment is healthy after the `DATABASE_URL` swap
- the queue backlog begins draining successfully on the new database

These are explicit go/no-go gates, not informal checks.

## Rollback Model

Rollback is intentionally split into two windows.

### Safe Rollback Window

Before the worker resumes consuming queued jobs against the new database, rollback is simple:

- patch `DATABASE_URL` back to Neon
- restart the webhook deployment
- restart the worker deployment
- return `APP_MODE` to `normal`

This is the main rollback point and should be treated as the cutover commit boundary.

### Post-Resume Rollback Window

After the worker starts draining queued jobs into the new database, the new database becomes the source of truth for fresh writes. Rolling back to Neon after that point is no longer a trivial secret flip.

That means the cutover should not be declared complete until:

- the webhook is healthy on the new DB
- workers resume successfully
- backlog drain is stable

## Risks And Mitigations

### 1. Single-Node Storage Risk

Risk:
- node loss or disk corruption would take out the live in-cluster database

Mitigation:
- mandatory external R2 backups
- documented restore process
- regular restore rehearsal

### 2. Disk Headroom Risk

Risk:
- the VPS has limited free disk space

Mitigation:
- keep the database PVC modest
- avoid large temporary dump files where possible
- stream backups directly to object storage when practical
- verify free disk before dry runs and cutover

### 3. Silent Data Mismatch Risk

Risk:
- restore succeeds but data is incomplete or inconsistent

Mitigation:
- comparison scripts
- explicit table-count gates
- key-table spot checks
- smoke tests against the target before switching traffic

### 4. Inline Processing During Cutover

Risk:
- webhook pods perform inline work against the old or unavailable database during maintenance

Mitigation:
- queue-only mode
- worker scale-down during final sync

## Non-Goals For Phase One

This first migration does not attempt to deliver:

- multi-node PostgreSQL HA inside Kubernetes
- point-in-time recovery
- automated failover
- cross-region replication
- dual-write database routing inside the application

Those can be addressed later once the system is safely running off Neon.
