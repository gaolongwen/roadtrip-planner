from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    nickname = Column(String(50), comment="昵称")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="关联用户ID")
    joined_at = Column(DateTime, default=datetime.utcnow, comment="加入时间")


class TripRoute(Base):
    __tablename__ = "trip_routes"

    trip_id = Column(String(36), primary_key=True, comment="行程ID")
    start_city = Column(String(100), comment="起点城市")
    end_city = Column(String(100), comment="终点城市")
    total_days = Column(Integer, comment="总天数")
    route_data = Column(Text, comment="JSON字符串，存储每日行程")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class CityCoordinate(Base):
    """城市坐标表（市人民政府位置）"""
    __tablename__ = "city_coordinates"

    city = Column(String(100), primary_key=True, comment="城市名称")
    province = Column(String(50), comment="省份")
    latitude = Column(Float, nullable=False, comment="纬度")
    longitude = Column(Float, nullable=False, comment="经度")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class POICityDistance(Base):
    """景点到所属城市/县城的距离"""
    __tablename__ = "poi_city_distances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    poi_id = Column(Integer, ForeignKey("pois.id"), nullable=False, index=True, comment="景点ID")
    city = Column(String(50), nullable=False, comment="地级市名称")
    district = Column(String(50), comment="县/区名称")
    city_distance = Column(Integer, comment="到地级市中心距离（米）")
    city_duration = Column(Integer, comment="到地级市中心驾车时长（秒）")
    district_distance = Column(Integer, comment="到县/区中心距离（米）")
    district_duration = Column(Integer, comment="到县/区中心驾车时长（秒）")
    source = Column(String(20), default="amap", comment="数据来源: amap/estimate")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class POIDistance(Base):
    """景点间距离缓存表"""
    __tablename__ = "poi_distances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    poi1_id = Column(Integer, nullable=False, index=True, comment="景点1 ID")
    poi2_id = Column(Integer, nullable=False, index=True, comment="景点2 ID")
    distance = Column(Integer, comment="驾车距离（米）")
    duration = Column(Integer, comment="驾车时长（秒）")
    source = Column(String(20), default="amap", comment="数据来源: amap/estimate")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    __table_args__ = (
        # 唯一约束：两点之间只存一条记录（双向距离相同）
        # MySQL: {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
