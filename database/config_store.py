# database/config_store.py

import sqlite3

DB_PATH = "settings.db"

def init_config_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_config(key: str, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO bot_config (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, repr(value)))
    conn.commit()
    conn.close()

def get_config(key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM bot_config WHERE key = ?', (key,))
    result = c.fetchone()
    conn.close()
    return eval(result[0]) if result else None

def get_all_config() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, value FROM bot_config')
    rows = c.fetchall()
    conn.close()
    return {key: eval(value) for key, value in rows}
