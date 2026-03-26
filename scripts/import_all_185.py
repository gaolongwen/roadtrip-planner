#!/usr/bin/env python3
"""导入全部 185 条景点数据"""
import json
import sqlite3
from datetime import datetime
import re

def clean_city(city):
    """清理城市名"""
    if not city:
        return None
    city = re.sub(r'[（(][^)）]*[)）]', '', city)
    return city.strip() if city.strip() else None

def infer_category(name, tips):
    """推断类别"""
    text = f"{name or ''} {tips or ''}".lower()
    if any(w in text for w in ['石窟', '佛', '寺', '庙', '塔', '道', '教堂', '古建', '古镇', '古村', '墓', '博物馆']):
        return '人文'
    elif any(w in text for w in ['峡谷', '瀑布', '山', '湖', '河', '地质', '自然', '公园', '森林']):
        return '自然'
    return '人文'

def infer_tags(name, tips):
    """推断标签"""
    tags = []
    text = f"{name or ''} {tips or ''}"
    mapping = {
        '古建': ['古建', '木构', '唐代', '宋代', '明代', '清代', '辽', '金', '元', '五代'],
        '石窟': ['石窟', '摩崖'],
        '佛教': ['佛', '寺', '塔', '禅'],
        '道教': ['道', '观'],
        '长城': ['长城', '关'],
        '古镇': ['古镇', '古村'],
        '自然': ['峡谷', '瀑布', '山', '湖'],
        '世界遗产': ['世界遗产', '世遗'],
    }
    for tag, keywords in mapping.items():
        if any(k in text for k in keywords):
            tags.append(tag)
    return tags[:3] if tags else ['景点']

def is_wild(name, tips):
    """判断是否野生景点"""
    text = f"{name or ''} {tips or ''}".lower()
    return any(k in text for k in ['遗址', '野', '未开发', '废弃', '矿', '捡', '挖', '古墓'])

def main():
    print("开始导入 185 条景点数据...")
    
    # 读取数据
    with open('/root/.openclaw/workspace/roadtrip-planner/scripts/feishu_185.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data['records']
    print(f"读取到 {len(records)} 条记录")
    
    # 连接数据库
    conn = sqlite3.connect('/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db')
    cursor = conn.cursor()
    
    # 清空现有数据
    cursor.execute("DELETE FROM pois")
    print("已清空现有数据")
    
    # 山西城市列表
    sx_cities = ['大同', '朔州', '忻州', '阳泉', '太原', '吕梁', '晋中', '长治', '临汾', '晋城', '运城']
    
    imported = 0
    for idx, r in enumerate(records, 1):
        f = r['fields']
        
        # 名称（必填）
        name = f.get('景点名') or f.get('地址') or f'未命名{idx}'
        
        # 城市和省份
        city_raw = f.get('地级市') or ''
        city = clean_city(city_raw)
        
        if city and any(c in city for c in sx_cities):
            province = '山西'
        elif city and '河南' not in city_raw:
            province = '河南'
        else:
            province = '河南' if '河南' in str(city_raw) else '山西'
        
        # 其他字段
        district = f.get('县级市/县') or ''
        town = f.get('镇/乡') or ''
        address = f'{town} {f.get("地址") or ""}'.strip()
        tips = f.get('备注') or ''
        
        category = infer_category(name, tips)
        tags = infer_tags(name, tips)
        wild = is_wild(name, tips)
        
        # 坐标（待补充真实数据）
        lat = 35.0 + (idx % 20) * 0.3
        lng = 110.0 + (idx % 20) * 0.4
        
        try:
            cursor.execute("""
                INSERT INTO pois (id, name, province, city, district, address,
                    latitude, longitude, category, tags, rating, price, duration,
                    description, tips, images, is_wild, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                idx, name, province, city or '未知', district, address,
                lat, lng, category, json.dumps(tags, ensure_ascii=False),
                4.0, 0.0, 1, tips, tips, '[]', 1 if wild else 0,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            imported += 1
        except Exception as e:
            print(f"导入失败 [{idx}] {name}: {e}")
    
    conn.commit()
    
    # 验证
    cursor.execute("SELECT COUNT(*) FROM pois")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT province, COUNT(*) FROM pois GROUP BY province")
    by_prov = cursor.fetchall()
    
    conn.close()
    
    print(f"\n✅ 导入完成！")
    print(f"   成功: {imported} 条")
    print(f"   数据库总计: {total} 条")
    print(f"\n   按省份:")
    for p, c in by_prov:
        print(f"   {p}: {c} 条")

if __name__ == '__main__':
    main()
