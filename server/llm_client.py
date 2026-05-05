"""
Laplace — LLM Client

OpenAI-compatible LLM client with fallback models and a structured
intent contract for JSON-mode calls.
"""

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from server.schemas import IntentResponse, intent_response_json_schema

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


class LLMResponseFormatUnsupported(Exception):
    """Raised when a model gateway rejects structured response_format."""


async def chat_completion(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.1,
    json_mode: bool = True,
) -> dict:
    """
    调用 LLM Chat Completion API。

    Args:
        system_prompt: 系统 prompt
        user_message: 用户消息
        model: 模型名称，None 则使用主模型
        max_tokens: 最大 token 数
        temperature: 温度，低温 = 更确定性
        json_mode: True 时校验为 IntentResponse JSON

    Returns:
        解析后的 JSON 响应或 {"text": "..."}

    Raises:
        Exception: 所有模型都失败时
    """
    models_to_try = [model or PRIMARY_MODEL] + FALLBACK_MODELS

    last_error = None
    for m in models_to_try:
        try:
            return await _call_model(
                m,
                system_prompt,
                user_message,
                max_tokens,
                temperature,
                json_mode,
            )
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
    json_mode: bool = True,
) -> dict:
    """调用单个模型；JSON 模式优先尝试 response_format。"""
    if not json_mode:
        data = await _post_chat_completion(
            model,
            system_prompt,
            user_message,
            max_tokens,
            temperature,
            use_structured_output=False,
        )
        content = _extract_message_content(data)
        return {"text": content, "_model": model}

    response_format = "json_schema"
    try:
        data = await _post_chat_completion(
            model,
            system_prompt,
            user_message,
            max_tokens,
            temperature,
            use_structured_output=True,
        )
    except LLMResponseFormatUnsupported:
        response_format = "text_fallback"
        data = await _post_chat_completion(
            model,
            system_prompt,
            user_message,
            max_tokens,
            temperature,
            use_structured_output=False,
        )

    parsed = parse_intent_response(_extract_message_content(data))
    parsed["_model"] = model
    parsed["_response_format"] = response_format
    return parsed


async def _post_chat_completion(
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float,
    use_structured_output: bool,
) -> dict:
    """Send one Chat Completions request."""
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if use_structured_output:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "laplace_intent_response",
                "strict": True,
                "schema": intent_response_json_schema(),
            },
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if use_structured_output and resp.status_code in (400, 422):
            if _looks_like_response_format_error(resp):
                raise LLMResponseFormatUnsupported(_safe_error_text(resp))
        resp.raise_for_status()
        return resp.json()


def parse_intent_response(content: str | dict) -> dict:
    """Parse and validate an LLM intent response."""
    raw = content if isinstance(content, dict) else json.loads(extract_json_object(content))
    try:
        parsed = IntentResponse.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"LLM JSON schema validation failed: {e}") from e
    return parsed.model_dump(exclude_none=True)


def extract_json_object(content: str) -> str:
    """Extract the first complete JSON object from model text."""
    text = content.strip()
    if not text:
        raise ValueError("LLM returned empty content")

    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain a JSON object")

    in_string = False
    escape = False
    depth = 0
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    raise ValueError("LLM response contains an incomplete JSON object")


def _extract_message_content(data: dict) -> str:
    """Extract assistant content from an OpenAI-compatible response."""
    message = data["choices"][0]["message"]
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
        if parts:
            return "\n".join(parts)
    raise ValueError("LLM response message has no text content")


def _looks_like_response_format_error(resp: httpx.Response) -> bool:
    text = _safe_error_text(resp).lower()
    markers = ("response_format", "json_schema", "structured", "schema")
    return any(marker in text for marker in markers)


def _safe_error_text(resp: httpx.Response) -> str:
    try:
        return resp.text[:1000]
    except Exception:
        return ""
