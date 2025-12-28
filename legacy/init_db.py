import sqlite3
from pathlib import Path

DB_NAME = "ocr_data.db"

def init_db():
    db_path = Path.cwd() / DB_NAME
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_code TEXT,
                invoice_number TEXT,
                date TEXT,
                amount TEXT,
                create_time TEXT
            )
            """
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO users (username, password)
            VALUES (?, ?)
            """,
            ("admin", "123456"),
        )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
