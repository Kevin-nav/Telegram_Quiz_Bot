"""Diagnostic script – print question_bank status summary and test question selection."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from the bot root so src.core.config can find .env
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Use the bot's own settings (loads .env automatically)
from src.core.config import get_settings

_settings = get_settings()
DATABASE_URL = _settings.async_database_url

COURSES_TO_CHECK = [
    "linear-electronics",
    "programming-in-labview",
    "thermodynamics",
    "differential-equations",
    "transformers-and-dc-machines",
    "programming-in-matlab",
    "general-psychology",
]

TEST_USER_ID = 5135164547  # Kevin


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    # ── 1. Per-course status counts ──────────────────────────────────────────
    async with Session() as session:
        result = await session.execute(
            text(
                "SELECT course_id, status, COUNT(*) AS cnt "
                "FROM question_bank "
                "GROUP BY course_id, status "
                "ORDER BY course_id, status"
            )
        )
        rows = result.all()

    print("\n=== question_bank status breakdown ===")
    if not rows:
        print("  (empty table — no questions imported yet)")
    else:
        print(f"{'course_id':<46} {'status':<12} {'count':>6}")
        print("-" * 66)
        for course_id, status, cnt in rows:
            print(f"{course_id:<46} {status:<12} {cnt:>6}")

    # ── 2. Simulate select_questions for each catalog course ─────────────────
    from src.domains.adaptive.service import AdaptiveLearningService
    from src.infra.db.repositories.question_bank_repository import QuestionBankRepository

    repo = QuestionBankRepository()
    service = AdaptiveLearningService(question_bank_repository=repo)

    print("\n=== Adaptive select_questions simulation (quiz_length=5) ===")
    print(f"{'course_id':<46} {'ready_rows':>10} {'selected':>9} {'result'}")
    print("-" * 80)
    for course_id in COURSES_TO_CHECK:
        try:
            output = await service.select_questions(
                user_id=TEST_USER_ID,
                course_id=course_id,
                quiz_length=5,
            )
            ready = len(output.question_rows)
            selected = len(output.selected_questions)
            result = "OK" if selected > 0 else "EMPTY selection (no questions returned)"
            print(f"{course_id:<46} {ready:>10} {selected:>9}  {result}")
        except Exception as exc:
            print(f"{course_id:<46} {'':>10}           EXCEPTION: {exc}")

    await engine.dispose()


asyncio.run(main())

