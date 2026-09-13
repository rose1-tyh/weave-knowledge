"""应用图标生成脚本 —— 朱砂圆角方块 + 白色「织」字 → assets/weave.ico

一次性工具：改品牌视觉时重跑即可（需要 Pillow，Windows 自带微软雅黑字体）。
用法：cd backend && python scripts/make_icon.py
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICO_PATH = os.path.join(OUT_DIR, "weave.ico")
PNG_PATH = os.path.join(OUT_DIR, "weave-512.png")

VERMILION = (232, 69, 60)        # --vermilion
SIZES = [16, 24, 32, 48, 64, 128, 256]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",    # 微软雅黑 Bold
    r"C:\Windows\Fonts\simhei.ttf",    # 黑体
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",  # Linux 兜底
]


def _load_font(px: int):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, px)
    raise RuntimeError("未找到可用中文字体（msyh/simhei/noto）")


def render(master: int = 512) -> Image.Image:
    """512px 母版：朱砂圆角方块 + 居中「织」"""
    img = Image.new("RGBA", (master, master), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = int(master * 0.22)
    draw.rounded_rectangle([0, 0, master - 1, master - 1], radius=radius, fill=VERMILION)

    font = _load_font(int(master * 0.62))
    text = "织"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((master - w) / 2 - bbox[0], (master - h) / 2 - bbox[1]),
              text, font=font, fill=(255, 255, 255, 255))
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    master = render()

    # ICO（多尺寸，PyInstaller / pywebview / 窗口通用）
    master.save(ICO_PATH, format="ICO", sizes=[(s, s) for s in SIZES])
    # PNG（README / 发布页用）
    master.save(PNG_PATH, format="PNG")

    print(f"已生成：{ICO_PATH}")
    print(f"已生成：{PNG_PATH}")


if __name__ == "__main__":
    main()
