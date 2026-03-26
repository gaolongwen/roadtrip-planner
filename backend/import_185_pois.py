#!/usr/bin/env python3
"""
Import 185 POIs from Feishu Bitable to SQLite database
"""

import json
import sqlite3
import re
from datetime import datetime

def clean_city(city):
    """Remove parentheses from city names"""
    if not city:
        return None
    # Remove content in parentheses: "（张家口）阳原县" → "阳原县"
    city = re.sub(r'[（(][^)）]*[)）]', '', city)
    return city.strip() if city.strip() else None

def infer_category(name, description, tips):
    """Infer category from name and description"""
    text = f"{name or ''} {description or ''} {tips or ''}".lower()
    
    # Human culture keywords
    human_keywords = ['石窟', '佛', '寺', '庙', '塔', '道教', '教堂', '古建', '古村', '古镇', 
                      '古堡', '关帝', '书院', '衙门', '祠', '殿', '陵', '墓', '遗址', '古城']
    # Nature keywords
    nature_keywords = ['峡谷', '瀑布', '山', '湖', '河', '地质', '自然', '溶洞', '冰洞', 
                       '温泉', '森林', '湿地', '草原', '水库', '公园']
    
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
        '工业遗产': ['矿山', '工厂', '矿井', '电厂', '煤矿'],
        '挂壁公路': ['挂壁', '公路'],
        '彩塑': ['彩塑', '壁画', '悬塑'],
        '古墓': ['古墓', '陵墓', '墓葬', '地宫'],
        '瀑布': ['瀑布', '天河'],
        '峡谷': ['峡谷', '红石峡'],
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
    
    # Add non-URL references
    refs = []
    for i in range(1, 4):
        ref = fields.get(f'参考{i}')
        if ref and 'http' not in ref:
            refs.append(ref)
    
    if refs:
        parts.append("参考：" + " | ".join(refs))
    
    return " ".join(parts) if parts else (fields.get('景点名') or fields.get('地址', '景点'))

def build_address(fields):
    """Build full address from components"""
    parts = []
    
    town = fields.get('镇/乡')
    if town:
        parts.append(town)
    
    address = fields.get('地址')
    if address:
        parts.append(address)
    
    return " ".join(parts) if parts else (fields.get('景点名') or '未知地址')

def is_wild_attraction(name, tips, description):
    """Determine if this is a wild/unofficial attraction"""
    text = f"{name or ''} {tips or ''} {description or ''}".lower()
    wild_keywords = ['遗址', '野', '未开发', '原始', '废弃', '矿', '捡', '挖', '古墓', '荒', 
                     '未命名', '玛瑙', '化石', '古栈道']
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
                    '北关', '龙安', '安阳县']
    
    # Clean city name first
    clean_city_name = clean_city(city)
    if clean_city_name and any(c in clean_city_name for c in henan_cities):
        return '河南'
    
    return '山西'

def import_pois():
    """Main import function"""
    print("=" * 60)
    print("Importing 185 POIs from Feishu to SQLite")
    print("=" * 60)
    
    # Load data from Feishu
    feishu_data = {
        "records": [{"fields": {"县级市/县": "阳高县", "参考1": None, "参考2": None, "参考3": None, "图片1": None, "图片2": None, "图片3": None, "图片4": None, "地址": "洪门寺遗址", "地级市": "大同", "备注": "大同市阳高县友宰镇大辛庄村自驾导航 洪门寺遗址", "文本": None, "景点名": "洪门寺遗址", "镇/乡": "友宰镇"}, "id": "recUMe5xLX", "record_id": "recUMe5xLX"}],
        "has_more": False,
        "total": 185
    }
    
    # This will be replaced by actual data loading
    print("⚠️  Note: Using placeholder data. Replace with actual Feishu API call.")
    
    # Connect to database
    db_path = '/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT COUNT(*) FROM pois")
    before_count = cursor.fetchone()[0]
    print(f"Current records in database: {before_count}")
    
    # Clear existing data
    cursor.execute("DELETE FROM pois")
    print("✓ Cleared existing records\n")
    
    conn.close()
    print("Database connection closed for demo. Replace with actual import logic.")

if __name__ == '__main__':
    import_pois()
