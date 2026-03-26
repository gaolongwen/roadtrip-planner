#!/usr/bin/env python3
"""从飞书多维表格重新导入完整数据"""

import sqlite3
import json
import requests
from typing import List, Dict, Any

# 飞书 API 配置
APP_TOKEN = "P3UMbgEQqa9KwmsGyoBcKOD4nHd"
TABLE_ID = "tbldQ7jIq289FPTu"

def fetch_all_records() -> List[Dict[str, Any]]:
    """获取所有记录"""
    all_records = []
    page_token = None
    
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
        headers = {
            "Authorization": f"Bearer {get_tenant_token()}",
            "Content-Type": "application/json"
        }
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        
        if data.get("code") != 0:
            print(f"Error: {data}")
            break
        
        records = data["data"]["items"]
        all_records.extend(records)
        
        if not data["data"].get("has_more"):
            break
        
        page_token = data["data"]["page_token"]
    
    return all_records

def get_tenant_token() -> str:
    """获取飞书访问令牌"""
    # 从环境变量或配置文件读取
    import os
    return os.environ.get("FEISHU_TENANT_TOKEN", "")

def map_record_to_poi(record: Dict) -> Dict:
    """将飞书记录映射为 POI 数据"""
    fields = record["fields"]
    
    # 图片（合并图片1-4）
    images = []
    for i in range(1, 5):
        img = fields.get(f"图片{i}")
        if img and img.strip():
            images.append(img.strip())
    
    # 参考链接（合并参考1-3，过滤空值）
    refs = []
    for i in range(1, 4):
        ref = fields.get(f"参考{i}")
        if ref and ref.strip() and ref.startswith("http"):
            refs.append(ref.strip())
    
    # 取第一个参考链接
    reference_url = refs[0] if refs else None
    
    return {
        "name": fields.get("景点名", ""),
        "province": "山西",  # 飞书表格没有省份字段，暂时固定
        "city": fields.get("地级市") or "",
        "district": fields.get("县级市/县") or "",
        "address": fields.get("地址") or "",
        "description": fields.get("备注") or "",
        "images": images,
        "reference_url": reference_url,
    }

def update_database(records: List[Dict]):
    """更新数据库"""
    conn = sqlite3.connect('/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db')
    cursor = conn.cursor()
    
    updated = 0
    for record in records:
        poi = map_record_to_poi(record)
        if not poi["name"]:
            continue
        
        # 更新图片和参考链接
        cursor.execute("""
            UPDATE pois 
            SET images = ?, reference_url = ?, description = ?
            WHERE name = ?
        """, (
            json.dumps(poi["images"], ensure_ascii=False),
            poi["reference_url"],
            poi["description"],
            poi["name"]
        ))
        
        if cursor.rowcount > 0:
            updated += 1
    
    conn.commit()
    conn.close()
    
    return updated

if __name__ == "__main__":
    print("正在从飞书获取数据...")
    # records = fetch_all_records()
    # print(f"获取到 {len(records)} 条记录")
    
    # updated = update_database(records)
    # print(f"更新了 {updated} 条记录")
    
    print("请使用 openclaw feishu 工具直接获取数据")
