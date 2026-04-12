# Neon To K8s Postgres Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move production from Neon to an in-cluster PostgreSQL instance with a short queued-write cutover, durable R2 backups, restore rehearsal tooling, and explicit verification and rollback steps.

**Architecture:** Keep the application on one canonical `DATABASE_URL`, but add an operator-controlled `APP_MODE` so webhook traffic can be accepted in `queue_only` mode during cutover while the worker is paused. Provision a single PostgreSQL `17` instance in Kubernetes with a PVC, run logical backups to R2, and add comparison scripts so cutover is guarded by explicit verification gates rather than intuition.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, ARQ, Redis, PostgreSQL 17, Kubernetes, Bash, Python, Cloudflare R2, pytest

---

### Task 1: Add Queue-Only Maintenance Mode

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\core\config.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\api\webhooks.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\api\telegram_dispatcher.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\api\health.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_config.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_webhook.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_telegram_dispatcher.py`

**Step 1: Write the failing tests**

Add tests that prove:

- `APP_MODE=queue_only` is accepted and exposed by settings
- a text webhook update routes to `background` instead of `inline` in queue-only mode
- the readiness payload reports the current app mode

**Step 2: Run tests to verify failure**

Run: `venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_webhook.py tests/test_telegram_dispatcher.py -v`
Expected: FAIL because `APP_MODE` and queue-only behavior do not exist yet.

**Step 3: Write the minimal implementation**

Add:

- `app_mode: str = Field(default="normal", alias="APP_MODE")`
- validation for `normal|queue_only`
- `TelegramUpdateDispatcher(..., force_background=...)`
- webhook construction that enables `force_background` when settings are in queue-only mode
- readiness payload detail that includes the app mode

**Step 4: Run the targeted tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_webhook.py tests/test_telegram_dispatcher.py -v`
Expected: PASS

### Task 2: Add Database Snapshot Metadata And Comparison Scripts

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\scripts\db_snapshot_metadata.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\scripts\compare_databases.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_db_snapshot_metadata.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_compare_databases.py`

**Step 1: Write the failing tests**

Add tests that prove:

- snapshot metadata includes Alembic head, PostgreSQL version, and table counts
- database comparison reports mismatched row counts and exits non-zero
- a matching comparison reports success

**Step 2: Run tests to verify failure**

Run: `venv\Scripts\python.exe -m pytest tests/test_db_snapshot_metadata.py tests/test_compare_databases.py -v`
Expected: FAIL because the scripts do not exist.

**Step 3: Write the minimal implementation**

Implement:

- metadata collection against one DSN
- comparison logic across two DSNs
- JSON output for automation
- a small built-in set of key tables plus optional full-table checks

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_db_snapshot_metadata.py tests/test_compare_databases.py -v`
Expected: PASS

### Task 3: Add Backup Upload Tooling For R2

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\core\config.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\r2\storage.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\scripts\upload_db_backup.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_upload_db_backup.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_r2_storage.py`

**Step 1: Write the failing tests**

Add tests for:

- backup object key generation under a `db-backups/` prefix
- content-type and metadata handling for backup uploads
- upload script manifest output with checksum and object key

**Step 2: Run tests to verify failure**

Run: `venv\Scripts\python.exe -m pytest tests/test_r2_storage.py tests/test_upload_db_backup.py -v`
Expected: FAIL because the backup upload path is not implemented.

**Step 3: Write the minimal implementation**

Add:

- `R2_DB_BACKUP_PREFIX`
- a backup object key helper
- a generic binary upload path in `R2Storage`
- a script that uploads a finished backup file and emits machine-readable metadata

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_r2_storage.py tests/test_upload_db_backup.py -v`
Expected: PASS

### Task 4: Add In-Cluster PostgreSQL And Backup Manifests

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\postgres-secret.example.yaml`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\postgres-service.yaml`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\postgres-statefulset.yaml`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\postgres-backup-cronjob.yaml`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\postgres-restore-job.yaml`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\k8s\config.yaml`

**Step 1: Write a manifest smoke test or validation step**

Use simple structural checks:

- the PostgreSQL service name is stable
- the StatefulSet mounts a PVC
- the backup CronJob references the same secret/config values used by the upload tooling

**Step 2: Run validation**

Run: `kubectl apply --dry-run=client -f k8s/postgres-service.yaml -f k8s/postgres-statefulset.yaml -f k8s/postgres-backup-cronjob.yaml`
Expected: FAIL or be unavailable until manifests are added.

**Step 3: Write the minimal implementation**

Add manifests for:

- a single Postgres pod
- a PVC on `local-path`
- a headless or stable ClusterIP service
- a backup CronJob that runs `pg_dump -Fc`, computes `sha256`, writes metadata, and uploads to R2
- a restore Job template that can load a snapshot into a scratch or target DB

**Step 4: Run validation again**

Run: `kubectl apply --dry-run=client -f k8s/postgres-service.yaml -f k8s/postgres-statefulset.yaml -f k8s/postgres-backup-cronjob.yaml`
Expected: PASS

### Task 5: Add Operator Runbooks For Provisioning, Dry Run, Cutover, Rollback, And Restore

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\README.md`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\docs\deployment_setup.md`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\docs\postgres_migration_runbook.md`

**Step 1: Write the runbook sections**

Document:

- how to provision the new DB
- how to take and upload backups
- how to rehearse restore
- how to run comparison scripts
- exact cutover order
- the rollback boundary before workers resume

**Step 2: Validate docs against the current deploy model**

Check that all commands reference existing scripts/manifests and the actual namespace name.

**Step 3: Update the docs**

Add exact command examples using:

- `kubectl -n adarkwa-study-bot`
- `DATABASE_URL` patching
- worker scale-to-zero and scale-back-up
- queue-only `APP_MODE`

### Task 6: Run Targeted Verification

**Files:**
- No new files required

**Step 1: Run the targeted Python tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_webhook.py tests/test_telegram_dispatcher.py tests/test_r2_storage.py tests/test_db_snapshot_metadata.py tests/test_compare_databases.py tests/test_upload_db_backup.py -v`
Expected: PASS

**Step 2: Run manifest smoke validation**

Run: `kubectl apply --dry-run=client -f k8s/postgres-service.yaml -f k8s/postgres-statefulset.yaml -f k8s/postgres-backup-cronjob.yaml`
Expected: PASS

**Step 3: Review the resulting git diff**

Run: `git status --short`
Expected: only the intended migration-related files plus the user's pre-existing unrelated changes
