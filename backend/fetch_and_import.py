#!/usr/bin/env python3
"""
Fetch and import 185 POIs from Feishu to SQLite
This script uses the OpenClaw feishu tools via subprocess
"""

import json
import sqlite3
import re
from datetime import datetime

def clean_city(city):
    """Remove parentheses from city names"""
    if not city:
        return None
    city = re.sub(r'[（(][^)）]*[)）]', '', city)
    return city.strip() if city.strip() else None

def infer_category(name, description, tips):
    """Infer category from name and description"""
    text = f"{name or ''} {description or ''} {tips or ''}".lower()
    
    human_keywords = ['石窟', '佛', '寺', '庙', '塔', '道教', '教堂', '古建', '古村', '古镇', 
                      '古堡', '关帝', '书院', '衙门', '祠', '殿', '陵', '墓', '遗址', '古城',
                      '文庙', '县衙', '博物馆', '故居', '行宫']
    nature_keywords = ['峡谷', '瀑布', '山', '湖', '河', '地质', '自然', '溶洞', '冰洞', 
                       '温泉', '森林', '湿地', '草原', '水库', '大坝', '天池']
    
    if any(keyword in text for keyword in human_keywords):
        return '人文'
    elif any(keyword in text for keyword in nature_keywords):
        return '自然'
    else:
        return '人文'

def infer_tags(name, description, tips):
    """Infer tags from name and description"""
    tags = []
    text = f"{name or ''} {description or ''} {tips or ''}"
    
    tag_keywords = {
        '古建': ['古建', '建筑', '木构', '唐代', '宋代', '明代', '清代', '辽代', '金代', '元代', '五代', '北魏', '北齐'],
        '石窟': ['石窟', '摩崖', '造像', '石刻'],
        '佛教': ['佛', '寺', '塔', '禅', '菩萨', '观音', '释迦'],
        '道教': ['道教', '道观', '老君'],
        '长城': ['长城', '关隘', '烽火台', '边关'],
        '古村': ['古镇', '古村', '村落', '民居', '窑洞'],
        '自然': ['峡谷', '瀑布', '山', '湖', '河', '地质', '溶洞', '冰洞', '森林'],
        '世界遗产': ['世界遗产', '世遗', 'UNESCO'],
        '博物馆': ['博物馆', '纪念馆', '陈列馆'],
        '教堂': ['教堂', '天主', '基督'],
        '工业遗产': ['矿山', '工厂', '矿井', '电厂', '煤矿', '水泥厂'],
        '挂壁公路': ['挂壁', '公路'],
        '彩塑': ['彩塑', '壁画', '悬塑'],
        '古墓': ['古墓', '陵墓', '墓葬', '地宫'],
        '瀑布': ['瀑布', '天河'],
        '峡谷': ['峡谷', '红石峡'],
        '化石': ['化石', '恐龙', '陨石'],
        '民俗': ['民俗', '古民居', '大院', '庄园'],
    }
    
    for tag, keywords in tag_keywords.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    
    return tags[:3] if tags else ['景点']

def build_description(fields):
    """Build description from available fields"""
    parts = []
    
    if fields.get('备注'):
        parts.append(fields['备注'])
    
    refs = []
    for i in range(1, 4):
        ref = fields.get(f'参考{i}')
        if ref and 'http' not in ref:
            refs.append(ref)
    
    if refs:
        parts.append("参考：" + " | ".join(refs))
    
    result = " ".join(parts) if parts else (fields.get('景点名') or fields.get('地址', '景点'))
    return result[:2000] if result else '景点'

def build_address(fields):
    """Build full address from components"""
    parts = []
    
    town = fields.get('镇/乡')
    if town:
        parts.append(town)
    
    address = fields.get('地址')
    if address:
        parts.append(address)
    
    result = " ".join(parts) if parts else (fields.get('景点名') or '未知地址')
    return result[:500] if result else '未知地址'

def is_wild_attraction(name, tips, description):
    """Determine if this is a wild/unofficial attraction"""
    text = f"{name or ''} {tips or ''} {description or ''}".lower()
    wild_keywords = ['遗址', '野', '未开发', '原始', '废弃', '矿', '捡', '挖', '古墓', '荒', 
                     '未命名', '玛瑙', '化石', '古栈道', '无门票', '无开发']
    return any(keyword in text for keyword in wild_keywords)

def get_province_from_city(city):
    """Determine province from city name"""
    if not city:
        return '山西'
    
    henan_cities = ['洛阳', '安阳', '新乡', '焦作', '三门峡', '南阳', '郑州', '信阳', 
                    '济源', '永城', '平顶山', '鹤壁', '开封', '许昌', '驻马店', '商丘', 
                    '漯河', '周口', '巩义', '登封', '新密', '偃师', '孟津', '新安', 
                    '陕州', '渑池', '卢氏', '栾川', '汝阳', '内乡', '西峡', '镇平', 
                    '南召', '方城', '淅川', '辉县', '卫辉', '沁阳', '修武', '博爱', 
                    '武陟', '温县', '林州', '滑县', '汤阴', '内黄', '文峰', '殷都', 
                    '北关', '龙安', '安阳县', '汝州', '舞钢']
    
    clean_city_name = clean_city(city)
    if clean_city_name and any(c in clean_city_name for c in henan_cities):
        return '河南'
    
    return '山西'

def import_records_from_json(records_data):
    """Import records from JSON data"""
    print("=" * 60)
    print("Importing POIs to SQLite")
    print("=" * 60)
    
    records = records_data.get('records', [])
    print(f"\n✓ Loaded {len(records)} records")
    
    # Connect to database
    db_path = 'data/roadtrip.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT COUNT(*) FROM pois")
    before_count = cursor.fetchone()[0]
    print(f"Current records in database: {before_count}")
    
    # Clear existing data
    cursor.execute("DELETE FROM pois")
    print("✓ Cleared existing records\n")
    
    # Import each record
    imported = 0
    errors = []
    
    for idx, record in enumerate(records, start=1):
        fields = record.get('fields', {})
        
        # Get name
        name = fields.get('景点名')
        if not name:
            name = fields.get('地址') or f'未命名景点{idx}'
        
        # Build fields
        address = build_address(fields)
        description = build_description(fields)
        tips = fields.get('备注') or ''
        
        city = clean_city(fields.get('地级市'))
        district = fields.get('县级市/县') or ''
        
        category = infer_category(name, description, tips)
        tags = infer_tags(name, description, tips)
        is_wild = is_wild_attraction(name, tips, description)
        
        # Coordinates (placeholder)
        latitude = 35.0 + (idx % 40) * 0.15
        longitude = 110.0 + (idx % 30) * 0.2
        
        rating = 4.0
        price = 0.0
        duration = 1
        
        images = []
        for i in range(1, 5):
            img = fields.get(f'图片{i}')
            if img:
                images.append(img)
        
        province = get_province_from_city(fields.get('地级市'))
        
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
                print(f"  Processed {idx}/{len(records)} records...")
                
        except Exception as e:
            errors.append(f"Record {idx} ({name}): {e}")
    
    # Commit
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM pois")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM pois WHERE is_wild = 1")
    wild_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT category, COUNT(*) FROM pois GROUP BY category")
    categories = cursor.fetchall()
    
    cursor.execute("SELECT province, COUNT(*) FROM pois GROUP BY province")
    provinces = cursor.fetchall()
    
    cursor.execute("SELECT city, COUNT(*) as cnt FROM pois GROUP BY city ORDER BY cnt DESC LIMIT 10")
    top_cities = cursor.fetchall()
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Import Complete!")
    print("=" * 60)
    print(f"Records imported: {imported}")
    print(f"Errors: {len(errors)}")
    print(f"Total in database: {final_count}")
    print(f"Wild attractions: {wild_count}")
    
    print("\nBy Category:")
    for cat, count in categories:
        print(f"  {cat}: {count}")
    
    print("\nBy Province:")
    for prov, count in provinces:
        print(f"  {prov}: {count}")
    
    print("\nTop 10 Cities:")
    for city, count in top_cities:
        print(f"  {city}: {count}")
    
    if errors:
        print("\nErrors encountered:")
        for error in errors[:5]:
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    print("=" * 60)
    
    return imported

if __name__ == '__main__':
    # Read JSON from stdin
    import sys
    json_data = sys.stdin.read()
    data = json.loads(json_data)
    import_records_from_json(data)
