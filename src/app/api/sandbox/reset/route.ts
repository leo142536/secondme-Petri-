// src/app/api/sandbox/reset/route.ts - 重置沙盒

import { NextResponse } from "next/server";
import { resetSandboxState } from "@/lib/sandbox-state";

export async function GET() {
  resetSandboxState();
  return NextResponse.json({ ok: true });
}
