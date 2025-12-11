#!/usr/bin/env python3
"""
全功能验证脚本 - 测试控制器所有能力
包括：截屏、鼠标、键盘、标注、Action执行器、AI接口
"""

import sys
import os
import time
import math
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import get_controller, AIBrain, ComputerAgent, Action, ActionType, Point, CoordinateType, ScreenState, Size
from src.core.base import ActionExecutor
from src.vision.annotator import ScreenAnnotator


def countdown(seconds, message):
    for i in range(seconds, 0, -1):
        print(f"\r  {message} {i}...", end="", flush=True)
        time.sleep(1)
    print(f"\r  {message} 开始!     ")


def test_screenshot(controller):
    """测试截屏功能"""
    print("\n" + "=" * 60)
    print("📸 [1/8] 截屏功能测试")
    print("=" * 60)
    
    try:
        img_bytes = controller.screenshot()
        
        # 保存原始截图
        with open("test_1_screenshot.png", "wb") as f:
            f.write(img_bytes)
        
        # 获取图像信息
        img = Image.open(BytesIO(img_bytes))
        print(f"  ✅ 截屏成功!")
        print(f"     尺寸: {img.size[0]} x {img.size[1]}")
        print(f"     格式: {img.format}")
        print(f"     文件: test_1_screenshot.png ({len(img_bytes)//1024}KB)")
        return True, img_bytes
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False, None


def test_mouse_move(controller):
    """测试鼠标移动"""
    print("\n" + "=" * 60)
    print("🖱️  [2/8] 鼠标移动测试")
    print("=" * 60)
    
    try:
        size = controller.get_screen_size()
        print(f"  屏幕尺寸: {size.width} x {size.height}")
        
        countdown(2, "鼠标即将移动")
        
        # 画一个五角星
        center_x, center_y = size.width // 2, size.height // 2
        radius = 150
        points = []
        
        # 五角星的5个顶点 (跳跃连接)
        for i in range(5):
            angle = math.radians(90 + i * 144)  # 144度间隔画五角星
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y - radius * math.sin(angle))
            points.append((x, y))
        
        # 连接五角星
        star_order = [0, 2, 4, 1, 3, 0]  # 五角星连接顺序
        print("  画五角星...")
        for idx in star_order:
            x, y = points[idx]
            controller.mouse_move(x, y, duration=0.15)
            time.sleep(0.05)
        
        print(f"  ✅ 鼠标移动成功! (画了一个五角星)")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_mouse_click(controller):
    """测试鼠标点击"""
    print("\n" + "=" * 60)
    print("👆 [3/8] 鼠标点击测试")
    print("=" * 60)
    
    try:
        size = controller.get_screen_size()
        
        # 移动到屏幕中央
        center_x, center_y = size.width // 2, size.height // 2
        controller.mouse_move(center_x, center_y, duration=0.3)
        
        countdown(2, "即将在屏幕中央点击")
        
        # 单击
        controller.mouse_click(center_x, center_y)
        print("  ✅ 单击完成!")
        
        time.sleep(0.3)
        
        # 右键点击
        controller.mouse_click(center_x + 50, center_y, button='right')
        print("  ✅ 右键点击完成!")
        
        time.sleep(0.3)
        
        # 关闭可能出现的菜单
        controller.key_press("escape")
        
        # 双击
        controller.mouse_click(center_x, center_y + 50, clicks=2)
        print("  ✅ 双击完成!")
        
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_mouse_drag(controller):
    """测试鼠标拖拽"""
    print("\n" + "=" * 60)
    print("✋ [4/8] 鼠标拖拽测试")
    print("=" * 60)
    
    try:
        size = controller.get_screen_size()
        
        countdown(2, "即将测试拖拽")
        
        # 从左上到右下拖拽
        start_x, start_y = size.width // 3, size.height // 3
        end_x, end_y = size.width * 2 // 3, size.height * 2 // 3
        
        controller.mouse_move(start_x, start_y, duration=0.2)
        time.sleep(0.1)
        controller.mouse_drag(start_x, start_y, end_x, end_y, duration=0.5)
        
        print(f"  ✅ 拖拽完成! ({start_x},{start_y}) → ({end_x},{end_y})")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_scroll(controller):
    """测试滚轮"""
    print("\n" + "=" * 60)
    print("📜 [5/8] 滚轮测试")
    print("=" * 60)
    
    try:
        countdown(2, "即将测试滚轮")
        
        # 向下滚动
        print("  向下滚动...")
        controller.mouse_scroll(-5)
        time.sleep(0.3)
        
        # 向上滚动
        print("  向上滚动...")
        controller.mouse_scroll(5)
        time.sleep(0.3)
        
        print("  ✅ 滚轮测试完成!")
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_keyboard(controller):
    """测试键盘输入"""
    print("\n" + "=" * 60)
    print("⌨️  [6/8] 键盘测试")
    print("=" * 60)
    
    try:
        countdown(3, "即将打开Spotlight并输入文字")
        
        # 打开Spotlight
        controller.hotkey("command", "space")
        time.sleep(0.8)
        
        # 输入文字
        test_text = "Hello AI"
        controller.type_text(test_text)
        print(f"  ✅ 输入文字: '{test_text}'")
        
        time.sleep(0.5)
        
        # 截图记录
        img = controller.screenshot()
        with open("test_6_keyboard.png", "wb") as f:
            f.write(img)
        print(f"  📸 截图保存: test_6_keyboard.png")
        
        # 关闭Spotlight
        controller.key_press("escape")
        print("  ✅ 键盘测试完成!")
        
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_annotation(controller, screenshot_bytes):
    """测试标注功能"""
    print("\n" + "=" * 60)
    print("🏷️  [7/8] 标注功能测试")
    print("=" * 60)
    
    try:
        annotator = ScreenAnnotator()
        
        # 加载截图
        img = Image.open(BytesIO(screenshot_bytes))
        
        # 定义一些模拟的UI元素区域
        elements = [
            {"id": 1, "label": "按钮A", "bbox": (100, 100, 250, 150), "color": "red"},
            {"id": 2, "label": "输入框", "bbox": (300, 100, 500, 150), "color": "blue"},
            {"id": 3, "label": "菜单", "bbox": (100, 200, 200, 350), "color": "green"},
            {"id": 4, "label": "内容区", "bbox": (250, 200, 600, 450), "color": "purple"},
            {"id": 5, "label": "提交", "bbox": (450, 480, 550, 520), "color": "orange"},
        ]
        
        # 创建绘图对象
        draw = ImageDraw.Draw(img)
        
        # 尝试加载字体
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except:
            font = ImageFont.load_default()
            small_font = font
        
        # 绘制标注
        print("  绘制标注区域...")
        for elem in elements:
            bbox = elem["bbox"]
            color = elem["color"]
            label = elem["label"]
            
            # 绘制矩形框
            draw.rectangle(bbox, outline=color, width=3)
            
            # 绘制标签背景
            label_bbox = draw.textbbox((bbox[0], bbox[1] - 20), f"[{elem['id']}] {label}", font=small_font)
            draw.rectangle(label_bbox, fill=color)
            
            # 绘制标签文字
            draw.text((bbox[0], bbox[1] - 20), f"[{elem['id']}] {label}", fill="white", font=small_font)
            
            # 绘制中心点
            center_x = (bbox[0] + bbox[2]) // 2
            center_y = (bbox[1] + bbox[3]) // 2
            draw.ellipse((center_x-5, center_y-5, center_x+5, center_y+5), fill=color)
            
            print(f"    [{elem['id']}] {label}: {bbox}")
        
        # 添加图例
        legend_y = 550
        draw.text((50, legend_y), "📋 标注图例:", fill="black", font=font)
        for i, elem in enumerate(elements):
            draw.rectangle((50, legend_y + 25 + i*25, 70, legend_y + 45 + i*25), fill=elem["color"])
            draw.text((80, legend_y + 25 + i*25), f"[{elem['id']}] {elem['label']}", fill="black", font=small_font)
        
        # 保存标注后的图像
        img.save("test_7_annotated.png")
        print(f"  ✅ 标注完成!")
        print(f"  📸 保存: test_7_annotated.png")
        
        # 测试坐标转换
        print("\n  坐标转换测试:")
        screen_size = controller.get_screen_size()
        for elem in elements[:3]:
            bbox = elem["bbox"]
            center_x = (bbox[0] + bbox[2]) // 2
            center_y = (bbox[1] + bbox[3]) // 2
            
            # 绝对坐标转百分比
            pct_x = center_x / screen_size.width
            pct_y = center_y / screen_size.height
            
            print(f"    [{elem['id']}] {elem['label']}: 绝对({center_x},{center_y}) → 百分比({pct_x:.2%},{pct_y:.2%})")
        
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_interface(controller):
    """测试AI接口"""
    print("\n" + "=" * 60)
    print("🧠 [8/8] AI接口测试")
    print("=" * 60)
    
    try:
        # 定义一个测试用的AI大脑
        class DemoAIBrain(AIBrain):
            def __init__(self):
                self.step = 0
                self.actions = [
                    Action(ActionType.MOUSE_MOVE, coordinate=Point(0.5, 0.5, CoordinateType.PERCENTAGE)),
                    Action(ActionType.WAIT, duration=0.3),
                    Action(ActionType.SCROLL, scroll_amount=2, scroll_direction="down"),
                    Action(ActionType.WAIT, duration=0.3),
                    Action(ActionType.SCROLL, scroll_amount=2, scroll_direction="up"),
                    None,  # 结束信号
                ]
            
            def think(self, screen_state: ScreenState, task: str) -> Action:
                print(f"    🧠 AI思考中... (步骤 {self.step + 1})")
                print(f"       屏幕: {screen_state.screen_size}")
                print(f"       截图: {len(screen_state.screenshot_base64)} 字符")
                
                if self.step < len(self.actions) - 1:
                    action = self.actions[self.step]
                    self.step += 1
                    print(f"       决策: {action.action_type.value}")
                    return action
                else:
                    print(f"       决策: 任务完成!")
                    return None
        
        # 创建Agent
        brain = DemoAIBrain()
        agent = ComputerAgent(brain, controller)
        
        print("  创建AI Agent...")
        print("  执行任务: '演示AI控制'")
        print("-" * 40)
        
        countdown(2, "AI Agent即将开始执行")
        
        # 运行Agent
        max_steps = 10
        step = 0
        
        while step < max_steps:
            print(f"\n  [Step {step + 1}]")
            action = agent.step("演示AI控制")
            
            if action is None:
                print("  ✅ AI Agent完成任务!")
                break
            
            step += 1
            time.sleep(0.2)
        
        print("-" * 40)
        print(f"  ✅ AI接口测试完成! (执行了 {step} 步)")
        
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("     🔬 Computer Control Framework 全功能验证")
    print("=" * 60)
    print("\n⚠️  请注意观察屏幕，将会执行各种操作!")
    
    controller = get_controller()
    results = []
    
    # 1. 截屏测试
    success, screenshot = test_screenshot(controller)
    results.append(("截屏", success))
    
    # 2. 鼠标移动测试
    success = test_mouse_move(controller)
    results.append(("鼠标移动", success))
    
    # 3. 鼠标点击测试
    success = test_mouse_click(controller)
    results.append(("鼠标点击", success))
    
    # 4. 鼠标拖拽测试
    success = test_mouse_drag(controller)
    results.append(("鼠标拖拽", success))
    
    # 5. 滚轮测试
    success = test_scroll(controller)
    results.append(("滚轮", success))
    
    # 6. 键盘测试
    success = test_keyboard(controller)
    results.append(("键盘", success))
    
    # 7. 标注测试
    if screenshot:
        success = test_annotation(controller, screenshot)
        results.append(("标注", success))
    else:
        results.append(("标注", False))
    
    # 8. AI接口测试
    success = test_ai_interface(controller)
    results.append(("AI接口", success))
    
    # ===== 汇总 =====
    print("\n" + "=" * 60)
    print("     📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name}: {status}")
        if success:
            passed += 1
    
    print("-" * 60)
    print(f"  总计: {passed}/{len(results)} 通过")
    
    if passed == len(results):
        print("\n🎉 所有测试通过! 框架完全可用!")
    else:
        print(f"\n⚠️  有 {len(results) - passed} 项测试失败")
    
    print("\n📁 生成的文件:")
    for f in sorted(os.listdir(".")):
        if f.startswith("test_") and f.endswith(".png"):
            size = os.path.getsize(f) // 1024
            print(f"   - {f} ({size}KB)")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

