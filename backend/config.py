"""
config.py - 全局配置
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── SecondMe OAuth ─────────────────────────────────────────────
SECONDME_CLIENT_ID     = os.getenv("SECONDME_CLIENT_ID", "your_client_id")
SECONDME_CLIENT_SECRET = os.getenv("SECONDME_CLIENT_SECRET", "your_client_secret")
SECONDME_REDIRECT_URI  = os.getenv("SECONDME_REDIRECT_URI", "http://localhost:8000/auth/callback")
SECONDME_AUTH_URL      = "https://api.secondme.io/oauth/authorize"
SECONDME_TOKEN_URL     = "https://api.secondme.io/oauth/token"
SECONDME_PROFILE_URL   = "https://api.secondme.io/v1/me/profile"

# ── SecondMe LME（Language Model of Me）────────────────────────
# 用户自己的分身 LLM，以 OAuth token 鉴权，兼容 OpenAI Chat API
SECONDME_LME_BASE_URL  = os.getenv("SECONDME_LME_BASE_URL", "https://api.second.me/lme/v1")
SECONDME_LME_MODEL     = os.getenv("SECONDME_LME_MODEL", "lme")

# ── LLM ────────────────────────────────────────────────────────
LLM_API_KEY   = os.getenv("LLM_API_KEY", "sk-your-key")
LLM_BASE_URL  = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL     = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ── 演化引擎 ────────────────────────────────────────────────────
MAX_TICKS          = int(os.getenv("MAX_TICKS", "5"))        # 回合数
TRIBE_THRESHOLD    = int(os.getenv("TRIBE_THRESHOLD", "4"))  # 引力阈值 → 成部落
AGENT_COUNT        = 10

# ── 知乎热点（备用预设）────────────────────────────────────────
DEFAULT_TOPIC = (
    "AI 时代普通人应该作何选择：彻底躺平还是疯狂内卷？"
    "大模型已经能写代码、画图、做分析，普通人的核心价值还剩什么？"
)

# ── 服务 ────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 8000
