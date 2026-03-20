"""
generate_avatars.py - 基于刘看山基础图，生成 10 个带彩色圆形光环的 Agent 头像
"""
from PIL import Image, ImageDraw, ImageFilter
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "..", "frontend", "static")
BASE_IMG = os.path.join(STATIC_DIR, "liukanshan_base.png")
OUT_DIR = os.path.join(STATIC_DIR, "avatars")

os.makedirs(OUT_DIR, exist_ok=True)

# Agent 配色表（与 agents.py 一致）
AGENTS = [
    ("agent_0", "#FFD700", "我的分身"),      # 金色 - 真人
    ("agent_1", "#00d4ff", "极致理性码农"),
    ("agent_2", "#9b59b6", "悲观哲学家"),
    ("agent_3", "#e74c3c", "激进创业者"),
    ("agent_4", "#f39c12", "人文学者"),
    ("agent_5", "#2ecc71", "躺平博主"),
    ("agent_6", "#1abc9c", "量化交易员"),
    ("agent_7", "#e67e22", "焦虑中产"),
    ("agent_8", "#e91e63", "激进女性主义者"),
    ("agent_9", "#27ae60", "老庄道家"),
]

SIZE = 200        # 输出尺寸
BORDER = 12       # 光环边框宽度
GLOW_EXTRA = 8    # 外发光额外像素


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_avatar(agent_id: str, color_hex: str, is_human: bool = False):
    """生成单个 Agent 的圆形头像"""
    color = hex_to_rgb(color_hex)
    border_width = BORDER + (4 if is_human else 0)

    # 加载基础图并转 RGBA
    base = Image.open(BASE_IMG).convert("RGBA")

    # 裁成正方形
    w, h = base.size
    sq = min(w, h)
    left = (w - sq) // 2
    top = (h - sq) // 2
    base = base.crop((left, top, left + sq, top + sq))
    base = base.resize((SIZE - border_width * 2, SIZE - border_width * 2), Image.LANCZOS)

    # 创建圆形遮罩
    inner_size = SIZE - border_width * 2
    mask = Image.new("L", (inner_size, inner_size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, inner_size, inner_size), fill=255)

    # 应用圆形遮罩
    circular = Image.new("RGBA", (inner_size, inner_size), (0, 0, 0, 0))
    circular.paste(base, (0, 0), mask)

    # 创建带光环的完整图像
    full = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # 画光环（彩色圆环）
    draw = ImageDraw.Draw(full)
    # 外发光
    for i in range(GLOW_EXTRA, 0, -1):
        alpha = int(80 * (1 - i / GLOW_EXTRA))
        glow_color = (*color, alpha)
        draw.ellipse(
            (i, i, SIZE - i, SIZE - i),
            outline=glow_color,
            width=2,
        )
    # 实心彩色边框
    draw.ellipse(
        (0, 0, SIZE - 1, SIZE - 1),
        outline=(*color, 255),
        width=border_width,
    )

    # 真人 Agent 额外画一个内圈金色线
    if is_human:
        draw.ellipse(
            (border_width - 2, border_width - 2,
             SIZE - border_width + 1, SIZE - border_width + 1),
            outline=(255, 255, 255, 180),
            width=2,
        )

    # 贴入圆形头像
    full.paste(circular, (border_width, border_width), circular)

    # 保存
    out_path = os.path.join(OUT_DIR, f"{agent_id}.png")
    full.save(out_path, "PNG")
    print(f"  ✅ {agent_id} → {out_path}")


def main():
    print("🧫 Petri - 生成 Agent 头像...")
    for agent_id, color, name in AGENTS:
        is_human = agent_id == "agent_0"
        make_avatar(agent_id, color, is_human)
    print(f"\n🎉 完成！{len(AGENTS)} 个头像保存在 {OUT_DIR}")


if __name__ == "__main__":
    main()
