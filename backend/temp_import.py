#!/usr/bin/env python3
"""临时导入脚本 - 从飞书获取的数据"""
import json
import sqlite3
import re
from datetime import datetime

# 数据处理函数
def clean_city(city):
    if not city:
        return None
    city = re.sub(r'[（(][^)）]*[)）]', '', city)
    return city.strip() if city.strip() else None

def infer_category(name, desc, tips):
    text = f"{name or ''} {desc or ''} {tips or ''}".lower()
    if any(k in text for k in ['石窟','佛','寺','庙','塔','道教','教堂','古建','古村','古镇','古堡','关帝','书院','衙门','祠','殿','陵','墓','遗址','古城']):
        return '人文'
    elif any(k in text for k in ['峡谷','瀑布','山','湖','河','地质','自然','溶洞','冰洞','温泉','森林','湿地','草原']):
        return '自然'
    return '人文'

def infer_tags(name, desc, tips):
    tags, text = [], f"{name or ''} {desc or ''} {tips or ''}"
    mapping = {
        '古建': ['古建','建筑','木构','唐代','宋代','明代','清代','辽代','金代','元代','北魏'],
        '石窟': ['石窟','摩崖','造像','石刻'],
        '佛教': ['佛','寺','塔','禅','菩萨'],
        '道教': ['道教','道观','老君'],
        '长城': ['长城','关隘','烽火台'],
        '古村': ['古镇','古村','村落','民居','窑洞'],
        '自然': ['峡谷','瀑布','山','湖','河','地质','溶洞'],
        '世界遗产': ['世界遗产','世遗','UNESCO'],
        '博物馆': ['博物馆','纪念馆'],
        '教堂': ['教堂','天主','基督'],
        '工业遗产': ['矿山','工厂','矿井','电厂'],
        '挂壁公路': ['挂壁','公路'],
        '彩塑': ['彩塑','壁画','悬塑'],
        '古墓': ['古墓','陵墓','墓葬'],
    }
    for tag, kws in mapping.items():
        if any(k in text for k in kws):
            tags.append(tag)
    return tags[:3] or ['景点']

def get_province(city):
    if not city: return '山西'
    henan = ['洛阳','安阳','新乡','焦作','三门峡','南阳','郑州','信阳','济源','永城','平顶山','鹤壁','开封','许昌','驻马店','商丘','漯河','周口']
    return '河南' if any(c in clean_city(city) for c in henan) else '山西'

# 完整的 185 条数据将在运行时通过标准输入传入
# 现在先创建数据库并清空表
print("=" * 60)
print("准备导入数据")
print("=" * 60)

# 连接数据库
conn = sqlite3.connect('data/roadtrip.db')
cursor = conn.cursor()

# 清空现有数据
cursor.execute("DELETE FROM pois")
conn.commit()
print("✓ 已清空现有数据")

# 检查表结构
cursor.execute("SELECT COUNT(*) FROM pois")
print(f"✓ 当前记录数: {cursor.fetchone()[0]}")

conn.close()
print("\n数据库已准备好，等待数据导入...")
print("请通过标准输入传入 JSON 数据")
