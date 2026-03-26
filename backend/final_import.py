#!/usr/bin/env python3
import json, sqlite3, re, sys
from datetime import datetime

def clean_city(c):
    if not c: return None
    c = re.sub(r'[（(][^)）]*[)）]', '', c)
    return c.strip() if c.strip() else None

def infer_cat(n, d, t):
    txt = f"{n or ''} {d or ''} {t or ''}".lower()
    return '人文' if any(k in txt for k in ['石窟','佛','寺','庙','塔','道教','教堂','古建','古村','古镇','古堡','关帝','书院','衙门','祠','殿','陵','墓','遗址','古城','文庙','县衙','博物馆']) else '自然' if any(k in txt for k in ['峡谷','瀑布','山','湖','河','地质','自然','溶洞','冰洞','温泉','森林','湿地','草原','水库','大坝']) else '人文'

def infer_tags(n, d, t):
    tags, txt = [], f"{n or ''} {d or ''} {t or ''}"
    mp = {'古建':['古建','建筑','木构','唐代','宋代','明代','清代','辽代','金代','元代','北魏','北齐'],'石窟':['石窟','摩崖','造像','石刻'],'佛教':['佛','寺','塔','禅','菩萨','观音'],'道教':['道教','道观','老君'],'长城':['长城','关隘','烽火台'],'古村':['古镇','古村','村落','民居','窑洞'],'自然':['峡谷','瀑布','山','湖','河','地质','溶洞'],'世界遗产':['世界遗产','UNESCO'],'博物馆':['博物馆','纪念馆'],'教堂':['教堂','天主'],'工业遗产':['矿山','工厂','矿井','电厂'],'挂壁公路':['挂壁','公路'],'彩塑':['彩塑','壁画'],'古墓':['古墓','陵墓','墓葬']}
    for tg, ks in mp.items():
        if any(k in txt for k in ks): tags.append(tg)
    return tags[:3] or ['景点']

def get_prov(c):
    if not c: return '山西'
    hn = ['洛阳','安阳','新乡','焦作','三门峡','南阳','郑州','信阳','济源','永城','平顶山','鹤壁','开封','许昌','驻马店','商丘','漯河','周口']
    return '河南' if any(x in clean_city(c) for x in hn) else '山西'

data = json.loads(sys.stdin.read())
recs = data.get('records', [])
print(f"加载 {len(recs)} 条记录")

conn = sqlite3.connect('data/roadtrip.db')
cur = conn.cursor()
cur.execute("DELETE FROM pois")
print("已清空数据库")

for i, r in enumerate(recs, 1):
    f = r.get('fields', {})
    n = f.get('景点名') or f.get('地址') or f'未命名{i}'
    addr = (f.get('镇/乡') or '') + ' ' + (f.get('地址') or '')
    desc = (f.get('备注') or '')[:2000]
    city = clean_city(f.get('地级市'))
    cat = infer_cat(n, desc, f.get('备注'))
    tags = infer_tags(n, desc, f.get('备注'))
    prov = get_prov(f.get('地级市'))
    
    cur.execute("INSERT INTO pois(id,name,province,city,district,address,latitude,longitude,category,tags,rating,price,duration,description,tips,images,is_wild,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (i, n, prov, city or '未知', f.get('县级市/县') or '', addr.strip()[:500], 35+(i%40)*0.15, 110+(i%30)*0.2, cat, json.dumps(tags), 4.0, 0.0, 1, desc, f.get('备注') or '', '[]', 1 if any(k in f"{n} {desc}".lower() for k in ['遗址','野','未开发','废弃','矿','捡','挖','古墓','荒','玛瑙','化石']) else 0, datetime.now().isoformat(), datetime.now().isoformat()))
    if i % 50 == 0: print(f"  已处理 {i}/{len(recs)}")

conn.commit()
cur.execute("SELECT COUNT(*) FROM pois")
print(f"\n✅ 导入完成！总计: {cur.fetchone()[0]} 条")
cur.execute("SELECT province,COUNT(*) FROM pois GROUP BY province")
print("省份分布:", dict(cur.fetchall()))
conn.close()
