"""
macOS Platform Controller
macOS平台控制器实现

使用技术栈:
- Quartz (CoreGraphics): 底层事件注入
- AppKit: 鼠标位置等系统信息
- screencapture: 截屏命令
- pyautogui: 作为备选方案
"""

import os
import platform
import subprocess
import tempfile
import time
from typing import Optional

from ..core.base import ComputerController
from ..core.types import CoordinateType, MouseButton, Point, Rect, Size


class MacOSController(ComputerController):
    """
    macOS控制器

    优先使用Quartz框架进行底层控制，提供最佳性能和兼容性
    """

    def __init__(self):
        super().__init__()

        if platform.system() != "Darwin":
            raise RuntimeError("MacOSController can only run on macOS")

        # 尝试导入Quartz
        try:
            import AppKit
            import Quartz
            self._quartz = Quartz
            self._appkit = AppKit
            self._use_quartz = True
        except ImportError:
            print("Warning: Quartz not available, falling back to pyautogui")
            self._use_quartz = False
            try:
                import pyautogui
                self._pyautogui = pyautogui
                self._pyautogui.FAILSAFE = False  # 禁用安全角落
            except ImportError as e:
                raise RuntimeError(
                    "Neither Quartz nor pyautogui is available. "
                    "Install pyobjc-framework-Quartz or pyautogui."
                ) from e

        # 缓存屏幕尺寸
        self._screen_size = self.get_screen_size()

    # ==================== 屏幕信息 ====================

    def get_screen_size(self) -> Size:
        """获取屏幕尺寸"""
        if self._use_quartz:
            width = self._quartz.CGDisplayPixelsWide(self._quartz.CGMainDisplayID())
            height = self._quartz.CGDisplayPixelsHigh(self._quartz.CGMainDisplayID())
            return Size(width, height)
        else:
            w, h = self._pyautogui.size()
            return Size(w, h)

    def get_mouse_position(self) -> Point:
        """获取当前鼠标位置"""
        if self._use_quartz:
            loc = self._appkit.NSEvent.mouseLocation()
            # macOS坐标系Y轴是从下往上的，需要转换
            screen_height = self._quartz.CGDisplayPixelsHigh(0)
            return Point(int(loc.x), int(screen_height - loc.y), CoordinateType.ABSOLUTE)
        else:
            x, y = self._pyautogui.position()
            return Point(x, y, CoordinateType.ABSOLUTE)

    # ==================== 截屏功能 ====================

    def screenshot(self, region: Optional[Rect] = None) -> bytes:
        """
        截取屏幕

        使用macOS原生screencapture命令，支持Retina显示
        """
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if region:
                # 截取指定区域
                x, y, w, h = region.left, region.top, region.width, region.height
                cmd = ["screencapture", "-x", "-R", f"{x},{y},{w},{h}", tmp_path]
            else:
                # 全屏截图 -C 包含鼠标指针
                cmd = ["screencapture", "-x", "-C", tmp_path]

            subprocess.run(cmd, check=True, capture_output=True)

            with open(tmp_path, 'rb') as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ==================== 鼠标控制 ====================

    def mouse_move(self, x: int, y: int, duration: float = 0.0) -> None:
        """移动鼠标"""
        if self._use_quartz:
            if duration > 0:
                # 平滑移动
                start = self.get_mouse_position()
                steps = max(int(duration * 60), 1)  # 60fps
                for i in range(steps + 1):
                    t = i / steps
                    cur_x = int(start.x + (x - start.x) * t)
                    cur_y = int(start.y + (y - start.y) * t)
                    self._send_mouse_event(
                        self._quartz.kCGEventMouseMoved, cur_x, cur_y, 0
                    )
                    time.sleep(duration / steps)
            else:
                self._send_mouse_event(
                    self._quartz.kCGEventMouseMoved, x, y, 0
                )
            time.sleep(0.01)  # macOS需要一点时间同步
        else:
            self._pyautogui.moveTo(x, y, duration=duration)

    def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: MouseButton = MouseButton.LEFT,
        clicks: int = 1,
        interval: float = 0.1
    ) -> None:
        """鼠标点击"""
        if x is not None and y is not None:
            self.mouse_move(x, y)

        if self._use_quartz:
            pos = self.get_mouse_position()
            px, py = int(pos.x), int(pos.y)

            down_event, up_event, btn = self._get_click_events(button)

            for i in range(clicks):
                self._send_mouse_event(down_event, px, py, btn)
                self._send_mouse_event(up_event, px, py, btn)
                if i < clicks - 1:
                    time.sleep(interval)
        else:
            btn_str = button.value
            self._pyautogui.click(x, y, clicks=clicks, interval=interval, button=btn_str)

    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> None:
        """按下鼠标"""
        if self._use_quartz:
            pos = self.get_mouse_position()
            down_event, _, btn = self._get_click_events(button)
            self._send_mouse_event(down_event, int(pos.x), int(pos.y), btn)
        else:
            self._pyautogui.mouseDown(button=button.value)

    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> None:
        """释放鼠标"""
        if self._use_quartz:
            pos = self.get_mouse_position()
            _, up_event, btn = self._get_click_events(button)
            self._send_mouse_event(up_event, int(pos.x), int(pos.y), btn)
        else:
            self._pyautogui.mouseUp(button=button.value)

    def mouse_scroll(
        self,
        clicks: int,
        x: Optional[int] = None,
        y: Optional[int] = None,
        horizontal: bool = False
    ) -> None:
        """鼠标滚轮"""
        if x is not None and y is not None:
            self.mouse_move(x, y)

        if self._use_quartz:
            # 每次滚动10单位，分多次执行
            direction = 1 if clicks >= 0 else -1
            remaining = abs(clicks)

            while remaining > 0:
                scroll_amount = min(remaining, 10) * direction

                if horizontal:
                    event = self._quartz.CGEventCreateScrollWheelEvent(
                        None,
                        self._quartz.kCGScrollEventUnitLine,
                        2,  # wheelCount
                        0,  # vertical
                        scroll_amount  # horizontal
                    )
                else:
                    event = self._quartz.CGEventCreateScrollWheelEvent(
                        None,
                        self._quartz.kCGScrollEventUnitLine,
                        1,  # wheelCount
                        scroll_amount  # vertical
                    )

                self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)
                remaining -= 10
        else:
            if horizontal:
                self._pyautogui.hscroll(clicks, x, y)
            else:
                self._pyautogui.scroll(clicks, x, y)

    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: MouseButton = MouseButton.LEFT,
        duration: float = 0.5
    ) -> None:
        """鼠标拖拽 - macOS需要特殊的拖拽事件"""
        if self._use_quartz:
            # 移动到起始位置
            self.mouse_move(start_x, start_y)
            time.sleep(0.05)

            # 按下
            self.mouse_down(button)
            time.sleep(0.1)

            # 拖拽移动
            steps = max(int(duration * 60), 1)
            drag_event = self._get_drag_event(button)
            btn = self._get_button_const(button)

            for i in range(steps + 1):
                t = i / steps
                cur_x = int(start_x + (end_x - start_x) * t)
                cur_y = int(start_y + (end_y - start_y) * t)
                self._send_mouse_event(drag_event, cur_x, cur_y, btn)
                time.sleep(duration / steps)

            time.sleep(0.1)
            # 释放
            self.mouse_up(button)
        else:
            self._pyautogui.moveTo(start_x, start_y)
            self._pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button.value)

    # ==================== 键盘控制 ====================

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本"""
        if self._use_quartz:
            for char in text:
                self._type_character(char)
                if interval > 0:
                    time.sleep(interval)
        else:
            self._pyautogui.write(text, interval=interval)

    def key_press(self, key: str) -> None:
        """按键"""
        self.key_down(key)
        time.sleep(0.05)
        self.key_up(key)

    def key_down(self, key: str) -> None:
        """按下按键"""
        if self._use_quartz:
            key_code = self._get_key_code(key)
            if key_code is not None:
                event = self._quartz.CGEventCreateKeyboardEvent(None, key_code, True)
                self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)
                time.sleep(0.01)
        else:
            self._pyautogui.keyDown(key)

    def key_up(self, key: str) -> None:
        """释放按键"""
        if self._use_quartz:
            key_code = self._get_key_code(key)
            if key_code is not None:
                event = self._quartz.CGEventCreateKeyboardEvent(None, key_code, False)
                self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)
                time.sleep(0.01)
        else:
            self._pyautogui.keyUp(key)

    # ==================== 内部方法 ====================

    def _send_mouse_event(self, event_type: int, x: int, y: int, button: int) -> None:
        """发送鼠标事件"""
        event = self._quartz.CGEventCreateMouseEvent(None, event_type, (x, y), button)
        self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)

    def _get_click_events(self, button: MouseButton):
        """获取点击事件类型"""
        if button == MouseButton.LEFT:
            return (
                self._quartz.kCGEventLeftMouseDown,
                self._quartz.kCGEventLeftMouseUp,
                self._quartz.kCGMouseButtonLeft
            )
        elif button == MouseButton.RIGHT:
            return (
                self._quartz.kCGEventRightMouseDown,
                self._quartz.kCGEventRightMouseUp,
                self._quartz.kCGMouseButtonRight
            )
        else:  # MIDDLE
            return (
                self._quartz.kCGEventOtherMouseDown,
                self._quartz.kCGEventOtherMouseUp,
                self._quartz.kCGMouseButtonCenter
            )

    def _get_drag_event(self, button: MouseButton) -> int:
        """获取拖拽事件类型"""
        if button == MouseButton.LEFT:
            return self._quartz.kCGEventLeftMouseDragged
        elif button == MouseButton.RIGHT:
            return self._quartz.kCGEventRightMouseDragged
        else:
            return self._quartz.kCGEventOtherMouseDragged

    def _get_button_const(self, button: MouseButton) -> int:
        """获取按钮常量"""
        if button == MouseButton.LEFT:
            return self._quartz.kCGMouseButtonLeft
        elif button == MouseButton.RIGHT:
            return self._quartz.kCGMouseButtonRight
        else:
            return self._quartz.kCGMouseButtonCenter

    def _type_character(self, char: str) -> None:
        """输入单个字符"""
        # 这里简化处理，实际需要更完整的键码映射
        key_code = self._get_key_code(char.lower())
        if key_code is not None:
            # 检查是否需要Shift
            needs_shift = char.isupper() or char in '~!@#$%^&*()_+{}|:"<>?'

            if needs_shift:
                shift_code = self._get_key_code('shift')
                if shift_code:
                    event = self._quartz.CGEventCreateKeyboardEvent(None, shift_code, True)
                    self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)

            # 按键
            event = self._quartz.CGEventCreateKeyboardEvent(None, key_code, True)
            self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)
            event = self._quartz.CGEventCreateKeyboardEvent(None, key_code, False)
            self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)

            if needs_shift:
                shift_code = self._get_key_code('shift')
                if shift_code:
                    event = self._quartz.CGEventCreateKeyboardEvent(None, shift_code, False)
                    self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)

            time.sleep(0.01)

    def _get_key_code(self, key: str) -> Optional[int]:
        """获取按键码"""
        # macOS按键码映射 (来自 pyautogui/_pyautogui_osx.py)
        key_map = {
            'a': 0x00, 's': 0x01, 'd': 0x02, 'f': 0x03, 'h': 0x04,
            'g': 0x05, 'z': 0x06, 'x': 0x07, 'c': 0x08, 'v': 0x09,
            'b': 0x0b, 'q': 0x0c, 'w': 0x0d, 'e': 0x0e, 'r': 0x0f,
            'y': 0x10, 't': 0x11, '1': 0x12, '2': 0x13, '3': 0x14,
            '4': 0x15, '6': 0x16, '5': 0x17, '=': 0x18, '9': 0x19,
            '7': 0x1a, '-': 0x1b, '8': 0x1c, '0': 0x1d, ']': 0x1e,
            'o': 0x1f, 'u': 0x20, '[': 0x21, 'i': 0x22, 'p': 0x23,
            'l': 0x25, 'j': 0x26, "'": 0x27, 'k': 0x28, ';': 0x29,
            '\\': 0x2a, ',': 0x2b, '/': 0x2c, 'n': 0x2d, 'm': 0x2e,
            '.': 0x2f, '`': 0x32, ' ': 0x31, 'space': 0x31,
            'enter': 0x24, 'return': 0x24, '\n': 0x24, '\r': 0x24,
            'tab': 0x30, '\t': 0x30,
            'backspace': 0x33, 'delete': 0x75, 'del': 0x75,
            'escape': 0x35, 'esc': 0x35,
            'command': 0x37, 'cmd': 0x37, 'win': 0x37,
            'shift': 0x38, 'shiftleft': 0x38, 'shiftright': 0x3c,
            'capslock': 0x39,
            'option': 0x3a, 'alt': 0x3a, 'altleft': 0x3a, 'altright': 0x3d,
            'ctrl': 0x3b, 'control': 0x3b, 'ctrlleft': 0x3b, 'ctrlright': 0x3e,
            'fn': 0x3f,
            'f1': 0x7a, 'f2': 0x78, 'f3': 0x63, 'f4': 0x76,
            'f5': 0x60, 'f6': 0x61, 'f7': 0x62, 'f8': 0x64,
            'f9': 0x65, 'f10': 0x6d, 'f11': 0x67, 'f12': 0x6f,
            'home': 0x73, 'end': 0x77,
            'pageup': 0x74, 'pgup': 0x74,
            'pagedown': 0x79, 'pgdn': 0x79,
            'left': 0x7b, 'right': 0x7c, 'down': 0x7d, 'up': 0x7e,
        }
        return key_map.get(key.lower())
