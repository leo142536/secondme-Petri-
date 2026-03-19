"""
llm.py - LLM 调用层（OpenAI-compatible API）
支持任何兼容 OpenAI 的接口（GPT-4o、通义千问、DeepSeek 等）
"""
import json
import re
import asyncio
from openai import AsyncOpenAI
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


_client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

# ── Prompt 模板 ─────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """系统设定：你是用户 {agent_name} 的数字分身，性格画像：{profile}。

当前世界大事件（知乎热点）：{topic}

上一回合广场上的核心言论有：
{history_context}

行动指令：请结合你的人设，用极简、犀利的口语（限 30 字内）发表你的反驳或赞同。
寻找一个你最认同的发言者，试图与他结盟。

强制返回 JSON 格式（不要包含任何其他文字）：
{{
  "thought": "你的内部推理(10字以内)",
  "speech": "你的公开发言(30字以内)",
  "agree_with_id": "你最认同的某人ID（必须是10个Agent之一）"
}}"""


def _format_history(history: list[dict]) -> str:
    """将上一轮所有 Agent 发言格式化为上下文"""
    if not history:
        return "（这是第一回合，广场上还没有任何发言）"
    lines = [f"  [{h['agent_id']}] {h['agent_name']}: {h['speech']}" for h in history]
    return "\n".join(lines)


async def ask_agent(
    agent_id: str,
    agent_name: str,
    profile: str,
    topic: str,
    history: list[dict],
    all_agent_ids: list[str],
) -> dict:
    """
    调用 LLM 为单个 Agent 生成一轮响应。
    返回结构: {"agent_id", "agent_name", "thought", "speech", "agree_with_id"}
    """
    history_context = _format_history(history)
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        agent_name=agent_name,
        profile=profile,
        topic=topic,
        history_context=history_context,
    )

    try:
        response = await _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=200,
            response_format={"type": "json_object"},  # 强制 JSON 输出
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        # 容错：LLM 返回非 JSON 时，用正则提取或返回默认值
        result = _fallback_parse(raw if "raw" in dir() else str(e), all_agent_ids, agent_id)

    # 确保 agree_with_id 合法
    if result.get("agree_with_id") not in all_agent_ids or result.get("agree_with_id") == agent_id:
        import random
        result["agree_with_id"] = random.choice(
            [aid for aid in all_agent_ids if aid != agent_id]
        )

    return {
        "agent_id":      agent_id,
        "agent_name":    agent_name,
        "thought":       result.get("thought", "..."),
        "speech":        result.get("speech", "无言以对。"),
        "agree_with_id": result["agree_with_id"],
    }


def _fallback_parse(raw: str, all_agent_ids: list[str], self_id: str) -> dict:
    """LLM 输出异常时的降级解析"""
    import random
    agree_id = next(
        (aid for aid in all_agent_ids if aid in raw and aid != self_id),
        random.choice([aid for aid in all_agent_ids if aid != self_id])
    )
    # 尝试从文本中提取双引号内容作为 speech
    speeches = re.findall(r'"([^"]{5,60})"', raw)
    speech = speeches[0] if speeches else raw[:30] or "沉默是金。"
    return {"thought": "解析异常", "speech": speech, "agree_with_id": agree_id}
