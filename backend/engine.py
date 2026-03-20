"""
engine.py - asyncio 并发演化引擎（核心）

特性：
  1. 根据议题复杂度自动决定演化轮数（3~8 轮随机）
  2. 动态 Agent 进出：每轮有概率淘汰弱势 Agent 或引入新 Agent
  3. 支持外部 SecondMe Agent 注入（API 预留）
"""
import asyncio
import random
import time
from typing import Optional
from agents import Agent, build_sandbox, ALL_PERSONAS, _assign_avatars
from matrix import AffinityMatrix, get_tribe_name
from llm import ask_agent
from zhihu import fetch_hot_topic
from config import MAX_TICKS, AGENT_COUNT

# ── 候补 Agent 动态生成（排除已在场角色）────────────────────────
def _build_reserve_pool(current_agents: list[Agent]) -> list[Agent]:
    """从全角色池中排除当前在场角色，构成候补池"""
    current_names = {a.name for a in current_agents}
    reserves = []
    idx = 100
    for name, profile, color in ALL_PERSONAS:
        if name not in current_names:
            reserves.append(Agent(
                id=f"reserve_{idx}",
                name=name,
                profile=profile,
                color=color,
            ))
            idx += 1
    return reserves


def _decide_max_ticks(topic: str) -> int:
    """根据议题复杂度决定演化轮数"""
    # 关键词越多说明议题越复杂
    complex_keywords = ["AI", "人工智能", "经济", "房价", "教育", "医疗", "战争",
                        "就业", "生育", "阶层", "内卷", "躺平", "科技"]
    hit_count = sum(1 for kw in complex_keywords if kw in topic)

    if hit_count >= 4:
        return random.randint(6, 8)   # 高复杂度议题
    elif hit_count >= 2:
        return random.randint(4, 6)   # 中等复杂度
    else:
        return random.randint(3, 5)   # 一般议题


class SandboxEngine:
    def __init__(self):
        self.agents: list[Agent] = []
        self.topic: str = ""
        self.matrix = AffinityMatrix()
        self.history: list[dict] = []
        self.current_tick: int = 0
        self.max_ticks: int = MAX_TICKS
        self.is_running: bool = False
        self.tribes: dict[str, int] = {}
        self.finished: bool = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._reserve_pool: list[Agent] = []  # 候补池（初始化时动态构建）
        self._external_agents: list[Agent] = []  # 外部注入的 SecondMe Agent

    # ── 初始化 ──────────────────────────────────────────────────
    async def initialize(self, human_agent: Agent):
        self.topic = await fetch_hot_topic()
        all_agents = await build_sandbox(human_agent, topic=self.topic)
        
        # 初始只放 4 个（加快首轮响应，之后每轮陆续加入）
        init_count = min(4, len(all_agents))
        self.agents = all_agents[:init_count]
        
        self.matrix = AffinityMatrix(n=len(self.agents))
        self.history = []
        self.current_tick = 0
        self.finished = False
        self.tribes = {}
        # 将剩余的生成的 AI，加上预设池的备用合并为候补池
        self._reserve_pool = all_agents[init_count:] + _build_reserve_pool(self.agents)

        # 根据议题决定轮数
        self.max_ticks = _decide_max_ticks(self.topic)

        await self._push({
            "type": "init",
            "topic": self.topic,
            "max_ticks": self.max_ticks,
            "agents": [
                {
                    "id":       a.id,
                    "name":     a.name,
                    "profile":  a.profile,
                    "color":    a.color,
                    "is_human": a.is_human,
                    "avatar":   a.avatar,
                }
                for a in self.agents
            ],
        })

    # ── 外部 Agent 注入 ─────────────────────────────────────────
    def inject_external_agent(self, agent: Agent):
        """API 预留：运行时注入外部 SecondMe Agent"""
        self._external_agents.append(agent)

    # ── Agent 动态进出 ──────────────────────────────────────────
    async def _maybe_rotate_agents(self, tick: int):
        """每轮动态加入新Agent（补齐至少6人），或有概率淘汰弱势Agent"""
        if tick <= 1 or tick >= self.max_ticks:
            return  # 第一轮和最后一轮不换人

        # 如果场上人数少于 6 人，这回合一定加人
        # 否则 30% 概率换人
        action = "none"
        if len(self.agents) < 6:
            action = "add"
        elif random.random() <= 0.3:
            action = "swap"

        if action == "none":
            return

        agent_ids = [a.id for a in self.agents]

        # 选人
        new_agent = None
        if self._external_agents:
            new_agent = self._external_agents.pop(0)
        elif self._reserve_pool:
            new_agent = self._reserve_pool.pop(0)
        
        if not new_agent:
            return
            
        avatars = _assign_avatars(1)
        new_agent.avatar = avatars[0] if avatars else ""

        if action == "add":
            # 向局内加入新 Agent
            if not new_agent.id.startswith("agent_"):
                new_agent.id = f"agent_dyn_{len(self.agents) + 1}"
            self.agents.append(new_agent)
            self.matrix.add_agent()

            await self._push({
                "type": "agent_added",
                "tick": tick,
                "joined": {
                    "id":       new_agent.id,
                    "name":     new_agent.name,
                    "profile":  new_agent.profile,
                    "color":    new_agent.color,
                    "is_human": new_agent.is_human,
                    "avatar":   new_agent.avatar,
                }
            })
        elif action == "swap":
            # 找出最"边缘化"的非真人 Agent（亲密度总和最低的）
            non_human = [a for a in self.agents if not a.is_human]
            if not non_human:
                return

            weakest = min(non_human, key=lambda a: self.matrix.agent_total(
                agent_ids.index(a.id), len(agent_ids)
            ))

            idx = self.agents.index(weakest)
            old_name = weakest.name
            new_agent.id = weakest.id  # 复用 id 槽位
            self.agents[idx] = new_agent

            await self._push({
                "type":       "agent_swap",
                "tick":       tick,
                "left_name":  old_name,
                "left_id":    new_agent.id,
                "joined":     {
                    "id":       new_agent.id,
                    "name":     new_agent.name,
                    "profile":  new_agent.profile,
                    "color":    new_agent.color,
                    "is_human": new_agent.is_human,
                    "avatar":   new_agent.avatar,
                },
            })

    # ── 演化主循环 ───────────────────────────────────────────────
    async def run(self):
        self.is_running = True
        agent_ids = [a.id for a in self.agents]

        for tick in range(1, self.max_ticks + 1):
            self.current_tick = tick

            # 动态换人
            await self._maybe_rotate_agents(tick)
            agent_ids = [a.id for a in self.agents]  # 刷新 id 列表

            await self._push({
                "type": "tick_start", "tick": tick, "max_ticks": self.max_ticks
            })

            # ── 并发调用 LLM（实时推送：谁先回来谁先显示） ──────
            agent_map = {}  # task -> agent
            for a in self.agents:
                task = asyncio.create_task(ask_agent(
                    agent_id=a.id,
                    agent_name=a.name,
                    profile=a.profile,
                    topic=self.topic,
                    history=self.history,
                    all_agent_ids=agent_ids,
                    user_token=a.access_token,
                ))
                agent_map[task] = a

            new_history = []
            for coro in asyncio.as_completed(agent_map.keys()):
                try:
                    res = await coro
                except Exception as exc:
                    # 找到对应的 agent（从尚未处理的里面找）
                    a = None
                    for t, ag in agent_map.items():
                        if t.done() and ag.last_speech == "":
                            a = ag
                            break
                    if a is None:
                        a = list(agent_map.values())[0]
                    res = {
                        "agent_id": a.id,
                        "agent_name": a.name,
                        "thought": "...",
                        "speech": f"[API Error] {str(exc)[:80]}",
                        "agree_with_id": agent_ids[0] if a.id != agent_ids[0] else agent_ids[1],
                    }

                # 找到这个结果对应的 agent
                ag = None
                for t, a in agent_map.items():
                    if a.id == res.get("agent_id"):
                        ag = a
                        break
                if ag:
                    ag.last_speech = res["speech"]

                new_history.append(res)
                self.matrix.update(agent_ids, res["agree_with_id"], res["agent_id"])

                # 实时推送到前端——不等其他 Agent
                await self._push({
                    "type":          "speech",
                    "tick":          tick,
                    "agent_id":      res["agent_id"],
                    "agent_name":    res["agent_name"],
                    "speech":        res["speech"],
                    "agree_with_id": res["agree_with_id"],
                })
                await asyncio.sleep(0.02)

            self.history = new_history

            edges = self.matrix.to_edges(agent_ids)
            await self._push({
                "type":   "matrix_update",
                "tick":   tick,
                "edges":  edges,
                "matrix": self.matrix.as_2d_list(),
            })

            await asyncio.sleep(0.3)  # 回合间隔缩短

        # ── 部落检测 ─────────────────────────────────────────
        self.tribes = self.matrix.detect_tribes(agent_ids)
        tribe_info = _build_tribe_info(self.tribes, self.agents)

        await self._push({
            "type":   "evolution_complete",
            "tribes": tribe_info,
        })

        self.finished = True
        self.is_running = False

    # ── SSE 推送 ──────────────────────────────────────────────
    async def _push(self, event: dict):
        await self._event_queue.put(event)

    async def event_stream(self):
        while not self.finished or not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=30.0)
                yield event
            except asyncio.TimeoutError:
                yield {"type": "heartbeat"}


# ── 部落信息格式化 ──────────────────────────────────────────────
def _build_tribe_info(tribe_map: dict[str, int], agents: list[Agent]) -> list[dict]:
    groups: dict[int, list[dict]] = {}
    for agent_id, tribe_id in tribe_map.items():
        groups.setdefault(tribe_id, [])
        agent = next((a for a in agents if a.id == agent_id), None)
        if agent:
            groups[tribe_id].append({
                "id":       agent.id,
                "name":     agent.name,
                "color":    agent.color,
                "is_human": agent.is_human,
            })

    result = []
    for tribe_id, members in groups.items():
        result.append({
            "tribe_id":   tribe_id,
            "tribe_name": get_tribe_name(tribe_id),
            "members":    members,
            "has_human":  any(m["is_human"] for m in members),
        })
    return result


# ── 全局单例 ────────────────────────────────────────────────────
sandbox: Optional[SandboxEngine] = None


def get_sandbox() -> SandboxEngine:
    global sandbox
    if sandbox is None:
        sandbox = SandboxEngine()
    return sandbox
