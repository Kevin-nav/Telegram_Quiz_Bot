from src.domains.question_bank.asset_service import (
    QuestionBankAssetService,
    build_question_asset_key,
)


class FakeStorage:
    def __init__(self):
        self.calls = []

    def put_object(self, key: str, body: bytes, content_type: str) -> None:
        self.calls.append(
            {
                "key": key,
                "body": body,
                "content_type": content_type,
            }
        )

    def build_public_url(self, key: str) -> str:
        return f"https://cdn.example.com/{key}"


def test_build_question_asset_key_returns_versioned_path():
    key = build_question_asset_key(
        course_slug="differential-equations",
        question_key="q-001",
        version="abc123",
        asset_name="question_variant_0.png",
    )

    assert key == "questions/differential-equations/q-001/abc123/question_variant_0.png"


def test_asset_service_uploads_question_variant_and_returns_key_and_url():
    storage = FakeStorage()
    service = QuestionBankAssetService(storage)

    uploaded = service.upload_question_variant(
        course_slug="differential-equations",
        question_key="q-001",
        version="abc123",
        variant_index=2,
        image_bytes=b"png-bytes",
    )

    assert uploaded.key == "questions/differential-equations/q-001/abc123/question_variant_2.png"
    assert (
        uploaded.url
        == "https://cdn.example.com/questions/differential-equations/q-001/abc123/question_variant_2.png"
    )
    assert storage.calls == [
        {
            "key": "questions/differential-equations/q-001/abc123/question_variant_2.png",
            "body": b"png-bytes",
            "content_type": "image/png",
        }
    ]


def test_asset_service_uploads_explanation_image():
    storage = FakeStorage()
    service = QuestionBankAssetService(storage)

    uploaded = service.upload_explanation_image(
        course_slug="linear-electronics",
        question_key="op-amp-001",
        version="v2",
        image_bytes=b"explanation-bytes",
    )

    assert uploaded.key == "questions/linear-electronics/op-amp-001/v2/explanation.png"
    assert uploaded.url == "https://cdn.example.com/questions/linear-electronics/op-amp-001/v2/explanation.png"
