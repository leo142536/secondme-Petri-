"""
llm.py - LLM 调用层（双轨路由）

路由逻辑：
  - agent_0（真人）+ 有 access_token  →  SecondMe LME（用户自己的分身 AI）
  - 其他所有 Agent                    →  通用 OpenAI-compatible LLM

SecondMe LME 兼容 OpenAI Chat API，用 OAuth token 鉴权：
  POST {SECONDME_LME_BASE_URL}/chat/completions
  Authorization: Bearer {access_token}
"""
import json
import re
import asyncio
import logging
from openai import AsyncOpenAI
from config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
    SECONDME_LME_BASE_URL, SECONDME_LME_MODEL,
)

logger = logging.getLogger(__name__)

# ── 通用 LLM 客户端（9 个 Mock Agent 共用）──────────────────────
print(f"[LLM INIT] BASE_URL={LLM_BASE_URL}")
print(f"[LLM INIT] MODEL={LLM_MODEL}")
print(f"[LLM INIT] API_KEY={LLM_API_KEY[:10]}...")
_client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


# ── Prompt 模板 ─────────────────────────────────────────────────
# 通用 LLM：需要 profile 注入人设
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

# SecondMe LME：不注入 profile（LME 本身即用户人格），只提供场景
LME_PROMPT_TEMPLATE = """你正在参加一个 AI 分身广场实验。

当前知乎热点话题：{topic}

广场上其他人的发言：
{history_context}

请用你自己的真实风格，用简洁犀利的口语（30 字以内）表达你的观点，
并选出一位你最认同的发言者ID，尝试与他结盟。

强制返回 JSON 格式（不要包含任何其他文字）：
{{
  "thought": "你的内部推理(10字以内)",
  "speech": "你的公开发言(30字以内)",
  "agree_with_id": "你最认同的某人ID（必须从以下列表选择：{agent_ids_str}）"
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
    user_token: str = "",   # SecondMe OAuth token（仅 agent_0 传入）
) -> dict:
    """
    调用 LLM 为单个 Agent 生成一轮响应。
    返回结构: {"agent_id", "agent_name", "thought", "speech", "agree_with_id"}
    """
    history_context = _format_history(history)
    other_ids = [aid for aid in all_agent_ids if aid != agent_id]

    # ── 路由判断 ─────────────────────────────────────────────────
    use_lme = bool(user_token) and agent_id == "agent_0"

    if use_lme:
        result = await _ask_via_lme(
            user_token=user_token,
            agent_name=agent_name,
            topic=topic,
            history_context=history_context,
            all_agent_ids=all_agent_ids,
            agent_id=agent_id,
        )
        logger.info(f"[LME] agent_0 ({agent_name}) → {result.get('speech', '')[:20]}...")
    else:
        result = await _ask_via_generic_llm(
            agent_id=agent_id,
            agent_name=agent_name,
            profile=profile,
            topic=topic,
            history_context=history_context,
            all_agent_ids=all_agent_ids,
        )

    # ── 确保 agree_with_id 合法 ──────────────────────────────────
    if result.get("agree_with_id") not in all_agent_ids or result.get("agree_with_id") == agent_id:
        import random
        result["agree_with_id"] = random.choice(other_ids)

    return {
        "agent_id":      agent_id,
        "agent_name":    agent_name,
        "thought":       result.get("thought", "..."),
        "speech":        result.get("speech", "无言以对。"),
        "agree_with_id": result["agree_with_id"],
        "via_lme":       use_lme,   # 供前端标记"真人分身"徽章
    }


# ── SecondMe LME 调用 ────────────────────────────────────────────
async def _ask_via_lme(
    user_token: str,
    agent_name: str,
    topic: str,
    history_context: str,
    all_agent_ids: list[str],
    agent_id: str,
) -> dict:
    """
    通过 SecondMe LME API 调用用户自己的分身 LLM。
    LME 兼容 OpenAI Chat Completions，以 OAuth Bearer token 鉴权。
    """
    lme_client = AsyncOpenAI(
        api_key=user_token,
        base_url=SECONDME_LME_BASE_URL,
    )
    agent_ids_str = "、".join(all_agent_ids)
    prompt = LME_PROMPT_TEMPLATE.format(
        topic=topic,
        history_context=history_context,
        agent_ids_str=agent_ids_str,
    )
    try:
        response = await lme_client.chat.completions.create(
            model=SECONDME_LME_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        return result
    except Exception as e:
        # LME 调用失败 → 优雅 fallback 到通用 LLM（不影响演示）
        logger.warning(f"[LME] 调用失败，fallback 到通用 LLM: {e}")
        return await _ask_via_generic_llm(
            agent_id=agent_id,
            agent_name=agent_name,
            profile="（SecondMe 真实用户，具体人设由 LME 动态推理）",
            topic=topic,
            history_context=history_context,
            all_agent_ids=all_agent_ids,
        )


# ── 通用 LLM 调用 ────────────────────────────────────────────────
async def _ask_via_generic_llm(
    agent_id: str,
    agent_name: str,
    profile: str,
    topic: str,
    history_context: str,
    all_agent_ids: list[str],
) -> dict:
    """调用通用 OpenAI-compatible LLM，用于 9 个 Mock Agent"""
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
        )
        raw = response.choices[0].message.content.strip()
        # 尝试提取 JSON（模型可能会包裹在 ```json 代码块中）
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        # 尝试提取 { ... } 部分
        if raw.find("{") >= 0:
            raw = raw[raw.find("{"):raw.rfind("}")+1]
        return json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        return _fallback_parse(raw if "raw" in dir() else str(e), all_agent_ids, agent_id)


def _fallback_parse(raw: str, all_agent_ids: list[str], self_id: str) -> dict:
    """LLM 输出异常时的降级解析"""
    import random
    agree_id = next(
        (aid for aid in all_agent_ids if aid in raw and aid != self_id),
        random.choice([aid for aid in all_agent_ids if aid != self_id])
    )
    speeches = re.findall(r'"([^"]{5,60})"', raw)
    speech = speeches[0] if speeches else raw[:30] or "沉默是金。"
    return {"thought": "解析异常", "speech": speech, "agree_with_id": agree_id}
