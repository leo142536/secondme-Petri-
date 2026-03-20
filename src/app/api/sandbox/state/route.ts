// src/app/api/sandbox/state/route.ts - 获取沙盒当前状态

import { NextResponse } from "next/server";
import { getSandboxState } from "@/lib/sandbox-state";

export const dynamic = "force-dynamic";

export async function GET() {
  const state = getSandboxState();
  const agentIds = state.agents.map((a) => a.id);
  return NextResponse.json({
    agents: state.agents,
    edges: state.matrix.toEdges(agentIds),
    current_tick: state.currentTick,
    max_ticks: state.maxTicks,
    finished: state.finished,
  });
}
