import sqlite3
import logging

DB_NAME = "bot_database.db"
logger = logging.getLogger(__name__)

def get_connection():
    return sqlite3.connect(DB_NAME)

def initialize_db():
    conn = get_connection()
    c = conn.cursor()
    
    # جدول چت‌ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            interval INTEGER,
            enabled_assets TEXT DEFAULT 'ALL',
            language TEXT DEFAULT 'fa'
        )
    ''')
    
    # آپدیت جدول‌های قدیمی (اضافه کردن ستون‌های جدید)
    try:
        c.execute("ALTER TABLE chats ADD COLUMN enabled_assets TEXT DEFAULT 'ALL'")
    except sqlite3.OperationalError: pass

    try:
        c.execute("ALTER TABLE chats ADD COLUMN language TEXT DEFAULT 'fa'")
    except sqlite3.OperationalError: pass

    # جدول هشدارها
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            asset TEXT,
            target_price REAL,
            condition TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- مدیریت چت‌ها ---
def add_or_update_chat(chat_id, user_id, title):
    conn = get_connection()
    c = conn.cursor()
    # اگر چت جدید است، پیش‌فرض فارسی باشد. اگر هست، تایتل آپدیت شود.
    c.execute("INSERT OR IGNORE INTO chats (chat_id, user_id, title, enabled_assets, language) VALUES (?, ?, ?, 'ALL', 'fa')", (chat_id, user_id, title))
    c.execute("UPDATE chats SET title = ?, user_id = ? WHERE chat_id = ?", (title, user_id, chat_id))
    conn.commit()
    conn.close()

def remove_chat(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def set_chat_interval(chat_id, interval):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE chats SET interval = ? WHERE chat_id = ?", (interval, chat_id))
    conn.commit()
    conn.close()

def set_chat_assets(chat_id, assets_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE chats SET enabled_assets = ? WHERE chat_id = ?", (assets_str, chat_id))
    conn.commit()
    conn.close()

def get_chat_assets(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT enabled_assets FROM chats WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "ALL"

# --- مدیریت زبان ---
def set_chat_language(chat_id, lang):
    conn = get_connection()
    c = conn.cursor()
    # ابتدا سعی می‌کنیم آپدیت کنیم
    c.execute("UPDATE chats SET language = ? WHERE chat_id = ?", (lang, chat_id))
    # اگر سطر وجود نداشت (مثلاً کاربر جدید است)، اینسرت می‌کنیم
    if c.rowcount == 0:
         c.execute("INSERT INTO chats (chat_id, language) VALUES (?, ?)", (chat_id, lang))
    conn.commit()
    conn.close()

def get_chat_language(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT language FROM chats WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "fa" # پیش‌فرض فارسی

def get_user_chats(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT chat_id, title, interval FROM chats WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def get_all_scheduled_chats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT chat_id, interval, enabled_assets, language FROM chats WHERE interval > 0")
    results = c.fetchall()
    conn.close()
    return results

# --- مدیریت هشدارها ---
def add_alert(user_id, asset, target_price, condition):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO alerts (user_id, asset, target_price, condition) VALUES (?, ?, ?, ?)", 
              (user_id, asset, target_price, condition))
    conn.commit()
    conn.close()

def get_all_alerts():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, user_id, asset, target_price, condition FROM alerts")
    results = c.fetchall()
    conn.close()
    return results

def get_user_alerts(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, asset, target_price, condition FROM alerts WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def delete_alert(alert_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()