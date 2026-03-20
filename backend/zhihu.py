"""
zhihu.py - 知乎热榜话题拉取（官方 API + 备用预设）

使用黑客松开放的知乎官方 API：
  GET https://openapi.zhihu.com/hackathon/hot-list
  鉴权: HMAC-SHA256 签名
"""
import time
import hmac
import hashlib
import base64
import uuid
import httpx
from config import DEFAULT_TOPIC

# ── 知乎 API 凭证（从 .env 或写死均可，按需调整）──────────────
import os
from dotenv import load_dotenv
load_dotenv()

ZHIHU_APP_KEY    = os.getenv("ZHIHU_APP_KEY", "")
ZHIHU_APP_SECRET = os.getenv("ZHIHU_APP_SECRET", "")
ZHIHU_BASE_URL   = "https://openapi.zhihu.com"

# ── 备用：直接抓公开页（不需要凭证）─────────────────────────
ZHIHU_HOT_FALLBACK = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=3"
FALLBACK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.zhihu.com/hot",
}


def _make_zhihu_sign(app_key: str, app_secret: str) -> tuple[str, str, str, str]:
    """按知乎官方签名算法生成请求头所需的值"""
    timestamp = str(int(time.time()))
    log_id = f"request_{uuid.uuid4().hex[:16]}"
    extra_info = ""

    sign_str = f"app_key:{app_key}|ts:{timestamp}|logid:{log_id}|extra_info:{extra_info}"
    signature = base64.b64encode(
        hmac.new(app_secret.encode(), sign_str.encode(), hashlib.sha256).digest()
    ).decode()

    return timestamp, log_id, extra_info, signature


async def _fetch_via_official_api() -> str | None:
    """通过知乎官方 OpenAPI 获取热榜"""
    if not ZHIHU_APP_KEY or not ZHIHU_APP_SECRET:
        return None

    ts, log_id, extra_info, sign = _make_zhihu_sign(ZHIHU_APP_KEY, ZHIHU_APP_SECRET)

    headers = {
        "Content-Type": "application/json",
        "X-App-Key": ZHIHU_APP_KEY,
        "X-Timestamp": ts,
        "X-Log-Id": log_id,
        "X-Extra-Info": extra_info,
        "X-Sign": sign,
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(
            f"{ZHIHU_BASE_URL}/hackathon/hot-list",
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        # 取前 3 条热榜拼成一个多议题场景
        items = data.get("data", [])[:3]
        if items:
            topics = [item.get("title", "") for item in items if item.get("title")]
            return "【知乎热榜】" + " ｜ ".join(topics)
    return None


async def _fetch_via_public_api() -> str | None:
    """备用：直接抓知乎公开热榜页"""
    async with httpx.AsyncClient(headers=FALLBACK_HEADERS, timeout=5.0) as client:
        resp = await client.get(ZHIHU_HOT_FALLBACK)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])[:3]
        topics = []
        for item in items:
            target = item.get("target", {})
            title = target.get("title", "")
            if title:
                topics.append(title)
        if topics:
            return "【知乎热榜】" + " ｜ ".join(topics)
    return None


async def fetch_hot_topic() -> str:
    """
    获取知乎热榜话题，作为培养皿的外部刺激源（试剂）。
    优先级：官方 API → 公开页抓取 → 写死的预设
    """
    # 1. 尝试官方 API
    try:
        result = await _fetch_via_official_api()
        if result:
            return result
    except Exception:
        pass

    # 2. 尝试公开页
    try:
        result = await _fetch_via_public_api()
        if result:
            return result
    except Exception:
        pass

    # 3. 兜底预设
    return DEFAULT_TOPIC
