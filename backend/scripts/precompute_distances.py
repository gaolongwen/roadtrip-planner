#!/usr/bin/env python3
"""
预计算景点间驾车距离
后台运行，调用高德 API 计算所有景点对的距离
"""
import sys
import os
import time
import asyncio
import httpx
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine
from models import POI, POIDistance, Base

AMAP_KEY = "f955956f2816c38335a8bc6e02dbb078"

# 创建表
Base.metadata.create_all(bind=engine)


async def get_driving_distance(client: httpx.AsyncClient, origin: str, destination: str) -> dict:
    """调用高德驾车API获取距离和时长"""
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
        print(f"  API 错误: {e}")
        return None


async def compute_all_distances():
    """计算所有景点对的距离（串行模式，安全限流）"""
    db = SessionLocal()
    
    try:
        # 获取所有景点
        pois = db.query(POI).all()
        total = len(pois)
        print(f"共有 {total} 个景点", flush=True)
        
        # 计算需要查询的对数（无向图，只计算一半）
        total_pairs = total * (total - 1) // 2
        print(f"需要计算 {total_pairs} 对距离", flush=True)
        
        # 获取已计算的记录
        existing = db.query(POIDistance).all()
        existing_set = set()
        for e in existing:
            key = tuple(sorted([e.poi1_id, e.poi2_id]))
            existing_set.add(key)
        
        print(f"已存在 {len(existing_set)} 条记录", flush=True)
        print(f"需要新计算 {total_pairs - len(existing_set)} 对", flush=True)
        
        # 构建待计算的任务列表
        tasks = []
        for i, poi1 in enumerate(pois):
            for j, poi2 in enumerate(pois):
                if i >= j:
                    continue
                
                key = tuple(sorted([poi1.id, poi2.id]))
                if key in existing_set:
                    continue
                
                tasks.append((poi1, poi2, key))
        
        print(f"开始串行计算 {len(tasks)} 对距离（QPS=2）...", flush=True)
        print(f"预计耗时: {len(tasks) * 0.5 / 60:.1f} 分钟", flush=True)
        
        # 创建 HTTP 客户端
        async with httpx.AsyncClient(timeout=30) as client:
            computed = 0
            errors = 0
            commit_interval = 50  # 每50条提交一次
            
            for idx, (poi1, poi2, key) in enumerate(tasks):
                # 串行请求
                origin = f"{poi1.longitude},{poi1.latitude}"
                destination = f"{poi2.longitude},{poi2.latitude}"
                result = await get_driving_distance(client, origin, destination)
                
                if result:
                    # 存储时用排序后的顺序，避免重复
                    distance = POIDistance(
                        poi1_id=key[0],
                        poi2_id=key[1],
                        distance=result["distance"],
                        duration=result["duration"],
                        source=result["source"]
                    )
                    db.add(distance)
                    computed += 1
                else:
                    errors += 1
                
                # 定期提交
                if computed % commit_interval == 0:
                    db.commit()
                    progress = (computed + len(existing_set)) / total_pairs * 100
                    print(f"进度: {progress:.1f}% ({computed}/{len(tasks)}) - 错误: {errors} - 最近: {poi1.name} → {poi2.name}", flush=True)
                
                # 限流：每2秒最多1次请求 = QPS 0.5
                await asyncio.sleep(0.5)
            
            # 提交剩余记录
            db.commit()
            
            print(f"\n完成！", flush=True)
            print(f"  新计算: {computed} 条", flush=True)
            print(f"  已存在: {len(existing_set)} 条", flush=True)
            print(f"  失败: {errors} 条", flush=True)
            print(f"  总计: {computed + len(existing_set)} 条", flush=True)
    
    finally:
        db.close()


def main():
    print(f"开始预计算景点距离 - {datetime.now()}", flush=True)
    print("=" * 50, flush=True)
    
    asyncio.run(compute_all_distances())
    
    print("=" * 50, flush=True)
    print(f"结束 - {datetime.now()}", flush=True)


if __name__ == "__main__":
    main()
