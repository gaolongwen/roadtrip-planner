#!/usr/bin/env python3
"""获取城市人民政府坐标"""
import os
import sys
import time
import httpx
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import CityCoordinate, POI

AMAP_KEY = os.getenv("AMAP_KEY", "f955956f2816c38335a8bc6e02dbb078")


def get_city_coord(city: str, province: str = "") -> tuple:
    """获取城市人民政府坐标
    
    返回: (longitude, latitude) 或 None
    """
    # 高德地图地理编码 API
    url = "https://restapi.amap.com/v3/geocode/geo"
    
    # 搜索"XX市人民政府"
    address = f"{city}人民政府"
    params = {
        "key": AMAP_KEY,
        "address": address,
        "city": city,
    }
    
    try:
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()
        
        if data.get("status") == "1" and data.get("geocodes"):
            location = data["geocodes"][0].get("location", "")
            if location:
                lng, lat = location.split(",")
                return float(lng), float(lat)
    except Exception as e:
        print(f"  获取 {city} 坐标失败: {e}")
    
    return None


def main():
    db = SessionLocal()
    
    # 获取所有城市
    cities = db.query(POI.city, POI.province).distinct().all()
    print(f"共 {len(cities)} 个城市")
    
    added = 0
    for city, province in cities:
        if not city:
            continue
        
        # 检查是否已存在
        existing = db.query(CityCoordinate).filter(CityCoordinate.city == city).first()
        if existing:
            print(f"  {city}: 已存在")
            continue
        
        print(f"获取 {city} 坐标...")
        coord = get_city_coord(city, province)
        
        if coord:
            lng, lat = coord
            cc = CityCoordinate(
                city=city,
                province=province or "",
                longitude=lng,
                latitude=lat
            )
            db.add(cc)
            db.commit()
            print(f"  ✓ {city}: ({lng}, {lat})")
            added += 1
        else:
            print(f"  ✗ {city}: 获取失败")
        
        time.sleep(0.2)  # 避免限速
    
    db.close()
    print(f"\n完成！新增 {added} 个城市坐标")


if __name__ == "__main__":
    main()
