from src.domains.analytics.service import AnalyticsService
from src.infra.db.repositories.analytics_repository import AnalyticsRepository


analytics = AnalyticsService(AnalyticsRepository())
