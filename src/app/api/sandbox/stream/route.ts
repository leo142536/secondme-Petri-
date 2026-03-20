// src/app/api/sandbox/stream/route.ts - SSE 实时事件流

import { NextResponse } from "next/server";
import { getSandboxState } from "@/lib/sandbox-state";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const send = (data: any) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      };

      let waited = 0;
      const MAX_WAIT = 120_000; // 最长等 120 秒

      while (waited < MAX_WAIT) {
        const state = getSandboxState();

        // 消费所有待发事件
        while (state.events.length > 0) {
          const evt = state.events.shift();
          if (evt) send(evt);
        }

        if (state.finished) {
          controller.close();
          return;
        }

        // 发心跳保持连接
        if (waited % 5000 < 200) {
          send({ type: "heartbeat" });
        }

        await new Promise((r) => setTimeout(r, 200));
        waited += 200;
      }

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "Access-Control-Allow-Origin": "*",
    },
  });
}
