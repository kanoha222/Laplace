"""
Laplace — FastAPI Server

对话式 FGO 数据查询 API。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import json
import uuid
from pathlib import Path
from server.prompts import get_system_prompt, get_generation_prompt
from server.llm_client import chat_completion
from server.query_executor import execute_query, load_database
from server.logger import log_chat_trace
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 预消化翻译字典
NP_CARD_MAP = {"buster": "红卡", "arts": "蓝卡", "quick": "绿卡"}
NP_TARGET_MAP = {"all": "全体(光炮)", "one": "单体", "support": "辅助"}
CLASS_MAP = {
    "saber": "剑阶", "archer": "弓阶", "lancer": "枪阶",
    "rider": "骑阶", "caster": "术阶", "assassin": "杀阶",
    "berserker": "狂阶", "ruler": "裁定者(Ruler)", "avenger": "复仇者(Avenger)",
    "mooncancer": "月癌(MoonCancer)", "alterego": "他人格(AlterEgo)",
    "foreigner": "降临者(Foreigner)", "pretender": "伪装者(Pretender)",
    "shielder": "盾阶", "beast": "兽阶(Beast)"
}

_effect_map = None

def get_effect_translation(effect_code: str) -> str:
    global _effect_map
    if _effect_map is None:
        _effect_map = {}
        schema_path = Path(__file__).parent / "knowledge" / "effect_schema.json"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for effect in data.get("effects", []):
                    name = effect.get("name")
                    aliases = effect.get("aliases_zh", [])
                    if name and aliases:
                        _effect_map[name] = aliases[0]
    return _effect_map.get(effect_code, effect_code)


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
    traceId: str | None = None


@app.on_event("startup")
async def startup():
    """启动时预加载数据库。"""
    load_database()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理用户对话请求。"""
    user_message = request.message
    trace_id = uuid.uuid4().hex[:8]  # 生成一个 8 位的 trace_id
    
    # 1. 意图解析 (第一阶段)
    try:
        parsed = await chat_completion(
            system_prompt=get_system_prompt(),
            user_message=user_message,
            temperature=0.1,
            json_mode=True
        )
    except Exception as e:
        print(f"[{trace_id}] LLM Parse Error: {e}")
        log_chat_trace(trace_id, user_message, {}, 0, "无法连接到 LLM 或解析失败，请检查模型配置。", error=str(e))
        return ChatResponse(
            reply="抱歉，我遇到了网络问题或模型暂时不可用，请稍后再试。",
            servants=[],
            count=0,
            query={},
            model="error",
            traceId=trace_id
        )

    model_used = parsed.pop("_model", "unknown")

    # 2. 检查意图
    if parsed.get("intent") != "query_servants":
        reply_text = parsed.get("rawResponse", "抱歉，我目前只能回答 FGO 从者相关的问题。")
        log_chat_trace(trace_id, user_message, parsed, 0, reply_text)
        return ChatResponse(
            reply=reply_text,
            servants=[],
            count=0,
            query=parsed,
            model=model_used,
            traceId=trace_id
        )

    # 3. 执行查询
    conditions = parsed.get("conditions", {})
    servants = execute_query(conditions)

    # 4. 构建精简 Context
    total_found = len(servants)
    max_context_size = 5
    top_results = []
    
    for s in servants[:max_context_size]:
        raw_np_card = s.get("npCard")
        raw_np_target = s.get("npTarget")
        raw_class_name = s.get("className")
        raw_effects = s.get("skillEffects") or []
        
        translated_effects = [get_effect_translation(e) for e in raw_effects]
        
        top_results.append({
            "name": s.get("name"),
            "aliasCN": s.get("aliasCN"),
            "className": CLASS_MAP.get(str(raw_class_name).lower(), raw_class_name),
            "rarity": s.get("rarity"),
            "totalSelfCharge": s.get("totalSelfCharge"),
            "npCard": NP_CARD_MAP.get(str(raw_np_card).lower(), raw_np_card),
            "npTarget": NP_TARGET_MAP.get(str(raw_np_target).lower(), raw_np_target),
            "skillEffects": translated_effects
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
        print(f"[{trace_id}] RAG Generate Error: {e}")
        # 如果生成失败，降级回旧的逻辑
        response_template = parsed.get("responseTemplate", "为你找到了以下从者：")
        final_reply = f"{response_template}（共 {total_found} 位）"
        if total_found > max_context_size:
            final_reply += f"（仅显示前 {max_context_size} 位详情，更多请查看卡片）"

    # 记录完整链路
    log_chat_trace(trace_id, user_message, conditions, total_found, final_reply)

    # 限制返回给前端的数量，避免响应过大
    max_results = 50
    returned_servants = servants[:max_results]

    return ChatResponse(
        reply=final_reply,
        servants=returned_servants,
        count=total_found,
        query=conditions,
        model=model_used,
        traceId=trace_id
    )


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "service": "laplace"}

# 挂载前端静态文件目录
app.mount("/", StaticFiles(directory="demo", html=True), name="static")
