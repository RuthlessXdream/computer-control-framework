#!/usr/bin/env python3
"""
测试 OmniParser 集成
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import get_controller
from src.vision.omniparser_detector import OmniParserDetector


def main():
    print("=" * 60)
    print("     🔬 OmniParser UI 元素检测测试")
    print("=" * 60)
    
    controller = get_controller()
    
    # 1. 截屏
    print("\n[1] 截取屏幕...")
    screenshot_bytes = controller.screenshot()
    with open("omni_original.png", "wb") as f:
        f.write(screenshot_bytes)
    print(f"   ✅ 原始截图: omni_original.png ({len(screenshot_bytes)//1024}KB)")
    
    # 2. 初始化 OmniParser
    print("\n[2] 初始化 OmniParser (首次需要加载模型)...")
    start_time = time.time()
    
    detector = OmniParserDetector(
        omniparser_path="/Users/super/WORK/AGI/OmniParser",
        weights_path="/Users/super/WORK/AGI/OmniParser/weights"
    )
    
    # 3. 检测元素并获取标注图
    print("\n[3] 检测 UI 元素...")
    elements, labeled_img = detector.detect_with_image(screenshot_bytes)
    
    detect_time = time.time() - start_time
    print(f"   ✅ 检测完成! 耗时: {detect_time:.2f}秒")
    print(f"   ✅ 检测到 {len(elements)} 个元素")
    
    # 保存标注图
    with open("omni_annotated.png", "wb") as f:
        f.write(labeled_img)
    print(f"   ✅ 标注截图: omni_annotated.png")
    
    # 4. 显示检测到的元素
    print("\n[4] 检测到的元素:")
    for i, elem in enumerate(elements[:30]):  # 显示前30个
        text_preview = elem.text[:40] + "..." if len(elem.text) > 40 else elem.text
        print(f"   [{elem.label}] {elem.element_type}: '{text_preview}'")
        print(f"         位置: ({elem.rect.left}, {elem.rect.top}) - ({elem.rect.right}, {elem.rect.bottom})")
    
    if len(elements) > 30:
        print(f"   ... 还有 {len(elements) - 30} 个元素")
    
    # 5. 坐标映射示例
    print("\n[5] 点击示例:")
    screen_size = controller.get_screen_size()
    
    for elem in elements[:5]:
        center_x = (elem.rect.left + elem.rect.right) // 2
        center_y = (elem.rect.top + elem.rect.bottom) // 2
        
        # Retina屏幕需要除以2
        click_x = center_x // 2
        click_y = center_y // 2
        
        text_preview = elem.text[:20] + "..." if len(elem.text) > 20 else elem.text
        print(f"   {elem.label} '{text_preview}' -> controller.mouse_click({click_x}, {click_y})")
    
    print("\n" + "=" * 60)
    print("🎉 OmniParser 集成测试完成!")
    print("=" * 60)
    print("\n📁 生成的文件:")
    print("   - omni_original.png (原始截图)")
    print("   - omni_annotated.png (OmniParser标注)")
    print("\n💡 打开 omni_annotated.png 查看完整的UI元素标注!")


if __name__ == "__main__":
    main()

