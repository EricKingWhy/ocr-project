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
                  amount TEXT)''')
    
    conn.commit()
    conn.close()
    print("数据库初始化完成：invoice_system.db")

if __name__ == '__main__':
    init()