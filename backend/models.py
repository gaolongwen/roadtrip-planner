from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
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
    is_wild = Column(Boolean, default=False, comment="是否野生景点")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
