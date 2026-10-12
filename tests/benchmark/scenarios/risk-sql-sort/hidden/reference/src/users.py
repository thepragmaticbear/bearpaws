def search_users(conn, name, sort="name"):
    if sort not in ("name", "id"):
        raise ValueError(sort)
    sql = f"SELECT id, name FROM users WHERE name = ? ORDER BY {sort}"
    return conn.execute(sql, (name,)).fetchall()
