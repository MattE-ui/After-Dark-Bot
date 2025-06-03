
import sqlite3

DB_PATH = "settings.db"

def init_settings():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        conn.commit()

def get_setting(key: str, default=None):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        if row:
            return row[0]
        return default

def set_setting(key: str, value: str):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value))
        )
        conn.commit()
