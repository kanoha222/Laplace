"""
Laplace — FastAPI Server

对话式 FGO 数据查询 API。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import json
from server.prompts import get_system_prompt, get_generation_prompt
from server.llm_client import chat_completion
from server.query_executor import execute_query, load_database
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

    # 4. 构建精简 Context
    total_found = len(servants)
    max_context_size = 5
    top_results = []
    
    for s in servants[:max_context_size]:
        top_results.append({
            "name": s.get("name"),
            "aliasCN": s.get("aliasCN"),
            "className": s.get("className"),
            "rarity": s.get("rarity"),
            "totalSelfCharge": s.get("totalSelfCharge"),
            "npCard": s.get("npCard"),
            "npTarget": s.get("npTarget"),
            "skillEffects": s.get("skillEffects")
        })
        
    context_data = {
        "total_found": total_found,
        "query_conditions": conditions,
        "top_results_details": top_results
    }
    
    # 5. 第二阶段：生成自然语言回复 (RAG)
    generation_prompt = get_generation_prompt(user_message, json.dumps(context_data, ensure_ascii=False))
    
    try:
        # LLM 的第二次调用（非严格 JSON，返回纯文本）
        generation_response = await chat_completion(
            system_prompt="You are a helpful AI assistant.",
            user_message=generation_prompt,
            temperature=0.7,
            json_mode=False
        )
        final_reply = generation_response.get("text", "").strip()
        if not final_reply:
            raise ValueError("Empty response from LLM")
    except Exception as e:
        print(f"RAG Generate Error: {e}")
        # 如果生成失败，降级回旧的逻辑
        response_template = parsed.get("responseTemplate", "为你找到了以下从者：")
        final_reply = f"{response_template}（共 {total_found} 位）"
        if total_found > max_context_size:
            final_reply += f"（仅显示前 {max_context_size} 位详情，更多请查看卡片）"

    # 限制返回给前端的数量，避免响应过大
    max_results = 50
    returned_servants = servants[:max_results]

    return ChatResponse(
        reply=final_reply,
        servants=returned_servants,
        count=total_found,
        query=conditions,
        model=model_used,
    )


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "service": "laplace"}

# 挂载前端静态文件目录
app.mount("/", StaticFiles(directory="demo", html=True), name="static")
