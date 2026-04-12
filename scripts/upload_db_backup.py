from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import get_settings
from src.infra.r2.storage import (
    R2Storage,
    build_database_backup_object_key,
)


def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def build_backup_manifest(
    *,
    database_name: str,
    backup_path: Path,
    checksum_sha256: str,
    backup_key: str,
    metadata_key: str,
    uploaded_at: str | None = None,
) -> dict[str, object]:
    return {
        "database_name": database_name,
        "backup_filename": backup_path.name,
        "backup_size_bytes": backup_path.stat().st_size,
        "checksum_sha256": checksum_sha256,
        "backup_object_key": backup_key,
        "metadata_object_key": metadata_key,
        "uploaded_at": uploaded_at or datetime.now(UTC).isoformat(),
    }


def upload_backup(
    *,
    storage: R2Storage,
    database_name: str,
    backup_path: Path,
    metadata_path: Path | None = None,
) -> dict[str, object]:
    settings = get_settings()
    backup_bytes = backup_path.read_bytes()
    checksum_sha256 = compute_sha256(backup_bytes)
    backup_key = build_database_backup_object_key(
        database_name,
        backup_path.name,
        prefix=settings.r2_db_backup_prefix,
    )
    metadata_key = f"{backup_key}.metadata.json"
    manifest = build_backup_manifest(
        database_name=database_name,
        backup_path=backup_path,
        checksum_sha256=checksum_sha256,
        backup_key=backup_key,
        metadata_key=metadata_key,
    )

    metadata = {
        "database_name": database_name,
        "checksum_sha256": checksum_sha256,
    }
    storage.put_database_backup(
        backup_key,
        backup_bytes,
        metadata=metadata,
    )

    if metadata_path is not None:
        operator_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        manifest["operator_metadata"] = operator_metadata

    storage.put_bytes_object(
        metadata_key,
        json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8"),
        "application/json",
        metadata={"database_name": database_name},
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a completed PostgreSQL backup file to Cloudflare R2.",
    )
    parser.add_argument("--database-name", required=True)
    parser.add_argument("--backup-file", required=True)
    parser.add_argument("--metadata-file")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage = R2Storage()
    manifest = upload_backup(
        storage=storage,
        database_name=args.database_name,
        backup_path=Path(args.backup_file),
        metadata_path=Path(args.metadata_file) if args.metadata_file else None,
    )
    if args.pretty:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
