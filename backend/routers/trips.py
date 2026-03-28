import uuid
import random
import string
import json
import os
import asyncio
import httpx
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db
from models import Trip, TripPOI, TripMember, POI, User, TripRoute
from routers.auth import require_user, get_current_user

# 高德地图 API Key
AMAP_KEY = os.getenv("AMAP_KEY", "f955956f2816c38335a8bc6e02dbb078")

# OpenAI 兼容 API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

router = APIRouter(prefix="/api/trips", tags=["trips"])

# 后台任务状态存储（内存存储，重启后丢失）
planning_tasks: Dict[str, dict] = {}


def generate_share_code(length=6):
    """生成短分享码"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def poi_to_dict(poi: POI) -> dict:
    """转换 POI 为字典"""
    import json
    return {
        "id": poi.id,
        "name": poi.name,
        "province": poi.province,
        "city": poi.city,
        "district": poi.district,
        "address": poi.address,
        "latitude": poi.latitude,
        "longitude": poi.longitude,
        "category": poi.category,
        "rating": poi.rating,
        "images": json.loads(poi.images) if poi.images else [],
    }


async def do_plan_trip(trip_id: str, start_city: str, end_city: str, days: int, task_id: str):
    """后台执行行程规划（两阶段工作流）"""
    from database import SessionLocal
    from models import POIDistance
    
    planning_tasks[task_id]["status"] = "stage1"
    planning_tasks[task_id]["progress"] = 10
    
    try:
        db = SessionLocal()
        
        # 获取行程中的所有景点
        trip_pois = db.query(TripPOI).filter(TripPOI.trip_id == trip_id).all()
        if not trip_pois:
            raise Exception("行程中没有景点")

        poi_ids = [tp.poi_id for tp in trip_pois]
        pois = db.query(POI).filter(POI.id.in_(poi_ids)).all()

        if not pois:
            raise Exception("未找到景点信息")

        # ========== 阶段1：规划城市链 ==========
        planning_tasks[task_id]["message"] = "阶段1：规划城市链..."
        
        cities = list(set([p.city for p in pois if p.city]))
        city_poi_count = {}
        for p in pois:
            city_poi_count[p.city] = city_poi_count.get(p.city, 0) + 1
        
        # 获取城市代表景点
        city_rep = {}
        for city in cities:
            p = db.query(POI).filter(POI.city == city).first()
            if p:
                city_rep[city] = p
        
        # 获取城市间距离
        city_distances = {}
        for c1 in cities:
            city_distances[c1] = {}
            for c2 in cities:
                if c1 == c2:
                    city_distances[c1][c2] = 0
                elif c1 in city_rep and c2 in city_rep:
                    d = db.query(POIDistance).filter(
                        POIDistance.poi1_id == min(city_rep[c1].id, city_rep[c2].id),
                        POIDistance.poi2_id == max(city_rep[c1].id, city_rep[c2].id)
                    ).first()
                    if d:
                        city_distances[c1][c2] = d.duration // 60
        
        # 调用 LLM 规划城市链
        city_chain_prompt = f"""规划从{start_city}到{end_city}的{days}天旅游路线城市序列。

可用城市：{', '.join(cities)}
各城市景点数量：{json.dumps(city_poi_count, ensure_ascii=False)}
城市间驾车时长（分钟）：{json.dumps(city_distances, ensure_ascii=False)}

要求：
- 序列长度={days}
- 起点={start_city}，终点={end_city}
- 相邻城市驾车尽量短
- 可重复城市（如停留多天）

直接输出JSON数组，如：["大同","大同","太原","郑州","郑州"]
不要解释。"""

        city_chain = await call_llm_json_array(city_chain_prompt, cities)
        if not city_chain:
            # 失败时生成默认城市链
            city_chain = [start_city] * days
        
        planning_tasks[task_id]["progress"] = 40
        planning_tasks[task_id]["message"] = f"城市链规划完成：{' → '.join(city_chain)}"
        
        # ========== 阶段2：规划每日路线 ==========
        planning_tasks[task_id]["status"] = "stage2"
        planning_tasks[task_id]["message"] = "阶段2：规划每日路线..."
        
        poi_coords = {p.name: {"lng": p.longitude, "lat": p.latitude} for p in pois}
        visited_poi_ids = set()
        daily_routes = []
        
        for i in range(len(city_chain) - 1):
            city_a = city_chain[i]
            city_b = city_chain[i + 1]
            
            # 筛选候选景点
            nearby_cities = {city_a, city_b}
            candidate_pois = [p for p in pois if p.city in nearby_cities and p.id not in visited_poi_ids]
            
            if not candidate_pois:
                daily_routes.append({
                    "day": i + 1,
                    "start_city": city_a,
                    "end_city": city_b,
                    "pois": [],
                    "route": f"{city_a} → {city_b}",
                    "drive_time": city_distances.get(city_a, {}).get(city_b, 120),
                    "visit_time": 0,
                    "total_time": city_distances.get(city_a, {}).get(city_b, 120) // 60,
                    "description": f"直接从{city_a}前往{city_b}"
                })
                continue
            
            # 构建景点信息
            poi_info = [{"id": p.id, "name": p.name, "city": p.city, "duration": p.duration or 2} for p in candidate_pois]
            
            # 获取景点间距离
            distances = {}
            all_pois = candidate_pois + [city_rep.get(city_a), city_rep.get(city_b)]
            all_pois = [p for p in all_pois if p]
            
            for j, p1 in enumerate(all_pois):
                for k, p2 in enumerate(all_pois):
                    if j < k and p1.id != p2.id:
                        d = db.query(POIDistance).filter(
                            POIDistance.poi1_id == min(p1.id, p2.id),
                            POIDistance.poi2_id == max(p1.id, p2.id)
                        ).first()
                        if d:
                            distances[f"{p1.id}_{p2.id}"] = d.duration // 60
            
            # 调用 LLM 规划每日路线
            planning_tasks[task_id]["message"] = f"规划第 {i+1} 天行程：{city_a} → {city_b}..."
            
            daily_prompt = f"""规划从{city_a}到{city_b}的单日行程。

候选景点：
{json.dumps(poi_info, ensure_ascii=False, indent=2)}

景点间驾车时长（分钟）：
{json.dumps(distances, ensure_ascii=False, indent=2)}

规则：
1. 选择2-3个景点
2. 路线：{city_a} → 景点1 → 景点2 → ... → {city_b}
3. 单段驾车≤3.5小时
4. 总时间（自驾+游玩）约8-10小时

输出JSON：
{{"selected_pois":[景点ID列表],"route":"城市A→景点1→城市B","total_drive_time":分钟,"total_visit_time":小时,"description":"说明"}}
只输出JSON。"""

            candidate_ids = [p['id'] for p in poi_info]
            daily_result = await call_llm_json_obj(daily_prompt, candidate_ids)
            
            if daily_result and "selected_pois" in daily_result:
                selected_ids = daily_result.get("selected_pois", [])
                selected_poi_details = []
                for poi_id in selected_ids:
                    poi = db.query(POI).filter(POI.id == poi_id).first()
                    if poi:
                        selected_poi_details.append({"id": poi.id, "name": poi.name, "city": poi.city, "duration": poi.duration or 2})
                        visited_poi_ids.add(poi.id)
                
                daily_routes.append({
                    "day": i + 1,
                    "start_city": city_a,
                    "end_city": city_b,
                    "pois": selected_poi_details,
                    "route": daily_result.get("route", f"{city_a} → {city_b}"),
                    "drive_time": daily_result.get("total_drive_time", 0),
                    "visit_time": daily_result.get("total_visit_time", 0),
                    "total_time": daily_result.get("total_drive_time", 0) // 60 + daily_result.get("total_visit_time", 0),
                    "description": daily_result.get("description", "")
                })
            else:
                # 失败时取前2个景点
                default_pois = candidate_pois[:2]
                for p in default_pois:
                    visited_poi_ids.add(p.id)
                
                daily_routes.append({
                    "day": i + 1,
                    "start_city": city_a,
                    "end_city": city_b,
                    "pois": [{"id": p.id, "name": p.name, "city": p.city, "duration": p.duration or 2} for p in default_pois],
                    "route": f"{city_a} → " + " → ".join([p.name for p in default_pois]) + f" → {city_b}",
                    "drive_time": 120,
                    "visit_time": sum(p.duration or 2 for p in default_pois),
                    "total_time": sum(p.duration or 2 for p in default_pois) + 2,
                    "description": f"游览{len(default_pois)}个景点"
                })
            
            progress = 40 + int((i + 1) / (len(city_chain) - 1) * 50)
            planning_tasks[task_id]["progress"] = progress
        
        # 构建最终结果
        plan_result = {
            "days": daily_routes,
            "city_chain": city_chain,
            "start_city": start_city,
            "end_city": end_city,
            "total_days": days,
            "total_pois_visited": len(visited_poi_ids),
            "total_pois_selected": len(pois),
            "poi_coords": poi_coords,
            "route_summary": f"共安排 {len(visited_poi_ids)}/{len(pois)} 个景点"
        }
        
        # 存储规划结果
        planning_tasks[task_id]["status"] = "saving"
        planning_tasks[task_id]["progress"] = 90
        
        route = db.query(TripRoute).filter(TripRoute.trip_id == trip_id).first()
        if route:
            route.start_city = start_city
            route.end_city = end_city
            route.total_days = days
            route.route_data = json.dumps(plan_result, ensure_ascii=False)
            route.updated_at = datetime.utcnow()
        else:
            route = TripRoute(
                trip_id=trip_id,
                start_city=start_city,
                end_city=end_city,
                total_days=days,
                route_data=json.dumps(plan_result, ensure_ascii=False)
            )
            db.add(route)

        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if trip:
            trip.updated_at = datetime.utcnow()
        db.commit()

        # 完成
        planning_tasks[task_id]["status"] = "completed"
        planning_tasks[task_id]["progress"] = 100
        planning_tasks[task_id]["result"] = plan_result

    except Exception as e:
        import traceback
        planning_tasks[task_id]["status"] = "failed"
        planning_tasks[task_id]["error"] = str(e)
        print(f"规划失败: {e}\n{traceback.format_exc()}")
    finally:
        db.close()


async def call_llm_json_array(prompt: str, cities: list = None) -> list:
    """调用 LLM 获取 JSON 数组（支持从 reasoning 提取）"""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )

            if response.status_code == 200:
                result = response.json()
                msg = result["choices"][0]["message"]
                content = msg.get("content", "")
                reasoning = msg.get("reasoning_content", "")
                
                # 优先从 content 提取，失败则从 reasoning 提取
                text = content if content else reasoning
                import re
                
                # 找所有 JSON 数组
                all_arrays = re.findall(r'\["[^"]+?"(?:\s*,\s*"[^"]+?")*\]', text)
                for arr_str in all_arrays:
                    arr = json.loads(arr_str)
                    # 过滤示例格式（包含"城市"字样）
                    if any("城市" in c for c in arr):
                        continue
                    # 如果提供了 cities 列表，验证所有城市都在列表中
                    if cities and all(c in cities for c in arr):
                        return arr
                    elif not cities:
                        return arr
                
    except Exception as e:
        print(f"LLM call failed: {e}")
    
    return None


async def call_llm_json_obj(prompt: str, candidate_ids: list = None) -> dict:
    """调用 LLM 获取 JSON 对象（支持从 reasoning 提取）"""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )

            if response.status_code == 200:
                result = response.json()
                msg = result["choices"][0]["message"]
                content = msg.get("content", "")
                reasoning = msg.get("reasoning_content", "")
                
                text = content if content else reasoning
                import re
                
                # 方法1: 提取 ID 数组
                array_match = re.search(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', text)
                if array_match:
                    selected_ids = json.loads(array_match.group())
                    if candidate_ids:
                        selected_ids = [i for i in selected_ids if i in candidate_ids]
                    return {"selected_pois": selected_ids}
                
                # 方法2: 提取景点列表（"景点：1, 2, 35"）
                poi_match = re.search(r'景点[：:]\s*(\d+(?:\s*[，,]\s*\d+)*)', text)
                if poi_match:
                    selected_ids = [int(x) for x in re.findall(r'\d+', poi_match.group(1))]
                    if candidate_ids:
                        selected_ids = [i for i in selected_ids if i in candidate_ids]
                    return {"selected_pois": selected_ids}
                
                # 方法3: 完整 JSON 对象
                obj_match = re.search(r'\{[\s\S]*"selected_pois"[\s\S]*?\[[\s\S]*?\][\s\S]*?\}', text)
                if obj_match:
                    parsed = json.loads(obj_match.group())
                    return parsed
                
    except Exception as e:
        print(f"LLM call failed: {e}")
    
    return None
async def call_llm_simple(prompt: str) -> list:
    """调用 LLM 获取 JSON 数组"""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                if content:
                    # 提取 JSON 数组
                    import re
                    json_match = re.search(r'\[[\s\S]*?\]', content)
                    if json_match:
                        return json.loads(json_match.group())
    except Exception as e:
        print(f"LLM call failed: {e}")
    
    return None


async def call_llm_json(prompt: str) -> dict:
    """调用 LLM 获取 JSON 对象"""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                if content:
                    # 提取 JSON 对象
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        return json.loads(json_match.group())
    except Exception as e:
        print(f"LLM call failed: {e}")
    
    return None


# ========== 行程管理 ==========

@router.get("")
def list_user_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """获取当前用户加入的所有行程"""
    # 查找用户加入的所有行程
    user_trips = db.query(TripMember).filter(TripMember.user_id == current_user.id).all()
    trip_ids = [ut.trip_id for ut in user_trips]
    
    if not trip_ids:
        return []
    
    # 获取行程详情
    trips = db.query(Trip).filter(Trip.trip_id.in_(trip_ids)).all()
    
    result = []
    for trip in trips:
        # 统计成员数和景点数
        member_count = db.query(TripMember).filter(TripMember.trip_id == trip.trip_id).count()
        poi_count = db.query(TripPOI).filter(TripPOI.trip_id == trip.trip_id).count()
        
        result.append({
            "trip_id": trip.trip_id,
            "share_code": trip.share_code,
            "name": trip.name,
            "created_at": trip.created_at,
            "updated_at": trip.updated_at,
            "member_count": member_count,
            "poi_count": poi_count,
        })
    
    # 按更新时间倒序排列
    result.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return result


@router.post("")
def create_trip(
    name: str = Form(default="未命名行程"),
    nickname: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """创建新行程，创建者自动成为第一个成员（需要登录）"""
    trip_id = str(uuid.uuid4())
    share_code = generate_share_code()

    # 确保分享码唯一
    while db.query(Trip).filter(Trip.share_code == share_code).first():
        share_code = generate_share_code()

    trip = Trip(trip_id=trip_id, share_code=share_code, name=name)
    db.add(trip)

    # 创建者自动成为第一个成员（关联用户ID）
    member = TripMember(
        trip_id=trip_id, 
        nickname=current_user.nickname or current_user.username,
        user_id=current_user.id
    )
    db.add(member)

    db.commit()
    db.refresh(trip)

    # 返回完整行程详情
    return {
        "trip_id": trip.trip_id,
        "share_code": trip.share_code,
        "name": trip.name,
        "created_at": trip.created_at,
        "pois": [],
        "members": [{"nickname": member.nickname, "joined_at": member.joined_at}],
    }


@router.get("/{trip_id}")
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    """获取行程详情"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    
    # 获取景点列表
    trip_pois = db.query(TripPOI).filter(TripPOI.trip_id == trip_id).order_by(TripPOI.day_number, TripPOI.order_index).all()
    
    # 获取 POI 详情
    poi_ids = [tp.poi_id for tp in trip_pois]
    pois = db.query(POI).filter(POI.id.in_(poi_ids)).all() if poi_ids else []
    poi_map = {p.id: p for p in pois}
    
    # 组装数据
    poi_list = []
    for tp in trip_pois:
        poi = poi_map.get(tp.poi_id)
        if poi:
            poi_dict = poi_to_dict(poi)
            poi_dict.update({
                "day_number": tp.day_number,
                "order_index": tp.order_index,
                "notes": tp.notes,
                "added_by": tp.added_by,
            })
            poi_list.append(poi_dict)
    
    # 获取成员
    members = db.query(TripMember).filter(TripMember.trip_id == trip_id).all()
    
    return {
        "trip_id": trip.trip_id,
        "share_code": trip.share_code,
        "name": trip.name,
        "created_at": trip.created_at,
        "updated_at": trip.updated_at,
        "pois": poi_list,
        "members": [{"nickname": m.nickname, "joined_at": m.joined_at} for m in members],
    }


@router.get("/code/{share_code}")
def get_trip_by_code(share_code: str, db: Session = Depends(get_db)):
    """通过分享码获取行程"""
    trip = db.query(Trip).filter(Trip.share_code == share_code.upper()).first()
    if not trip:
        raise HTTPException(status_code=404, detail="分享码无效")
    
    return {"trip_id": trip.trip_id, "name": trip.name}


@router.patch("/{trip_id}")
def update_trip(trip_id: str, name: Optional[str] = None, db: Session = Depends(get_db)):
    """更新行程名称"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    
    if name:
        trip.name = name
        trip.updated_at = datetime.utcnow()
        db.commit()
    
    return {"trip_id": trip.trip_id, "name": trip.name}


# ========== 景点管理 ==========

@router.post("/{trip_id}/pois")
def add_poi_to_trip(
    trip_id: str,
    poi_id: int,
    day_number: int = 1,
    notes: str = "",
    nickname: str = "匿名",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """添加景点到行程（需要登录）"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    
    poi = db.query(POI).filter(POI.id == poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="景点不存在")
    
    # 检查是否已存在
    existing = db.query(TripPOI).filter(and_(TripPOI.trip_id == trip_id, TripPOI.poi_id == poi_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="景点已在行程中")
    
    # 获取当前最大顺序
    max_order = db.query(TripPOI).filter(and_(TripPOI.trip_id == trip_id, TripPOI.day_number == day_number)).count()
    
    trip_poi = TripPOI(
        trip_id=trip_id,
        poi_id=poi_id,
        day_number=day_number,
        order_index=max_order,
        notes=notes,
        added_by=current_user.nickname or current_user.username,
    )
    db.add(trip_poi)
    
    # 更新行程时间
    trip.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "添加成功", "poi_id": poi_id}


@router.delete("/{trip_id}/pois/{poi_id}")
def remove_poi_from_trip(trip_id: str, poi_id: int, db: Session = Depends(get_db)):
    """从行程移除景点"""
    trip_poi = db.query(TripPOI).filter(and_(TripPOI.trip_id == trip_id, TripPOI.poi_id == poi_id)).first()
    if not trip_poi:
        raise HTTPException(status_code=404, detail="景点不在行程中")
    
    db.delete(trip_poi)
    
    # 更新行程时间
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if trip:
        trip.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "移除成功"}


@router.patch("/{trip_id}/pois/{poi_id}")
def update_trip_poi(
    trip_id: str,
    poi_id: int,
    day_number: Optional[int] = None,
    order_index: Optional[int] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """更新行程景点信息（日期、顺序、备注）"""
    trip_poi = db.query(TripPOI).filter(and_(TripPOI.trip_id == trip_id, TripPOI.poi_id == poi_id)).first()
    if not trip_poi:
        raise HTTPException(status_code=404, detail="景点不在行程中")
    
    if day_number is not None:
        trip_poi.day_number = day_number
    if order_index is not None:
        trip_poi.order_index = order_index
    if notes is not None:
        trip_poi.notes = notes
    
    # 更新行程时间
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if trip:
        trip.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "更新成功"}


# ========== 成员管理 ==========

@router.post("/{trip_id}/members")
def join_trip(
    trip_id: str, 
    nickname: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """加入行程（需要登录）"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    
    # 使用当前用户的昵称
    user_nickname = current_user.nickname or current_user.username
    
    # 检查用户是否已通过 user_id 加入
    existing_by_user = db.query(TripMember).filter(
        and_(TripMember.trip_id == trip_id, TripMember.user_id == current_user.id)
    ).first()
    if existing_by_user:
        return {"message": "已加入该行程", "nickname": existing_by_user.nickname}
    
    # 检查昵称是否已被占用
    existing = db.query(TripMember).filter(
        and_(TripMember.trip_id == trip_id, TripMember.nickname == user_nickname)
    ).first()
    if existing:
        # 如果昵称被占用但不是当前用户，创建一个唯一昵称
        user_nickname = f"{user_nickname}_{current_user.id}"
    
    member = TripMember(
        trip_id=trip_id, 
        nickname=user_nickname,
        user_id=current_user.id
    )
    db.add(member)
    db.commit()
    
    return {"message": "加入成功", "nickname": user_nickname}


@router.get("/{trip_id}/members")
def get_trip_members(trip_id: str, db: Session = Depends(get_db)):
    """获取行程成员列表"""
    members = db.query(TripMember).filter(TripMember.trip_id == trip_id).all()
    return [{"nickname": m.nickname, "joined_at": m.joined_at} for m in members]


# ========== 路线规划 ==========

import math

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
    """用 Haversine 公式计算两点直线距离，估算驾车时间"""
    R = 6371  # 地球半径（公里）
    
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance_km = R * c
    
    # 直线距离 × 1.3 ≈ 驾车距离
    driving_distance = distance_km * 1.3
    
    # 山区/城市平均时速 50km/h
    duration_hours = driving_distance / 50
    duration_seconds = int(duration_hours * 3600)
    
    return {
        "distance": int(driving_distance * 1000),  # 米
        "duration": duration_seconds  # 秒
    }


async def get_driving_distance(origin: str, destination: str) -> dict:
    """调用高德驾车API获取真实距离和时长"""
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": AMAP_KEY,
        "origin": origin,
        "destination": destination,
        "extensions": "base"
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            data = response.json()

            if data.get("status") == "1" and data.get("route"):
                path = data["route"]["paths"][0]
                result = {
                    "distance": int(path.get("distance", 0)),
                    "duration": int(path.get("duration", 0))
                }
                print(f"高德API: {origin[:15]} -> {destination[:15]}: {result['distance']//1000}公里, {result['duration']//60}分钟")
                return result
            else:
                print(f"高德API失败: status={data.get('status')}, info={data.get('info')}")
                return estimate_distance(origin, destination)
    except Exception as e:
        print(f"高德API异常: {e}")
        return estimate_distance(origin, destination)


def estimate_distance(origin: str, destination: str) -> dict:
    """备用：用 Haversine 公式估算"""
    try:
        o_lng, o_lat = map(float, origin.split(","))
        d_lng, d_lat = map(float, destination.split(","))
        return haversine_distance(o_lat, o_lng, d_lat, d_lng)
    except:
        return {"distance": 0, "duration": 0}


async def get_city_location(city_name: str) -> tuple:
    """获取城市坐标"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": AMAP_KEY,
        "address": city_name
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        data = response.json()

        if data.get("status") == "1" and data.get("geocodes"):
            location = data["geocodes"][0].get("location", "")
            if location:
                lng, lat = location.split(",")
                return (float(lng), float(lat))
    return None


async def call_llm_plan(pois: list, start_city: str, end_city: str, days: int, distance_matrix: dict, poi_coords: dict) -> dict:
    """调用 LLM 规划路线"""
    if not OPENAI_API_KEY:
        return generate_default_plan(pois, start_city, end_city, days)

    # 构建景点详情
    poi_details = []
    for poi in pois:
        poi_details.append({
            "name": poi['name'],
            "city": poi['city'],
            "visit_hours": poi.get('duration', 2)
        })

    # 构建简化的距离信息（只保留关键距离）
    distance_text = ""
    # 按距离排序，只保留最近的几个
    sorted_distances = sorted(
        [(k, v) for k, v in distance_matrix.items() if v.get('duration', 0) > 0],
        key=lambda x: x[1].get('duration', float('inf'))
    )[:30]  # 只保留30个最近的距离
    
    for (p1, p2), info in sorted_distances:
        distance_text += f"{p1}→{p2}: {info['duration']//60}分钟\n"

    prompt = f"""你是自驾行程规划专家。根据景点距离规划最优路线。

## 规划规则（必须遵守）

1. **可重新排序景点**：不必按原顺序，按距离最优安排
2. **连续性**：前一天住宿地 = 后一天起点
3. **时间控制**：每天游玩+驾车 ≤ 10小时
4. **顺路原则**：选距离近的景点，不走回头路

## 行程信息
- 起点：{start_city}
- 终点：{end_city}
- 天数：{days}天

## 景点（可重排顺序）
{json.dumps([p['name'] + f"({p['city']}, {p['visit_hours']}h)" for p in poi_details], ensure_ascii=False)}

## 距离参考（分钟）
{distance_text}

## 输出JSON格式
{{
  "days": [
    {{
      "day": 1,
      "start_city": "起点城市",
      "pois": [{{"name": "景点名", "visit_hours": 2}}],
      "stay_city": "住宿城市",
      "route": "A → B → C",
      "drive_time": 60,
      "visit_time": 5,
      "total_time": 6,
      "description": "行程描述"
    }}
  ],
  "route_summary": "路线概览"
}}

只输出JSON，无其他文字。"""

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 2000
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                print(f"LLM response: {content[:500]}")  # 调试日志
                
                # 提取 JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                # 清理内容
                content = content.strip()
                if content.startswith("{") and content.endswith("}"):
                    pass  # 已经是有效 JSON
                else:
                    # 尝试找到 JSON 对象
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        content = content[start:end]
                
                plan = json.loads(content)
                
                if "days" not in plan:
                    plan = {"days": plan.get("days", []), "route_summary": ""}
                
                return plan
            else:
                print(f"LLM API status: {response.status_code}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Content: {content[:500] if 'content' in dir() else 'N/A'}")
    except Exception as e:
        print(f"LLM API error: {e}")

    return generate_default_plan(pois, start_city, end_city, days)


def generate_default_plan(pois: list, start_city: str, end_city: str, days: int) -> dict:
    """生成默认规划（当 LLM 不可用时）"""
    result = {
        "days": [],
        "route_summary": f"{start_city}出发，最终到达{end_city}",
        "total_distance": "未知",
        "suggestions": "建议根据实际情况调整行程"
    }

    if not pois:
        return result

    # 按城市分组
    city_pois = {}
    for poi in pois:
        city = poi.get("city", "未知")
        if city not in city_pois:
            city_pois[city] = []
        city_pois[city].append(poi)

    # 简单分配：每天约2-3个景点
    pois_per_day = max(1, len(pois) // days)

    day_plans = []
    current_pois = []
    current_city = start_city
    day_num = 1

    for poi in pois:
        current_pois.append({"name": poi["name"], "visit_hours": poi.get("duration", 2)})
        
        if len(current_pois) >= pois_per_day and day_num <= days:
            stay_city = poi.get("city", current_city)
            day_plans.append({
                "day": day_num,
                "start_city": current_city,
                "pois": current_pois.copy(),
                "stay_city": stay_city,
                "route": f"{current_city} → " + " → ".join([p["name"] for p in current_pois]) + f" → {stay_city}",
                "drive_time": 120,  # 默认2小时驾车
                "visit_time": sum(p["visit_hours"] for p in current_pois),
                "total_time": sum(p["visit_hours"] for p in current_pois) + 2,
                "description": f"游览{len(current_pois)}个景点，住宿{stay_city}"
            })
            current_city = stay_city
            current_pois = []
            day_num += 1

    if current_pois and day_num <= days:
        day_plans.append({
            "day": day_num,
            "start_city": current_city,
            "pois": current_pois,
            "stay_city": end_city,
            "route": f"{current_city} → " + " → ".join([p["name"] for p in current_pois]) + f" → {end_city}",
            "drive_time": 120,  # 默认2小时驾车
            "visit_time": sum(p["visit_hours"] for p in current_pois),
            "total_time": sum(p["visit_hours"] for p in current_pois) + 2,
            "description": f"游览{len(current_pois)}个景点，抵达终点{end_city}"
        })

    result["days"] = day_plans
    return result


@router.post("/{trip_id}/plan")
async def plan_trip_route(
    trip_id: str,
    start_city: str = Form(...),
    end_city: str = Form(...),
    days: int = Form(default=3),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """规划行程路线（异步后台执行）"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    # 检查是否有景点
    trip_pois = db.query(TripPOI).filter(TripPOI.trip_id == trip_id).count()
    if trip_pois == 0:
        raise HTTPException(status_code=400, detail="行程中没有景点，请先添加景点")

    # 创建任务
    task_id = str(uuid.uuid4())
    planning_tasks[task_id] = {
        "trip_id": trip_id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat()
    }

    # 启动后台任务
    background_tasks.add_task(do_plan_trip, trip_id, start_city, end_city, days, task_id)

    return {
        "message": "规划任务已启动",
        "task_id": task_id,
        "status_url": f"/api/trips/{trip_id}/plan/status/{task_id}"
    }


@router.get("/{trip_id}/plan/status/{task_id}")
def get_plan_status(trip_id: str, task_id: str):
    """获取规划任务状态"""
    if task_id not in planning_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = planning_tasks[task_id]
    
    # 状态映射
    status_map = {
        "pending": "准备中",
        "geocoding": "获取坐标",
        "distance": "计算距离",
        "calculating": "计算中",
        "planning": "AI规划中",
        "saving": "保存结果",
        "completed": "已完成",
        "failed": "失败"
    }

    return {
        "task_id": task_id,
        "status": task["status"],
        "status_text": status_map.get(task["status"], task["status"]),
        "progress": task["progress"],
        "message": task.get("message", ""),
        "error": task.get("error"),
        "result": task.get("result") if task["status"] == "completed" else None
    }


@router.get("/{trip_id}/route")
def get_trip_route(trip_id: str, db: Session = Depends(get_db)):
    """获取行程路线"""
    route = db.query(TripRoute).filter(TripRoute.trip_id == trip_id).first()
    if not route:
        return {"route": None}

    return {
        "route": {
            "start_city": route.start_city,
            "end_city": route.end_city,
            "total_days": route.total_days,
            "data": json.loads(route.route_data) if route.route_data else None,
            "updated_at": route.updated_at
        }
    }


@router.post("/{trip_id}/export")
async def export_to_feishu(trip_id: str, db: Session = Depends(get_db)):
    """导出到飞书文档"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    route = db.query(TripRoute).filter(TripRoute.trip_id == trip_id).first()
    if not route or not route.route_data:
        raise HTTPException(status_code=400, detail="请先规划行程路线")

    # 获取飞书配置
    feishu_app_id = os.getenv("FEISHU_APP_ID", "")
    feishu_app_secret = os.getenv("FEISHU_APP_SECRET", "")

    if not feishu_app_id or not feishu_app_secret:
        # 返回模拟链接
        return {
            "message": "飞书未配置，返回预览",
            "url": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/trip/{trip_id}",
            "preview": json.loads(route.route_data)
        }

    try:
        # 获取飞书 access token
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": feishu_app_id,
                    "app_secret": feishu_app_secret
                }
            )

            if token_response.status_code != 200:
                raise Exception("获取飞书token失败")

            token_data = token_response.json()
            if token_data.get("code") != 0:
                raise Exception(token_data.get("msg", "获取token失败"))

            access_token = token_data["tenant_access_token"]

            # 创建文档
            route_data = json.loads(route.route_data)
            content = f"# {trip.name}\n\n"
            content += f"起点：{route.start_city}\n"
            content += f"终点：{route.end_city}\n"
            content += f"总天数：{route.total_days}天\n\n"

            for day in route_data.get("days", []):
                content += f"## 第{day['day']}天\n"
                content += f"路线：{day.get('route', '')}\n"
                content += f"景点：{', '.join(day.get('pois', []))}\n"
                content += f"说明：{day.get('description', '')}\n\n"

            # 创建飞书文档
            doc_response = await client.post(
                "https://open.feishu.cn/open-apis/docx/v1/documents",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "title": trip.name,
                    "content": content
                }
            )

            if doc_response.status_code == 200:
                doc_data = doc_response.json()
                if doc_data.get("code") == 0:
                    return {
                        "message": "导出成功",
                        "url": f"https://feishu.cn/docx/{doc_data['data']['document']['document_id']}"
                    }
    except Exception as e:
        print(f"Feishu API error: {e}")

    # 返回预览
    return {
        "message": "导出失败，返回预览",
        "url": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/trip/{trip_id}",
        "preview": json.loads(route.route_data)
    }
