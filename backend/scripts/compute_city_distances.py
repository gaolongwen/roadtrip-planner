#!/usr/bin/env python3
"""
计算景点到所属城市/县城的距离
调用高德 API 获取城市/县城中心坐标，然后计算驾车距离
"""
import sys
import os
import time
import asyncio
import httpx
import math
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine
from models import POI, POICityDistance, Base

AMAP_KEY = "f955956f2816c38335a8bc6e02dbb078"

# 创建表
Base.metadata.create_all(bind=engine)

# 坐标缓存
coordinate_cache = {}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """
    计算两点间的 Haversine 直线距离（米）
    """
    R = 6371000  # 地球半径（米）

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return int(R * c)


def estimate_driving_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> dict:
    """
    用直线距离 × 1.3 估算驾车距离
    """
    straight_dist = haversine_distance(lat1, lon1, lat2, lon2)
    estimated_dist = int(straight_dist * 1.3)
    # 假设平均时速 50km/h，计算时长
    estimated_duration = int(estimated_dist / 50000 * 3600)  # 秒

    return {
        "distance": estimated_dist,
        "duration": estimated_duration,
        "source": "estimate"
    }


async def get_geocode(client: httpx.AsyncClient, address: str) -> tuple:
    """
    调用高德地理编码 API 获取地址坐标
    返回 (latitude, longitude) 或 None
    """
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": AMAP_KEY,
        "address": address
    }

    try:
        response = await client.get(url, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "1" and data.get("geocodes"):
            geocode = data["geocodes"][0]
            location = geocode.get("location", "")
            if location:
                lon, lat = location.split(",")
                return (float(lat), float(lon))

        return None
    except Exception as e:
        print(f"  地理编码错误 ({address}): {e}")
        return None


async def get_driving_distance(client: httpx.AsyncClient, origin: str, destination: str) -> dict:
    """
    调用高德驾车 API 获取距离和时长
    origin/destination 格式: "longitude,latitude"
    """
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": AMAP_KEY,
        "origin": origin,
        "destination": destination,
        "extensions": "base"
    }

    try:
        response = await client.get(url, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "1" and data.get("route"):
            path = data["route"]["paths"][0]
            return {
                "distance": int(path.get("distance", 0)),
                "duration": int(path.get("duration", 0)),
                "source": "amap"
            }
        else:
            return None
    except Exception as e:
        print(f"  驾车 API 错误: {e}")
        return None


async def get_city_coordinate(client: httpx.AsyncClient, province: str, city: str, district: str = None) -> tuple:
    """
    获取城市或县城的中心坐标（带缓存）
    返回 (latitude, longitude) 或 None
    """
    # 构建缓存 key
    cache_key = f"{province}{city}{district or ''}"

    if cache_key in coordinate_cache:
        return coordinate_cache[cache_key]

    # 构建地址
    if district:
        address = f"{province}{city}{district}"
    else:
        address = f"{province}{city}"

    coord = await get_geocode(client, address)

    # 缓存结果
    coordinate_cache[cache_key] = coord

    return coord


async def compute_city_distances():
    """计算所有景点到所属城市/县城的距离"""
    db = SessionLocal()

    try:
        # 获取所有景点
        pois = db.query(POI).all()
        total = len(pois)
        print(f"共有 {total} 个景点", flush=True)

        # 获取已计算的记录
        existing = db.query(POICityDistance).all()
        existing_poi_ids = {e.poi_id for e in existing}

        print(f"已存在 {len(existing_poi_ids)} 条记录", flush=True)
        print(f"需要新计算 {total - len(existing_poi_ids)} 条", flush=True)

        # 统计
        computed = 0
        errors = 0
        skipped = 0

        # 创建 HTTP 客户端
        async with httpx.AsyncClient(timeout=30) as client:
            for idx, poi in enumerate(pois):
                # 跳过已存在的
                if poi.id in existing_poi_ids:
                    skipped += 1
                    continue

                # 显示进度
                if (idx + 1) % 10 == 0 or idx == 0:
                    print(f"进度: {idx + 1}/{total} - {poi.name}", flush=True)

                # 获取地级市坐标
                city_coord = await get_city_coordinate(client, poi.province, poi.city)

                # 计算到地级市的距离
                city_distance = None
                city_duration = None
                source = "amap"

                if city_coord:
                    origin = f"{poi.longitude},{poi.latitude}"
                    dest = f"{city_coord[1]},{city_coord[0]}"

                    result = await get_driving_distance(client, origin, dest)
                    if result:
                        city_distance = result["distance"]
                        city_duration = result["duration"]
                        source = result["source"]
                    else:
                        # 用直线距离估算
                        est = estimate_driving_distance(poi.latitude, poi.longitude, city_coord[0], city_coord[1])
                        city_distance = est["distance"]
                        city_duration = est["duration"]
                        source = "estimate"

                # 获取县城坐标并计算距离
                district_distance = None
                district_duration = None

                if poi.district:
                    district_coord = await get_city_coordinate(client, poi.province, poi.city, poi.district)

                    if district_coord:
                        origin = f"{poi.longitude},{poi.latitude}"
                        dest = f"{district_coord[1]},{district_coord[0]}"

                        result = await get_driving_distance(client, origin, dest)
                        if result:
                            district_distance = result["distance"]
                            district_duration = result["duration"]
                        else:
                            # 用直线距离估算
                            est = estimate_driving_distance(poi.latitude, poi.longitude, district_coord[0], district_coord[1])
                            district_distance = est["distance"]
                            district_duration = est["duration"]

                # 保存记录
                distance_record = POICityDistance(
                    poi_id=poi.id,
                    city=poi.city,
                    district=poi.district,
                    city_distance=city_distance,
                    city_duration=city_duration,
                    district_distance=district_distance,
                    district_duration=district_duration,
                    source=source
                )
                db.add(distance_record)
                computed += 1

                # 定期提交
                if computed % 20 == 0:
                    db.commit()
                    print(f"  已提交 {computed} 条记录", flush=True)

                # 限流：每次请求后等待
                await asyncio.sleep(0.1)  # QPS ≈ 10

            # 提交剩余记录
            db.commit()

            print(f"\n完成！", flush=True)
            print(f"  新计算: {computed} 条", flush=True)
            print(f"  已存在: {skipped} 条", flush=True)
            print(f"  失败: {errors} 条", flush=True)
            print(f"  总计: {computed + skipped} 条", flush=True)

    finally:
        db.close()


def main():
    print(f"开始计算景点到城市距离 - {datetime.now()}", flush=True)
    print("=" * 50, flush=True)

    asyncio.run(compute_city_distances())

    print("=" * 50, flush=True)
    print(f"结束 - {datetime.now()}", flush=True)


if __name__ == "__main__":
    main()
