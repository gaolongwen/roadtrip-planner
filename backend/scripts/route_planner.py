#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路线规划工作流
两阶段规划：
1. 城市链规划：根据景点分布规划城市序列
2. 每日路线规划：规划相邻城市间的景点路线
"""

import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import httpx
from typing import List, Dict, Any, Optional
from database import SessionLocal
from models import POI, POIDistance

# LLM 配置
OPENAI_API_KEY = "sk-sp-UAnq05xlBQIwylSCH2FdXNry1hKrVvMGnFyAN56QyMWO4Vhp"
OPENAI_BASE_URL = "https://api.lkeap.cloud.tencent.com/coding/v3"
OPENAI_MODEL = "glm-5"


def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """调用 LLM API"""
    client = httpx.Client(timeout=180)
    
    response = client.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 2000  # GLM-5 需要足够的空间进行推理
        }
    )
    
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    
    # 如果内容为空，检查 reasoning_content
    if not content and "reasoning_content" in data["choices"][0]["message"]:
        # reasoning 完成但内容为空，可能需要继续
        pass
    
    return content


def get_pois_by_city(db, cities: List[str]) -> Dict[str, List[POI]]:
    """按城市分组景点"""
    result = {}
    for city in cities:
        pois = db.query(POI).filter(POI.city == city).all()
        result[city] = pois
    return result


def get_distance(db, poi1_id: int, poi2_id: int) -> Optional[Dict]:
    """获取两个景点间的距离"""
    # 尝试两种顺序
    key1 = tuple(sorted([poi1_id, poi2_id]))
    
    dist = db.query(POIDistance).filter(
        POIDistance.poi1_id == key1[0],
        POIDistance.poi2_id == key1[1]
    ).first()
    
    if dist:
        return {
            "distance": dist.distance,
            "duration": dist.duration,
            "source": dist.source
        }
    return None


def get_city_distances(db, cities: List[str]) -> Dict[str, Dict[str, int]]:
    """获取城市间的驾车时长（取代表性景点计算）"""
    city_pois = {}
    for city in cities:
        poi = db.query(POI).filter(POI.city == city).first()
        if poi:
            city_pois[city] = poi
    
    distances = {}
    for c1 in cities:
        distances[c1] = {}
        for c2 in cities:
            if c1 == c2:
                distances[c1][c2] = 0
            elif c1 in city_pois and c2 in city_pois:
                dist = get_distance(db, city_pois[c1].id, city_pois[c2].id)
                if dist:
                    distances[c1][c2] = dist["duration"] // 60  # 转为分钟
    
    return distances


def stage1_plan_city_chain(
    db,
    start_city: str,
    end_city: str,
    days: int,
    selected_pois: List[POI]
) -> List[str]:
    """
    阶段1：规划城市链
    
    输入：起点、终点、天数、已选景点
    输出：城市序列（长度=天数）
    """
    
    # 获取所有涉及的城市
    cities = list(set([poi.city for poi in selected_pois if poi.city]))
    
    # 获取城市间距离
    city_distances = get_city_distances(db, cities)
    
    # 统计每个城市的景点数量
    city_poi_count = {}
    for poi in selected_pois:
        city = poi.city
        if city:
            city_poi_count[city] = city_poi_count.get(city, 0) + 1
    
    # 构建 prompt
    prompt = f"""你是一个旅游路线规划专家。请根据以下信息规划一条城市序列。

## 基本信息
- 起点城市：{start_city}
- 终点城市：{end_city}
- 游玩天数：{days} 天
- 城市列表：{', '.join(cities)}

## 各城市景点数量
{json.dumps(city_poi_count, ensure_ascii=False, indent=2)}

## 城市间驾车时长（分钟）
{json.dumps(city_distances, ensure_ascii=False, indent=2)}

## 规则
1. 城市序列长度必须等于 {days} 天
2. 城市可以重复（例如：大同→大同→太原→太原）
3. 必须从 {start_city} 开始，到 {end_city} 结束
4. 相邻城市间的驾车时长尽量不超过 3 小时
5. 优先选择景点数量多的城市
6. 尽量不走回头路

## 输出格式
返回 JSON 数组，例如：
["大同", "大同", "太原", "晋中", "郑州"]

只输出 JSON 数组，不要其他内容。
"""

    response = call_llm(prompt, temperature=0.3)
    
    # 解析 JSON
    try:
        # 提取 JSON 数组
        import re
        json_match = re.search(r'\[[\s\S]*?\]', response)
        if json_match:
            city_chain = json.loads(json_match.group())
            return city_chain
    except Exception as e:
        print(f"解析城市链失败: {e}")
        print(f"LLM 返回: {response}")
    
    # 失败时返回简单的城市序列
    return [start_city] * days


def stage2_plan_daily_route(
    db,
    city_a: str,
    city_b: str,
    selected_pois: List[POI],
    visited_poi_ids: set,
    day_number: int
) -> Dict[str, Any]:
    """
    阶段2：规划单日路线
    
    输入：起点城市A、终点城市B、已选景点、已访问景点
    输出：单日行程规划
    """
    
    # 筛选城市A和B附近的景点（扩展到相邻城市）
    nearby_cities = {city_a, city_b}
    
    # 获取附近景点
    candidate_pois = [poi for poi in selected_pois if poi.city in nearby_cities]
    
    # 剔除已访问景点
    candidate_pois = [poi for poi in candidate_pois if poi.id not in visited_poi_ids]
    
    if not candidate_pois:
        return {
            "day": day_number,
            "start_city": city_a,
            "end_city": city_b,
            "pois": [],
            "total_drive_time": 0,
            "total_play_time": 0,
            "route": f"{city_a} → {city_b}"
        }
    
    # 获取城市代表景点（用于计算城市间距离）
    city_rep_poi = {}
    for city in nearby_cities:
        poi = db.query(POI).filter(POI.city == city).first()
        if poi:
            city_rep_poi[city] = poi
    
    # 构建景点信息
    poi_info = []
    for poi in candidate_pois:
        poi_info.append({
            "id": poi.id,
            "name": poi.name,
            "city": poi.city,
            "duration": poi.duration or 2,  # 游玩时长
        })
    
    # 获取景点间距离
    distances = {}
    all_pois = candidate_pois + list(city_rep_poi.values())
    
    for i, p1 in enumerate(all_pois):
        for j, p2 in enumerate(all_pois):
            if i < j:
                dist = get_distance(db, p1.id, p2.id)
                if dist:
                    key = f"{p1.id}_{p2.id}"
                    distances[key] = dist["duration"] // 60  # 分钟
    
    # 构建 prompt
    prompt = f"""你是一个旅游路线规划专家。请规划从 {city_a} 到 {city_b} 的单日行程。

## 基本信息
- 起点：{city_a}
- 终点：{city_b}
- 第 {day_number} 天

## 候选景点
{json.dumps(poi_info, ensure_ascii=False, indent=2)}

## 景点间驾车时长（分钟）
{json.dumps(distances, ensure_ascii=False, indent=2)}

## 规划规则
1. 选择 2-3 个景点
2. 路线：{city_a} → 景点1 → 景点2 → ... → {city_b}
3. 单段驾车时长不超过 3.5 小时（210分钟）
4. 总时间（自驾+游玩）约 8-10 小时
5. 优先选择顺路的景点
6. 景点游玩时长已标注

## 输出格式
返回 JSON：
{{
  "selected_pois": [景点ID列表],
  "route": "城市A → 景点1 → 景点2 → 城市B",
  "total_drive_time": 总驾车时长（分钟）,
  "total_play_time": 总游玩时长（小时）,
  "reasoning": "选择理由"
}}

只输出 JSON，不要其他内容。
"""

    response = call_llm(prompt, temperature=0.5)
    
    # 解析 JSON
    try:
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
            
            # 补充景点详情
            selected_ids = result.get("selected_pois", [])
            selected_poi_details = []
            for poi_id in selected_ids:
                poi = db.query(POI).filter(POI.id == poi_id).first()
                if poi:
                    selected_poi_details.append({
                        "id": poi.id,
                        "name": poi.name,
                        "city": poi.city,
                        "duration": poi.duration or 2
                    })
            
            return {
                "day": day_number,
                "start_city": city_a,
                "end_city": city_b,
                "pois": selected_poi_details,
                "total_drive_time": result.get("total_drive_time", 0),
                "total_play_time": result.get("total_play_time", 0),
                "route": result.get("route", f"{city_a} → {city_b}"),
                "reasoning": result.get("reasoning", "")
            }
    except Exception as e:
        print(f"解析每日路线失败: {e}")
        print(f"LLM 返回: {response}")
    
    # 失败时返回空路线
    return {
        "day": day_number,
        "start_city": city_a,
        "end_city": city_b,
        "pois": [],
        "total_drive_time": 0,
        "total_play_time": 0,
        "route": f"{city_a} → {city_b}"
    }


def plan_trip(
    start_city: str,
    end_city: str,
    days: int,
    selected_poi_ids: List[int]
) -> Dict[str, Any]:
    """
    完整行程规划
    
    输入：起点城市、终点城市、天数、已选景点ID列表
    输出：完整行程规划
    """
    db = SessionLocal()
    
    try:
        # 获取已选景点
        selected_pois = db.query(POI).filter(POI.id.in_(selected_poi_ids)).all()
        
        print(f"=== 路线规划 ===")
        print(f"起点: {start_city}")
        print(f"终点: {end_city}")
        print(f"天数: {days}")
        print(f"已选景点: {len(selected_pois)} 个\n")
        
        # 阶段1：规划城市链
        print(">>> 阶段1：规划城市链...")
        city_chain = stage1_plan_city_chain(db, start_city, end_city, days, selected_pois)
        print(f"城市链: {' → '.join(city_chain)}\n")
        
        # 阶段2：规划每日路线
        print(">>> 阶段2：规划每日路线...")
        daily_routes = []
        visited_poi_ids = set()
        
        for i in range(len(city_chain) - 1):
            city_a = city_chain[i]
            city_b = city_chain[i + 1]
            
            print(f"\n第 {i+1} 天: {city_a} → {city_b}")
            
            daily = stage2_plan_daily_route(
                db,
                city_a,
                city_b,
                selected_pois,
                visited_poi_ids,
                i + 1
            )
            
            # 记录已访问景点
            for poi in daily["pois"]:
                visited_poi_ids.add(poi["id"])
            
            daily_routes.append(daily)
            
            # 打印结果
            print(f"  路线: {daily['route']}")
            print(f"  景点: {', '.join([p['name'] for p in daily['pois']])}")
            print(f"  驾车: {daily['total_drive_time']} 分钟")
            print(f"  游玩: {daily['total_play_time']} 小时")
        
        # 汇总
        result = {
            "start_city": start_city,
            "end_city": end_city,
            "days": days,
            "city_chain": city_chain,
            "daily_routes": daily_routes,
            "total_pois_visited": len(visited_poi_ids),
            "total_selected": len(selected_pois)
        }
        
        print(f"\n=== 规划完成 ===")
        print(f"已安排景点: {len(visited_poi_ids)}/{len(selected_pois)}")
        
        return result
    
    finally:
        db.close()


if __name__ == "__main__":
    # 测试用例
    import sys
    
    # 示例：大同到郑州，5天，选择一些景点
    start = "大同"
    end = "郑州"
    days = 5
    
    # 示例景点ID（从数据库随机选几个）
    db = SessionLocal()
    sample_pois = db.query(POI).filter(POI.city.in_(["大同", "太原", "晋中", "郑州"])).limit(10).all()
    sample_ids = [p.id for p in sample_pois]
    db.close()
    
    result = plan_trip(start, end, days, sample_ids)
    
    # 保存结果
    with open("/tmp/trip_plan.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到 /tmp/trip_plan.json")
