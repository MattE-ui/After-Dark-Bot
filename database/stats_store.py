# database/stats_store.py

import sqlite3

DB_PATH = "settings.db"

def init_stats_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER,
            stat TEXT,
            value INTEGER,
            PRIMARY KEY (user_id, stat)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS global_stats (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def set_user_stat(user_id: int, stat: str, value: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO user_stats (user_id, stat, value)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, stat) DO UPDATE SET value = excluded.value
    ''', (user_id, stat, value))
    conn.commit()
    conn.close()

def get_user_stat(user_id: int, stat: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM user_stats WHERE user_id = ? AND stat = ?', (user_id, stat))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def increment_user_stat(user_id: int, stat: str, amount: int = 1):
    current = get_user_stat(user_id, stat)
    set_user_stat(user_id, stat, current + amount)

def get_top_users(stat: str, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT user_id, value FROM user_stats
        WHERE stat = ?
        ORDER BY value DESC
        LIMIT ?
    ''', (stat, limit))
    results = c.fetchall()
    conn.close()
    return results

def set_global_stat(key: str, value: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO global_stats (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def get_global_stat(key: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM global_stats WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0
