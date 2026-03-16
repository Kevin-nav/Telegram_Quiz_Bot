def telegram_update_key(update_id: int) -> str:
    return f"idempotency:telegram_update:{update_id}"


def rate_limit_key(user_id: int, action: str) -> str:
    return f"ratelimit:user:{user_id}:{action}"
