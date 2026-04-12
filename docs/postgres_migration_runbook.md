# Neon To K3s Postgres Migration Runbook

This runbook covers:

- provisioning the in-cluster PostgreSQL instance
- enabling recurring R2 backups
- rehearsing restore and verification
- performing the production cutover with queued writes
- rolling back before the new database becomes the source of truth

The current production namespace is:

```text
adarkwa-study-bot
```

## 1. Preconditions

Before touching production:

- confirm the cluster has enough free disk for the PostgreSQL PVC and temporary dump files
- confirm R2 credentials and bucket access work
- confirm the current backend image is healthy
- keep Neon intact until the new database has been stable for an observation window

Useful setup:

```bash
export NAMESPACE=adarkwa-study-bot
export BACKEND_IMAGE="$(kubectl get deployment adarkwa-bot-webhook -n "${NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}')"
```

## 2. Provision The In-Cluster PostgreSQL Instance

Create the PostgreSQL secret from the example after replacing placeholder values:

```bash
kubectl apply -n "${NAMESPACE}" -f k8s/postgres-secret.example.yaml
```

Provision the service and stateful set:

```bash
kubectl apply -n "${NAMESPACE}" -f k8s/postgres-service.yaml
kubectl apply -n "${NAMESPACE}" -f k8s/postgres-statefulset.yaml
kubectl rollout status statefulset/adarkwa-postgres -n "${NAMESPACE}" --timeout=300s
kubectl get pods -n "${NAMESPACE}" -l app=adarkwa-postgres -o wide
```

## 3. Bootstrap The Target Schema

Run Alembic against the new database before any data restore.

Build the target database URL from the secret values you chose. The in-cluster hostname is:

```text
adarkwa-postgres:5432
```

Run a one-off migration pod with the current backend image:

```bash
export TARGET_DATABASE_URL='postgresql://<user>:<password>@adarkwa-postgres:5432/<database>'

kubectl run adarkwa-postgres-schema-bootstrap \
  -n "${NAMESPACE}" \
  --rm -i --restart=Never \
  --image="${BACKEND_IMAGE}" \
  --env="DATABASE_URL=${TARGET_DATABASE_URL}" \
  --command -- alembic upgrade head
```

## 4. Enable Scheduled Backups To R2

Render the backup CronJob with the same backend image used by production:

```bash
sed "s|__IMAGE__|${BACKEND_IMAGE}|g" k8s/postgres-backup-cronjob.yaml | \
  kubectl apply -n "${NAMESPACE}" -f -
```

Kick off a manual backup once to prove the path:

```bash
kubectl create job \
  --namespace "${NAMESPACE}" \
  --from=cronjob/adarkwa-postgres-backup \
  "adarkwa-postgres-backup-manual-$(date +%Y%m%d%H%M%S)"

kubectl get jobs -n "${NAMESPACE}"
kubectl logs -n "${NAMESPACE}" job/<manual-backup-job-name>
```

The backup job should:

- create a `pg_dump -Fc` snapshot
- collect snapshot metadata
- upload both to R2

## 5. Rehearse Restore

Edit the `BACKUP_OBJECT_KEY` in `k8s/postgres-restore-job.yaml` to the backup object you want to restore, then apply it:

```bash
kubectl apply -n "${NAMESPACE}" -f k8s/postgres-restore-job.yaml
kubectl logs -n "${NAMESPACE}" job/adarkwa-postgres-restore
```

For a non-destructive rehearsal, point the restore job at a scratch database rather than the production target database.

## 6. Compare Source And Target

Run the snapshot comparison before cutover:

```bash
export SOURCE_DATABASE_URL="$(kubectl get secret adarkwa-bot-secret -n "${NAMESPACE}" -o jsonpath='{.data.DATABASE_URL}' | base64 -d)"

kubectl run adarkwa-db-compare \
  -n "${NAMESPACE}" \
  --rm -i --restart=Never \
  --image="${BACKEND_IMAGE}" \
  --env="SOURCE_URL=${SOURCE_DATABASE_URL}" \
  --env="TARGET_URL=${TARGET_DATABASE_URL}" \
  --command -- sh -lc \
  'python scripts/compare_databases.py --source-url "$SOURCE_URL" --target-url "$TARGET_URL" --pretty'
```

Do not proceed if:

- any table count mismatches
- Alembic heads differ unexpectedly
- the target database fails health checks

## 7. Production Cutover

### 7.1 Put The App In Queue-Only Mode

This keeps webhook requests accepted while preventing inline processing:

```bash
kubectl patch configmap adarkwa-bot-config \
  -n "${NAMESPACE}" \
  --type merge \
  -p '{"data":{"APP_MODE":"queue_only"}}'

kubectl rollout restart deployment/adarkwa-bot-webhook -n "${NAMESPACE}"
kubectl rollout status deployment/adarkwa-bot-webhook -n "${NAMESPACE}" --timeout=300s
```

### 7.2 Pause The Worker

```bash
kubectl scale deployment/adarkwa-bot-worker -n "${NAMESPACE}" --replicas=0
kubectl get pods -n "${NAMESPACE}" -l app=adarkwa-bot,component=worker
```

At this point:

- webhook requests still return `200`
- updates queue in Redis/ARQ
- no new background writes are consumed

### 7.3 Take The Final Neon Backup

Take the final Neon `pg_dump -Fc` from any trusted machine that has `pg_dump` available, then upload it with:

```bash
python scripts/upload_db_backup.py \
  --database-name neondb \
  --backup-file <path-to-final-neon-dump> \
  --pretty
```

Record:

- the object key
- the SHA-256 checksum
- the upload timestamp

### 7.4 Restore And Verify

Restore the final dump into the in-cluster PostgreSQL instance, then rerun the comparison step until it passes.

### 7.5 Swap `DATABASE_URL`

Patch the application secret to the new in-cluster PostgreSQL URL:

```bash
kubectl patch secret adarkwa-bot-secret \
  -n "${NAMESPACE}" \
  --type merge \
  -p "{\"stringData\":{\"DATABASE_URL\":\"${TARGET_DATABASE_URL}\"}}"
```

Run the normal migration job against the new database and restart the webhook:

```bash
export MIGRATION_JOB_NAME="adarkwa-bot-migrate-cutover-$(date +%Y%m%d%H%M%S)"

sed \
  -e "s|__IMAGE__|${BACKEND_IMAGE}|g" \
  -e "s|__MIGRATION_JOB_NAME__|${MIGRATION_JOB_NAME}|g" \
  k8s/migration-job.yaml | kubectl apply -n "${NAMESPACE}" -f -

kubectl wait \
  -n "${NAMESPACE}" \
  --for=condition=complete \
  "job/${MIGRATION_JOB_NAME}" \
  --timeout=300s

kubectl rollout restart deployment/adarkwa-bot-webhook -n "${NAMESPACE}"
kubectl rollout status deployment/adarkwa-bot-webhook -n "${NAMESPACE}" --timeout=300s
```

Confirm:

```bash
kubectl exec -n "${NAMESPACE}" deploy/adarkwa-bot-webhook -- printenv DATABASE_URL
curl -s https://tg-bot-tanjah.sankoslides.com/health/ready
```

### 7.6 Resume The Worker

```bash
kubectl scale deployment/adarkwa-bot-worker -n "${NAMESPACE}" --replicas=1
kubectl rollout status deployment/adarkwa-bot-worker -n "${NAMESPACE}" --timeout=300s
kubectl logs -n "${NAMESPACE}" deployment/adarkwa-bot-worker --tail=100
```

### 7.7 Return To Normal Mode

```bash
kubectl patch configmap adarkwa-bot-config \
  -n "${NAMESPACE}" \
  --type merge \
  -p '{"data":{"APP_MODE":"normal"}}'

kubectl rollout restart deployment/adarkwa-bot-webhook -n "${NAMESPACE}"
kubectl rollout status deployment/adarkwa-bot-webhook -n "${NAMESPACE}" --timeout=300s
```

## 8. Rollback Boundary

Rollback is simple only before the worker has resumed against the new database.

If you need to back out before that point:

```bash
kubectl patch secret adarkwa-bot-secret \
  -n "${NAMESPACE}" \
  --type merge \
  -p "{\"stringData\":{\"DATABASE_URL\":\"${SOURCE_DATABASE_URL}\"}}"

kubectl patch configmap adarkwa-bot-config \
  -n "${NAMESPACE}" \
  --type merge \
  -p '{"data":{"APP_MODE":"normal"}}'

kubectl rollout restart deployment/adarkwa-bot-webhook -n "${NAMESPACE}"
kubectl scale deployment/adarkwa-bot-worker -n "${NAMESPACE}" --replicas=1
```

After the worker resumes on the new database and starts draining queued jobs, the new database becomes the source of truth for fresh writes. At that point rollback is no longer just a secret swap.

## 9. Post-Cutover Observation

During the first observation window:

- keep Neon intact
- keep scheduled R2 backups running
- compare key table counts daily
- watch worker logs for persistence errors
- confirm `/health/ready` stays healthy

Only decommission Neon after the in-cluster database and restore path have both been proven in production.
