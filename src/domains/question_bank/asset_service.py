from __future__ import annotations

import logging
from dataclasses import dataclass

from src.infra.r2.storage import R2Storage


QUESTION_ASSET_CONTENT_TYPE = "image/png"

log = logging.getLogger(__name__)


def build_question_asset_key(
    *,
    course_slug: str,
    question_key: str,
    version: str,
    asset_name: str,
) -> str:
    return "/".join(
        [
            "questions",
            course_slug.strip("/"),
            question_key.strip("/"),
            version.strip("/"),
            asset_name.strip("/"),
        ]
    )


@dataclass(slots=True)
class UploadedAsset:
    key: str
    url: str


class QuestionBankAssetService:
    def __init__(self, storage: R2Storage | None = None):
        self.storage = storage or R2Storage()

    def upload_question_variant(
        self,
        *,
        course_slug: str,
        question_key: str,
        version: str,
        variant_index: int,
        image_bytes: bytes,
    ) -> UploadedAsset:
        key = build_question_asset_key(
            course_slug=course_slug,
            question_key=question_key,
            version=version,
            asset_name=f"question_variant_{variant_index}.png",
        )
        return self._upload_png_if_missing(key, image_bytes)

    def upload_explanation_image(
        self,
        *,
        course_slug: str,
        question_key: str,
        version: str,
        image_bytes: bytes,
    ) -> UploadedAsset:
        key = build_question_asset_key(
            course_slug=course_slug,
            question_key=question_key,
            version=version,
            asset_name="explanation.png",
        )
        return self._upload_png_if_missing(key, image_bytes)

    def _upload_png_if_missing(self, key: str, image_bytes: bytes) -> UploadedAsset:
        """Upload to R2 only if the object doesn't already exist."""
        object_exists = getattr(self.storage, "object_exists", None)
        if callable(object_exists) and object_exists(key):
            log.info("R2 object already exists, skipping upload: %s", key)
            return UploadedAsset(key=key, url=self.storage.build_public_url(key))

        self.storage.put_object(key, image_bytes, QUESTION_ASSET_CONTENT_TYPE)
        return UploadedAsset(key=key, url=self.storage.build_public_url(key))
