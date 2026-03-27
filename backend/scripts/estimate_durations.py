#!/usr/bin/env python3
"""
用 LLM 批量估算景点游玩时长
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import POI
import httpx

# LLM 配置
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-sp-UAnq05xlBQIwylSCH2FdXNry1hKrVvMGnFyAN56QyMWO4Vhp")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.lkeap.cloud.tencent.com/coding/v3")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "glm-5")


def estimate_duration_batch(pois: list) -> dict:
    """批量估算景点游玩时长"""
    
    # 构建 prompt
    poi_list = "\n".join([f"{i+1}. {p['name']}（{p['city']}，{p['category']}，{p.get('tags', '')}）" 
                          for i, p in enumerate(pois)])
    
    prompt = f"""请估算以下景点的建议游玩时长（小时）。根据景点类型、规模、知名度合理估算：

{poi_list}

返回 JSON 格式：
{{
  "景点名称": 时长（小时）,
  ...
}}

规则：
- 知名大景点（5A景区）：3-8小时
- 中等景点（4A景区）：2-4小时
- 小景点/遗址：1-2小时
- 古村落/小镇：2-3小时
- 自然风光：2-4小时
- 博物馆：2-3小时
"""

    try:
        client = httpx.Client(timeout=60)
        response = client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2000
            }
        )
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # 提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        else:
            print(f"  LLM 返回格式错误: {content[:100]}")
            return {}
    
    except Exception as e:
        print(f"  LLM 调用失败: {e}")
        return {}


def main():
    db = SessionLocal()
    
    try:
        # 获取需要估算的景点
        pois = db.query(POI).filter(POI.duration == 2).all()
        total = len(pois)
        print(f"需要估算 {total} 个景点的游玩时长")
        
        # 分批处理（每批 30 个）
        batch_size = 30
        updated = 0
        
        for i in range(0, total, batch_size):
            batch = pois[i:i + batch_size]
            
            # 准备数据
            poi_data = [{
                "id": p.id,
                "name": p.name,
                "city": p.city,
                "category": p.category,
                "tags": p.tags
            } for p in batch]
            
            print(f"\n批次 {i//batch_size + 1}: {len(batch)} 个景点")
            
            # 调用 LLM
            durations = estimate_duration_batch(poi_data)
            
            if durations:
                # 更新数据库
                for p in batch:
                    if p.name in durations:
                        hours = durations[p.name]
                        # 转换为整数（向上取整）
                        p.duration = int(hours) if hours == int(hours) else int(hours) + 1
                        print(f"  ✅ {p.name}: {p.duration}小时")
                        updated += 1
                
                db.commit()
            else:
                print(f"  ❌ 批次 {i//batch_size + 1} 估算失败")
            
            # 避免 API 限速
            time.sleep(2)
        
        print(f"\n完成！更新了 {updated} 个景点")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
