"""
Windows Platform Controller
Windows平台控制器实现

使用技术栈:
- ctypes/win32api: 原生 Windows API (优先)
- pyautogui: 备选方案
- pywinauto: UI自动化和窗口控制 (可选)
- PIL/mss: 截屏

特性:
- 支持原生 Windows API，性能更好
- 自动降级到 pyautogui
- 内置重试机制
"""

import platform
import time
import logging
from typing import Optional, List, Dict, Any, Callable, TypeVar
from io import BytesIO
from functools import wraps

from ..core.base import ComputerController
from ..core.types import Point, Size, Rect, MouseButton, CoordinateType

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_on_failure(max_attempts: int = 3, delay: float = 0.1) -> Callable:
    """重试装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.debug(f"操作失败，重试 {attempt + 1}/{max_attempts}: {e}")
                        time.sleep(delay)
            raise last_error
        return wrapper
    return decorator


class WindowsController(ComputerController):
    """
    Windows控制器
    
    优先使用原生 Windows API，自动降级到 pyautogui
    
    功能特性:
    - 原生 API 支持 (ctypes)
    - 自动降级机制
    - 内置重试
    - 窗口管理
    - UI 自动化
    """
    
    def __init__(self, use_native: bool = True, retry_attempts: int = 3):
        """
        初始化 Windows 控制器
        
        Args:
            use_native: 是否优先使用原生 API
            retry_attempts: 重试次数
        """
        super().__init__()
        
        if platform.system() != "Windows":
            raise RuntimeError("WindowsController can only run on Windows")
        
        self._retry_attempts = retry_attempts
        self._use_native = use_native
        self._native_available = False
        
        # 尝试导入原生 API
        if use_native:
            try:
                import ctypes
                from ctypes import wintypes
                self._ctypes = ctypes
                self._user32 = ctypes.windll.user32
                self._kernel32 = ctypes.windll.kernel32
                self._native_available = True
                logger.info("Windows 原生 API 已加载")
            except Exception as e:
                logger.warning(f"无法加载原生 API，将使用 pyautogui: {e}")
        
        # 导入pyautogui
        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._pyautogui.FAILSAFE = False
            self._pyautogui.PAUSE = 0.01  # 减少默认暂停
            self._has_pyautogui = True
        except ImportError:
            if not self._native_available:
                raise RuntimeError("pyautogui is required when native API is not available")
            self._has_pyautogui = False
        
        # 尝试导入pywinauto (可选)
        self._has_pywinauto = False
        try:
            import pywinauto
            from pywinauto.keyboard import send_keys
            self._pywinauto = pywinauto
            self._send_keys = send_keys
            self._has_pywinauto = True
            logger.info("pywinauto 已加载")
        except ImportError:
            logger.debug("pywinauto 未安装，部分高级功能不可用")
        
        # 导入 mss 用于高性能截屏
        self._has_mss = False
        try:
            import mss
            self._mss = mss
            self._has_mss = True
            logger.debug("mss 已加载，使用高性能截屏")
        except ImportError:
            pass
        
        # 导入PIL用于截屏备选
        self._has_pil = False
        try:
            from PIL import ImageGrab
            self._image_grab = ImageGrab
            self._has_pil = True
        except ImportError:
            pass
        
        self._screen_size = self.get_screen_size()
        logger.info(f"Windows 控制器初始化完成，屏幕尺寸: {self._screen_size}")
    
    # ==================== 屏幕信息 ====================
    
    def get_screen_size(self) -> Size:
        """获取屏幕尺寸"""
        if self._native_available:
            try:
                width = self._user32.GetSystemMetrics(0)  # SM_CXSCREEN
                height = self._user32.GetSystemMetrics(1)  # SM_CYSCREEN
                return Size(width, height)
            except Exception as e:
                logger.debug(f"原生获取屏幕尺寸失败: {e}")
        
        if self._has_pyautogui:
            w, h = self._pyautogui.size()
            return Size(w, h)
        
        raise RuntimeError("无法获取屏幕尺寸")
    
    def get_mouse_position(self) -> Point:
        """获取当前鼠标位置"""
        if self._native_available:
            try:
                from ctypes import wintypes, byref
                point = wintypes.POINT()
                self._user32.GetCursorPos(byref(point))
                return Point(point.x, point.y, CoordinateType.ABSOLUTE)
            except Exception as e:
                logger.debug(f"原生获取鼠标位置失败: {e}")
        
        if self._has_pyautogui:
            x, y = self._pyautogui.position()
            return Point(x, y, CoordinateType.ABSOLUTE)
        
        raise RuntimeError("无法获取鼠标位置")
    
    # ==================== 截屏功能 ====================
    
    @retry_on_failure(max_attempts=3)
    def screenshot(self, region: Optional[Rect] = None) -> bytes:
        """
        截取屏幕
        
        优先使用 mss (更快)，备选 PIL/pyautogui
        """
        # 方法1: mss (最快)
        if self._has_mss:
            try:
                with self._mss.mss() as sct:
                    if region:
                        monitor = {
                            "left": region.left,
                            "top": region.top,
                            "width": region.width,
                            "height": region.height
                        }
                    else:
                        monitor = sct.monitors[0]  # 主显示器
                    
                    img = sct.grab(monitor)
                    
                    # 转换为 PNG
                    from PIL import Image
                    pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                    buffer = BytesIO()
                    pil_img.save(buffer, format='PNG')
                    return buffer.getvalue()
            except Exception as e:
                logger.debug(f"mss 截屏失败: {e}")
        
        # 方法2: PIL ImageGrab
        if self._has_pil:
            try:
                if region:
                    bbox = (region.left, region.top, region.right, region.bottom)
                    img = self._image_grab.grab(bbox=bbox)
                else:
                    img = self._image_grab.grab()
                
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                return buffer.getvalue()
            except Exception as e:
                logger.debug(f"PIL 截屏失败: {e}")
        
        # 方法3: pyautogui
        if self._has_pyautogui:
            if region:
                bbox = (region.left, region.top, region.width, region.height)
                img = self._pyautogui.screenshot(region=bbox)
            else:
                img = self._pyautogui.screenshot()
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        
        raise RuntimeError("无可用的截屏方法")
    
    # ==================== 鼠标控制 ====================
    
    def _native_mouse_move(self, x: int, y: int) -> None:
        """原生 API 移动鼠标"""
        self._user32.SetCursorPos(x, y)
    
    def _native_mouse_event(self, flags: int, x: int = 0, y: int = 0, data: int = 0) -> None:
        """发送原生鼠标事件"""
        self._user32.mouse_event(flags, x, y, data, 0)
    
    @retry_on_failure(max_attempts=3)
    def mouse_move(self, x: int, y: int, duration: float = 0.0) -> None:
        """移动鼠标"""
        if duration > 0:
            # 平滑移动
            start = self.get_mouse_position()
            steps = max(int(duration * 60), 1)
            
            for i in range(1, steps + 1):
                t = i / steps
                cur_x = int(start.x + (x - start.x) * t)
                cur_y = int(start.y + (y - start.y) * t)
                
                if self._native_available:
                    self._native_mouse_move(cur_x, cur_y)
                elif self._has_pyautogui:
                    self._pyautogui.moveTo(cur_x, cur_y, _pause=False)
                
                time.sleep(duration / steps)
        else:
            if self._native_available:
                self._native_mouse_move(x, y)
            elif self._has_pyautogui:
                self._pyautogui.moveTo(x, y, _pause=False)
    
    @retry_on_failure(max_attempts=3)
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
            time.sleep(0.02)  # 短暂等待确保位置更新
        
        if self._native_available:
            # 原生 API 鼠标事件标志
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004
            MOUSEEVENTF_RIGHTDOWN = 0x0008
            MOUSEEVENTF_RIGHTUP = 0x0010
            MOUSEEVENTF_MIDDLEDOWN = 0x0020
            MOUSEEVENTF_MIDDLEUP = 0x0040
            
            if button == MouseButton.LEFT:
                down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
            elif button == MouseButton.RIGHT:
                down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
            else:
                down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
            
            for i in range(clicks):
                self._native_mouse_event(down)
                time.sleep(0.01)
                self._native_mouse_event(up)
                if i < clicks - 1:
                    time.sleep(interval)
        elif self._has_pyautogui:
            self._pyautogui.click(x, y, clicks=clicks, interval=interval, button=button.value)
    
    @retry_on_failure(max_attempts=3)
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> None:
        """按下鼠标"""
        if self._native_available:
            flags = {
                MouseButton.LEFT: 0x0002,
                MouseButton.RIGHT: 0x0008,
                MouseButton.MIDDLE: 0x0020
            }
            self._native_mouse_event(flags[button])
        elif self._has_pyautogui:
            self._pyautogui.mouseDown(button=button.value)
    
    @retry_on_failure(max_attempts=3)
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> None:
        """释放鼠标"""
        if self._native_available:
            flags = {
                MouseButton.LEFT: 0x0004,
                MouseButton.RIGHT: 0x0010,
                MouseButton.MIDDLE: 0x0040
            }
            self._native_mouse_event(flags[button])
        elif self._has_pyautogui:
            self._pyautogui.mouseUp(button=button.value)
    
    @retry_on_failure(max_attempts=3)
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
        
        if self._native_available:
            MOUSEEVENTF_WHEEL = 0x0800
            MOUSEEVENTF_HWHEEL = 0x1000
            WHEEL_DELTA = 120
            
            flag = MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL
            self._native_mouse_event(flag, data=clicks * WHEEL_DELTA)
        elif self._has_pyautogui:
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
        self.mouse_move(start_x, start_y)
        time.sleep(0.05)
        self.mouse_down(button)
        time.sleep(0.05)
        self.mouse_move(end_x, end_y, duration=duration)
        time.sleep(0.05)
        self.mouse_up(button)
    
    # ==================== 键盘控制 ====================
    
    def _get_vk_code(self, key: str) -> Optional[int]:
        """获取虚拟键码"""
        # Windows 虚拟键码映射
        vk_map = {
            # 特殊键
            'enter': 0x0D, 'return': 0x0D,
            'tab': 0x09,
            'space': 0x20, ' ': 0x20,
            'backspace': 0x08, 'back': 0x08,
            'delete': 0x2E, 'del': 0x2E,
            'escape': 0x1B, 'esc': 0x1B,
            
            # 修饰键
            'shift': 0x10, 'shiftleft': 0xA0, 'shiftright': 0xA1,
            'ctrl': 0x11, 'control': 0x11, 'ctrlleft': 0xA2, 'ctrlright': 0xA3,
            'alt': 0x12, 'altleft': 0xA4, 'altright': 0xA5,
            'win': 0x5B, 'winleft': 0x5B, 'winright': 0x5C,
            'command': 0x5B, 'cmd': 0x5B,  # Windows 键作为 Command
            
            # 功能键
            'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
            'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
            'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
            
            # 方向键
            'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
            
            # 其他
            'home': 0x24, 'end': 0x23,
            'pageup': 0x21, 'pgup': 0x21,
            'pagedown': 0x22, 'pgdn': 0x22,
            'insert': 0x2D,
            'capslock': 0x14,
            'numlock': 0x90,
            'printscreen': 0x2C, 'prtsc': 0x2C,
        }
        
        key_lower = key.lower()
        
        if key_lower in vk_map:
            return vk_map[key_lower]
        
        # 单字符
        if len(key) == 1:
            return ord(key.upper())
        
        return None
    
    def _native_key_event(self, vk: int, down: bool) -> None:
        """发送原生键盘事件"""
        KEYEVENTF_KEYUP = 0x0002
        flags = 0 if down else KEYEVENTF_KEYUP
        self._user32.keybd_event(vk, 0, flags, 0)
    
    @retry_on_failure(max_attempts=3)
    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本"""
        if self._has_pywinauto:
            # pywinauto 支持更多特殊字符和中文
            self._send_keys(text, pause=interval, with_spaces=True)
        elif self._has_pyautogui:
            self._pyautogui.write(text, interval=interval)
        elif self._native_available:
            # 原生方式逐字符输入
            for char in text:
                vk = self._get_vk_code(char)
                if vk:
                    self._native_key_event(vk, True)
                    time.sleep(0.01)
                    self._native_key_event(vk, False)
                    if interval > 0:
                        time.sleep(interval)
    
    @retry_on_failure(max_attempts=3)
    def key_press(self, key: str) -> None:
        """按键"""
        if self._native_available:
            vk = self._get_vk_code(key)
            if vk:
                self._native_key_event(vk, True)
                time.sleep(0.02)
                self._native_key_event(vk, False)
                return
        
        if self._has_pyautogui:
            self._pyautogui.press(key)
    
    @retry_on_failure(max_attempts=3)
    def key_down(self, key: str) -> None:
        """按下按键"""
        if self._native_available:
            vk = self._get_vk_code(key)
            if vk:
                self._native_key_event(vk, True)
                return
        
        if self._has_pyautogui:
            self._pyautogui.keyDown(key)
    
    @retry_on_failure(max_attempts=3)
    def key_up(self, key: str) -> None:
        """释放按键"""
        if self._native_available:
            vk = self._get_vk_code(key)
            if vk:
                self._native_key_event(vk, False)
                return
        
        if self._has_pyautogui:
            self._pyautogui.keyUp(key)
    
    def hotkey(self, *keys: str) -> None:
        """组合键"""
        if self._has_pyautogui:
            self._pyautogui.hotkey(*keys)
        else:
            # 原生方式
            for key in keys:
                self.key_down(key)
            time.sleep(0.05)
            for key in reversed(keys):
                self.key_up(key)
    
    # ==================== Windows 特有功能 ====================
    
    def get_window_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """获取指定位置的窗口信息"""
        if self._native_available:
            try:
                from ctypes import wintypes, create_unicode_buffer
                
                hwnd = self._user32.WindowFromPoint(wintypes.POINT(x, y))
                if hwnd:
                    # 获取窗口标题
                    length = self._user32.GetWindowTextLengthW(hwnd) + 1
                    buffer = create_unicode_buffer(length)
                    self._user32.GetWindowTextW(hwnd, buffer, length)
                    
                    # 获取窗口矩形
                    rect = wintypes.RECT()
                    self._user32.GetWindowRect(hwnd, self._ctypes.byref(rect))
                    
                    return {
                        "hwnd": hwnd,
                        "title": buffer.value,
                        "rect": Rect(rect.left, rect.top, rect.right, rect.bottom),
                    }
            except Exception as e:
                logger.debug(f"获取窗口信息失败: {e}")
        
        if self._has_pywinauto:
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
            except Exception:
                pass
        
        return None
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """获取当前活动窗口"""
        if self._native_available:
            try:
                from ctypes import wintypes, create_unicode_buffer
                
                hwnd = self._user32.GetForegroundWindow()
                if hwnd:
                    length = self._user32.GetWindowTextLengthW(hwnd) + 1
                    buffer = create_unicode_buffer(length)
                    self._user32.GetWindowTextW(hwnd, buffer, length)
                    
                    rect = wintypes.RECT()
                    self._user32.GetWindowRect(hwnd, self._ctypes.byref(rect))
                    
                    return {
                        "hwnd": hwnd,
                        "title": buffer.value,
                        "rect": Rect(rect.left, rect.top, rect.right, rect.bottom),
                    }
            except Exception as e:
                logger.debug(f"获取活动窗口失败: {e}")
        
        if self._has_pywinauto:
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
            except Exception:
                pass
        
        if self._has_pyautogui:
            try:
                title = self._pyautogui.getActiveWindowTitle()
                return {"title": title}
            except Exception:
                pass
        
        return None
    
    def focus_window(self, title: str) -> bool:
        """聚焦到指定标题的窗口"""
        if self._native_available:
            try:
                from ctypes import wintypes, create_unicode_buffer, WINFUNCTYPE
                
                target_hwnd = None
                
                # 枚举窗口回调
                WNDENUMPROC = WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                
                def enum_callback(hwnd, lparam):
                    nonlocal target_hwnd
                    length = self._user32.GetWindowTextLengthW(hwnd) + 1
                    buffer = create_unicode_buffer(length)
                    self._user32.GetWindowTextW(hwnd, buffer, length)
                    
                    if title.lower() in buffer.value.lower():
                        target_hwnd = hwnd
                        return False  # 停止枚举
                    return True
                
                self._user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
                
                if target_hwnd:
                    self._user32.SetForegroundWindow(target_hwnd)
                    return True
            except Exception as e:
                logger.debug(f"聚焦窗口失败: {e}")
        
        if self._has_pywinauto:
            try:
                from pywinauto import Desktop
                windows = Desktop(backend="uia").windows()
                for win in windows:
                    if title.lower() in win.window_text().lower():
                        win.set_focus()
                        return True
            except Exception:
                pass
        
        return False
    
    def get_ui_elements(self, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        获取当前窗口的UI元素列表
        
        使用Windows UI Automation获取可交互元素
        
        Args:
            max_depth: 递归深度限制
        """
        if not self._has_pywinauto:
            return []
        
        elements = []
        try:
            from pywinauto import Desktop
            win = Desktop(backend="uia").active()
            if win:
                self._collect_elements(win, elements, depth=0, max_depth=max_depth)
        except Exception as e:
            logger.debug(f"获取 UI 元素失败: {e}")
        
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
            
            # 只收集可见且有意义的元素
            if rect.width() > 0 and rect.height() > 0:
                element = {
                    "type": control.element_info.control_type,
                    "name": control.window_text(),
                    "rect": Rect(rect.left, rect.top, rect.right, rect.bottom),
                    "automation_id": getattr(control.element_info, "automation_id", ""),
                    "depth": depth,
                }
                elements.append(element)
            
            # 递归子控件
            for child in control.children():
                self._collect_elements(child, elements, depth + 1, max_depth)
        except Exception:
            pass
    
    def minimize_window(self, hwnd: int = None) -> bool:
        """最小化窗口"""
        if self._native_available:
            try:
                if hwnd is None:
                    hwnd = self._user32.GetForegroundWindow()
                if hwnd:
                    self._user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                    return True
            except Exception:
                pass
        return False
    
    def maximize_window(self, hwnd: int = None) -> bool:
        """最大化窗口"""
        if self._native_available:
            try:
                if hwnd is None:
                    hwnd = self._user32.GetForegroundWindow()
                if hwnd:
                    self._user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                    return True
            except Exception:
                pass
        return False
    
    def restore_window(self, hwnd: int = None) -> bool:
        """恢复窗口"""
        if self._native_available:
            try:
                if hwnd is None:
                    hwnd = self._user32.GetForegroundWindow()
                if hwnd:
                    self._user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    return True
            except Exception:
                pass
        return False
