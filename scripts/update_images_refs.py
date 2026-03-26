#!/usr/bin/env python3
"""从飞书多维表格导出的JSON数据更新数据库"""

import sqlite3
import json

# 飞书导出的数据（这里需要完整的JSON）
# 由于数据量太大，我直接处理

def update_from_feishu_data():
    conn = sqlite3.connect('/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db')
    cursor = conn.cursor()
    
    # 首先清空现有的 images 和 reference_url
    cursor.execute("UPDATE pois SET images = '[]', reference_url = NULL")
    
    # 然后根据景点名匹配更新
    # 这里需要从飞书API获取数据...
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("请使用 feishu_bitable 工具获取数据后手动更新")
