def test_latex_object_key_generation():
    from src.infra.r2.storage import build_latex_object_key

    key = build_latex_object_key("math101", "q42", "abc123")

    assert key == "latex/math101/q42/abc123.png"


def test_database_backup_key_generation():
    from src.infra.r2.storage import build_database_backup_object_key

    key = build_database_backup_object_key(
        "adarkwa-study-bot",
        "2026-04-12T120000Z.dump",
    )

    assert key == "db-backups/adarkwa-study-bot/2026-04-12T120000Z.dump"


def test_put_database_backup_uses_generic_upload_path():
    from src.infra.r2.storage import R2Storage

    calls = []

    class FakeClient:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    storage = R2Storage(client=FakeClient(), bucket_name="backup-bucket")
    storage.put_database_backup(
        "db-backups/adarkwa/backup.dump",
        b"backup-bytes",
        metadata={"checksum_sha256": "abc123"},
    )

    assert calls == [
        {
            "Bucket": "backup-bucket",
            "Key": "db-backups/adarkwa/backup.dump",
            "Body": b"backup-bytes",
            "ContentType": "application/octet-stream",
            "Metadata": {"checksum_sha256": "abc123"},
        }
    ]
