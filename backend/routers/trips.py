import uuid
import random
import string
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db
from models import Trip, TripPOI, TripMember, POI

router = APIRouter(prefix="/api/trips", tags=["trips"])


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


# ========== 行程管理 ==========

@router.post("")
def create_trip(name: str = "未命名行程", db: Session = Depends(get_db)):
    """创建新行程"""
    trip_id = str(uuid.uuid4())
    share_code = generate_share_code()
    
    # 确保分享码唯一
    while db.query(Trip).filter(Trip.share_code == share_code).first():
        share_code = generate_share_code()
    
    trip = Trip(trip_id=trip_id, share_code=share_code, name=name)
    db.add(trip)
    db.commit()
    db.refresh(trip)
    
    return {
        "trip_id": trip.trip_id,
        "share_code": trip.share_code,
        "name": trip.name,
        "created_at": trip.created_at,
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
    db: Session = Depends(get_db)
):
    """添加景点到行程"""
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
        added_by=nickname,
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
def join_trip(trip_id: str, nickname: str, db: Session = Depends(get_db)):
    """加入行程"""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    
    # 检查昵称是否已存在
    existing = db.query(TripMember).filter(and_(TripMember.trip_id == trip_id, TripMember.nickname == nickname)).first()
    if existing:
        return {"message": "昵称已存在，自动加入", "nickname": nickname}
    
    member = TripMember(trip_id=trip_id, nickname=nickname)
    db.add(member)
    db.commit()
    
    return {"message": "加入成功", "nickname": nickname}


@router.get("/{trip_id}/members")
def get_trip_members(trip_id: str, db: Session = Depends(get_db)):
    """获取行程成员列表"""
    members = db.query(TripMember).filter(TripMember.trip_id == trip_id).all()
    return [{"nickname": m.nickname, "joined_at": m.joined_at} for m in members]
