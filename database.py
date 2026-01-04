import sqlite3
from typing import List, Tuple

def init_db():
    conn = sqlite3.connect("chats.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_message(chat_id: int, role: str, content: str):
    conn = sqlite3.connect("chats.db")
    cursor = conn.cursor()
    # Оставляем не более 10 последних сообщений
    cursor.execute("""
        DELETE FROM messages
        WHERE chat_id = ? AND rowid NOT IN (
            SELECT rowid FROM messages
            WHERE chat_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        )
    """, (chat_id, chat_id))
    cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", 
                   (chat_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(chat_id: int) -> List[Tuple[str, str]]:
    conn = sqlite3.connect("chats.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM messages
        WHERE chat_id = ?
        ORDER BY timestamp ASC
    """, (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_chat_history(chat_id: int):
    """Полностью удаляет историю для chat_id"""
    conn = sqlite3.connect("chats.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()