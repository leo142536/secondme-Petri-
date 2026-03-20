// src/app/api/sandbox/start/route.ts - 启动演化引擎

import { NextResponse } from "next/server";
import { getSandboxState, initSandbox } from "@/lib/sandbox-state";
import { getTribeName } from "@/lib/agents";

const DEFAULT_TOPIC = "AI 时代普通人应该如何选择：彻底躺平还是疯狂内卷？";
const MAX_TICKS = parseInt(process.env.MAX_TICKS || "5");
const LLM_API_KEY = process.env.LLM_API_KEY || "";
const LLM_BASE_URL = process.env.LLM_BASE_URL || "https://api.openai.com/v1";
const LLM_MODEL = process.env.LLM_MODEL || "gpt-4o-mini";

async function fetchTopic(): Promise<string> {
  try {
    const res = await fetch(
      "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=1",
      {
        headers: { "User-Agent": "Mozilla/5.0" },
        next: { revalidate: 300 },
      }
    );
    const data = await res.json();
    const title = data?.data?.[0]?.target?.title;
    return title ? `${title}（来自知乎热榜）` : DEFAULT_TOPIC;
  } catch {
    return DEFAULT_TOPIC;
  }
}

async function askAgent(params: {
  agentId: string; agentName: string; profile: string;
  topic: string; history: any[]; allAgentIds: string[];
}): Promise<any> {
  const { agentId, agentName, profile, topic, history, allAgentIds } = params;

  const historyContext = history.length === 0
    ? "（这是第一回合，广场上还没有任何发言）"
    : history.map((h: any) => `  [${h.agent_id}] ${h.agent_name}: ${h.speech}`).join("\n");

  const prompt = `系统设定：你是用户 ${agentName} 的数字分身，性格画像：${profile}。

当前世界大事件（知乎热点）：${topic}

上一回合广场上的核心言论有：
${historyContext}

行动指令：请结合你的人设，用极简、犀利的口语（限 30 字内）发表你的反驳或赞同。
寻找一个你最认同的发言者，试图与他结盟。

强制返回 JSON 格式（不要包含任何其他文字）：
{
  "thought": "你的内部推理(10字以内)",
  "speech": "你的公开发言(30字以内)",
  "agree_with_id": "你最认同的某人ID（必须是10个Agent之一）"
}`;

  try {
    const res = await fetch(`${LLM_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${LLM_API_KEY}`,
      },
      body: JSON.stringify({
        model: LLM_MODEL,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.85,
        max_tokens: 200,
        response_format: { type: "json_object" },
      }),
    });
    const data = await res.json();
    const result = JSON.parse(data.choices[0].message.content.trim());

    // 校验 agree_with_id
    if (!allAgentIds.includes(result.agree_with_id) || result.agree_with_id === agentId) {
      result.agree_with_id = allAgentIds.find((id) => id !== agentId) ?? allAgentIds[0];
    }
    return { agentId, agentName, ...result };
  } catch {
    const fallbackAgreeId = allAgentIds.find((id) => id !== agentId) ?? allAgentIds[0];
    return { agentId, agentName, thought: "...", speech: "（信号中断）", agree_with_id: fallbackAgreeId };
  }
}

export async function POST() {
  try {
    const state = initSandbox();
    state.maxTicks = MAX_TICKS;
    state.isRunning = true;
    state.finished = false;

    // 获取议题
    state.topic = await fetchTopic();
    const agentIds = state.agents.map((a) => a.id);

    // 推送初始化事件
    state.events.push({
      type: "init",
      topic: state.topic,
      agents: state.agents.map((a) => ({
        id: a.id, name: a.name, profile: a.profile,
        color: a.color, is_human: a.is_human,
      })),
    });

    // 异步执行演化循环（不 await，让 POST 立即返回，SSE 拉取事件）
    runEvolution(state, agentIds, MAX_TICKS).catch(console.error);

    return NextResponse.json({ ok: true, topic: state.topic });
  } catch (e: any) {
    return NextResponse.json({ detail: e.message }, { status: 500 });
  }
}

async function runEvolution(state: any, agentIds: string[], maxTicks: number) {
  for (let tick = 1; tick <= maxTicks; tick++) {
    state.currentTick = tick;
    state.events.push({ type: "tick_start", tick, max_ticks: maxTicks });

    // 并发调用所有 Agent
    const results = await Promise.all(
      state.agents.map((a: any) =>
        askAgent({
          agentId: a.id, agentName: a.name, profile: a.profile,
          topic: state.topic, history: state.history, allAgentIds: agentIds,
        })
      )
    );

    const newHistory: any[] = [];
    for (const res of results) {
      state.matrix.update(agentIds, res.agree_with_id, res.agentId);
      newHistory.push({ agent_id: res.agentId, agent_name: res.agentName, speech: res.speech });
      state.events.push({
        type: "speech",
        tick,
        agent_id: res.agentId,
        agent_name: res.agentName,
        speech: res.speech,
        agree_with_id: res.agree_with_id,
      });
    }
    state.history = newHistory;

    const edges = state.matrix.toEdges(agentIds);
    state.events.push({ type: "matrix_update", tick, edges });

    await new Promise((r) => setTimeout(r, 500));
  }

  // 部落检测
  const tribeMap = state.matrix.detectTribes(agentIds);
  const groups: Record<number, any[]> = {};
  for (const [agentId, tribeId] of Object.entries(tribeMap)) {
    if (!groups[tribeId as number]) groups[tribeId as number] = [];
    const agent = state.agents.find((a: any) => a.id === agentId);
    if (agent) groups[tribeId as number].push({ name: agent.name, color: agent.color, is_human: agent.is_human });
  }

  const tribes = Object.entries(groups).map(([tribeId, members]) => ({
    tribe_id: Number(tribeId),
    tribe_name: getTribeName(Number(tribeId)),
    members,
    has_human: members.some((m: any) => m.is_human),
  }));

  state.events.push({ type: "evolution_complete", tribes });
  state.finished = true;
  state.isRunning = false;
}
