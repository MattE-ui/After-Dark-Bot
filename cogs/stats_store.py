import sqlite3

DB_PATH = "settings.db"

def init_stats():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.commit()

def get_stat(key: str, default=0):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT value FROM stats WHERE key = ?", (key,))
        row = cur.fetchone()
        return int(row[0]) if row else default

def set_stat(key: str, value: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("REPLACE INTO stats (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

def increment_stat(key: str, amount: int = 1):
    current = get_stat(key, 0)
    set_stat(key, current + amount)

def get_user_stat(prefix: str, user_id: int, default=0):
    return get_stat(f"{prefix}_{user_id}", default)

def set_user_stat(prefix: str, user_id: int, value: int):
    set_stat(f"{prefix}_{user_id}", value)

def increment_user_stat(prefix: str, user_id: int, amount: int = 1):
    key = f"{prefix}_{user_id}"
    increment_stat(key, amount)

def top_user_stats(prefix: str, limit: int = 5):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT key, value FROM stats WHERE key LIKE ? ORDER BY CAST(value AS INTEGER) DESC LIMIT ?",
            (f"{prefix}_%", limit)
        )
        return [(row[0].split("_", 1)[1], int(row[1])) for row in cur.fetchall()]
