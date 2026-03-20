// src/lib/agents.ts - Agent 定义与 Mock 数据

export interface Agent {
  id: string;
  name: string;
  profile: string;
  color: string;
  is_human: boolean;
  last_speech?: string;
}

export const MOCK_AGENTS: Agent[] = [
  { id: "agent_1", name: "极致理性码农", profile: "INTJ，相信万物皆算法，用数据否定一切感性，拒绝内耗，崇尚效率最大化。", color: "#00d4ff", is_human: false },
  { id: "agent_2", name: "悲观哲学家",   profile: "加缪的信徒，认为人生荒诞、努力徒劳，AI 只是加速虚无的工具。", color: "#9b59b6", is_human: false },
  { id: "agent_3", name: "激进创业者",   profile: "连续创业三次，相信颠覆即正义，把躺平视为懦夫行为，越卷越兴奋。", color: "#e74c3c", is_human: false },
  { id: "agent_4", name: "人文学者",     profile: "文学博士，担忧技术侵蚀人文，认为情感和意义才是人的护城河。", color: "#f39c12", is_human: false },
  { id: "agent_5", name: "躺平博主",     profile: "月薪三千却心满意足，认为资本主义是骗局，极简生活才是自由。", color: "#2ecc71", is_human: false },
  { id: "agent_6", name: "量化交易员",   profile: "把一切都建模，包括人类行为。认为内卷/躺平是伪命题，套利才是真理。", color: "#1abc9c", is_human: false },
  { id: "agent_7", name: "焦虑中产",     profile: "房贷车贷孩子，每天凌晨两点还在刷副业教程，既不想卷又不敢躺。", color: "#e67e22", is_human: false },
  { id: "agent_8", name: "激进女性主义者", profile: "认为内卷文化本质是父权叙事，拒绝以男性定义的成功为标准奋斗。", color: "#e91e63", is_human: false },
  { id: "agent_9", name: "老庄道家",     profile: "研究《道德经》二十年，认为无为才是最高效率，水善利万物而不争。", color: "#27ae60", is_human: false },
];

export const DEFAULT_HUMAN_AGENT: Agent = {
  id: "agent_0",
  name: "我的分身（演示）",
  profile: "28 岁产品经理，ENFP，喜欢哲学和技术，对 AI 时代充满期待又有些迷茫。",
  color: "#FFD700",
  is_human: true,
};

export function buildSandbox(humanAgent: Agent): Agent[] {
  return [humanAgent, ...MOCK_AGENTS];
}

// ── 亲密度矩阵 ──────────────────────────────────────────────────
export class AffinityMatrix {
  private mat: number[][];
  private n: number;

  constructor(n = 10) {
    this.n = n;
    this.mat = Array.from({ length: n }, () => Array(n).fill(0));
  }

  private idx(agentIds: string[], id: string): number {
    return agentIds.indexOf(id);
  }

  update(agentIds: string[], agreeWithId: string, selfId: string) {
    const i = this.idx(agentIds, selfId);
    const j = this.idx(agentIds, agreeWithId);
    if (i >= 0 && j >= 0 && i !== j) {
      this.mat[i][j] += 1;
      this.mat[j][i] += 0.5; // 对方被动正反馈
    }
  }

  toEdges(agentIds: string[]): { source: string; target: string; weight: number }[] {
    const edges: { source: string; target: string; weight: number }[] = [];
    for (let i = 0; i < this.n; i++) {
      for (let j = i + 1; j < this.n; j++) {
        const w = this.mat[i][j] + this.mat[j][i];
        if (w > 0) {
          edges.push({ source: agentIds[i], target: agentIds[j], weight: w });
        }
      }
    }
    return edges;
  }

  detectTribes(agentIds: string[], threshold = 4): Record<string, number> {
    const n = agentIds.length;
    const parent = agentIds.map((_, i) => i);
    const find = (x: number): number => (parent[x] === x ? x : (parent[x] = find(parent[x])));
    const union = (a: number, b: number) => { parent[find(a)] = find(b); };

    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        if (this.mat[i][j] + this.mat[j][i] >= threshold) union(i, j);
      }
    }

    const rootMap: Record<number, number> = {};
    let nextId = 0;
    const result: Record<string, number> = {};
    for (let i = 0; i < n; i++) {
      const root = find(i);
      if (rootMap[root] === undefined) rootMap[root] = nextId++;
      result[agentIds[i]] = rootMap[root];
    }
    return result;
  }
}

const TRIBE_NAMES = [
  "熵增抵抗联盟", "赛博存在主义部落", "量子躺平实验室",
  "超理性自由邦", "人文复兴联合体", "混沌变量集群",
];

export function getTribeName(id: number): string {
  return TRIBE_NAMES[id % TRIBE_NAMES.length];
}
