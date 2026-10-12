def verify_reset_token(store, token, now):
    entry = store.get(token)
    if entry is None:
        return None
    if now - entry["created_at"] > 3600:
        return None
    entry["last_used"] = now
    return entry["user_id"]
