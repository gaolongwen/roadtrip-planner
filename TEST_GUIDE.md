# 测试指南

## 前端修复内容

### 1. 修复了图标导入问题
- 在 `TripView.vue` 中添加了图标导入：`Plus, Link, Edit, Delete, Download`
- 在 `MapView.vue` 中添加了图标导入：`Refresh, Loading`
- 在 `PoiCard.vue` 中添加了图标导入：`Close, Location, Star, CollectionTag, Link, TopRight, MapLocation, Position, Edit`

### 2. 修复了 MapContainer 组件问题
- 添加了缺失的事件定义：`poi-click`, `poi-add`
- 添加了 `highlightPois` 方法

### 3. 改进了用户体验
- 添加了"复制分享码"按钮，用户可以单独复制分享码
- 改进了"复制链接"功能，现在会同时复制分享码和链接
- 优化了提示消息，更清晰地显示分享码

## 如何测试

### 1. 创建行程
1. 访问 http://43.128.121.98:8080
2. 点击顶部导航栏的"我的行程"
3. 点击"创建行程"按钮
4. 输入行程名称（例如："五一南太行之旅"）
5. 点击"创建"

### 2. 查看分享码
创建成功后，右侧会显示行程卡片，包含：
- 行程名称
- **分享码**（醒目显示）
- "复制分享码"按钮
- "复制链接"按钮

### 3. 复制分享码
- 点击"复制分享码"按钮：只复制分享码（例如：ABC123）
- 点击"复制链接"按钮：复制分享码和链接（例如：分享码: ABC123\n链接: http://...）

### 4. 添加景点到行程
1. 在地图上点击景点标记
2. 如果已创建行程，景点会被添加到行程中
3. 右侧行程面板会显示已添加的景点列表

## 后端 API 验证

### 创建行程
```bash
curl -X POST "http://localhost:8001/api/trips?name=测试行程"
```

返回：
```json
{
  "trip_id": "xxx-xxx-xxx",
  "share_code": "ABC123",
  "name": "测试行程",
  "created_at": "2026-03-26T..."
}
```

### 获取行程详情
```bash
curl "http://localhost:8001/api/trips/{trip_id}"
```

返回：
```json
{
  "trip_id": "xxx-xxx-xxx",
  "share_code": "ABC123",
  "name": "测试行程",
  "pois": [],
  "members": [],
  ...
}
```

## 注意事项

1. **前端 URL**: http://43.128.121.98:8080
2. **后端 API**: http://43.128.121.98:8001
3. 修改前端代码后，需要运行 `npm run build` 重新构建
4. 构建后的文件在 `frontend/dist/` 目录
5. Python HTTP Server 会自动提供最新的构建文件

## 如果还有问题

如果创建行程后右侧仍然空白，请检查：
1. 浏览器控制台是否有 JavaScript 错误
2. 网络请求是否成功（查看 Network 标签）
3. 确认后端服务正在运行（`ps aux | grep uvicorn`）
