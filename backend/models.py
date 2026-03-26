from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from database import Base


class POI(Base):
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="景点名称")
    province = Column(String(50), comment="省份")
    city = Column(String(50), comment="城市")
    district = Column(String(50), comment="区县")
    address = Column(String(500), comment="详细地址")
    latitude = Column(Float, nullable=False, comment="纬度")
    longitude = Column(Float, nullable=False, comment="经度")
    category = Column(String(50), comment="类型：自然/人文/娱乐等")
    tags = Column(String(1000), default="[]", comment="JSON数组字符串")
    rating = Column(Float, default=0.0, comment="评分1-5")
    price = Column(Float, default=0.0, comment="门票价格")
    duration = Column(Integer, default=1, comment="建议游玩时长，小时")
    description = Column(String(2000), comment="描述")
    tips = Column(String(1000), comment="游玩贴士")
    images = Column(String(5000), default="[]", comment="图片URL，JSON数组字符串")
    reference_url = Column(String(500), comment="参考链接")
    is_wild = Column(Boolean, default=False, comment="是否野生景点")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class Trip(Base):
    __tablename__ = "trips"

    trip_id = Column(String(36), primary_key=True, comment="行程UUID")
    share_code = Column(String(8), unique=True, nullable=False, comment="分享码")
    name = Column(String(255), default="未命名行程", comment="行程名称")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class TripPOI(Base):
    __tablename__ = "trip_pois"

    trip_id = Column(String(36), primary_key=True, comment="行程ID")
    poi_id = Column(Integer, primary_key=True, comment="景点ID")
    day_number = Column(Integer, default=1, comment="第几天")
    order_index = Column(Integer, default=0, comment="顺序")
    notes = Column(Text, comment="备注")
    added_by = Column(String(100), comment="添加者昵称")
    added_at = Column(DateTime, default=datetime.utcnow, comment="添加时间")


class TripMember(Base):
    __tablename__ = "trip_members"

    trip_id = Column(String(36), primary_key=True, comment="行程ID")
    nickname = Column(String(100), primary_key=True, comment="昵称")
    joined_at = Column(DateTime, default=datetime.utcnow, comment="加入时间")
