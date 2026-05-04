"""
Laplace — FastAPI Server

对话式 FGO 数据查询 API。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.prompts import get_system_prompt
from server.llm_client import chat_completion
from server.query_executor import execute_query, load_database

app = FastAPI(
    title="Laplace API",
    description="AI Native FGO 数据助手",
    version="0.2.0",
)

# CORS — 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """对话请求。"""
    message: str


class ChatResponse(BaseModel):
    """对话响应。"""
    reply: str
    servants: list[dict]
    count: int
    query: dict
    model: str


@app.on_event("startup")
async def startup():
    """启动时预加载数据库。"""
    load_database()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    对话端点：接收用户自然语言，返回查询结果。

    流程：
    1. 用户消息 → LLM 意图解析
    2. JSON 查询指令 → Query Executor
    3. 结果 → 组装响应
    """
    user_message = req.message.strip()
    if not user_message:
        return ChatResponse(
            reply='请输入你的问题，例如"帮我找一下 30 自充的从者有哪些"',
            servants=[],
            count=0,
            query={},
            model="",
        )

    # 1. LLM 意图解析
    system_prompt = get_system_prompt()
    try:
        parsed = await chat_completion(system_prompt, user_message)
    except Exception as e:
        return ChatResponse(
            reply=f"AI 服务暂时不可用：{str(e)}",
            servants=[],
            count=0,
            query={},
            model="error",
        )

    model_used = parsed.pop("_model", "unknown")

    # 2. 检查意图
    if parsed.get("intent") != "query_servants":
        return ChatResponse(
            reply=parsed.get("rawResponse", "抱歉，我目前只能回答 FGO 从者相关的问题。"),
            servants=[],
            count=0,
            query=parsed,
            model=model_used,
        )

    # 3. 执行查询
    conditions = parsed.get("conditions", {})
    servants = execute_query(conditions)

    # 4. 组装回复
    response_template = parsed.get("responseTemplate", "为你找到了以下从者：")
    reply = f"{response_template}（共 {len(servants)} 位）"

    # 限制返回数量，避免响应过大
    max_results = 50
    returned_servants = servants[:max_results]
    if len(servants) > max_results:
        reply += f"\n（结果较多，显示前 {max_results} 位）"

    return ChatResponse(
        reply=reply,
        servants=returned_servants,
        count=len(servants),
        query=conditions,
        model=model_used,
    )


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "service": "laplace"}
