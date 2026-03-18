def telegram_update_key(update_id: int) -> str:
    return f"idempotency:telegram_update:{update_id}"


def rate_limit_key(user_id: int, action: str) -> str:
    return f"ratelimit:user:{user_id}:{action}"


def user_profile_key(user_id: int) -> str:
    return f"user-profile:{user_id}"


def active_quiz_key(user_id: int) -> str:
    return f"active-quiz:{user_id}"


def quiz_session_key(session_id: str) -> str:
    return f"quiz-session:{session_id}"


def poll_map_key(poll_id: str) -> str:
    return f"poll-map:{poll_id}"


def quiz_session_lock_key(session_id: str) -> str:
    return f"lock:quiz-session:{session_id}"


def question_bank_cache_key(course_id: str) -> str:
    return f"question-bank:{course_id}"


def analytics_dedupe_key(user_id: int, event_type: str) -> str:
    normalized = event_type.lower().replace(" ", "-")
    return f"analytics-dedupe:{normalized}:{user_id}"
