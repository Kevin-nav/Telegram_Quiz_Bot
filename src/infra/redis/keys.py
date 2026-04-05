from src.bot.runtime_config import TANJAH_BOT_ID


def telegram_update_key(update_id: int, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"idempotency:telegram_update:{bot_id}:{update_id}"


def rate_limit_key(user_id: int, action: str) -> str:
    return f"ratelimit:user:{user_id}:{action}"


def user_profile_key(user_id: int, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"user-profile:{bot_id}:{user_id}"


def active_quiz_key(user_id: int, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"active-quiz:{bot_id}:{user_id}"


def quiz_session_key(session_id: str, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"quiz-session:{bot_id}:{session_id}"


def poll_map_key(poll_id: str, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"poll-map:{bot_id}:{poll_id}"


def report_draft_key(user_id: int, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"report-draft:{bot_id}:{user_id}"


def pending_report_note_key(user_id: int, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"pending-report-note:{bot_id}:{user_id}"


def quiz_session_lock_key(session_id: str, bot_id: str = TANJAH_BOT_ID) -> str:
    return f"lock:quiz-session:{bot_id}:{session_id}"


def question_bank_cache_key(course_id: str) -> str:
    return f"question-bank:{course_id}"


def adaptive_snapshot_key(
    user_id: int,
    course_id: str,
    bot_id: str = TANJAH_BOT_ID,
) -> str:
    return f"adaptive-snapshot:{bot_id}:{user_id}:{course_id}"


def adaptive_update_lock_key(
    user_id: int,
    course_id: str,
    bot_id: str = TANJAH_BOT_ID,
) -> str:
    return f"lock:adaptive-update:{bot_id}:{user_id}:{course_id}"


def adaptive_attempt_key(attempt_id: str) -> str:
    return f"idempotency:adaptive-attempt:{attempt_id}"


def analytics_dedupe_key(
    user_id: int,
    event_type: str,
    bot_id: str = TANJAH_BOT_ID,
) -> str:
    normalized = event_type.lower().replace(" ", "-")
    return f"analytics-dedupe:{bot_id}:{normalized}:{user_id}"
