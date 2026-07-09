"""
生成小程序所需占位图片
- tabBar 图标 (81x81)
- 首页背景图 (750x420)
- 公司滚动展示图 (280x180)
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'miniprogram', 'images')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_icon(name, bg_color, fg_color, text=''):
    """创建 81x81 的 tabBar 图标"""
    size = 81
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角背景圆
    margin = 8
    draw.ellipse([margin, margin, size - margin, size - margin], fill=bg_color)

    # 绘制简单图标符号
    if text:
        # 使用文字作为图标
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 36)
        except Exception:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
            except Exception:
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (size - tw) // 2
        y = (size - th) // 2 - 2
        draw.text((x, y), text, fill=fg_color, font=font)

    path = os.path.join(OUTPUT_DIR, name)
    img.save(path)
    print(f'Created: {path}')


def create_hero_bg():
    """创建首页背景图 750x420"""
    w, h = 750, 420
    img = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(img)

    # 渐变效果（模拟）
    for i in range(h):
        r = int(26 + (21 - 26) * i / h)    # 26 -> 21
        g = int(115 + (87 - 115) * i / h)  # 115 -> 87
        b = int(232 + (176 - 232) * i / h)  # 232 -> 176
        draw.line([(0, i), (w, i)], fill=(r, g, b))

    # 装饰性几何图形
    # 圆形
    draw.ellipse([500, -50, 850, 300], fill=(255, 255, 255, 25), outline=None)
    draw.ellipse([600, 150, 800, 350], fill=(255, 255, 255, 20), outline=None)

    # 文字
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 48)
        font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    except Exception:
        try:
            font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
            font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

    draw.text((50, 160), '访客登记系统', fill=(255, 255, 255), font=font_large)
    draw.text((50, 230), 'Visitor Registration System', fill=(255, 255, 255, 200), font=font_small)

    path = os.path.join(OUTPUT_DIR, 'hero-bg.png')
    img.save(path)
    print(f'Created: {path}')
    return path


def create_scroll_image(index, color_scheme):
    """创建公司滚动展示图 280x180"""
    w, h = 280, 180
    img = Image.new('RGB', (w, h), color_scheme['bg'])
    draw = ImageDraw.Draw(img)

    # 装饰矩形
    draw.rectangle([20, 30, 260, 60], fill=color_scheme['accent'])
    draw.rectangle([20, 80, 200, 110], fill=color_scheme['accent'])

    # 小方块装饰
    for i in range(3):
        x = 20 + i * 60
        draw.rectangle([x, 130, x + 40, 160], fill=color_scheme['accent'])

    # 标签
    labels = ['办公环境', '公司大楼', '会议室']
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
    except Exception:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
        except Exception:
            font = ImageFont.load_default()

    draw.text((80, 70), labels[index], fill=(255, 255, 255), font=font)

    path = os.path.join(OUTPUT_DIR, f'company-{index + 1}.png')
    img.save(path)
    print(f'Created: {path}')
    return path


if __name__ == '__main__':
    print('Generating placeholder images...')

    # TabBar 图标
    # 首页图标 - 房屋形状
    create_icon('home.png', '#CCCCCC', '#FFFFFF', '🏠')
    create_icon('home-active.png', '#1a73e8', '#FFFFFF', '🏠')

    # 登记图标 - 笔形状
    create_icon('register.png', '#CCCCCC', '#FFFFFF', '✏️')
    create_icon('register-active.png', '#1a73e8', '#FFFFFF', '✏️')

    # 我的图标 - 人物形状
    create_icon('mine.png', '#CCCCCC', '#FFFFFF', '👤')
    create_icon('mine-active.png', '#1a73e8', '#FFFFFF', '👤')

    # 首页背景图
    create_hero_bg()

    # 公司滚动展示图 (3张)
    color_schemes = [
        {'bg': (52, 73, 94), 'accent': (255, 255, 255, 50)},    # 深蓝灰
        {'bg': (41, 128, 185), 'accent': (255, 255, 255, 50)},   # 蓝色
        {'bg': (39, 174, 96), 'accent': (255, 255, 255, 50)},    # 绿色
    ]
    scroll_images = []
    for i in range(3):
        path = create_scroll_image(i, color_schemes[i])
        scroll_images.append(f'/images/company-{i + 1}.png')

    # 更新系统配置中的图片路径
    hero_path = '/images/hero-bg.png'
    print(f'\nDone! All images saved to: {OUTPUT_DIR}')
    print(f'\nUpdate system config in database:')
    print(f'  home_bg_images: ["{hero_path}"]')
    print(f'  company_scroll_images: {scroll_images}')
