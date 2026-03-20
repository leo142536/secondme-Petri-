"""
generate_avatar_pool.py
收集所有 bee_flat_* + bee_agent_* + bee_pool_* 基础图
裁正方形 → 去白底/黑底 → 透明 PNG → 存入 avatar_pool
"""
from PIL import Image
import numpy as np
import os
import glob

BRAIN_DIR = "/Users/aaa/.gemini/antigravity/brain/f0a4b4fa-0a3d-41a6-973c-f6811181d8fa"
OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "frontend", "static", "avatar_pool"
)

SIZE = 256
BG_THRESHOLD = 240  # 白底阈值（RGB 各通道 > 此值视为背景）
BG_DARK_THRESHOLD = 25  # 黑底阈值（RGB 各通道 < 此值视为背景）


def remove_background(img: Image.Image) -> Image.Image:
    """去除白色或黑色背景，转为透明"""
    img = img.convert("RGBA")
    data = np.array(img)

    # 检测四个角的平均颜色，判断是白底还是黑底
    corners = [
        data[0, 0, :3], data[0, -1, :3],
        data[-1, 0, :3], data[-1, -1, :3],
    ]
    avg_corner = np.mean(corners, axis=0)

    if avg_corner.mean() > 200:
        # 白底：RGB 各通道都高于阈值的像素变透明
        mask = (data[:, :, 0] > BG_THRESHOLD) & \
               (data[:, :, 1] > BG_THRESHOLD) & \
               (data[:, :, 2] > BG_THRESHOLD)
    elif avg_corner.mean() < 40:
        # 黑底：RGB 各通道都低于阈值的像素变透明
        mask = (data[:, :, 0] < BG_DARK_THRESHOLD) & \
               (data[:, :, 1] < BG_DARK_THRESHOLD) & \
               (data[:, :, 2] < BG_DARK_THRESHOLD)
    else:
        # 无明显纯色背景，不处理
        return img

    data[mask, 3] = 0  # 设置 alpha = 0
    return Image.fromarray(data)


def process_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(OUT_DIR, "*.png")):
        os.remove(old)

    # 收集所有基础图（优先 bee_flat，再 bee_agent / bee_pool）
    patterns = [
        os.path.join(BRAIN_DIR, "bee_flat_*_*.png"),
        os.path.join(BRAIN_DIR, "bee_agent_*_*.png"),
        os.path.join(BRAIN_DIR, "bee_pool_*_*.png"),
        os.path.join(BRAIN_DIR, "bee_extra_*_*.png"),
    ]
    base_files = {}
    for pattern in patterns:
        for f in glob.glob(pattern):
            basename = os.path.basename(f)
            parts = basename.rsplit("_", 1)
            key = parts[0]
            if key not in base_files or f > base_files[key]:
                base_files[key] = f

    print(f"📦 找到 {len(base_files)} 个基础图")

    idx = 0
    for key in sorted(base_files.keys()):
        filepath = base_files[key]
        try:
            img = Image.open(filepath)
        except Exception as e:
            print(f"  ⚠️ 跳过 {key}: {e}")
            continue

        # 裁为正方形
        w, h = img.size
        sq = min(w, h)
        left, top = (w - sq) // 2, (h - sq) // 2
        img = img.crop((left, top, left + sq, top + sq))
        img = img.resize((SIZE, SIZE), Image.LANCZOS)

        # 去背景
        img = remove_background(img)

        out_name = f"avatar_{idx:03d}.png"
        img.save(os.path.join(OUT_DIR, out_name), "PNG")
        print(f"  ✅ {key} → {out_name}")
        idx += 1

    print(f"\n🎉 共 {idx} 个透明头像 → {OUT_DIR}")


if __name__ == "__main__":
    process_all()
