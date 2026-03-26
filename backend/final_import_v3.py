#!/usr/bin/env python3
"""
Step 1: Fetch all records from Feishu and save to JSON
Step 2: Import to SQLite database
"""

# This script should be called to:
# 1. Call feishu_bitable_list_records API
# 2. Save the complete response to JSON
# 3. Import to SQLite

import json
import sqlite3
from datetime import datetime
import re

def clean_city(city):
    if not city:
        return None
    city = re.sub(r'[（(][^)）]*[)）]', '', city)
    return city.strip() if city.strip() else None

def infer_category(name, description, tips):
    text = f"{name or ''} {description or ''} {tips or ''}".lower()
    
    if any(word in text for word in ['石窟', '佛', '寺', '庙', '塔', '道教', '教堂', '古建', '古村', '古镇', '古堡', '关帝', '书院', '衙门', '祠', '殿']):
        return '人文'
    elif any(word in text for word in ['峡谷', '瀑布', '山', '湖', '河', '地质', '自然', '溶洞', '冰洞', '温泉', '森林', '湿地', '草原']):
        return '自然'
    else:
        return '人文'

def infer_tags(name, description, tips):
    tags = []
    text = f"{name or ''} {description or ''} {tips or ''}"
    
    tag_keywords = {
        '古建': ['古建', '建筑', '木构', '唐代', '宋代', '明代', '清代', '辽代', '金代', '元代', '五代', '北魏', '北齐'],
        '石窟': ['石窟', '摩崖', '造像'],
        '佛教': ['佛', '寺', '塔', '禅', '菩萨', '观音', '释迦'],
        '道教': ['道教', '道观', '老君'],
        '长城': ['长城', '关隘', '烽火台', '边关'],
        '古村': ['古镇', '古村', '村落', '民居', '窑洞'],
        '自然': ['峡谷', '瀑布', '山', '湖', '河', '地质', '溶洞', '冰洞'],
        '世界遗产': ['世界遗产', '世遗', 'UNESCO'],
        '博物馆': ['博物馆', '纪念馆', '陈列馆'],
        '教堂': ['教堂', '天主', '基督'],
        '工业遗产': ['矿山', '工厂', '矿井', '电厂'],
        '挂壁公路': ['挂壁', '公路'],
        '彩塑': ['彩塑', '壁画', '悬塑'],
        '古墓': ['古墓', '陵墓', '墓葬', '帝陵'],
    }
    
    for tag, keywords in tag_keywords.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    
    return tags[:3] if tags else ['景点']

def build_description(fields):
    parts = []
    if fields.get('备注'):
        parts.append(fields['备注'])
    return " ".join(parts) if parts else fields.get('景点名', '景点')

def build_address(fields):
    parts = []
    town = fields.get('镇/乡')
    if town:
        parts.append(town)
    address = fields.get('地址')
    if address:
        parts.append(address)
    return " ".join(parts) if parts else fields.get('景点名', '未知地址')

def is_wild_attraction(name, tips, description):
    text = f"{name or ''} {tips or ''} {description or ''}".lower()
    wild_keywords = ['遗址', '野', '未开发', '原始', '废弃', '矿', '捡', '挖', '古墓', '荒', '玛瑙', '化石']
    return any(keyword in text for keyword in wild_keywords)

def import_records(records_json):
    """Import records from JSON to SQLite"""
    print("=" * 60)
    print("导入景点数据")
    print("=" * 60)
    
    records = json.loads(records_json) if isinstance(records_json, str) else records_json
    print(f"\n加载了 {len(records)} 条记录")
    
    conn = sqlite3.connect('data/roadtrip.db')
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM pois")
    print("已清空现有数据\n")
    
    imported = 0
    errors = []
    
    for idx, record in enumerate(records, start=1):
        fields = record.get('fields', {})
        
        name = fields.get('景点名') or fields.get('地址') or f'未命名景点{idx}'
        address = build_address(fields)
        description = build_description(fields)
        tips = fields.get('备注') or ''
        
        city = clean_city(fields.get('地级市'))
        district = fields.get('县级市/县') or ''
        
        category = infer_category(name, description, tips)
        tags = infer_tags(name, description, tips)
        is_wild = is_wild_attraction(name, tips, description)
        
        latitude = 35.0 + (idx % 20) * 0.3
        longitude = 110.0 + (idx % 20) * 0.4
        
        rating = 4.0
        price = 0.0
        duration = 1
        
        images = []
        for i in range(1, 5):
            img = fields.get(f'图片{i}')
            if img:
                images.append(img)
        
        province = '山西'
        henan_cities = ['洛阳', '安阳', '新乡', '焦作', '三门峡', '南阳', '郑州', '信阳', '济源', '永城', '平顶山', '鹤壁', '开封', '许昌', '驻马店', '商丘', '漯河', '周口']
        if city and any(c in city for c in henan_cities):
            province = '河南'
        
        try:
            cursor.execute("""
                INSERT INTO pois (
                    id, name, province, city, district, address,
                    latitude, longitude, category, tags, rating, price,
                    duration, description, tips, images, is_wild,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                idx, name, province, city or '未知', district, address,
                latitude, longitude, category,
                json.dumps(tags, ensure_ascii=False),
                rating, price, duration, description, tips,
                json.dumps(images, ensure_ascii=False),
                1 if is_wild else 0,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            imported += 1
            
            if idx % 50 == 0:
                print(f"  已处理 {idx}/{len(records)} 条记录...")
                
        except Exception as e:
            errors.append(f"记录 {idx} ({name}): {e}")
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM pois")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM pois WHERE is_wild = 1")
    wild_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT province, COUNT(*) FROM pois GROUP BY province")
    provinces = cursor.fetchall()
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 导入完成!")
    print("=" * 60)
    print(f"成功导入: {imported} 条")
    print(f"错误: {len(errors)} 条")
    print(f"数据库总记录: {final_count} 条")
    print(f"野生景点: {wild_count} 条")
    
    print("\n按省份:")
    for prov, count in provinces:
        print(f"  {prov}: {count}")
    
    print("=" * 60)
    
    return imported

if __name__ == '__main__':
    # Read from file or stdin
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
            records = data.get('records', data)
    else:
        # Read from stdin
        data = json.load(sys.stdin)
        records = data.get('records', data)
    
    import_records(records)
