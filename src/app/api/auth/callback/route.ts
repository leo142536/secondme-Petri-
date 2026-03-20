// src/app/api/auth/callback/route.ts - SecondMe OAuth 回调 + 注入沙盒

import { NextRequest, NextResponse } from "next/server";
import { initSandbox } from "@/lib/sandbox-state";
import { Agent } from "@/lib/agents";

const CLIENT_ID = process.env.SECONDME_CLIENT_ID || "";
const CLIENT_SECRET = process.env.SECONDME_CLIENT_SECRET || "";
const REDIRECT_URI = process.env.SECONDME_REDIRECT_URI || `${process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"}/api/auth/callback`;
const TOKEN_URL = process.env.SECONDME_TOKEN_URL || "https://openapi.secondme.world/oauth2/token";
const PROFILE_URL = process.env.SECONDME_PROFILE_URL || "https://openapi.secondme.world/v1/me";

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  if (!code) {
    return NextResponse.redirect(new URL("/?error=no_code", req.url));
  }

  try {
    // 1. 换取 access_token
    const tokenRes = await fetch(TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code,
        redirect_uri: REDIRECT_URI,
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
      }),
    });
    const tokenData = await tokenRes.json();
    const accessToken: string = tokenData.access_token;

    // 2. 拉取用户 Profile
    const profileRes = await fetch(PROFILE_URL, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const profile = await profileRes.json();

    const profileStr = [
      `职业: ${profile.occupation || "未知"}`,
      `兴趣: ${(profile.interests || []).join(", ")}`,
      `性格标签: ${(profile.personality_tags || []).join(", ")}`,
      `自我描述: ${profile.bio || "无"}`,
    ].join("，");

    const humanAgent: Agent = {
      id: "agent_0",
      name: profile.display_name || "我的分身",
      profile: profileStr,
      color: "#FFD700",
      is_human: true,
    };

    // 3. 初始化沙盒（注入真实人格）
    initSandbox(humanAgent);

    return NextResponse.redirect(new URL("/?logged_in=1", req.url));
  } catch (e: any) {
    console.error("OAuth callback error:", e);
    return NextResponse.redirect(new URL("/?error=auth_failed", req.url));
  }
}
