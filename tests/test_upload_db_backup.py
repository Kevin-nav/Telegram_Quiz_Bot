import json
from pathlib import Path

from scripts.upload_db_backup import (
    build_backup_manifest,
    compute_sha256,
    upload_backup,
)


def test_compute_sha256_returns_hex_digest():
    assert (
        compute_sha256(b"backup-bytes")
        == "3f75e04c360b46d235f2fc1059fc5a3b29c02152b3e261f878d3875cf7f5277c"
    )


def test_build_backup_manifest_includes_keys_and_checksum(tmp_path: Path):
    backup_path = tmp_path / "snapshot.dump"
    backup_path.write_bytes(b"backup-bytes")

    manifest = build_backup_manifest(
        database_name="adarkwa-study-bot",
        backup_path=backup_path,
        checksum_sha256="abc123",
        backup_key="db-backups/adarkwa-study-bot/snapshot.dump",
        metadata_key="db-backups/adarkwa-study-bot/snapshot.dump.metadata.json",
        uploaded_at="2026-04-12T18:20:00+00:00",
    )

    assert manifest["backup_filename"] == "snapshot.dump"
    assert manifest["backup_size_bytes"] == len(b"backup-bytes")
    assert manifest["checksum_sha256"] == "abc123"


def test_upload_backup_uploads_backup_and_metadata(monkeypatch, tmp_path: Path):
    backup_path = tmp_path / "snapshot.dump"
    metadata_path = tmp_path / "snapshot.metadata.json"
    backup_path.write_bytes(b"backup-bytes")
    metadata_path.write_text(json.dumps({"source": "neon"}), encoding="utf-8")

    class FakeStorage:
        def __init__(self):
            self.database_uploads = []
            self.object_uploads = []

        def put_database_backup(self, key, body, metadata=None, content_type="application/octet-stream"):
            self.database_uploads.append(
                {
                    "key": key,
                    "body": body,
                    "metadata": metadata,
                    "content_type": content_type,
                }
            )

        def put_bytes_object(self, key, body, content_type, metadata=None):
            self.object_uploads.append(
                {
                    "key": key,
                    "body": body,
                    "content_type": content_type,
                    "metadata": metadata,
                }
            )

    monkeypatch.setattr(
        "scripts.upload_db_backup.get_settings",
        lambda: type("Settings", (), {"r2_db_backup_prefix": "db-backups"})(),
    )

    storage = FakeStorage()
    manifest = upload_backup(
        storage=storage,
        database_name="adarkwa-study-bot",
        backup_path=backup_path,
        metadata_path=metadata_path,
    )

    assert manifest["backup_object_key"] == "db-backups/adarkwa-study-bot/snapshot.dump"
    assert manifest["operator_metadata"] == {"source": "neon"}
    assert storage.database_uploads[0]["metadata"]["database_name"] == "adarkwa-study-bot"
    assert storage.object_uploads[0]["key"].endswith(".metadata.json")
