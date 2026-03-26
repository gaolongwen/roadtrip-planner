#!/usr/bin/env python3
"""
从飞书多维表格导入景点数据到 SQLite

使用方法：
1. 设置飞书 API 凭证
2. 运行 python import_from_feishu.py
"""

import json
import sys
import os

# 添加后端目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import SessionLocal, engine
from models import Base, POI

# 飞书多维表格配置
FEISHU_APP_TOKEN = "P3UMbgEQqa9KwmsGyoBcKOD4nHd"
FEISHU_TABLE_ID = "tbldQ7jIq289FPTu"


def import_from_json(json_file: str):
    """从 JSON 文件导入数据"""
    db = SessionLocal()
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        count = 0
        for item in data:
            poi = POI(
                name=item.get('name', ''),
                province=item.get('province', ''),
                city=item.get('city', ''),
                district=item.get('district', ''),
                address=item.get('address', ''),
                latitude=float(item.get('latitude', 0)),
                longitude=float(item.get('longitude', 0)),
                category=item.get('category', '其他'),
                tags=json.dumps(item.get('tags', []), ensure_ascii=False),
                rating=float(item.get('rating', 0)),
                price=float(item.get('price', 0)),
                duration=int(item.get('duration', 0)),
                description=item.get('description', ''),
                tips=item.get('tips', ''),
                images=json.dumps(item.get('images', []), ensure_ascii=False),
                is_wild=item.get('is_wild', False)
            )
            db.add(poi)
            count += 1
        
        db.commit()
        print(f"✅ 成功导入 {count} 条数据")
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        db.rollback()
    finally:
        db.close()


def export_from_feishu():
    """从飞书多维表格导出数据（需要飞书 API 凭证）"""
    # TODO: 实现飞书 API 调用
    # 需要安装：pip install feishu
    print("⚠️ 飞书 API 导出功能待实现")
    print("请手动从飞书导出 JSON 数据，然后使用 import_from_json() 导入")


if __name__ == "__main__":
    # 创建表
    Base.metadata.create_all(bind=engine)
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        import_from_json(json_file)
    else:
        print("用法：python import_from_feishu.py <json_file>")
        print("\nJSON 格式示例：")
        print('''
[
  {
    "name": "景点名称",
    "province": "省份",
    "city": "城市",
    "district": "区县",
    "address": "详细地址",
    "latitude": 35.5,
    "longitude": 113.5,
    "category": "自然",
    "tags": ["山水", "徒步"],
    "rating": 4.5,
    "price": 50,
    "duration": 3,
    "description": "景点描述",
    "tips": "游玩贴士",
    "images": ["url1", "url2"],
    "is_wild": false
  }
]
        ''')
