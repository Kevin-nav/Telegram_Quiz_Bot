from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import tempfile
from pathlib import Path

from src.bot.runtime_config import BotRuntimeConfig
from src.config import BOT_CONFIGS
from src.domains.question_bank.asset_service import QuestionBankAssetService
from src.domains.question_bank.latex_renderer import (
    build_explanation_latex,
    build_latex_option_variants,
    build_question_latex,
    build_variant_order_maps,
    render_latex_to_png,
)
from src.domains.question_bank.reporting import CourseImportReport, QuestionImportResult
from src.domains.question_bank.schemas import (
    ImportedQuestion,
    build_question_key,
    build_question_source_checksum,
)
from src.domains.question_bank.validation import validate_imported_question
from src.infra.db.repositories.question_bank_repository import QuestionBankRepository

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------
_TRANSIENT_EXCEPTIONS = (OSError, ConnectionError)

try:
    from sqlalchemy.exc import OperationalError as _SAOperationalError
    _TRANSIENT_EXCEPTIONS = (*_TRANSIENT_EXCEPTIONS, _SAOperationalError)
except ImportError:
    pass

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds
TELEGRAM_POLL_QUESTION_MAX_LENGTH = 300
TELEGRAM_POLL_OPTION_MAX_LENGTH = 100


def should_promote_to_latex_for_poll_limits(question: ImportedQuestion) -> bool:
    return (
        len(question.question_text) > TELEGRAM_POLL_QUESTION_MAX_LENGTH
        or any(
            len(option_text) > TELEGRAM_POLL_OPTION_MAX_LENGTH
            for option_text in question.options
        )
    )


def promote_to_latex_for_poll_limits(question: ImportedQuestion) -> None:
    if question.has_latex:
        return
    if should_promote_to_latex_for_poll_limits(question):
        question.has_latex = True


async def _retry_async(coro_factory, *, label: str = "operation"):
    """Retry an async callable up to MAX_RETRIES times with exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except _TRANSIENT_EXCEPTIONS as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning(
                    "[retry] %s failed (attempt %d/%d): %s — retrying in %.1fs",
                    label, attempt, MAX_RETRIES, exc, delay,
                )
                await asyncio.sleep(delay)
            else:
                log.error(
                    "[retry] %s failed after %d attempts: %s",
                    label, MAX_RETRIES, exc,
                )
    raise last_exc  # type: ignore[misc]


class QuestionBankImportService:
    def __init__(
        self,
        repository: QuestionBankRepository | None = None,
        asset_service: QuestionBankAssetService | None = None,
        *,
        bot_configs: dict[str, BotRuntimeConfig] | None = None,
        question_renderer=build_question_latex,
        explanation_renderer=build_explanation_latex,
        variant_builder=build_latex_option_variants,
        variant_order_builder=build_variant_order_maps,
        latex_to_png_renderer=render_latex_to_png,
    ):
        self.repository = repository or QuestionBankRepository()
        self.asset_service = asset_service or QuestionBankAssetService()
        self.bot_configs = bot_configs or BOT_CONFIGS
        self.question_renderer = question_renderer
        self.explanation_renderer = explanation_renderer
        self.variant_builder = variant_builder
        self.variant_order_builder = variant_order_builder
        self.latex_to_png_renderer = latex_to_png_renderer

    def load_question_rows(self, json_path: str | Path) -> list[dict]:
        source_path = Path(json_path)
        with source_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("Question bank JSON must contain a top-level list.")
        return payload

    async def import_course_from_json(
        self,
        *,
        course_id: str,
        json_path: str | Path,
        course_slug: str | None = None,
    ) -> CourseImportReport:
        source_path = Path(json_path)
        resolved_course_slug = course_slug or course_id
        report = CourseImportReport(
            course_id=course_id,
            course_slug=resolved_course_slug,
            source_path=source_path,
        )

        rows = self.load_question_rows(source_path)
        total = len(rows)
        for row_index, row in enumerate(rows):
            result = await self._import_row(
                course_id=course_id,
                course_slug=resolved_course_slug,
                row=row,
                row_index=row_index,
                total_rows=total,
            )
            report.add_result(result)

        return report

    async def _import_row(
        self,
        *,
        course_id: str,
        course_slug: str,
        row: dict,
        row_index: int,
        total_rows: int,
    ) -> QuestionImportResult:
        question_key: str | None = None
        source_checksum: str | None = None
        progress = f"[{row_index + 1}/{total_rows}]"

        try:
            question = ImportedQuestion.from_dict(row)
        except Exception as exc:
            log.warning("%s Row normalization failed: %s", progress, exc)
            return QuestionImportResult(
                row_index=row_index,
                status="invalid",
                errors=[f"row normalization failed: {exc}"],
            )

        promote_to_latex_for_poll_limits(question)

        errors = validate_imported_question(question)
        if errors:
            log.warning("%s Validation failed: %s", progress, errors)
            return QuestionImportResult(
                row_index=row_index,
                status="invalid",
                errors=errors,
            )

        question_key = build_question_key(course_id, question)
        source_checksum = build_question_source_checksum(question)

        # ---- Resume: skip if already "ready" with same checksum ----
        try:
            existing = await _retry_async(
                lambda: self.repository.get_question(question_key),
                label=f"get_question({question_key})",
            )
        except Exception:
            existing = None

        if (
            existing
            and existing.status == "ready"
            and existing.source_checksum == source_checksum
            and self._question_has_all_bot_assets(existing)
        ):
            log.info("%s [%s] Already ready — skipping.", progress, question_key)
            return QuestionImportResult(
                row_index=row_index,
                question_key=question_key,
                status="ready",
                variant_count=existing.variant_count or 0,
            )

        question_payload = {
            "question_key": question_key,
            "course_id": course_id,
            "course_slug": course_slug,
            "source_checksum": source_checksum,
            "status": "processing" if question.has_latex else "ready",
            "variant_count": 0,
            **question.to_dict(),
        }

        log.info("%s [%s] Saving to DB...", progress, question_key)
        stored_question = await _retry_async(
            lambda: self.repository.upsert_question(question_payload),
            label=f"upsert({question_key})",
        )

        try:
            if not question.has_latex:
                log.info("%s [%s] Ready (no LaTeX).", progress, question_key)
                return QuestionImportResult(
                    row_index=row_index,
                    question_key=question_key,
                    status="ready",
                )

            log.info("%s [%s] Processing LaTeX...", progress, question_key)
            latex_assets = await self._process_latex_assets(
                question_id=stored_question.id,
                course_slug=course_slug,
                question_key=question_key,
                source_checksum=source_checksum,
                question=question,
            )

            log.info("%s [%s] Replacing variant records...", progress, question_key)
            for bot_id, variant_records in latex_assets["variants_by_bot"].items():
                await _retry_async(
                    lambda bot_id=bot_id, variant_records=variant_records: (
                        self.repository.replace_asset_variants(
                            latex_assets["question_id"],
                            variant_records,
                            bot_id=bot_id,
                        )
                    ),
                    label=f"replace_variants({question_key}:{bot_id})",
                )
            await _retry_async(
                lambda: self.repository.update_question_status(
                    question_key,
                    status="ready",
                    source_checksum=source_checksum,
                    render_checksum=latex_assets["render_checksum"],
                    explanation_asset_key=latex_assets["explanation_asset_key"],
                    explanation_asset_url=latex_assets["explanation_asset_url"],
                    explanation_asset_keys_by_bot=latex_assets[
                        "explanation_asset_keys_by_bot"
                    ],
                    explanation_asset_urls_by_bot=latex_assets[
                        "explanation_asset_urls_by_bot"
                    ],
                    variant_count=latex_assets["variant_count"],
                ),
                label=f"update_status({question_key})",
            )
            log.info("%s [%s] LaTeX and DB done!", progress, question_key)
            return QuestionImportResult(
                row_index=row_index,
                question_key=question_key,
                status="ready",
                variant_count=latex_assets["variant_count"],
            )
        except Exception as exc:
            log.error("%s [%s] ERRORED: %s", progress, question_key, exc)
            # Try to mark as error in DB — but don't let *this* fail crash the loop
            try:
                await _retry_async(
                    lambda: self.repository.update_question_status(
                        question_key,
                        status="error",
                        source_checksum=source_checksum,
                        variant_count=0,
                    ),
                    label=f"mark_error({question_key})",
                )
            except Exception as inner_exc:
                log.error(
                    "%s [%s] Could not mark as error in DB: %s",
                    progress, question_key, inner_exc,
                )
            return QuestionImportResult(
                row_index=row_index,
                question_key=question_key,
                status="error",
                errors=[str(exc)],
            )

    async def _process_latex_assets(
        self,
        *,
        question_id: int,
        course_slug: str,
        question_key: str,
        source_checksum: str,
        question: ImportedQuestion,
    ) -> dict:
        option_variants = self.variant_builder(question.options)
        order_maps = self.variant_order_builder(question.option_count)
        variants_by_bot: dict[str, list[dict]] = {}
        explanation_asset_keys_by_bot: dict[str, str] = {}
        explanation_asset_urls_by_bot: dict[str, str] = {}
        render_inputs: list[str] = []

        for bot_id, bot_config in self.bot_configs.items():
            bot_variant_records: list[dict] = []
            for variant_index, option_variant in enumerate(option_variants):
                question_latex = self.question_renderer(
                    question.question_text,
                    option_variant,
                    bot_theme=bot_config.theme,
                )
                render_inputs.append(question_latex)
                image_bytes = self._render_latex_bytes(
                    question_latex,
                    suffix=f"{bot_id}_question_variant_{variant_index}.png",
                )
                uploaded = self.asset_service.upload_question_variant(
                    course_slug=course_slug,
                    question_key=question_key,
                    version=source_checksum,
                    variant_index=variant_index,
                    image_bytes=image_bytes,
                    bot_id=bot_id,
                )
                bot_variant_records.append(
                    {
                        "bot_id": bot_id,
                        "variant_index": variant_index,
                        "option_order": order_maps[variant_index],
                        "question_asset_key": uploaded.key,
                        "question_asset_url": uploaded.url,
                        "render_checksum": source_checksum,
                    }
                )
            variants_by_bot[bot_id] = bot_variant_records

            explanation_latex = self.explanation_renderer(
                question.correct_option_text,
                question.short_explanation,
                bot_theme=bot_config.theme,
            )
            render_inputs.append(explanation_latex)
            explanation_bytes = self._render_latex_bytes(
                explanation_latex,
                suffix=f"{bot_id}_explanation.png",
            )
            explanation_asset = self.asset_service.upload_explanation_image(
                course_slug=course_slug,
                question_key=question_key,
                version=source_checksum,
                image_bytes=explanation_bytes,
                bot_id=bot_id,
            )
            explanation_asset_keys_by_bot[bot_id] = explanation_asset.key
            explanation_asset_urls_by_bot[bot_id] = explanation_asset.url

        fallback_bot_id = "tanjah" if "tanjah" in explanation_asset_urls_by_bot else next(
            iter(explanation_asset_urls_by_bot)
        )
        render_checksum = hashlib.sha256(
            "".join(render_inputs).encode("utf-8")
        ).hexdigest()

        return {
            "question_id": question_id,
            "variants_by_bot": variants_by_bot,
            "explanation_asset_key": explanation_asset_keys_by_bot[fallback_bot_id],
            "explanation_asset_url": explanation_asset_urls_by_bot[fallback_bot_id],
            "explanation_asset_keys_by_bot": explanation_asset_keys_by_bot,
            "explanation_asset_urls_by_bot": explanation_asset_urls_by_bot,
            "variant_count": len(option_variants),
            "render_checksum": render_checksum,
        }

    def _render_latex_bytes(self, latex_content: str, *, suffix: str) -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / suffix
            success = self.latex_to_png_renderer(latex_content, str(output_path))
            if not success or not output_path.exists():
                raise ValueError(f"latex render failed for {suffix}")
            return output_path.read_bytes()

    def _question_has_all_bot_assets(self, question) -> bool:
        if not getattr(question, "has_latex", False):
            return True

        explanation_urls_by_bot = (
            getattr(question, "explanation_asset_urls_by_bot", None) or {}
        )
        if not isinstance(explanation_urls_by_bot, dict):
            explanation_urls_by_bot = {}

        asset_variants = list(getattr(question, "asset_variants", ()) or ())
        bot_ids_with_variants = {
            getattr(variant, "bot_id", "tanjah")
            for variant in asset_variants
        }

        for bot_id in self.bot_configs:
            if bot_id not in bot_ids_with_variants:
                return False
            if not (
                explanation_urls_by_bot.get(bot_id)
                or (bot_id == "tanjah" and getattr(question, "explanation_asset_url", None))
            ):
                return False
        return True
