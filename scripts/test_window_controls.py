#!/usr/bin/env python3
"""
测试窗口控制按钮检测
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.vision.accessibility_detector import AccessibilityDetector


def main():
    print("=" * 60)
    print("     🔴🟡🟢 窗口控制按钮检测测试")
    print("=" * 60)
    
    detector = AccessibilityDetector()
    
    # 获取窗口控制按钮
    print("\n[1] 检测窗口控制按钮...")
    controls = detector._get_window_controls()
    
    if controls:
        print(f"   ✅ 检测到 {len(controls)} 个窗口控制按钮:")
        for elem in controls:
            print(f"      {elem.label}: {elem.text}")
            print(f"         位置: ({elem.rect.left}, {elem.rect.top}) - ({elem.rect.right}, {elem.rect.bottom})")
    else:
        print("   ❌ 未检测到窗口控制按钮")
    
    # 获取菜单栏
    print("\n[2] 检测菜单栏项目...")
    menu_items = detector._get_menu_bar_items()
    
    if menu_items:
        print(f"   ✅ 检测到 {len(menu_items)} 个菜单项:")
        for elem in menu_items[:10]:  # 只显示前10个
            print(f"      {elem.label}: '{elem.text}' @ ({elem.rect.left}, {elem.rect.top})")
    else:
        print("   ❌ 未检测到菜单项")
    
    # 综合检测
    print("\n[3] 综合检测结果...")
    all_elements = detector.detect(b'')
    print(f"   ✅ 总共检测到 {len(all_elements)} 个元素")
    
    print("\n" + "=" * 60)
    print("🎉 测试完成!")
    print("=" * 60)
    
    # 显示如何点击
    print("\n💡 使用示例:")
    print("   # 点击关闭按钮")
    print("   controller.mouse_click(close_x, close_y)")
    print("")
    
    for elem in controls:
        cx = (elem.rect.left + elem.rect.right) // 2
        cy = (elem.rect.top + elem.rect.bottom) // 2
        print(f"   # {elem.text}: controller.mouse_click({cx}, {cy})")


if __name__ == "__main__":
    main()

