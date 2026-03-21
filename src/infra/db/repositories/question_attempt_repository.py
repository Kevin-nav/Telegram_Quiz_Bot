from src.infra.db.models.question_attempt import QuestionAttempt
from src.infra.db.session import AsyncSessionLocal


class QuestionAttemptRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def create_attempt(self, payload: dict) -> QuestionAttempt:
        async with self.session_factory() as session:
            attempt = QuestionAttempt(**payload)
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)
            return attempt
