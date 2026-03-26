#!/usr/bin/env python3
"""导入飞书景点数据到数据库"""

import sqlite3
import json
from datetime import datetime

# 山西城市列表
SHANXI_CITIES = ["大同", "朔州", "忻(xin)州", "忻州", "阳泉", "太原", "吕梁", "晋中", "长治", "临汾", "晋城", "运城"]

def get_province(city):
    """根据城市推断省份"""
    if not city:
        return "河南"
    
    city_clean = city.replace("（山西）", "").replace("（河南）", "").strip()
    city_clean = city_clean.replace("(山西)", "").replace("(河南)", "").strip()
    
    for sc in SHANXI_CITIES:
        if sc in city_clean or city_clean in sc:
            return "山西"
    
    if "(山西)" in city or "（山西）" in city:
        return "山西"
    
    return "河南"

def infer_category(name):
    """根据名称推断类别"""
    if not name:
        return "人文"
    
    nature_keywords = ["峡谷", "瀑布", "山", "河", "湖", "洞", "林", "泉", "冰川", "草原", "沙漠", "湿地", "火山", "天池"]
    for kw in nature_keywords:
        if kw in name:
            return "自然"
    return "人文"

def infer_tags(name, tips):
    """根据名称和备注推断标签"""
    tags = []
    if not name:
        return ""
    
    tag_rules = [
        ("石窟", "石窟"),
        ("石刻", "石刻"),
        ("摩崖", "石刻"),
        ("寺", "宗教"),
        ("庙", "宗教"),
        ("观", "宗教"),
        ("教堂", "宗教"),
        ("古村", "古村落"),
        ("古镇", "古村落"),
        ("墓", "陵墓"),
        ("陵", "陵墓"),
        ("长城", "长城"),
        ("峡谷", "峡谷"),
        ("瀑布", "瀑布"),
        ("溶洞", "溶洞"),
        ("冰洞", "溶洞"),
        ("冰窟", "溶洞"),
        ("恐龙", "恐龙"),
        ("化石", "化石"),
        ("矿山", "工业遗产"),
        ("矿井", "工业遗产"),
        ("发电厂", "工业遗产"),
        ("挂壁公路", "挂壁公路"),
        ("古栈道", "古道"),
        ("古道", "古道"),
    ]
    
    for keyword, tag in tag_rules:
        if keyword in name:
            tags.append(tag)
    
    if tips:
        if "无人机" in tips or "航拍" in tips:
            tags.append("航拍推荐")
        if "亲子" in tips or "研学" in tips:
            tags.append("亲子研学")
        if "自驾" in tips:
            tags.append("自驾推荐")
    
    return ",".join(list(set(tags)))

def clean_city(city):
    """清理城市名称"""
    if not city:
        return ""
    return city.replace("（山西）", "").replace("（河南）", "").replace("(山西)", "").replace("(河南)", "").strip()

def import_data(records):
    """导入数据到数据库"""
    conn = sqlite3.connect('/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db')
    cursor = conn.cursor()
    
    # 清空现有数据
    cursor.execute("DELETE FROM pois")
    
    imported = 0
    for rec in records:
        fields = rec.get("fields", {})
        
        name = fields.get("景点名") or fields.get("文本") or ""
        if not name:
            continue
        
        city_raw = fields.get("地级市") or ""
        city = clean_city(city_raw)
        district = fields.get("县级市/县") or ""
        town = fields.get("镇/乡") or ""
        address = fields.get("地址") or ""
        tips = fields.get("备注") or ""
        
        # 必填字段
        province = get_province(city_raw)
        category = infer_category(name)
        tags = infer_tags(name, tips)
        duration = 1  # 默认游玩时长 1 小时
        
        # 临时坐标（后续补充真实坐标）
        import random
        lat = round(35.0 + random.uniform(-2, 2), 6)
        lng = round(112.0 + random.uniform(-3, 3), 6)
        
        # 参考链接
        refs = []
        for i in range(1, 4):
            ref = fields.get(f"参考{i}")
            if ref:
                refs.append(ref)
        images = []
        for i in range(1, 5):
            img = fields.get(f"图片{i}")
            if img:
                images.append(img)
        
        cursor.execute("""
            INSERT INTO pois (
                name, province, city, district, address, 
                latitude, longitude, category, tags, 
                rating, price, duration, description, tips, images, is_wild
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, province, city, district, address,
            lat, lng, category, tags,
            0.0, 0.0, duration, tips, tips, json.dumps(images) if images else "", 0
        ))
        imported += 1
    
    conn.commit()
    
    # 验证
    cursor.execute("SELECT COUNT(*) FROM pois")
    count = cursor.fetchone()[0]
    
    conn.close()
    return count, imported

if __name__ == "__main__":
    # 从 feishu_records.json 读取数据
    with open("/root/.openclaw/workspace/roadtrip-planner/backend/feishu_records.json") as f:
        data = json.load(f)
        records = data.get("records", data) if isinstance(data, dict) else data
    
    count, imported = import_data(records)
    print(f"导入完成: {count} 条记录 (尝试 {imported} 条)")
