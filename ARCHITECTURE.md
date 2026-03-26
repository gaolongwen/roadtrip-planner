# 自驾行程规划网站 - 技术架构文档

## 项目概述

一个通用的自驾旅游行程规划网站，支持景点管理、地图可视化、路线规划、行程导出。

## 技术栈

| 组件 | 技术选择 | 版本 |
|------|---------|------|
| 前端框架 | Vue 3 + Vite | ^3.4.0 |
| UI组件库 | Element Plus (PC) + Vant (移动端) | ^2.5.0 / ^4.8.0 |
| 地图SDK | 高德地图 JS API | 2.0 |
| 后端框架 | Python FastAPI | ^0.109.0 |
| 数据库 | SQLite | 3.x |
| ORM | SQLAlchemy | ^2.0 |
| 部署 | 直接部署（无Docker） | - |

## 项目结构

```
roadtrip-planner/
├── frontend/              # Vue 3 前端
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── main.js        # 入口
│   │   ├── App.vue        # 根组件
│   │   ├── views/         # 页面
│   │   │   ├── MapView.vue      # 地图主页面
│   │   │   ├── AdminView.vue    # 后台管理
│   │   │   └── TripView.vue     # 行程规划（后续）
│   │   ├── components/    # 组件
│   │   │   ├── MapContainer.vue # 地图容器
│   │   │   ├── PoiMarker.vue    # 景点标记
│   │   │   ├── PoiCard.vue      # 景点卡片
│   │   │   └── PoiFilter.vue    # 筛选面板
│   │   ├── stores/        # Pinia 状态管理
│   │   │   └── poi.js     # 景点状态
│   │   └── api/           # API 封装
│   │       └── index.js
│   ├── package.json
│   └── vite.config.js
│
├── backend/               # FastAPI 后端
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置
│   ├── models.py          # SQLAlchemy 模型
│   ├── database.py        # 数据库连接
│   ├── schemas.py         # Pydantic 模型
│   ├── routers/           # API 路由
│   │   ├── __init__.py
│   │   ├── pois.py        # 景点 CRUD
│   │   └── routes.py      # 路线规划（后续）
│   ├── data/              # SQLite 数据库文件
│   │   └── roadtrip.db
│   └── requirements.txt
│
├── scripts/               # 数据脚本
│   ├── import_pois.py     # 导入景点数据
│   └── scrape_pois.py     # 抓取景点数据
│
└── ARCHITECTURE.md        # 本文档
```

## 数据模型

### POI（景点）

```python
class POI:
    id: int                  # 主键
    name: str                # 景点名称
    province: str            # 省份
    city: str                # 城市
    district: str            # 区县
    address: str             # 详细地址
    latitude: float          # 纬度
    longitude: float         # 经度
    category: str            # 类型（自然/人文/娱乐等）
    tags: str                # 标签（JSON数组）
    rating: float            # 评分（1-5）
    price: float             # 门票价格
    duration: int            # 建议游玩时长（小时）
    description: str         # 描述
    tips: str                # 游玩贴士
    images: str              # 图片URL（JSON数组）
    is_wild: bool            # 是否野生景点
    created_at: datetime     # 创建时间
    updated_at: datetime     # 更新时间
```

### Trip（行程）- 后续

```python
class Trip:
    id: int
    name: str
    start_date: date
    end_date: date
    pois: List[POI]          # 关联景点
    route: dict              # 路线数据
```

## API 设计

### 景点管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/pois | 获取景点列表（支持筛选） |
| GET | /api/pois/{id} | 获取单个景点 |
| POST | /api/pois | 创建景点 |
| PUT | /api/pois/{id} | 更新景点 |
| DELETE | /api/pois/{id} | 删除景点 |
| GET | /api/pois/bbox | 获取地图范围内景点 |

### 查询参数

```
GET /api/pois?province=山西&city=晋城&category=人文&is_wild=true
GET /api/pois/bbox?min_lng=113&max_lng=114&min_lat=35&max_lat=36
```

## 地图功能

### 高德地图集成

```javascript
// 初始化地图
const map = new AMap.Map('container', {
  zoom: 8,
  center: [113.5, 35.5]
})

// 添加景点标记
const marker = new AMap.Marker({
  position: [poi.longitude, poi.latitude],
  title: poi.name
})

// 点击事件
marker.on('click', () => showPoiDetail(poi))
```

### 交互功能

1. **景点标记**：不同类型用不同图标
2. **点击弹窗**：显示景点名称和简短描述
3. **侧边栏详情**：点击后展开详情卡片
4. **筛选面板**：按省份、城市、类型筛选
5. **地图范围查询**：拖拽地图后刷新可见景点

## 部署方案

### 开发环境

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 生产环境

```bash
# 后端（使用 gunicorn）
gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# 前端（nginx 托管静态文件）
npm run build
# 将 dist/ 目录放到 nginx
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name 43.128.121.98;

    # 前端静态文件
    location / {
        root /root/.openclaw/workspace/roadtrip-planner/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

## 开发里程碑

### Phase 1: MVP 地图可视化（本周）

- [x] 项目结构搭建
- [ ] 后端数据库模型
- [ ] 后端 CRUD API
- [ ] 前端地图页面
- [ ] 景点标记展示
- [ ] 景点详情弹窗
- [ ] 筛选功能
- [ ] 导入种子数据（185条南太行景点）

### Phase 2: 后台管理（下周）

- [ ] 景点管理界面
- [ ] 批量导入功能
- [ ] 图片上传

### Phase 3: 路线规划（后续）

- [ ] 景点选取功能
- [ ] 高德路径规划 API 集成
- [ ] 多日行程编排

### Phase 4: 行程导出（后续）

- [ ] 行程文档生成
- [ ] PDF 导出
- [ ] 分享功能

## 环境变量

```bash
# backend/.env
AMAP_KEY=your_amap_api_key
DATABASE_URL=sqlite:///./data/roadtrip.db
```

## 种子数据

现有 185 条南太行景点数据，存放在：
- 飞书多维表格：https://ucnjj5jwxk7e.feishu.cn/base/P3UMbgEQqa9KwmsGyoBcKOD4nHd
- 本地工作流文档：`/root/.openclaw/workspace/memory/roadtrip/`

需要编写脚本从飞书导出并导入到 SQLite。

---

*创建时间: 2026-03-26*
*作者: 大螃蟹 🦀*
