#!/usr/bin/env python3
"""
Import attractions from Feishu Bitable to SQLite database
Fetches all records and imports them
"""

import sqlite3
import json
from datetime import datetime
import re
import sys

# All 185 records from Feishu (truncated for display, full data in execution)
FEISHU_RECORDS = []  # Will be populated from the actual Feishu response

def clean_city(city):
    """Clean city name, remove parentheses and special characters"""
    if not city:
        return None
    # Remove patterns like "（河南）", "（安阳市）", etc
    city = re.sub(r'[（(][^)）]*[)）]', '', city)
    return city.strip() if city.strip() else None

def infer_category(name, description, tips):
    """Infer category from name and description"""
    text = f"{name or ''} {description or ''} {tips or ''}".lower()
    
    if any(word in text for word in ['石窟', '佛', '寺', '庙', '塔', '道教', '教堂']):
        return '人文'
    elif any(word in text for word in ['峡谷', '瀑布', '山', '湖', '河', '峡谷', '地质', '自然']):
        return '自然'
    elif any(word in text for word in ['古镇', '古村', '民居', '大院', '庄园']):
        return '人文'
    elif any(word in text for word in ['博物馆', '遗址', '陵墓', '墓']):
        return '人文'
    else:
        return '人文'

def infer_tags(name, description, tips):
    """Infer tags from name and description"""
    tags = []
    text = f"{name or ''} {description or ''} {tips or ''}"
    
    tag_keywords = {
        '古建': ['古建', '建筑', '木构', '唐代', '宋代', '明代', '清代', '辽代', '金代', '元代', '五代'],
        '石窟': ['石窟', '摩崖'],
        '佛教': ['佛', '寺', '塔', '禅'],
        '道教': ['道教', '道观'],
        '长城': ['长城', '关隘'],
        '古镇': ['古镇', '古村'],
        '自然': ['峡谷', '瀑布', '山', '湖', '河', '地质奇观'],
        '世界遗产': ['世界遗产', '世遗'],
        '博物馆': ['博物馆'],
        '教堂': ['教堂'],
        '工业遗产': ['矿山', '工厂', '矿井'],
        '挂壁公路': ['挂壁'],
    }
    
    for tag, keywords in tag_keywords.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    
    return tags[:3] if tags else ['景点']

def build_description(record):
    """Build description from available fields"""
    parts = []
    
    if record.get('备注'):
        parts.append(record['备注'])
    
    refs = []
    for i in range(1, 4):
        ref = record.get(f'参考{i}')
        if ref:
            refs.append(ref)
    
    if refs:
        parts.append("参考：" + " | ".join(refs))
    
    return " ".join(parts) if parts else record.get('景点名', '景点')

def build_address(record):
    """Build full address from components"""
    parts = []
    
    town = record.get('镇/乡')
    if town:
        parts.append(town)
    
    address = record.get('地址')
    if address:
        parts.append(address)
    
    return " ".join(parts) if parts else record.get('景点名', '未知地址')

def is_wild_attraction(name, tips, description):
    """Determine if this is a wild/unofficial attraction"""
    text = f"{name or ''} {tips or ''} {description or ''}".lower()
    
    wild_keywords = ['遗址', '野', '未开发', '原始', '废弃', '矿', '捡', '挖', '古墓']
    return any(keyword in text for keyword in wild_keywords)

def import_attractions(records):
    """Import attractions from records list"""
    
    print(f"Processing {len(records)} records from Feishu")
    
    # Connect to database
    conn = sqlite3.connect('data/roadtrip.db')
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM pois")
    print("Cleared existing records")
    
    # Import each record
    imported = 0
    skipped = 0
    
    for idx, record in enumerate(records, start=1):
        fields = record['fields']
        
        name = fields.get('景点名')
        if not name:
            # Skip records without name but keep count
            print(f"Skipping record {idx}: no name, using address instead")
            name = fields.get('地址') or f'未命名景点{idx}'
        
        # Build address
        address = build_address(fields)
        description = build_description(fields)
        tips = fields.get('备注', '')
        
        # Clean city
        city = clean_city(fields.get('地级市'))
        district = fields.get('县级市/县')
        
        # Infer category and tags
        category = infer_category(name, description, tips)
        tags = infer_tags(name, description, tips)
        
        # Determine if wild
        is_wild = is_wild_attraction(name, tips, description)
        
        # Default values
        latitude = 35.0 + (idx % 10) * 0.5
        longitude = 110.0 + (idx % 10) * 0.5
        rating = 4.0
        price = 0.0
        duration = 1  # MUST be >= 1
        
        # Build images array
        images = []
        for i in range(1, 5):
            img = fields.get(f'图片{i}')
            if img:
                images.append(img)
        
        # Determine province
        province = '山西'
        if city and city in ['洛阳', '安阳', '新乡', '焦作', '三门峡', '南阳', '郑州', '信阳', '济源', '永城', '平顶山', '鹤壁', '开封']:
            province = '河南'
        
        # Insert record
        try:
            cursor.execute("""
                INSERT INTO pois (
                    id, name, province, city, district, address,
                    latitude, longitude, category, tags, rating, price,
                    duration, description, tips, images, is_wild,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                idx,
                name,
                province,
                city or '未知',
                district or '',
                address,
                latitude,
                longitude,
                category,
                json.dumps(tags, ensure_ascii=False),
                rating,
                price,
                duration,
                description,
                tips or '',
                json.dumps(images, ensure_ascii=False),
                1 if is_wild else 0,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            imported += 1
            
            if idx % 50 == 0:
                print(f"Processed {idx}/{len(records)} records...")
                
        except Exception as e:
            print(f"Error inserting record {idx} ({name}): {e}")
            skipped += 1
    
    # Commit changes
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM pois")
    final_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n✅ Import complete!")
    print(f"   Imported: {imported}")
    print(f"   Skipped: {skipped}")
    print(f"   Total in DB: {final_count}")
    
    return imported

if __name__ == '__main__':
    # This script expects JSON data to be passed via stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            records = json.load(f)
    else:
        # Read from stdin
        records = json.load(sys.stdin)
    
    import_attractions(records)
