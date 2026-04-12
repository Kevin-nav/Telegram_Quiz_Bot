import json

from scripts.db_snapshot_metadata import build_snapshot_metadata, main


def test_build_snapshot_metadata_includes_counts_and_alembic_head():
    snapshot = build_snapshot_metadata(
        database_name="neondb",
        postgres_version="PostgreSQL 17.8",
        alembic_head="20260408_000003",
        table_counts={"users": 12, "question_attempts": 44},
        collected_at="2026-04-12T18:00:00+00:00",
    )

    assert snapshot["database_name"] == "neondb"
    assert snapshot["alembic_head"] == "20260408_000003"
    assert snapshot["table_count_total"] == 56
    assert snapshot["tables_checked"] == 2
    assert snapshot["table_counts"]["users"] == 12


def test_db_snapshot_metadata_main_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.db_snapshot_metadata.collect_database_snapshot",
        lambda database_url, tables=None: build_snapshot_metadata(
            database_name="targetdb",
            postgres_version="PostgreSQL 17.8",
            alembic_head="head123",
            table_counts={"users": 3},
            collected_at="2026-04-12T18:05:00+00:00",
        ),
    )

    exit_code = main(["--database-url", "postgresql://user:pass@host/db"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["database_name"] == "targetdb"
    assert payload["table_counts"] == {"users": 3}
