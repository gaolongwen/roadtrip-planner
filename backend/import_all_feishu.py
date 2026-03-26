#!/usr/bin/env python3
"""
Import all attractions from Feishu Bitable
This script fetches all records and imports them to SQLite
"""

import subprocess
import json
import sqlite3
from datetime import datetime
import re

def call_feishu_api(app_token, table_id):
    """Call Feishu API to get all records"""
    # This would normally call the API, but we'll use the data we already have
    # For now, return the records from our earlier fetch
    pass

def clean_city(city):
    """Clean city name, remove parentheses and special characters"""
    if not city:
        return None
    city = re.sub(r'[（(][^)）]*[)）]', '', city)
    return city.strip() if city.strip() else None

def infer_category(name, description, tips):
    """Infer category from name and description"""
    text = f"{name or ''} {description or ''} {tips or ''}".lower()
    
    if any(word in text for word in ['石窟', '佛', '寺', '庙', '塔', '道教', '教堂', '古建', '古村', '古镇', '古堡']):
        return '人文'
    elif any(word in text for word in ['峡谷', '瀑布', '山', '湖', '河', '地质', '自然', '公园', '溶洞']):
        return '自然'
    else:
        return '人文'

def infer_tags(name, description, tips):
    """Infer tags from name and description"""
    tags = []
    text = f"{name or ''} {description or ''} {tips or ''}"
    
    tag_keywords = {
        '古建': ['古建', '建筑', '木构', '唐代', '宋代', '明代', '清代', '辽代', '金代', '元代', '五代', '北魏', '北齐'],
        '石窟': ['石窟', '摩崖'],
        '佛教': ['佛', '寺', '塔', '禅', '菩萨'],
        '道教': ['道教', '道观'],
        '长城': ['长城', '关隘', '烽火台'],
        '古村': ['古镇', '古村', '村落', '民居'],
        '自然': ['峡谷', '瀑布', '山', '湖', '河', '地质', '溶洞', '冰洞'],
        '世界遗产': ['世界遗产', '世遗', 'UNESCO'],
        '博物馆': ['博物馆', '纪念馆'],
        '教堂': ['教堂', '天主', '基督'],
        '工业遗产': ['矿山', '工厂', '矿井', '电厂'],
        '挂壁公路': ['挂壁', '公路'],
        '彩塑': ['彩塑', '壁画', '悬塑'],
        '古墓': ['古墓', '陵墓', '墓葬'],
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
    
    # Add references if available
    refs = []
    for i in range(1, 4):
        ref = fields.get(f'参考{i}')
        if ref and 'xiaohongshu.com' not in ref:  # Skip URLs
            refs.append(ref)
    
    if refs:
        parts.append("参考：" + " | ".join(refs))
    
    return " ".join(parts) if parts else fields.get('景点名', '景点')

def build_address(fields):
    """Build full address from components"""
    parts = []
    
    town = fields.get('镇/乡')
    if town:
        parts.append(town)
    
    address = fields.get('地址')
    if address:
        parts.append(address)
    
    return " ".join(parts) if parts else fields.get('景点名', '未知地址')

def is_wild_attraction(name, tips, description):
    """Determine if this is a wild/unofficial attraction"""
    text = f"{name or ''} {tips or ''} {description or ''}".lower()
    wild_keywords = ['遗址', '野', '未开发', '原始', '废弃', '矿', '捡', '挖', '古墓', '荒', '未命名', '玛瑙']
    return any(keyword in text for keyword in wild_keywords)

def import_all_records(records_data):
    """Import all records to database"""
    print("=" * 60)
    print("Importing attractions from Feishu Bitable to SQLite")
    print("=" * 60)
    
    records = records_data['records']
    print(f"\nLoaded {len(records)} records from Feishu")
    
    # Connect to database
    conn = sqlite3.connect('data/roadtrip.db')
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT COUNT(*) FROM pois")
    before_count = cursor.fetchone()[0]
    print(f"Current records in database: {before_count}")
    
    # Clear existing data
    cursor.execute("DELETE FROM pois")
    print("Cleared existing records\n")
    
    # Import each record
    imported = 0
    errors = []
    
    for idx, record in enumerate(records, start=1):
        fields = record.get('fields', {})
        
        # Get name - use 地址 as fallback
        name = fields.get('景点名')
        if not name:
            name = fields.get('地址') or f'未命名景点{idx}'
        
        # Build other fields
        address = build_address(fields)
        description = build_description(fields)
        tips = fields.get('备注') or ''
        
        city = clean_city(fields.get('地级市'))
        district = fields.get('县级市/县') or ''
        
        category = infer_category(name, description, tips)
        tags = infer_tags(name, description, tags)
        is_wild = is_wild_attraction(name, tips, description)
        
        # Coordinates (placeholder)
        latitude = 35.0 + (idx % 20) * 0.3
        longitude = 110.0 + (idx % 20) * 0.4
        
        # Default values
        rating = 4.0
        price = 0.0
        duration = 1  # MUST be >= 1
        
        # Images
        images = []
        for i in range(1, 5):
            img = fields.get(f'图片{i}')
            if img:
                images.append(img)
        
        # Determine province based on city
        province = '山西'
        henan_cities = ['洛阳', '安阳', '新乡', '焦作', '三门峡', '南阳', '郑州', '信阳', '济源', '永城', '平顶山', '鹤壁', '开封', '许昌', '驻马店', '商丘', '漯河', '周口', '平顶山']
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
                print(f"  Processed {idx}/{len(records)} records...")
                
        except Exception as e:
            errors.append(f"Record {idx} ({name}): {e}")
    
    # Commit all changes
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM pois")
    final_count = cursor.fetchone()[0]
    
    # Show stats
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
    # Read the complete Feishu data
    with open('feishu_complete_records.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    import_all_records(data)
