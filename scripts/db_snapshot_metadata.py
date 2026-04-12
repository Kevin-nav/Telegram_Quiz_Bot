from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.security import normalize_sync_database_url


def build_snapshot_metadata(
    *,
    database_name: str,
    postgres_version: str,
    alembic_head: str | None,
    table_counts: dict[str, int],
    collected_at: str | None = None,
) -> dict[str, object]:
    return {
        "database_name": database_name,
        "postgres_version": postgres_version,
        "alembic_head": alembic_head,
        "collected_at": collected_at or datetime.now(UTC).isoformat(),
        "table_count_total": sum(table_counts.values()),
        "tables_checked": len(table_counts),
        "table_counts": dict(sorted(table_counts.items())),
    }


def collect_database_snapshot(
    database_url: str,
    *,
    tables: list[str] | None = None,
) -> dict[str, object]:
    engine = create_engine(normalize_sync_database_url(database_url), pool_pre_ping=True)
    with engine.connect() as conn:
        database_name = conn.execute(text("select current_database()")).scalar_one()
        postgres_version = conn.execute(text("select version()")).scalar_one()
        alembic_head = conn.execute(
            text("select version_num from alembic_version limit 1")
        ).scalar_one_or_none()

        selected_tables = tables or [
            row[0]
            for row in conn.execute(
                text(
                    """
                    select tablename
                    from pg_tables
                    where schemaname = 'public'
                    order by tablename
                    """
                )
            ).all()
        ]

        table_counts: dict[str, int] = {}
        for table_name in selected_tables:
            count = conn.exec_driver_sql(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).scalar_one()
            table_counts[table_name] = int(count)

    engine.dispose()
    return build_snapshot_metadata(
        database_name=database_name,
        postgres_version=postgres_version,
        alembic_head=alembic_head,
        table_counts=table_counts,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect PostgreSQL snapshot metadata and exact table counts.",
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--table", action="append", dest="tables")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    snapshot = collect_database_snapshot(
        args.database_url,
        tables=args.tables,
    )
    if args.pretty:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print(json.dumps(snapshot, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
