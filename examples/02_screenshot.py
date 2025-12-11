"""
示例2: 截屏功能

演示如何截取屏幕并保存
"""

import sys
sys.path.insert(0, '..')

from src import get_controller, Rect

def main():
    controller = get_controller()
    
    # 全屏截图
    print("截取全屏...")
    screenshot_bytes = controller.screenshot()
    
    with open("screenshot_full.png", "wb") as f:
        f.write(screenshot_bytes)
    print("已保存: screenshot_full.png")
    
    # 获取base64格式
    screenshot_base64 = controller.screenshot_base64()
    print(f"Base64长度: {len(screenshot_base64)}")
    
    # 区域截图 (左上角400x300区域)
    print("截取区域...")
    region = Rect(0, 0, 400, 300)
    region_bytes = controller.screenshot(region)
    
    with open("screenshot_region.png", "wb") as f:
        f.write(region_bytes)
    print("已保存: screenshot_region.png")
    
    print("完成!")

if __name__ == "__main__":
    main()

