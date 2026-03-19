"""
zhihu.py - 知乎热榜话题拉取（含备用预设）
"""
import httpx
from config import DEFAULT_TOPIC


ZHIHU_HOT_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.zhihu.com/hot",
}


async def fetch_hot_topic() -> str:
    """
    尝试从知乎热榜 API 拿第一条话题，失败则返回预设话题。
    返回格式: "标题 - 摘要"
    """
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=5.0) as client:
            resp = await client.get(ZHIHU_HOT_API)
            resp.raise_for_status()
            data = resp.json()
            item = data["data"][0]["target"]
            title   = item.get("title", "")
            excerpt = item.get("excerpt", "")
            return f"【知乎热榜】{title} — {excerpt}" if title else DEFAULT_TOPIC
    except Exception:
        # 网络不通或反爬时，使用预设硬核话题
        return DEFAULT_TOPIC
