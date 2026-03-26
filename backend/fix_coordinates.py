#!/usr/bin/env python3
"""
使用高德地图 API 修复景点坐标
"""

import requests
import sqlite3
import time
import json
import os

AMAP_KEY = os.environ.get('AMAP_API_KEY', 'f955956f2816c38335a8bc6e02dbb078')

def geocode(address):
    """调用高德地图地理编码 API"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        'key': AMAP_KEY,
        'address': address,
        'output': 'json'
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if data.get('status') == '1' and data.get('geocodes'):
            location = data['geocodes'][0]['location']
            lng, lat = location.split(',')
            return float(lat), float(lng)
        else:
            return None, None
    except Exception as e:
        print(f"  地理编码失败: {e}")
        return None, None

def main():
    print("=" * 60)
    print("修复景点坐标")
    print("=" * 60)
    
    conn = sqlite3.connect('data/roadtrip.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, province, city, district, address FROM pois")
    pois = cursor.fetchall()
    
    print(f"共 {len(pois)} 条记录需要处理\n")
    
    success = 0
    failed = 0
    
    for idx, (id_, name, province, city, district, address) in enumerate(pois, 1):
        # 构建完整地址
        full_address = f"{province}{city}{district}{address}"
        
        print(f"[{idx}/{len(pois)}] {name} - {full_address}", end=" ")
        
        lat, lng = geocode(full_address)
        
        if lat and lng:
            cursor.execute(
                "UPDATE pois SET latitude = ?, longitude = ? WHERE id = ?",
                (lat, lng, id_)
            )
            print(f"✅ ({lat:.4f}, {lng:.4f})")
            success += 1
        else:
            # 尝试简化地址
            simple_address = f"{province}{city}{name}"
            print(f"→ 简化地址...", end=" ")
            lat, lng = geocode(simple_address)
            
            if lat and lng:
                cursor.execute(
                    "UPDATE pois SET latitude = ?, longitude = ? WHERE id = ?",
                    (lat, lng, id_)
                )
                print(f"✅ ({lat:.4f}, {lng:.4f})")
                success += 1
            else:
                print(f"❌ 失败")
                failed += 1
        
        # 每 20 条提交一次
        if idx % 20 == 0:
            conn.commit()
        
        # 避免触发 API 限流
        time.sleep(0.1)
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ 完成！成功: {success}, 失败: {failed}")
    print("=" * 60)

if __name__ == '__main__':
    main()
