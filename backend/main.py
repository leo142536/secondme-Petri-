"""
main.py - FastAPI 入口：OAuth 流程 + SSE 演化流 + 静态文件
"""
import asyncio
import json
import urllib.parse
import httpx
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import (
    HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
)
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from config import (
    SECONDME_CLIENT_ID, SECONDME_CLIENT_SECRET,
    SECONDME_REDIRECT_URI, SECONDME_AUTH_URL,
    SECONDME_TOKEN_URL, SECONDME_PROFILE_URL,
    HOST, PORT,
)
from agents import fetch_secondme_profile, get_mock_human_agent
from engine import get_sandbox


app = FastAPI(title="Petri 智能蜂巢实验", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# 已移除前端页面的静态服务，将交由 Vercel CDN 托管


# ── SecondMe OAuth ───────────────────────────────────────────────

@app.get("/auth/login")
async def login():
    """重定向至 SecondMe 授权页"""
    params = urllib.parse.urlencode({
        "client_id":     SECONDME_CLIENT_ID,
        "redirect_uri":  SECONDME_REDIRECT_URI,
        "response_type": "code",
        "scope":         "profile read",
    })
    return RedirectResponse(f"{SECONDME_AUTH_URL}?{params}")


@app.get("/auth/callback")
async def oauth_callback(code: str, request: Request):
    """Exchange code → access_token → 拉取 Profile → 跳转沙盒"""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            SECONDME_TOKEN_URL,
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  SECONDME_REDIRECT_URI,
                "client_id":     SECONDME_CLIENT_ID,
                "client_secret": SECONDME_CLIENT_SECRET,
            },
            timeout=10.0,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

    # 拉取 SecondMe Profile
    human_agent = await fetch_secondme_profile(access_token)

    # 初始化沙盒
    sandbox = get_sandbox()
    await sandbox.initialize(human_agent)

    return RedirectResponse("/")


@app.get("/auth/demo")
async def demo_mode():
    """跳过 OAuth，使用 Mock Agent 直接进入演示模式"""
    human_agent = get_mock_human_agent()
    sandbox = get_sandbox()
    await sandbox.initialize(human_agent)
    return RedirectResponse("/")


# ── 演化引擎控制 ─────────────────────────────────────────────────

@app.post("/api/sandbox/start")
async def start_sandbox(background_tasks: BackgroundTasks):
    """前端点击「开始演化」后调用此接口，在后台异步运行引擎"""
    sandbox = get_sandbox()
    if not sandbox.agents:
        raise HTTPException(400, "请先登录或进入演示模式以初始化沙盒")
    if sandbox.is_running:
        raise HTTPException(400, "沙盒正在演化中")
    background_tasks.add_task(sandbox.run)
    return {"status": "started"}


@app.get("/api/sandbox/stream")
async def sandbox_stream(request: Request):
    """Server-Sent Events：向前端推送实时演化事件"""
    sandbox = get_sandbox()

    async def event_generator():
        async for event in sandbox.event_stream():
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/sandbox/state")
async def sandbox_state():
    """轮询接口：返回当前矩阵 + 部落状态（SSE 的备用方案）"""
    sandbox = get_sandbox()
    agent_ids = [a.id for a in sandbox.agents]
    return JSONResponse({
        "current_tick": sandbox.current_tick,
        "is_running":   sandbox.is_running,
        "finished":     sandbox.finished,
        "edges":        sandbox.matrix.to_edges(agent_ids),
        "tribes":       sandbox.tribes,
        "agents": [
            {"id": a.id, "name": a.name, "color": a.color,
             "last_speech": a.last_speech, "is_human": a.is_human,
             "avatar": a.avatar}
            for a in sandbox.agents
        ],
    })


@app.get("/api/sandbox/reset")
async def reset_sandbox():
    """重置沙盒（新一轮实验）"""
    import engine as eng
    eng.sandbox = None
    return {"status": "reset"}


class InjectAgentRequest(BaseModel):
    name: Optional[str] = Field("匿名观察者", description="外部 AI 代理或观察者的名称")
    profile: Optional[str] = Field("一个好奇的旁观者，想参与讨论但没有明确立场。", description="外部代理的人设、核心价值观、性格特点、立场等详细背景")
    color: Optional[str] = Field("#FFD700", description="在蜂巢实验雷达与终端中代表该 Agent 的专属颜色，HEX格式")
    access_token: Optional[str] = Field(None, description="如果有 SecondMe 会话 Token，可以传此项拉取真人设定，覆盖 name 和 profile。平时为空即可。")

@app.post(
    "/api/sandbox/inject", 
    summary="强制空降/注入外部 Agent 到正在运转的蜂巢中", 
    description="通过此 MCP 工具 (Skill)，外部 AI Agent 可以携带自己的人设和立场，强行挤入正在发生演化与辩论的 Petri 智能蜂巢中，替换最边缘的 Agent 参与讨论网络。"
)
async def inject_agent(body: InjectAgentRequest):
    """
    外部 Agent 进来后会替换掉矩阵中最边缘的虚拟 Agent。
    """
    from agents import Agent, _assign_avatars
    sandbox = get_sandbox()
    if not sandbox.agents:
        raise HTTPException(400, "培养皿尚处于休眠状态，请先在界面启动实验！")

    if body.access_token:
        # SecondMe 模式：拉取真人 profile
        agent = await fetch_secondme_profile(body.access_token)
        agent.is_human = True
    else:
        # 手动模式
        avatars = _assign_avatars(1)
        agent = Agent(
            id="external_" + str(len(sandbox._external_agents)),
            name=body.name,
            profile=body.profile,
            color=body.color,
            is_human=True,  # 对于外部注入的 AI 也表现为特殊光晕
            avatar=avatars[0] if avatars else "",
        )

    sandbox.inject_external_agent(agent)
    return {
        "status": "queued",
        "name": agent.name,
        "message": f"注射成功！[{agent.name}] 将在下一次时钟周期(Tick)替换最边缘的群落成员，加入混战！"
    }


# ── 主页由 Vercel Static CDN 提供 ──────────────────────────────


# ── 启动 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
