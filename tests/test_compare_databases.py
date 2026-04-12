import json

from scripts.compare_databases import compare_snapshots, main


def test_compare_snapshots_reports_matching_tables():
    source = {
        "database_name": "neon",
        "alembic_head": "head123",
        "table_counts": {"users": 2, "question_attempts": 9},
    }
    target = {
        "database_name": "cluster",
        "alembic_head": "head123",
        "table_counts": {"users": 2, "question_attempts": 9},
    }

    result = compare_snapshots(source, target)

    assert result["all_tables_match"] is True
    assert result["mismatches"] == []


def test_compare_snapshots_reports_count_mismatch():
    source = {
        "database_name": "neon",
        "alembic_head": "head123",
        "table_counts": {"users": 2, "question_attempts": 9},
    }
    target = {
        "database_name": "cluster",
        "alembic_head": "head123",
        "table_counts": {"users": 3, "question_attempts": 9},
    }

    result = compare_snapshots(source, target, key_tables=["users"])

    assert result["all_tables_match"] is False
    assert result["key_tables_match"] is False
    assert result["mismatches"] == [
        {
            "table": "users",
            "source_count": 2,
            "target_count": 3,
        }
    ]


def test_compare_databases_main_returns_non_zero_for_mismatch(monkeypatch, capsys):
    snapshots = iter(
        [
            {
                "database_name": "neon",
                "alembic_head": "head123",
                "table_counts": {"users": 2},
            },
            {
                "database_name": "cluster",
                "alembic_head": "head123",
                "table_counts": {"users": 1},
            },
        ]
    )

    monkeypatch.setattr(
        "scripts.compare_databases.collect_database_snapshot",
        lambda database_url, tables=None: next(snapshots),
    )

    exit_code = main(
        [
            "--source-url",
            "postgresql://user:pass@source/db",
            "--target-url",
            "postgresql://user:pass@target/db",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["all_tables_match"] is False
