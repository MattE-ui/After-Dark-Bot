import sqlite3

DB_PATH = "settings.db"  # same DB as config, but different table

def init_stats():
    """
    Create the 'stats' table if it doesn't exist.
    Each stat is stored as (key TEXT PRIMARY KEY, value TEXT).
    Keys for user stats are prefixed, e.g. "high_1234567890".
    """
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
    """
    Retrieve a stat by key. If not found, return default (int).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT value FROM stats WHERE key = ?", (key,))
        row = cur.fetchone()
        return int(row[0]) if row and row[0].isdigit() else default

def set_stat(key: str, value):
    """
    Insert or replace a stat (value stored as TEXT but treated as integer if digits).
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO stats (key, value) VALUES (?, ?)", (key, str(value))
        )
        conn.commit()

def increment_stat(key: str, amount: int = 1):
    """
    Atomically increment a stat by 'amount' (default is +1).
    """
    current = get_stat(key, 0)
    set_stat(key, current + amount)

def get_user_stat(prefix: str, user_id: int, default=0):
    """
    Helper to retrieve a user‐scoped stat. prefix might be 'high', 'fail', 'count', etc.
    Stored under key: f"{prefix}_{user_id}".
    """
    return get_stat(f"{prefix}_{user_id}", default)

def set_user_stat(prefix: str, user_id: int, value):
    """
    Set a user‐scoped stat to a given value.
    """
    set_stat(f"{prefix}_{user_id}", value)

def increment_user_stat(prefix: str, user_id: int, amount: int = 1):
    """
    Helper to increment a user‐scoped stat by 'amount'.
    """
    current = get_user_stat(prefix, user_id, 0)
    set_user_stat(prefix, user_id, current + amount)

def top_user_stats(prefix: str, limit: int = 5):
    """
    Return a list of (user_id, value) pairs for the top 'limit' users by that stat.
    Keys matching f"{prefix}_%" are sorted descending by numeric 'value'.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT key, value FROM stats WHERE key LIKE ? ORDER BY CAST(value AS INTEGER) DESC LIMIT ?",
            (f"{prefix}_%", limit)
        )
        return [(key.split("_", 1)[1], int(value)) for key, value in cur.fetchall()]
