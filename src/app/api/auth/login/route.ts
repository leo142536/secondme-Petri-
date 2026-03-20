// src/app/api/auth/login/route.ts - SecondMe OAuth 登录跳转

import { redirect } from "next/navigation";

const CLIENT_ID = process.env.SECONDME_CLIENT_ID || "";
const REDIRECT_URI = process.env.SECONDME_REDIRECT_URI || `${process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"}/api/auth/callback`;
const SECONDME_AUTH_URL = process.env.SECONDME_AUTH_URL || "https://openapi.secondme.world/oauth2/authorize";

export async function GET() {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope: "profile",
  });
  redirect(`${SECONDME_AUTH_URL}?${params.toString()}`);
}
