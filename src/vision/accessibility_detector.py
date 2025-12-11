"""
Accessibility Detector - 辅助功能检测器

使用系统辅助功能API获取UI元素
目前只支持macOS
"""

import subprocess
from typing import List

from ..core.types import Rect, ScreenElement
from .detector import ElementDetector


class AccessibilityDetector(ElementDetector):
    """
    辅助功能检测器

    使用macOS Accessibility API获取屏幕元素
    """

    def __init__(self):
        self._check_accessibility()

    def _check_accessibility(self):
        """检查辅助功能权限"""
        # 在实际使用时会在第一次调用时检查
        pass

    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """
        使用辅助功能API检测元素

        注意：这个方法不使用图片，而是直接查询系统
        """
        elements = []

        # 获取窗口控制按钮
        window_controls = self._get_window_controls()
        elements.extend(window_controls)

        # 获取菜单栏
        menu_items = self._get_menu_bar_items()
        elements.extend(menu_items)

        return elements

    def _get_window_controls(self) -> List[ScreenElement]:
        """获取窗口控制按钮（红黄绿）"""
        elements = []

        try:
            # 使用AppleScript获取窗口信息
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                tell frontApp
                    set win to front window
                    set winPos to position of win
                    return winPos
                end tell
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # 解析窗口位置
                pos_str = result.stdout.strip()
                if pos_str:
                    parts = pos_str.split(', ')
                    if len(parts) >= 2:
                        x = int(parts[0])
                        y = int(parts[1])

                        # 窗口控制按钮通常在左上角
                        # macOS标准位置：关闭(红)、最小化(黄)、全屏(绿)
                        button_size = 12
                        button_spacing = 8
                        button_y = y + 12
                        button_x_start = x + 12

                        buttons = [
                            ("close", button_x_start, button_y, (255, 95, 86)),
                            ("minimize", button_x_start + button_size + button_spacing, button_y, (255, 189, 46)),
                            ("fullscreen", button_x_start + 2 * (button_size + button_spacing), button_y, (39, 201, 63)),
                        ]

                        for name, bx, by, color in buttons:
                            elements.append(ScreenElement(
                                label=f"window_{name}",
                                rect=Rect(bx, by, bx + button_size, by + button_size),
                                element_type="window_control",
                                text=name
                            ))

        except Exception:
            pass

        return elements

    def _get_menu_bar_items(self) -> List[ScreenElement]:
        """获取菜单栏项目"""
        elements = []

        try:
            script = '''
            tell application "System Events"
                set menuBarItems to menu bar items of menu bar 1 of (first application process whose frontmost is true)
                set result to ""
                repeat with item in menuBarItems
                    set itemName to name of item
                    set itemPos to position of item
                    set itemSize to size of item
                    set result to result & itemName & "," & (item 1 of itemPos) & "," & (item 2 of itemPos) & "," & (item 1 of itemSize) & "," & (item 2 of itemSize) & ";"
                end repeat
                return result
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                items_str = result.stdout.strip()
                if items_str:
                    for i, item_data in enumerate(items_str.split(';')):
                        if item_data:
                            parts = item_data.split(',')
                            if len(parts) >= 5:
                                name = parts[0]
                                x = int(parts[1])
                                y = int(parts[2])
                                w = int(parts[3])
                                h = int(parts[4])

                                elements.append(ScreenElement(
                                    label=f"menu_{i}",
                                    rect=Rect(x, y, x + w, y + h),
                                    element_type="menu_item",
                                    text=name
                                ))

        except Exception:
            pass

        return elements


class HybridDetector(ElementDetector):
    """
    混合检测器

    结合视觉检测和辅助功能API
    """

    def __init__(
        self,
        visual_detector: ElementDetector,
        use_accessibility: bool = True
    ):
        self.visual_detector = visual_detector
        self.use_accessibility = use_accessibility
        self.accessibility_detector = AccessibilityDetector() if use_accessibility else None

    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """
        混合检测

        合并视觉检测和辅助功能检测的结果
        """
        elements = []

        # 视觉检测
        visual_elements = self.visual_detector.detect(image_bytes)
        elements.extend(visual_elements)

        # 辅助功能检测
        if self.accessibility_detector:
            a11y_elements = self.accessibility_detector.detect(image_bytes)

            # 重新编号，避免与视觉检测冲突
            base_index = len(elements)
            for i, elem in enumerate(a11y_elements):
                elem.label = f"~{base_index + i}"
                elements.append(elem)

        return elements
