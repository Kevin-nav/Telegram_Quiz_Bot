from src.core.config import get_settings


def create_r2_client():
    settings = get_settings()
    if not all(
        [
            settings.r2_account_id,
            settings.r2_access_key_id,
            settings.r2_secret_access_key,
            settings.r2_bucket_name,
        ]
    ):
        raise ValueError("R2 configuration is incomplete.")

    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for R2 support.") from exc

    endpoint_url = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )
