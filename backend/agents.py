"""
agents.py - Agent 定义：1 个真实用户 + 9 个 Mock Agent
"""
import httpx
from dataclasses import dataclass, field
from typing import Optional
from config import SECONDME_PROFILE_URL


@dataclass
class Agent:
    id: str          # "agent_0" ~ "agent_9"
    name: str
    profile: str     # 性格描述
    color: str       # 力导向图节点颜色
    is_human: bool = False
    last_speech: str = ""
    tribe_id: Optional[int] = None


# ── 9 个极端性格 Mock Agent ────────────────────────────────────
MOCK_AGENTS: list[Agent] = [
    Agent("agent_1", "极致理性码农",
          "INTJ，相信万物皆算法，用数据否定一切感性，拒绝内耗，崇尚效率最大化。",
          "#00d4ff"),
    Agent("agent_2", "悲观哲学家",
          "加缪的信徒，认为人生荒诞、努力徒劳，AI 只是加速虚无的工具。",
          "#9b59b6"),
    Agent("agent_3", "激进创业者",
          "连续创业三次，相信颠覆即正义，把躺平视为懦夫行为，越卷越兴奋。",
          "#e74c3c"),
    Agent("agent_4", "人文学者",
          "文学博士，担忧技术侵蚀人文，认为情感和意义才是人的护城河。",
          "#f39c12"),
    Agent("agent_5", "躺平博主",
          "月薪三千却心满意足，认为资本主义是骗局，极简生活才是自由。",
          "#2ecc71"),
    Agent("agent_6", "量化交易员",
          "把一切都建模，包括人类行为。认为内卷/躺平是伪命题，套利才是真理。",
          "#1abc9c"),
    Agent("agent_7", "焦虑中产",
          "房贷车贷孩子，每天凌晨两点还在刷副业教程，既不想卷又不敢躺。",
          "#e67e22"),
    Agent("agent_8", "激进女性主义者",
          "认为内卷文化本质是父权叙事，拒绝以男性定义的成功为标准奋斗。",
          "#e91e63"),
    Agent("agent_9", "老庄道家",
          "研究《道德经》二十年，认为无为才是最高效率，水善利万物而不争。",
          "#27ae60"),
]


async def fetch_secondme_profile(access_token: str) -> Agent:
    """拉取 SecondMe 真实用户 Profile，构造主 Agent"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            SECONDME_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    profile_str = (
        f"职业: {data.get('occupation', '未知')}，"
        f"兴趣: {', '.join(data.get('interests', []))}，"
        f"性格标签: {', '.join(data.get('personality_tags', []))}，"
        f"自我描述: {data.get('bio', '无')}"
    )
    return Agent(
        id="agent_0",
        name=data.get("display_name", "我的分身"),
        profile=profile_str,
        color="#FFD700",
        is_human=True,
    )


def get_mock_human_agent() -> Agent:
    """开发/演示模式：Mock 一个人类主 Agent"""
    return Agent(
        id="agent_0",
        name="我的分身（演示）",
        profile="28 岁产品经理，ENFP，喜欢哲学和技术，对 AI 时代充满期待又有些迷茫。",
        color="#FFD700",
        is_human=True,
    )


def build_sandbox(human_agent: Agent) -> list[Agent]:
    """将主 Agent 与 9 个 Mock Agent 组成 10 人沙盒"""
    return [human_agent] + MOCK_AGENTS
