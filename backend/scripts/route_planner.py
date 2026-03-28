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


def call_llm(prompt: str, temperature: float = 0.3) -> dict:
    """
    调用 LLM API
    
    返回: {"content": str, "reasoning": str}
    """
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
    msg = data["choices"][0]["message"]
    content = msg.get("content", "")
    reasoning = msg.get("reasoning_content", "")
    
    return {"content": content, "reasoning": reasoning}


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
    
    # 构建简化 prompt（避免 GLM-5 只输出 reasoning）
    prompt = f"""规划从{start_city}到{end_city}的{days}天旅游城市路线。

城市列表：{', '.join(cities)}
各城市景点数：{json.dumps(city_poi_count, ensure_ascii=False)}

要求：
1. 必须从{start_city}开始，到{end_city}结束
2. 输出{days}个城市名（可重复）
3. 相邻城市驾车不超过4小时

输出格式（只输出JSON数组）：
["城市1", "城市2", "城市3"]
"""

    result = call_llm(prompt, temperature=0.3)
    content = result["content"]
    reasoning = result["reasoning"]
    
    # 解析 JSON（优先从 content，如果为空则从 reasoning 提取）
    import re
    text_to_parse = content if content else reasoning
    
    try:
        # 方法1: 找所有 JSON 数组，过滤只包含合法城市的
        all_arrays = re.findall(r'\["[^"]+?"(?:\s*,\s*"[^"]+?")*\]', text_to_parse)
        for arr_str in all_arrays:
            city_chain = json.loads(arr_str)
            # 过滤掉示例格式（包含"城市"字样）
            if any("城市" in c for c in city_chain):
                continue
            # 检查是否都是合法城市
            if all(c in cities for c in city_chain) and len(city_chain) == days:
                return city_chain
        
        # 方法2: reasoning 末尾的 "城市链: 大同, 太原, 郑州" 或类似格式
        chain_match = re.search(r'(?:城市链|路线|行程)[：:]\s*([^\n]+)', text_to_parse)
        if chain_match:
            cities_str = chain_match.group(1)
            # 提取城市名（只保留在候选列表中的）
            found_cities = [c for c in cities if c in cities_str]
            if len(found_cities) == days:
                return found_cities
        
        print(f"未找到长度为 {days} 的城市链")
    except Exception as e:
        print(f"解析城市链失败: {e}")
    
    print(f"Content: {content[:200] if content else 'empty'}")
    print(f"Reasoning 片段: {reasoning[:300]}...")
    
    # 失败时返回简单的城市序列
    print(f"回退到默认城市链: [{start_city}] * {days}")
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
    
    # 构建简化 prompt
    poi_names = [f"{p['id']}:{p['name']}({p['city']},{p['duration']}h)" for p in poi_info]
    prompt = f"""规划从{city_a}到{city_b}的单日行程（第{day_number}天）。

候选景点：{', '.join(poi_names)}

要求：
1. 选择2-3个景点
2. 单段驾车不超过3.5小时

输出格式（只输出景点ID的JSON数组）：
[1, 2, 35]
"""

    result = call_llm(prompt, temperature=0.3)
    content = result["content"]
    reasoning = result["reasoning"]
    
    # 解析 JSON（优先从 content，如果为空则从 reasoning 提取）
    import re
    text_to_parse = content if content else reasoning
    
    try:
        selected_ids = []
        
        # 方法1: 标准数组格式 [1, 2, 35]
        array_match = re.search(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', text_to_parse)
        if array_match:
            selected_ids = json.loads(array_match.group())
        
        # 方法2: reasoning 末尾的 "景点：2, 35, 36" 或 "景点: 2, 35, 36"
        if not selected_ids:
            poi_match = re.search(r'景点[：:]\s*(\d+(?:\s*[，,]\s*\d+)*)', text_to_parse)
            if poi_match:
                ids_str = poi_match.group(1)
                selected_ids = [int(x) for x in re.findall(r'\d+', ids_str)]
        
        # 方法3: reasoning 末尾的 "selected_pois: [2, 35, 36]"
        if not selected_ids:
            sp_match = re.search(r'selected_pois[：:]\s*\[?\s*(\d+(?:\s*[，,]\s*\d+)*)\s*\]?', text_to_parse)
            if sp_match:
                ids_str = sp_match.group(1)
                selected_ids = [int(x) for x in re.findall(r'\d+', ids_str)]
        
        # 方法4: 完整 JSON 对象
        if not selected_ids:
            obj_match = re.search(r'\{[\s\S]*"selected_pois"[\s\S]*?\[[\s\S]*?\][\s\S]*?\}', text_to_parse)
            if obj_match:
                try:
                    parsed = json.loads(obj_match.group())
                    selected_ids = parsed.get("selected_pois", [])
                except:
                    pass
        
        # 过滤只保留候选景点ID
        candidate_ids = [p['id'] for p in poi_info]
        selected_ids = [i for i in selected_ids if i in candidate_ids]
        
        if selected_ids:
            # 补充景点详情
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
            
            route_str = f"{city_a} → " + " → ".join([p["name"] for p in selected_poi_details]) + f" → {city_b}"
            
            return {
                "day": day_number,
                "start_city": city_a,
                "end_city": city_b,
                "pois": selected_poi_details,
                "total_drive_time": 0,
                "total_play_time": sum([p["duration"] for p in selected_poi_details]),
                "route": route_str,
                "reasoning": ""
            }
    except Exception as e:
        print(f"解析每日路线失败: {e}")
        print(f"Content: {content[:200] if content else 'empty'}")
    
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
