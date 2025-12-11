"""
Windows Platform Controller
Windows平台控制器实现

使用技术栈:
- pyautogui: 鼠标键盘控制
- pywinauto (可选): UI自动化和窗口控制
- PIL/mss: 截屏
"""

import platform
import time
from typing import Optional, List, Dict, Any
from io import BytesIO

from ..core.base import ComputerController
from ..core.types import Point, Size, Rect, MouseButton, CoordinateType


class WindowsController(ComputerController):
    """
    Windows控制器
    
    使用pyautogui + pywinauto实现
    """
    
    def __init__(self):
        super().__init__()
        
        if platform.system() != "Windows":
            raise RuntimeError("WindowsController can only run on Windows")
        
        # 导入pyautogui
        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._pyautogui.FAILSAFE = False
        except ImportError:
            raise RuntimeError("pyautogui is required for Windows support")
        
        # 尝试导入pywinauto (可选，用于高级UI控制)
        try:
            import pywinauto
            from pywinauto.keyboard import send_keys
            self._pywinauto = pywinauto
            self._send_keys = send_keys
            self._has_pywinauto = True
        except ImportError:
            self._has_pywinauto = False
        
        # 导入PIL用于截屏
        try:
            from PIL import ImageGrab
            self._image_grab = ImageGrab
        except ImportError:
            self._image_grab = None
        
        self._screen_size = self.get_screen_size()
    
    # ==================== 屏幕信息 ====================
    
    def get_screen_size(self) -> Size:
        """获取屏幕尺寸"""
        w, h = self._pyautogui.size()
        return Size(w, h)
    
    def get_mouse_position(self) -> Point:
        """获取当前鼠标位置"""
        x, y = self._pyautogui.position()
        return Point(x, y, CoordinateType.ABSOLUTE)
    
    # ==================== 截屏功能 ====================
    
    def screenshot(self, region: Optional[Rect] = None) -> bytes:
        """截取屏幕"""
        if region:
            bbox = (region.left, region.top, region.right, region.bottom)
            img = self._pyautogui.screenshot(region=bbox)
        else:
            img = self._pyautogui.screenshot()
        
        # 转换为PNG字节
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    # ==================== 鼠标控制 ====================
    
    def mouse_move(self, x: int, y: int, duration: float = 0.0) -> None:
        """移动鼠标"""
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
        self._pyautogui.click(x, y, clicks=clicks, interval=interval, button=button.value)
    
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> None:
        """按下鼠标"""
        self._pyautogui.mouseDown(button=button.value)
    
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> None:
        """释放鼠标"""
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
        
        if horizontal:
            self._pyautogui.hscroll(clicks)
        else:
            self._pyautogui.scroll(clicks)
    
    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: MouseButton = MouseButton.LEFT,
        duration: float = 0.5
    ) -> None:
        """鼠标拖拽"""
        self._pyautogui.moveTo(start_x, start_y)
        self._pyautogui.drag(
            end_x - start_x,
            end_y - start_y,
            duration=duration,
            button=button.value
        )
    
    # ==================== 键盘控制 ====================
    
    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本"""
        if self._has_pywinauto:
            # pywinauto的send_keys支持更多特殊字符
            self._send_keys(text, pause=interval)
        else:
            self._pyautogui.write(text, interval=interval)
    
    def key_press(self, key: str) -> None:
        """按键"""
        self._pyautogui.press(key)
    
    def key_down(self, key: str) -> None:
        """按下按键"""
        self._pyautogui.keyDown(key)
    
    def key_up(self, key: str) -> None:
        """释放按键"""
        self._pyautogui.keyUp(key)
    
    def hotkey(self, *keys: str) -> None:
        """组合键"""
        self._pyautogui.hotkey(*keys)
    
    # ==================== Windows特有功能 ====================
    
    def get_window_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """获取指定位置的窗口信息"""
        if not self._has_pywinauto:
            return None
        
        try:
            from pywinauto import Desktop
            windows = Desktop(backend="uia").windows()
            for win in windows:
                rect = win.rectangle()
                if rect.left <= x <= rect.right and rect.top <= y <= rect.bottom:
                    return {
                        "title": win.window_text(),
                        "rect": Rect(rect.left, rect.top, rect.right, rect.bottom),
                        "class_name": win.class_name(),
                    }
        except:
            pass
        return None
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """获取当前活动窗口"""
        if not self._has_pywinauto:
            try:
                title = self._pyautogui.getActiveWindowTitle()
                return {"title": title}
            except:
                return None
        
        try:
            from pywinauto import Desktop
            win = Desktop(backend="uia").active()
            if win:
                rect = win.rectangle()
                return {
                    "title": win.window_text(),
                    "rect": Rect(rect.left, rect.top, rect.right, rect.bottom),
                    "class_name": win.class_name(),
                }
        except:
            pass
        return None
    
    def focus_window(self, title: str) -> bool:
        """聚焦到指定标题的窗口"""
        if not self._has_pywinauto:
            return False
        
        try:
            from pywinauto import Desktop
            windows = Desktop(backend="uia").windows()
            for win in windows:
                if title.lower() in win.window_text().lower():
                    win.set_focus()
                    return True
        except:
            pass
        return False
    
    def get_ui_elements(self) -> List[Dict[str, Any]]:
        """
        获取当前窗口的UI元素列表
        
        使用Windows UI Automation获取可交互元素
        """
        if not self._has_pywinauto:
            return []
        
        elements = []
        try:
            from pywinauto import Desktop
            win = Desktop(backend="uia").active()
            if win:
                # 递归获取控件
                self._collect_elements(win, elements, depth=0, max_depth=3)
        except:
            pass
        return elements
    
    def _collect_elements(
        self,
        control,
        elements: List[Dict[str, Any]],
        depth: int,
        max_depth: int
    ) -> None:
        """递归收集UI元素"""
        if depth > max_depth:
            return
        
        try:
            rect = control.rectangle()
            element = {
                "type": control.element_info.control_type,
                "name": control.window_text(),
                "rect": Rect(rect.left, rect.top, rect.right, rect.bottom),
                "automation_id": getattr(control.element_info, "automation_id", ""),
            }
            
            # 只收集可见且有意义的元素
            if rect.width() > 0 and rect.height() > 0:
                elements.append(element)
            
            # 递归子控件
            for child in control.children():
                self._collect_elements(child, elements, depth + 1, max_depth)
        except:
            pass

