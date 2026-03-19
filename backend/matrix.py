"""
matrix.py - 10×10 亲密度矩阵 + 部落聚合算法
"""
from dataclasses import dataclass, field
from typing import Optional
import math
from config import AGENT_COUNT, TRIBE_THRESHOLD


@dataclass
class AffinityMatrix:
    """
    维护 Agent 两两之间的引力权重。
    agree_with(i, j)  → weight[i][j] += 1, weight[j][i] += 1
    disagree(i, j)    → weight[i][j] -= 1, weight[j][i] -= 1
    """
    n: int = AGENT_COUNT
    weights: list[list[float]] = field(default_factory=list)

    def __post_init__(self):
        self.weights = [[0.0] * self.n for _ in range(self.n)]

    def update(self, agent_ids: list[str], agree_with_id: str, from_id: str) -> None:
        """根据一次赞同/反驳更新矩阵"""
        try:
            i = agent_ids.index(from_id)
            j = agent_ids.index(agree_with_id)
        except ValueError:
            return
        if i == j:
            return
        self.weights[i][j] = min(self.weights[i][j] + 1, 10)
        self.weights[j][i] = min(self.weights[j][i] + 1, 10)  # 引力是双向的

    def to_edges(self, agent_ids: list[str]) -> list[dict]:
        """转换为 ECharts links 格式，只返回权重 > 0 的边"""
        edges = []
        n = len(agent_ids)
        for i in range(n):
            for j in range(i + 1, n):
                w = self.weights[i][j]
                if w > 0:
                    edges.append({
                        "source": agent_ids[i],
                        "target": agent_ids[j],
                        "value":  w,
                        "lineStyle": {"width": max(1, w * 1.5)},
                    })
        return edges

    def detect_tribes(self, agent_ids: list[str]) -> dict[str, int]:
        """
        简单图遍历：如果两个 Agent 的互相引力 >= TRIBE_THRESHOLD，归为同一部落。
        返回 {agent_id: tribe_id} 字典。
        """
        n = len(agent_ids)
        tribe_map = {}  # agent_id → tribe_id
        tribe_counter = 0

        for i in range(n):
            for j in range(i + 1, n):
                if self.weights[i][j] >= TRIBE_THRESHOLD:
                    ai, aj = agent_ids[i], agent_ids[j]
                    tb_i = tribe_map.get(ai)
                    tb_j = tribe_map.get(aj)
                    if tb_i is None and tb_j is None:
                        tribe_map[ai] = tribe_counter
                        tribe_map[aj] = tribe_counter
                        tribe_counter += 1
                    elif tb_i is None:
                        tribe_map[ai] = tb_j
                    elif tb_j is None:
                        tribe_map[aj] = tb_i
                    elif tb_i != tb_j:
                        # 合并部落
                        old = max(tb_i, tb_j)
                        new = min(tb_i, tb_j)
                        tribe_map = {k: (new if v == old else v) for k, v in tribe_map.items()}

        return tribe_map

    def as_2d_list(self) -> list[list[float]]:
        return self.weights


# ── 部落命名（戏剧感拉满）────────────────────────────────────────
TRIBE_NAMES = [
    "赛博存在主义部落",
    "熵增抵抗联盟",
    "无为而治研究院",
    "效率至上委员会",
    "浪漫虚无主义剧团",
    "量子躺平实验室",
]

def get_tribe_name(tribe_id: int) -> str:
    return TRIBE_NAMES[tribe_id % len(TRIBE_NAMES)]
