def backfill_display_name(conn):
    conn.execute(
        "UPDATE users SET display_name = TRIM(first || ' ' || COALESCE(last, '')) "
        "WHERE display_name IS NULL OR display_name = ''"
    )
    conn.commit()
