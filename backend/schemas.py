from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class POIBase(BaseModel):
    name: str = Field(..., description="景点名称")
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    rating: Optional[float] = Field(default=0.0, ge=0, le=5)
    price: Optional[float] = Field(default=0.0, ge=0)
    duration: Optional[int] = Field(default=1, ge=1, description="建议游玩时长，小时")
    description: Optional[str] = None
    tips: Optional[str] = None
    images: Optional[List[str]] = None
    is_wild: Optional[bool] = False


class POICreate(POIBase):
    pass


class POIUpdate(BaseModel):
    name: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    price: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    tips: Optional[str] = None
    images: Optional[List[str]] = None
    is_wild: Optional[bool] = None


class POIResponse(POIBase):
    id: int
    tags: List[str] = []
    images: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
