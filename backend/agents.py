"""
agents.py - Agent 定义
特性：
  - 根据议题用 LLM 动态生成对立角色（每次都不同）
  - 如果 LLM 生成失败，降级到预设角色池
  - 每个 Agent 随机分配蜜蜂刘看山头像
"""
import os
import json
import random
import glob
import logging
import httpx
from dataclasses import dataclass, field
from typing import Optional
from config import SECONDME_PROFILE_URL, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

# ── 头像池路径 ──────────────────────────────────────────────────
AVATAR_POOL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "frontend", "static", "avatar_pool"
)


def _list_avatar_pool() -> list[str]:
    if not os.path.isdir(AVATAR_POOL_DIR):
        return []
    files = sorted(glob.glob(os.path.join(AVATAR_POOL_DIR, "avatar_*.png")))
    return [f"/static/avatar_pool/{os.path.basename(f)}" for f in files]


def _assign_avatars(count: int) -> list[str]:
    pool = _list_avatar_pool()
    if not pool:
        return [""] * count
    return random.sample(pool, min(count, len(pool)))


# ── 预设颜色池 ──────────────────────────────────────────────────
COLORS = [
    "#00d4ff", "#9b59b6", "#e74c3c", "#f39c12", "#2ecc71",
    "#1abc9c", "#e67e22", "#e91e63", "#27ae60", "#6366f1",
    "#8b5cf6", "#10b981", "#f59e0b", "#ec4899", "#14b8a6",
    "#64748b", "#f43f5e", "#a855f7", "#84cc16", "#0ea5e9",
]


@dataclass
class Agent:
    id: str
    name: str
    profile: str
    color: str
    is_human: bool = False
    last_speech: str = ""
    tribe_id: Optional[int] = None
    access_token: str = ""
    avatar: str = ""


# ── LLM 动态生成角色 ────────────────────────────────────────────
PERSONA_GEN_PROMPT = """你是一个社会模拟实验的角色设计师。

当前讨论议题：{topic}

请为这个议题设计 6 个具有**强烈观点对立**的讨论角色。要求：
1. 每个角色都有鲜明的身份标签（2-5字，如"00后厂妹"、"华尔街老炮"）
2. 每个角色的性格画像要简短犀利（30字以内），必须体现其对该议题的明确立场
3. 6个角色之间要形成多极对立（不是简单的正反两派，要有3-4个不同阵营）
4. 角色要接地气，有社会现实感，不要太学术

严格返回 JSON 数组（不要其他任何文字）：
[
  {{"name": "角色名", "profile": "性格画像和立场"}},
  ...
]"""


async def generate_personas_for_topic(topic: str) -> list[tuple[str, str, str]]:
    """用 LLM 根据议题动态生成 9 个对立角色"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {LLM_API_KEY}",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": PERSONA_GEN_PROMPT.format(topic=topic)}],
                    "temperature": 0.9,
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"].strip()

            # 提取 JSON
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            if raw.find("[") >= 0:
                raw = raw[raw.find("["):raw.rfind("]")+1]

            personas = json.loads(raw)
            colors = random.sample(COLORS, min(len(personas), len(COLORS)))
            result = [
                (p["name"], p["profile"], colors[i])
                for i, p in enumerate(personas[:6])
            ]
            logger.info(f"[角色生成] 为议题「{topic[:20]}...」生成了 {len(result)} 个角色")
            return result

    except Exception as e:
        logger.warning(f"[角色生成] LLM 生成失败，降级到预设池: {e}")
        return []


# ── 预设角色池（降级备用）─────────────────────────────────────
ALL_PERSONAS = [
    ("极致理性码农", "INTJ，相信万物皆算法，用数据否定一切感性，崇尚效率最大化。", "#00d4ff"),
    ("悲观哲学家", "加缪的信徒，认为人生荒诞、努力徒劳，AI 只是加速虚无的工具。", "#9b59b6"),
    ("激进创业者", "连续创业三次，相信颠覆即正义，把躺平视为懦夫行为，越卷越兴奋。", "#e74c3c"),
    ("人文学者", "文学博士，担忧技术侵蚀人文，认为情感和意义才是人的护城河。", "#f39c12"),
    ("躺平博主", "月薪三千却心满意足，认为资本主义是骗局，极简生活才是自由。", "#2ecc71"),
    ("量化交易员", "把一切都建模，包括人类行为。认为内卷/躺平是伪命题，套利才是真理。", "#1abc9c"),
    ("焦虑中产", "房贷车贷孩子，每天凌晨两点还在刷副业教程，既不想卷又不敢躺。", "#e67e22"),
    ("激进女性主义者", "认为内卷文化本质是父权叙事，拒绝以男性定义的成功为标准奋斗。", "#e91e63"),
    ("老庄道家", "研究道德经二十年，认为无为才是最高效率，水善利万物而不争。", "#27ae60"),
    ("科幻作家", "刘慈欣铁粉，坚信技术奇点即将到来，人类应进入星际文明。", "#6366f1"),
    ("佛系公务员", "体制内十年，不卷不躺，认为稳定就是最大的自由。", "#8b5cf6"),
    ("环保激进主义者", "Greta 追随者，认为经济增长是生态灾难。", "#10b981"),
    ("国学自媒体", "日更论语解读，相信传统智慧能解决一切现代问题。", "#f59e0b"),
    ("加密货币布道者", "All in Web3，认为法币是最大骗局，去中心化才是未来。", "#ec4899"),
    ("乡村教师", "扎根西部山区十年，见过真正贫穷，对城市中产焦虑嗤之以鼻。", "#14b8a6"),
    ("退休将军", "战略思维看一切，认为个人奋斗是战术级问题，国运才是战略级。", "#64748b"),
    ("00后整顿职场博主", "上班第一天就怼领导，信奉不开心就离职。", "#f43f5e"),
    ("赛博朋克艺术家", "数字游牧民，用 AI 创作卖 NFT，认为传统就业已死。", "#a855f7"),
    ("深圳厂妹", "流水线三年，用短视频记录生活，不信阶层跃迁。", "#fb923c"),
    ("北大哲学系研究生", "本科数学转哲学，对一切宏大叙事保持怀疑。", "#818cf8"),
]


async def fetch_secondme_profile(access_token: str) -> Agent:
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
        access_token=access_token,
    )


def get_mock_human_agent() -> Agent:
    return Agent(
        id="agent_0",
        name="我的分身（演示）",
        profile="28 岁产品经理，ENFP，喜欢哲学和技术，对 AI 时代充满期待又有些迷茫。",
        color="#FFD700",
        is_human=True,
    )


async def build_sandbox(human_agent: Agent, topic: str = "") -> list[Agent]:
    """
    根据议题动态生成角色 + 真人，组成沙盒。
    如果 LLM 生成失败，降级到预设池随机抽取。
    """
    # 尝试 LLM 动态生成
    personas = []
    if topic:
        personas = await generate_personas_for_topic(topic)

    # 降级到预设池
    if not personas:
        personas = random.sample(ALL_PERSONAS, 6)

    mock_agents = [
        Agent(id=f"agent_{i+1}", name=name, profile=profile, color=color)
        for i, (name, profile, color) in enumerate(personas[:6])
    ]

    agents = [human_agent] + mock_agents

    # 随机分配头像
    avatars = _assign_avatars(len(agents))
    for i, agent in enumerate(agents):
        agent.avatar = avatars[i] if i < len(avatars) else ""

    return agents
