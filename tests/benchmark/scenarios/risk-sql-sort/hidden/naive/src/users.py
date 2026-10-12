def search_users(conn, name, sort="name"):
    sql = f"SELECT id, name FROM users WHERE name = ? ORDER BY {sort}"
    return conn.execute(sql, (name,)).fetchall()
