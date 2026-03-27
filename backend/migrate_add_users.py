#!/usr/bin/env python3
"""
数据库迁移脚本：添加用户系统
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'roadtrip.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查 users 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("创建 users 表...")
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nickname VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("users 表创建成功")
    else:
        print("users 表已存在")
    
    # 检查 trip_members 表是否有 user_id 列
    cursor.execute("PRAGMA table_info(trip_members)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'user_id' not in columns:
        print("添加 user_id 列到 trip_members 表...")
        cursor.execute('ALTER TABLE trip_members ADD COLUMN user_id INTEGER REFERENCES users(id)')
        print("user_id 列添加成功")
    else:
        print("user_id 列已存在")
    
    conn.commit()
    conn.close()
    print("迁移完成！")

if __name__ == '__main__':
    migrate()
