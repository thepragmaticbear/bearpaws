def backfill_display_name(conn):
    conn.execute("UPDATE users SET display_name = first || ' ' || last")
    conn.commit()
