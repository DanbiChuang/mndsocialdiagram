"""
社群拓撲圖 API Server (FastAPI)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sigma_generator import generate_social_graph

app = FastAPI(title="Social Graph Generator API")

# CORS: 允許前端 (Vercel / localhost) 跨域呼叫
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    topic: str
    node_count: int = 2000


@app.post("/api/generate-social-graph")
async def generate(request: GenerateRequest):
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="topic 不可為空")

    # 限制 node_count 範圍
    node_count = max(100, min(request.node_count, 5000))

    try:
        result = generate_social_graph(request.topic, node_count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
