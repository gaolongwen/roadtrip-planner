#!/usr/bin/env python3
"""从百度百科获取景点图片"""

import sqlite3
import requests
import re
import time

# 热门景点列表（有百度百科条目的）
POI_BAIKE_MAP = {
    "云冈石窟": "云冈石窟",
    "晋华宫国家矿山公园": "晋华宫国家矿山公园",
    "应县木塔": "应县木塔",
    "善化寺": "善化寺",
    "华严寺": "华严寺",
    "悬空寺": "悬空寺",
    "雁门关": "雁门关",
    "五台山": "五台山",
    "佛光寺": "佛光寺",
    "南禅寺": "南禅寺",
    "晋祠": "晋祠",
    "平遥古城": "平遥古城",
    "双林寺": "双林寺",
    "镇国寺": "镇国寺",
    "壶口瀑布": "壶口瀑布",
    "广胜寺": "广胜寺",
    "小西天": "小西天",
    "大槐树": "洪洞大槐树",
    "尧庙": "尧庙",
    "鹳雀楼": "鹳雀楼",
    "普救寺": "普救寺",
    "永乐宫": "永乐宫",
    "解州关帝庙": "解州关帝庙",
    "常家庄园": "常家庄园",
    "乔家大院": "乔家大院",
    "王家大院": "王家大院",
    "绵山": "绵山",
    "张壁古堡": "张壁古堡",
    "石膏山": "石膏山",
    "红崖峡谷": "红崖峡谷",
    "太行山大峡谷": "太行山大峡谷",
    "红豆峡": "红豆峡",
    "青龙峡": "青龙峡",
    "八里沟": "八里沟",
    "万仙山": "万仙山",
    "郭亮村": "郭亮村",
    "云台山": "云台山",
    "青天河": "青天河",
    "神农山": "神农山",
    "王屋山": "王屋山",
    "五龙口": "五龙口",
    "黄河三峡": "黄河三峡",
    "小浪底": "小浪底",
    "龙门石窟": "龙门石窟",
    "白马寺": "白马寺",
    "关林": "关林",
    "嵩山": "嵩山",
    "少林寺": "少林寺",
    "中岳庙": "中岳庙",
    "嵩阳书院": "嵩阳书院",
    "嵩岳寺塔": "嵩岳寺塔",
    "法王寺": "法王寺",
    "会善寺": "会善寺",
    "初祖庵": "初祖庵",
    "塔林": "塔林",
    "少林寺塔林": "少林寺塔林",
    "红旗渠": "红旗渠",
    "太行大峡谷": "太行大峡谷林州",
}

def get_baike_image_url(poi_name, baike_name):
    """从百度百科获取图片URL"""
    try:
        url = f"https://baike.baidu.com/item/{baike_name}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        # 提取图片 hash
        # 格式1: /pic/xxx/hash
        # 格式2: data-src="https://bkimg.cdn.bcebos.com/pic/xxx"
        patterns = [
            r'/pic/[^/]+/[^/]+/([a-f0-9]+)',
            r'bkimg\.cdn\.bcebos\.com/pic/([a-f0-9]+)',
            r'data-src="([^"]*bkimg[^"]*)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, resp.text)
            if matches:
                hash_val = matches[0]
                if len(hash_val) > 20:  # 有效 hash
                    return f"https://bkimg.cdn.bcebos.com/pic/{hash_val}?x-bce-process=image/resize,w_400"
        
        return None
    except Exception as e:
        print(f"  获取 {poi_name} 图片失败: {e}")
        return None

def main():
    conn = sqlite3.connect('/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db')
    cursor = conn.cursor()
    
    updated = 0
    for poi_name, baike_name in POI_BAIKE_MAP.items():
        print(f"处理 {poi_name}...")
        img_url = get_baike_image_url(poi_name, baike_name)
        
        if img_url:
            cursor.execute(
                "UPDATE pois SET images = ? WHERE name = ?",
                (f'["{img_url}"]', poi_name)
            )
            if cursor.rowcount > 0:
                updated += 1
                print(f"  ✓ 已更新")
        
        time.sleep(0.5)  # 避免请求过快
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 更新了 {updated} 个景点的图片")

if __name__ == "__main__":
    main()
