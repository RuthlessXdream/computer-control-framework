"""
示例1: 基础控制

演示如何使用控制器进行基本的鼠标键盘操作
"""

import sys
sys.path.insert(0, '..')

from src import get_controller, MouseButton

def main():
    # 获取当前平台的控制器
    controller = get_controller()
    
    print(f"屏幕尺寸: {controller.get_screen_size()}")
    print(f"鼠标位置: {controller.get_mouse_position()}")
    
    # 移动鼠标到屏幕中央
    size = controller.get_screen_size()
    center_x = size.width // 2
    center_y = size.height // 2
    
    print(f"移动鼠标到屏幕中央 ({center_x}, {center_y})")
    controller.mouse_move(center_x, center_y, duration=0.5)
    
    # 等待一下
    controller.wait(1)
    
    # 点击
    print("点击")
    controller.mouse_click()
    
    # 输入文本 (需要先点击一个输入框)
    # print("输入文本")
    # controller.type_text("Hello from Computer Control Framework!")
    
    # 按键
    # print("按下Escape")
    # controller.key_press("escape")
    
    # 组合键
    # print("Cmd+Space (macOS Spotlight)")
    # controller.hotkey("command", "space")
    
    print("完成!")

if __name__ == "__main__":
    main()

