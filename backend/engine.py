"""
engine.py - asyncio 并发演化引擎（核心）
回合制 Event Loop：每 tick 中 10 个 Agent 并发调用 LLM，更新亲密度矩阵，
通过 asyncio.Queue 向 SSE 端点推送实时事件。
"""
import asyncio
import time
from typing import Optional
from agents import Agent, build_sandbox
from matrix import AffinityMatrix, get_tribe_name
from llm import ask_agent
from zhihu import fetch_hot_topic
from config import MAX_TICKS, AGENT_COUNT


class SandboxEngine:
    def __init__(self):
        self.agents: list[Agent] = []
        self.topic: str = ""
        self.matrix = AffinityMatrix()
        self.history: list[dict] = []          # 上一轮所有人的发言
        self.current_tick: int = 0
        self.is_running: bool = False
        self.tribes: dict[str, int] = {}       # agent_id → tribe_id
        self.finished: bool = False
        self._event_queue: asyncio.Queue = asyncio.Queue()

    # ── 初始化 ──────────────────────────────────────────────────
    async def initialize(self, human_agent: Agent):
        self.agents = build_sandbox(human_agent)
        self.matrix = AffinityMatrix(n=len(self.agents))
        self.history = []
        self.current_tick = 0
        self.finished = False
        self.tribes = {}
        self.topic = await fetch_hot_topic()

        # 向前端发送初始化事件
        await self._push({
            "type": "init",
            "topic": self.topic,
            "agents": [
                {
                    "id":      a.id,
                    "name":    a.name,
                    "profile": a.profile,
                    "color":   a.color,
                    "is_human": a.is_human,
                }
                for a in self.agents
            ],
        })

    # ── 演化主循环 ───────────────────────────────────────────────
    async def run(self):
        """执行 MAX_TICKS 轮演化，每轮所有 Agent 并发响应"""
        self.is_running = True
        agent_ids = [a.id for a in self.agents]

        for tick in range(1, MAX_TICKS + 1):
            self.current_tick = tick
            await self._push({"type": "tick_start", "tick": tick, "max_ticks": MAX_TICKS})

            # ── 并发调用 LLM（核心并发）──────────────────────────
            tasks = [
                ask_agent(
                    agent_id=a.id,
                    agent_name=a.name,
                    profile=a.profile,
                    topic=self.topic,
                    history=self.history,
                    all_agent_ids=agent_ids,
                )
                for a in self.agents
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # ── 处理回合结果 ────────────────────────────────────
            new_history = []
            for a, res in zip(self.agents, results):
                if isinstance(res, Exception):
                    res = {
                        "agent_id": a.id,
                        "agent_name": a.name,
                        "thought": "...",
                        "speech": "（信号中断）",
                        "agree_with_id": agent_ids[0] if a.id != agent_ids[0] else agent_ids[1],
                    }
                a.last_speech = res["speech"]
                new_history.append(res)

                # 更新亲密度矩阵
                self.matrix.update(agent_ids, res["agree_with_id"], res["agent_id"])

                # 向前端推送单条发言
                await self._push({
                    "type":    "speech",
                    "tick":    tick,
                    "agent_id":      res["agent_id"],
                    "agent_name":    res["agent_name"],
                    "speech":        res["speech"],
                    "agree_with_id": res["agree_with_id"],
                })
                await asyncio.sleep(0.05)  # 给前端动画留时间

            self.history = new_history

            # ── 推送最新亲密度矩阵（前端据此更新图） ────────────
            edges = self.matrix.to_edges(agent_ids)
            await self._push({
                "type":  "matrix_update",
                "tick":  tick,
                "edges": edges,
                "matrix": self.matrix.as_2d_list(),
            })

            await asyncio.sleep(1.0)  # tick 间隔，让动画平滑

        # ── 部落检测 ─────────────────────────────────────────────
        self.tribes = self.matrix.detect_tribes(agent_ids)
        tribe_info = _build_tribe_info(self.tribes, self.agents)

        await self._push({
            "type":   "evolution_complete",
            "tribes": tribe_info,
        })

        self.finished = True
        self.is_running = False

    # ── SSE 推送 ─────────────────────────────────────────────────
    async def _push(self, event: dict):
        await self._event_queue.put(event)

    async def event_stream(self):
        """FastAPI SSE 专用异步生成器"""
        while not self.finished or not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=30.0)
                yield event
            except asyncio.TimeoutError:
                yield {"type": "heartbeat"}


# ── 部落信息格式化 ──────────────────────────────────────────────
def _build_tribe_info(tribe_map: dict[str, int], agents: list[Agent]) -> list[dict]:
    """将 tribe_map 按 tribe_id 分组，返回前端友好的结构"""
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


# ── 全局单例（演示用；生产可改为 session-scoped）──────────────
sandbox: Optional[SandboxEngine] = None


def get_sandbox() -> SandboxEngine:
    global sandbox
    if sandbox is None:
        sandbox = SandboxEngine()
    return sandbox
