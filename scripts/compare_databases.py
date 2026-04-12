from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.db_snapshot_metadata import collect_database_snapshot


DEFAULT_KEY_TABLES = [
    "users",
    "user_bot_profiles",
    "question_attempts",
    "student_question_srs",
    "analytics_events",
]


def compare_snapshots(
    source_snapshot: dict[str, object],
    target_snapshot: dict[str, object],
    *,
    key_tables: list[str] | None = None,
) -> dict[str, object]:
    source_counts = source_snapshot.get("table_counts", {})
    target_counts = target_snapshot.get("table_counts", {})
    table_names = sorted(set(source_counts) | set(target_counts))
    mismatches = []

    for table_name in table_names:
        source_count = int(source_counts.get(table_name, -1))
        target_count = int(target_counts.get(table_name, -1))
        if source_count != target_count:
            mismatches.append(
                {
                    "table": table_name,
                    "source_count": source_count,
                    "target_count": target_count,
                }
            )

    selected_key_tables = key_tables or DEFAULT_KEY_TABLES
    key_table_status = {
        table_name: source_counts.get(table_name) == target_counts.get(table_name)
        for table_name in selected_key_tables
    }

    return {
        "source_database": source_snapshot.get("database_name"),
        "target_database": target_snapshot.get("database_name"),
        "source_alembic_head": source_snapshot.get("alembic_head"),
        "target_alembic_head": target_snapshot.get("alembic_head"),
        "all_tables_match": not mismatches,
        "key_tables_match": all(key_table_status.values()),
        "key_table_status": key_table_status,
        "mismatches": mismatches,
        "tables_compared": table_names,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare PostgreSQL row-count snapshots between two databases.",
    )
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--table", action="append", dest="tables")
    parser.add_argument("--key-table", action="append", dest="key_tables")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_snapshot = collect_database_snapshot(args.source_url, tables=args.tables)
    target_snapshot = collect_database_snapshot(args.target_url, tables=args.tables)
    comparison = compare_snapshots(
        source_snapshot,
        target_snapshot,
        key_tables=args.key_tables,
    )
    if args.pretty:
        print(json.dumps(comparison, indent=2, sort_keys=True))
    else:
        print(json.dumps(comparison, sort_keys=True))
    return 0 if comparison["all_tables_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
