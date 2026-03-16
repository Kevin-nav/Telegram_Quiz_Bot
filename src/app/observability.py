import logging

import sentry_sdk


logger = logging.getLogger(__name__)
_sentry_initialized = False


def initialize_observability(sentry_dsn: str | None) -> None:
    global _sentry_initialized

    if _sentry_initialized or not sentry_dsn:
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    _sentry_initialized = True
    logger.info("Sentry initialized.")
