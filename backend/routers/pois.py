import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db
from models import POI
from schemas import POICreate, POIUpdate, POIResponse

router = APIRouter(prefix="/api/pois", tags=["pois"])


def poi_to_response(poi: POI) -> dict:
    """Convert POI model to response dict with parsed JSON fields"""
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
        "tags": poi.tags.split(",") if poi.tags and not poi.tags.startswith("[") else (json.loads(poi.tags) if poi.tags else []),
        "rating": poi.rating,
        "price": poi.price,
        "duration": poi.duration,
        "description": poi.description,
        "tips": poi.tips,
        "images": json.loads(poi.images) if poi.images else [],
        "reference_url": poi.reference_url,
        "is_wild": poi.is_wild,
        "created_at": poi.created_at,
        "updated_at": poi.updated_at,
    }


@router.get("", response_model=List[POIResponse])
def get_pois(
    province: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    category: Optional[str] = None,
    categories: Optional[str] = Query(None, description="多个类别，逗号分隔，如: 人文,自然"),
    is_wild: Optional[bool] = None,
    wild_filter: Optional[str] = Query(None, description="野生筛选: 正规,野生 或 all"),
    tags: Optional[str] = Query(None, description="标签筛选，逗号分隔"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """获取景点列表，支持多条件筛选"""
    query = db.query(POI)

    filters = []
    if province:
        filters.append(POI.province == province)
    if city:
        filters.append(POI.city == city)
    if district:
        filters.append(POI.district == district)
    
    # 多类别筛选
    if categories:
        category_list = [c.strip() for c in categories.split(",")]
        filters.append(POI.category.in_(category_list))
    elif category:
        filters.append(POI.category == category)
    
    # 野生景点筛选（支持多选）
    if wild_filter:
        wild_values = [v.strip() for v in wild_filter.split(",")]
        if "正规" in wild_values and "野生" not in wild_values:
            filters.append(POI.is_wild == False)
        elif "野生" in wild_values and "正规" not in wild_values:
            filters.append(POI.is_wild == True)
        # 如果两个都有，不添加筛选条件（返回全部）
    elif is_wild is not None:
        filters.append(POI.is_wild == is_wild)
    
    if min_rating is not None:
        filters.append(POI.rating >= min_rating)
    
    # 标签筛选（JSON 字符串模糊匹配）
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            filters.append(POI.tags.like(f'%"{tag}"%'))

    if filters:
        query = query.filter(and_(*filters))

    pois = query.offset(skip).limit(limit).all()
    return [poi_to_response(p) for p in pois]


@router.get("/bbox", response_model=List[POIResponse])
def get_pois_by_bbox(
    min_lat: float = Query(..., ge=-90, le=90, description="最小纬度"),
    max_lat: float = Query(..., ge=-90, le=90, description="最大纬度"),
    min_lng: float = Query(..., ge=-180, le=180, description="最小经度"),
    max_lng: float = Query(..., ge=-180, le=180, description="最大经度"),
    categories: Optional[str] = Query(None, description="多个类别，逗号分隔"),
    wild_filter: Optional[str] = Query(None, description="野生筛选: 正规,野生"),
    tags: Optional[str] = Query(None, description="标签筛选，逗号分隔"),
    db: Session = Depends(get_db),
):
    """获取地图范围内（bounding box）的景点"""
    filters = [
        POI.latitude >= min_lat,
        POI.latitude <= max_lat,
        POI.longitude >= min_lng,
        POI.longitude <= max_lng,
    ]
    
    # 多类别筛选
    if categories:
        category_list = [c.strip() for c in categories.split(",")]
        filters.append(POI.category.in_(category_list))
    
    # 野生景点筛选
    if wild_filter:
        wild_values = [v.strip() for v in wild_filter.split(",")]
        if "正规" in wild_values and "野生" not in wild_values:
            filters.append(POI.is_wild == False)
        elif "野生" in wild_values and "正规" not in wild_values:
            filters.append(POI.is_wild == True)
    
    # 标签筛选
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            filters.append(POI.tags.like(f'%"{tag}"%'))
    
    pois = db.query(POI).filter(and_(*filters)).all()
    return [poi_to_response(p) for p in pois]


@router.get("/{poi_id}", response_model=POIResponse)
def get_poi(poi_id: int, db: Session = Depends(get_db)):
    """获取单个景点详情"""
    poi = db.query(POI).filter(POI.id == poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi_to_response(poi)


@router.post("", response_model=POIResponse, status_code=201)
def create_poi(poi_data: POICreate, db: Session = Depends(get_db)):
    """创建新景点"""
    poi_dict = poi_data.model_dump()
    # Convert list fields to JSON strings
    poi_dict["tags"] = json.dumps(poi_dict.get("tags") or [])
    poi_dict["images"] = json.dumps(poi_dict.get("images") or [])

    poi = POI(**poi_dict)
    db.add(poi)
    db.commit()
    db.refresh(poi)
    return poi_to_response(poi)


@router.put("/{poi_id}", response_model=POIResponse)
def update_poi(poi_id: int, poi_data: POIUpdate, db: Session = Depends(get_db)):
    """更新景点信息"""
    poi = db.query(POI).filter(POI.id == poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")

    update_dict = poi_data.model_dump(exclude_unset=True)
    # Convert list fields to JSON strings if present
    if "tags" in update_dict:
        update_dict["tags"] = json.dumps(update_dict["tags"] or [])
    if "images" in update_dict:
        update_dict["images"] = json.dumps(update_dict["images"] or [])

    for key, value in update_dict.items():
        setattr(poi, key, value)

    db.commit()
    db.refresh(poi)
    return poi_to_response(poi)


@router.delete("/{poi_id}", status_code=204)
def delete_poi(poi_id: int, db: Session = Depends(get_db)):
    """删除景点"""
    poi = db.query(POI).filter(POI.id == poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    db.delete(poi)
    db.commit()
    return None
