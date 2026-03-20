// src/lib/sandbox-state.ts - 全局沙盒状态（Vercel Serverless 用内存单例）
// ⚠️ Serverless 函数无状态，这里用 globalThis 在同一函数实例内维持状态

import { Agent, AffinityMatrix, buildSandbox, DEFAULT_HUMAN_AGENT, getTribeName } from "./agents";

export interface SandboxState {
  agents: Agent[];
  topic: string;
  history: any[];
  currentTick: number;
  maxTicks: number;
  isRunning: boolean;
  finished: boolean;
  tribes: any[];
  matrix: AffinityMatrix;
  events: any[]; // 待消费的 SSE 事件队列
  humanProfile?: string;
}

const g = globalThis as any;

export function getSandboxState(): SandboxState {
  if (!g.__petriSandbox) {
    resetSandboxState();
  }
  return g.__petriSandbox;
}

export function resetSandboxState(): SandboxState {
  const state: SandboxState = {
    agents: [],
    topic: "",
    history: [],
    currentTick: 0,
    maxTicks: 5,
    isRunning: false,
    finished: false,
    tribes: [],
    matrix: new AffinityMatrix(10),
    events: [],
  };
  g.__petriSandbox = state;
  return state;
}

export function initSandbox(humanAgent?: Agent): SandboxState {
  const state = resetSandboxState();
  const human = humanAgent ?? DEFAULT_HUMAN_AGENT;
  state.agents = buildSandbox(human);
  state.matrix = new AffinityMatrix(state.agents.length);
  return state;
}
