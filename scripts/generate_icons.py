"""生成线性扁平风格 TabBar 图标"""
from PIL import Image, ImageDraw

SIZE = 88
INACTIVE = (153, 153, 153)  # #999
ACTIVE = (26, 115, 232)      # #1a73e8
STROKE = 5
BASE = "E:/pyPro/访客登记系统v1/miniprogram/images"


def draw_home(color, path):
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 屋顶
    roof = [(10, 38), (44, 6), (78, 38)]
    d.line([roof[0], roof[1], roof[2], roof[0]], fill=color, width=STROKE)
    # 墙体
    d.rectangle([14, 38, 74, 80], outline=color, width=STROKE)
    # 门
    d.rectangle([34, 52, 54, 80], outline=color, width=STROKE)
    img.save(path)


def draw_person(color, path):
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 头部
    r = 11
    d.ellipse([44 - r, 20 - r, 44 + r, 20 + r], outline=color, width=STROKE)
    # 身体: 顶部弧形 + 两侧直线
    body_top, body_btm = 34, 78
    d.arc([18, body_top - 14, 70, body_top + 22], 3.14, 0, fill=color, width=STROKE)
    d.line([(18, body_top + 8), (18, body_btm)], fill=color, width=STROKE)
    d.line([(70, body_top + 8), (70, body_btm)], fill=color, width=STROKE)
    img.save(path)


def draw_clipboard(color, path):
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 板子
    d.rounded_rectangle([20, 28, 68, 80], radius=6, outline=color, width=STROKE)
    # 夹子
    d.rounded_rectangle([30, 16, 58, 30], radius=4, outline=color, width=STROKE)
    # 对勾
    x, y = 34, 50
    d.line([(x, y + 6), (x + 8, y + 14), (x + 22, y - 2)], fill=color, width=STROKE)
    img.save(path)


def draw_clock(color, path):
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 表盘
    r = 17
    d.ellipse([44 - r, 40 - r, 44 + r, 40 + r], outline=color, width=STROKE)
    # 中心点
    d.ellipse([42, 38, 46, 42], fill=color)
    # 时针
    d.line([(44, 40), (44, 28)], fill=color, width=STROKE)
    # 分针
    d.line([(44, 40), (52, 34)], fill=color, width=STROKE)
    img.save(path)


if __name__ == '__main__':
    draw_home(INACTIVE, f"{BASE}/home.png")
    draw_home(ACTIVE, f"{BASE}/home-active.png")
    draw_person(INACTIVE, f"{BASE}/mine.png")
    draw_person(ACTIVE, f"{BASE}/mine-active.png")
    draw_clipboard(INACTIVE, f"{BASE}/register.png")
    draw_clipboard(ACTIVE, f"{BASE}/register-active.png")
    draw_clock(INACTIVE, f"{BASE}/history.png")
    draw_clock(ACTIVE, f"{BASE}/history-active.png")
    print("Done! 8 icons generated.")
