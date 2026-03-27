from src.infra.db.models.question_report import QuestionReport
from src.infra.db.session import AsyncSessionLocal


class QuestionReportRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def create_report(self, payload: dict) -> QuestionReport:
        async with self.session_factory() as session:
            report = QuestionReport(**payload)
            session.add(report)
            await session.commit()
            await session.refresh(report)
            return report
