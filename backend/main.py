from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import pois, trips

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="自驾行程规划 API",
    description="自驾行程规划网站后端API，提供景点(POI)管理和行程协作功能",
    version="1.0.0",
)

# CORS 配置，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(pois.router)
app.include_router(trips.router)


@app.get("/")
def root():
    return {"message": "自驾行程规划 API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
