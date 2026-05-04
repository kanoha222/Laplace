"""
Laplace — LLM Client

OpenAI 兼容的 LLM 客户端，支持回退模型链。
"""

import json
import os
import httpx
from dotenv import load_dotenv

# 从项目根目录加载 .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("LLM_BASE_URL", "https://x.obao.cloud/v1")
API_KEY = os.getenv("LLM_API_KEY", "")
PRIMARY_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("LLM_FALLBACK_MODELS", "Deepseek-V4-Flash,gpt-5.4").split(",")
    if m.strip()
]


async def chat_completion(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.1,
) -> dict:
    """
    调用 LLM Chat Completion API。

    Args:
        system_prompt: 系统 prompt
        user_message: 用户消息
        model: 模型名称，None 则使用主模型
        max_tokens: 最大 token 数
        temperature: 温度，低温 = 更确定性

    Returns:
        解析后的 JSON 响应

    Raises:
        Exception: 所有模型都失败时
    """
    models_to_try = [model or PRIMARY_MODEL] + FALLBACK_MODELS

    last_error = None
    for m in models_to_try:
        try:
            result = await _call_model(m, system_prompt, user_message, max_tokens, temperature)
            return result
        except Exception as e:
            print(f"⚠️  模型 {m} 调用失败: {e}")
            last_error = e
            continue

    raise Exception(f"所有模型都调用失败。最后的错误: {last_error}")


async def _call_model(
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    """调用单个模型。"""
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]

    # 尝试解析 JSON（LLM 可能包裹在 ```json ... ``` 中）
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # 去掉首尾 ``` 行
        json_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith("```") and not inside:
                inside = True
                continue
            elif line.strip() == "```" and inside:
                break
            elif inside:
                json_lines.append(line)
        content = "\n".join(json_lines)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # 如果无法解析 JSON，返回原始文本
        parsed = {"intent": "unknown", "rawResponse": content}

    parsed["_model"] = model
    return parsed
