# db_init.py
import sqlite3

def init():
    conn = sqlite3.connect('invoice_system.db')
    c = conn.cursor()
    
    # 1. 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    # 插入默认管理员
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '123456')")
    
    # 2. 发票记录表
    c.execute('''CREATE TABLE IF NOT EXISTS invoices
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT,
                  number TEXT,
                  date TEXT,
                  amount TEXT,
                  address TEXT,
                  tax_no TEXT,
                  bank TEXT)''')

    # Add missing columns for existing databases.
    c.execute("PRAGMA table_info(invoices)")
    existing = {row[1] for row in c.fetchall()}
    columns = {
        "address": "TEXT",
        "tax_no": "TEXT",
        "bank": "TEXT",
    }
    for name, col_type in columns.items():
        if name not in existing:
            c.execute(f"ALTER TABLE invoices ADD COLUMN {name} {col_type}")
    
    conn.commit()
    conn.close()
    print("数据库初始化完成：invoice_system.db")

if __name__ == '__main__':
    init()
