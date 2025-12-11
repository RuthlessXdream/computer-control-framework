#!/usr/bin/env python3
"""
真正的标注测试 - 使用OCR检测屏幕上的实际元素
"""

import sys
import os
import time
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PIL import Image, ImageDraw, ImageFont
from src import get_controller
from src.vision.detector import EasyOCRDetector
from src.vision.annotator import ScreenAnnotator


def main():
    print("=" * 60)
    print("     🔍 真正的屏幕元素检测与标注")
    print("=" * 60)
    
    controller = get_controller()
    
    # 1. 截屏
    print("\n[1] 截取屏幕...")
    screenshot_bytes = controller.screenshot()
    
    # 保存原始截图
    with open("original_screenshot.png", "wb") as f:
        f.write(screenshot_bytes)
    print(f"   ✅ 原始截图: original_screenshot.png ({len(screenshot_bytes)//1024}KB)")
    
    # 2. 初始化OCR检测器
    print("\n[2] 初始化OCR检测器...")
    print("   (首次运行需要下载模型，请稍等...)")
    detector = EasyOCRDetector(languages=['en', 'ch_sim'])
    
    # 3. 检测元素
    print("\n[3] 检测屏幕元素...")
    start_time = time.time()
    elements = detector.detect(screenshot_bytes)
    detect_time = time.time() - start_time
    print(f"   ✅ 检测到 {len(elements)} 个元素 (耗时: {detect_time:.2f}秒)")
    
    # 显示检测到的元素
    print("\n   检测到的元素:")
    for i, elem in enumerate(elements[:20]):  # 只显示前20个
        text_preview = elem.text[:30] + "..." if len(elem.text) > 30 else elem.text
        print(f"     [{elem.label}] '{text_preview}' @ ({elem.rect.left},{elem.rect.top}) conf:{elem.confidence:.2f}")
    
    if len(elements) > 20:
        print(f"     ... 还有 {len(elements) - 20} 个元素")
    
    # 4. 标注
    print("\n[4] 绘制标注...")
    
    # 打开图片进行标注
    img = Image.open(BytesIO(screenshot_bytes))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except:
        font = ImageFont.load_default()
    
    # 颜色列表，循环使用
    colors = [
        "#FF0000",  # 红
        "#00FF00",  # 绿
        "#0000FF",  # 蓝
        "#FF00FF",  # 紫
        "#FFFF00",  # 黄
        "#00FFFF",  # 青
        "#FF8000",  # 橙
        "#8000FF",  # 紫罗兰
    ]
    
    for i, elem in enumerate(elements):
        color = colors[i % len(colors)]
        rect = elem.rect
        
        # 绘制边界框
        draw.rectangle(
            [(rect.left, rect.top), (rect.right, rect.bottom)],
            outline=color,
            width=2
        )
        
        # 绘制标签
        label = elem.label
        label_bbox = draw.textbbox((rect.left, rect.top - 18), label, font=font)
        
        # 标签背景
        draw.rectangle(
            [(rect.left, rect.top - 20), (label_bbox[2] + 4, rect.top)],
            fill=color
        )
        
        # 标签文字
        draw.text(
            (rect.left + 2, rect.top - 18),
            label,
            fill="white",
            font=font
        )
    
    # 保存标注后的图片
    img.save("annotated_screenshot.png")
    print(f"   ✅ 标注截图: annotated_screenshot.png")
    
    # 5. 生成坐标映射
    print("\n[5] 坐标映射示例:")
    screen_size = controller.get_screen_size()
    
    print(f"   屏幕尺寸: {screen_size.width} x {screen_size.height}")
    print("\n   如何点击标注元素:")
    
    for elem in elements[:5]:
        # 计算中心点
        center_x = (elem.rect.left + elem.rect.right) // 2
        center_y = (elem.rect.top + elem.rect.bottom) // 2
        
        # 转换为百分比 (注意：截图是Retina 2x，需要除以2)
        # 因为截图分辨率是屏幕的2倍
        pct_x = center_x / (screen_size.width * 2)  # Retina屏幕
        pct_y = center_y / (screen_size.height * 2)
        
        text_preview = elem.text[:20] + "..." if len(elem.text) > 20 else elem.text
        print(f"     {elem.label} '{text_preview}'")
        print(f"        绝对坐标: ({center_x}, {center_y})")
        print(f"        百分比: ({pct_x:.2%}, {pct_y:.2%})")
        print(f"        点击命令: controller.mouse_click({int(center_x/2)}, {int(center_y/2)})")
    
    print("\n" + "=" * 60)
    print("🎉 标注完成!")
    print("=" * 60)
    print("\n📁 生成的文件:")
    print("   - original_screenshot.png (原始截图)")
    print("   - annotated_screenshot.png (标注截图)")
    print("\n💡 打开 annotated_screenshot.png 查看标注效果!")


if __name__ == "__main__":
    main()

