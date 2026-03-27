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
    """后台执行行程规划"""
    from database import SessionLocal
    
    planning_tasks[task_id]["status"] = "calculating"
    planning_tasks[task_id]["progress"] = 20
    
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

        # 转换为字典格式
        poi_list = []
        for poi in pois:
            poi_list.append({
                "id": poi.id,
                "name": poi.name,
                "city": poi.city,
                "latitude": poi.latitude,
                "longitude": poi.longitude,
                "duration": poi.duration or 2
            })

        # 获取起点和终点坐标
        planning_tasks[task_id]["status"] = "geocoding"
        planning_tasks[task_id]["progress"] = 30
        start_loc = await get_city_location(start_city)
        end_loc = await get_city_location(end_city)

        # 构建景点坐标映射
        poi_coords = {p["name"]: {"lng": p["longitude"], "lat": p["latitude"]} for p in poi_list}

        # 并行计算所有距离
        planning_tasks[task_id]["status"] = "distance"
        planning_tasks[task_id]["progress"] = 40
        distance_tasks = []
        distance_keys = []

        if start_loc:
            for poi in poi_list:
                distance_tasks.append(get_driving_distance(
                    f"{start_loc[0]},{start_loc[1]}",
                    f"{poi['longitude']},{poi['latitude']}"
                ))
                distance_keys.append((start_city, poi["name"]))

        for i, poi1 in enumerate(poi_list):
            for j, poi2 in enumerate(poi_list):
                if i < j:
                    distance_tasks.append(get_driving_distance(
                        f"{poi1['longitude']},{poi1['latitude']}",
                        f"{poi2['longitude']},{poi2['latitude']}"
                    ))
                    distance_keys.append((poi1["name"], poi2["name"]))

        if end_loc:
            for poi in poi_list:
                distance_tasks.append(get_driving_distance(
                    f"{poi['longitude']},{poi['latitude']}",
                    f"{end_loc[0]},{end_loc[1]}"
                ))
                distance_keys.append((poi["name"], end_city))

        distance_results = await asyncio.gather(*distance_tasks, return_exceptions=True)

        distance_matrix = {}
        for key, result in zip(distance_keys, distance_results):
            if isinstance(result, Exception):
                distance_matrix[key] = {"distance": 0, "duration": 0}
            else:
                distance_matrix[key] = result
                if key[0] != start_city and key[1] != end_city:
                    distance_matrix[(key[1], key[0])] = result

        # 调用 LLM 规划
        planning_tasks[task_id]["status"] = "planning"
        planning_tasks[task_id]["progress"] = 70
        planning_tasks[task_id]["message"] = "AI 正在规划最佳路线..."
        
        plan_result = await call_llm_plan(poi_list, start_city, end_city, days, distance_matrix, poi_coords)

        # 添加景点坐标信息
        plan_result["poi_coords"] = poi_coords
        plan_result["start_city"] = start_city
        plan_result["end_city"] = end_city
        plan_result["start_coord"] = {"lng": start_loc[0], "lat": start_loc[1]} if start_loc else None
        plan_result["end_coord"] = {"lng": end_loc[0], "lat": end_loc[1]} if end_loc else None

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
        planning_tasks[task_id]["status"] = "failed"
        planning_tasks[task_id]["error"] = str(e)
    finally:
        db.close()


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

async def get_driving_distance(origin: str, destination: str) -> dict:
    """调用高德驾车API获取距离和时长"""
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": AMAP_KEY,
        "origin": origin,
        "destination": destination,
        "extensions": "base"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        data = response.json()

        if data.get("status") == "1" and data.get("route"):
            path = data["route"]["paths"][0]
            return {
                "distance": int(path.get("distance", 0)),
                "duration": int(path.get("duration", 0))
            }
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
                "drive_time": 60,
                "visit_time": sum(p["visit_hours"] for p in current_pois),
                "total_time": sum(p["visit_hours"] for p in current_pois) + 1,
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
            "drive_time": 60,
            "visit_time": sum(p["visit_hours"] for p in current_pois),
            "total_time": sum(p["visit_hours"] for p in current_pois) + 1,
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
