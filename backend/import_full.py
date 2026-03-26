#!/usr/bin/env python3
"""从飞书多维表格导入完整 185 条景点数据"""

import sqlite3
import json
from datetime import datetime

# 山西城市列表
SHANXI_CITIES = ["大同", "朔州", "忻州", "阳泉", "太原", "吕梁", "晋中", "长治", "临汾", "晋城", "运城"]

def clean_city(city):
    """清理城市名"""
    if not city:
        return ""
    city = city.replace("（河南）", "").replace("（山西）", "").replace("（河北）", "")
    city = city.replace("（张家口）", "").replace("（安阳市）", "").replace("（河北保定阜平县）", "")
    city = city.replace("忻(xin)州", "忻州")
    return city.strip()

def infer_province(city):
    """根据城市推断省份"""
    if not city:
        return "河南"
    city_clean = clean_city(city)
    for shanxi_city in SHANXI_CITIES:
        if shanxi_city in city_clean or city_clean in shanxi_city:
            return "山西"
    return "河南"

def infer_category(name, tips=""):
    if not name:
        return "人文"
    nature_keywords = ["峡谷", "瀑布", "山", "河", "湖", "洞", "林", "泉", "冰川", "草原", "沙漠", "湿地", "火山", "天池", "水库", "大坝"]
    for kw in nature_keywords:
        if kw in name:
            return "自然"
    return "人文"

def infer_tags(name, tips=""):
    tags = []
    if not name:
        return ""
    
    tag_rules = [
        ("石窟", "石窟"), ("石刻", "石刻"), ("摩崖", "石刻"),
        ("寺", "宗教"), ("庙", "宗教"), ("观", "宗教"), ("教堂", "宗教"),
        ("古村", "古村落"), ("古镇", "古村落"),
        ("墓", "陵墓"), ("陵", "陵墓"),
        ("长城", "长城"), ("峡谷", "峡谷"), ("瀑布", "瀑布"),
        ("溶洞", "溶洞"), ("冰洞", "溶洞"), ("冰窟", "溶洞"),
        ("恐龙", "恐龙"), ("化石", "化石"),
        ("矿山", "工业遗产"), ("矿井", "工业遗产"), ("发电厂", "工业遗产"),
        ("挂壁公路", "挂壁公路"),
        ("塔", "古塔"), ("楼", "古建筑"),
    ]
    
    for keyword, tag in tag_rules:
        if keyword in name:
            tags.append(tag)
    
    if tips:
        if "无人机" in tips or "航拍" in tips:
            tags.append("航拍推荐")
        if "亲子" in tips or "研学" in tips:
            tags.append("亲子研学")
    
    return ",".join(list(set(tags)))

# 读取飞书数据
with open('/root/.openclaw/workspace/roadtrip-planner/backend/feishu_full.json', 'r') as f:
    feishu_data = json.load(f)

records = feishu_data['records']

# 连接数据库
conn = sqlite3.connect('/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db')
cursor = conn.cursor()

# 清空现有数据
cursor.execute("DELETE FROM pois")

# 导入数据
imported = 0
skipped = 0
now = datetime.now().isoformat()

for rec in records:
    fields = rec.get('fields', {})
    name = fields.get('景点名', '')
    
    if not name:
        skipped += 1
        continue
    
    # 城市和省份
    city_raw = fields.get('地级市', '') or fields.get('县级市/县', '')
    city = clean_city(city_raw)
    province = infer_province(city)
    
    # 其他字段
    district = fields.get('县级市/县', '')
    town = fields.get('镇/乡', '')
    address = fields.get('地址', '')
    tips = fields.get('备注', '')
    
    # 推断类别和标签
    category = infer_category(name, tips)
    tags = infer_tags(name, tips)
    
    # 临时坐标（后续补充）
    import random
    lat = round(35.0 + random.uniform(-2, 2), 6)
    lng = round(112.0 + random.uniform(-3, 3), 6)
    
    # 插入数据库
    cursor.execute("""
        INSERT INTO pois (name, province, city, district, address, latitude, longitude, 
                         category, tags, rating, price, duration, description, tips, 
                         images, is_wild, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, province, city, district, address, lat, lng, 
          category, tags, 0.0, 0.0, 1, tips, tips, "", 0, now, now))
    imported += 1

conn.commit()

# 验证
cursor.execute("SELECT COUNT(*) FROM pois")
count = cursor.fetchone()[0]

cursor.execute("SELECT province, COUNT(*) FROM pois GROUP BY province")
by_province = cursor.fetchall()

conn.close()

print(f"✅ 导入完成: {count} 条记录")
print(f"跳过无名称: {skipped} 条")
print(f"按省份分布: {dict(by_province)}")
