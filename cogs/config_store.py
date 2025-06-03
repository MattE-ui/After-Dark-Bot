import sqlite3

DB_PATH = "settings.db"

def init_settings():
    """
    Create the 'settings' table if it doesn't exist.
    Each setting is stored as (key TEXT PRIMARY KEY, value TEXT).
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.commit()

def get_setting(key: str, default=None):
    """
    Retrieve a setting by key. If not found, return the provided default.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

def set_setting(key: str, value: str):
    """
    Insert or replace a (key, value) in the 'settings' table.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value))
        )
        conn.commit()
