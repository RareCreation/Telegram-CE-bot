import sqlite3
from typing import Optional, List, Tuple

def init_db():
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracking (
        tg_id INTEGER,
        steam_id TEXT,
        comment TEXT,
        last_status TEXT,
        PRIMARY KEY (tg_id, steam_id)
    )
    ''')
    conn.commit()
    conn.close()

def init_users_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY
    )
    ''')
    conn.commit()
    conn.close()

def add_user(tg_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tg_id FROM users WHERE tg_id = ?', (tg_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (tg_id) VALUES (?)', (tg_id,))
    conn.commit()
    conn.close()

def get_user_count() -> int:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_tracking(tg_id: int, steam_id: str, comment: str, last_status: str = "Currently Offline"):
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tracking (tg_id, steam_id, comment, last_status) VALUES (?, ?, ?, ?)',
                   (tg_id, steam_id, comment, last_status))
    conn.commit()
    conn.close()

def remove_tracking(tg_id: int, steam_id: str) -> bool:
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tracking WHERE tg_id = ? AND steam_id = ?', (tg_id, steam_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_tracking_count(tg_id: int) -> int:
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM tracking WHERE tg_id = ?', (tg_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_tracking() -> List[Tuple[int, str, str]]:
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tg_id, steam_id, comment FROM tracking')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_tracking_status(tg_id: int, steam_id: str, status: str):
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE tracking SET last_status = ? WHERE tg_id = ? AND steam_id = ?',
                   (status, tg_id, steam_id))
    conn.commit()
    conn.close()

def get_tracking_status(tg_id: int, steam_id: str) -> Optional[str]:
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_status FROM tracking WHERE tg_id = ? AND steam_id = ?', (tg_id, steam_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def check_tracking_exists(tg_id: int, steam_id: str) -> bool:
    conn = sqlite3.connect('tracking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM tracking WHERE tg_id = ? AND steam_id = ?', (tg_id, steam_id))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def get_all_users() -> List[int]:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT tg_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users