"""
Linux Platform Controller
Linux平台控制器实现

使用技术栈:
- xdotool: 主要控制方式 (X11)
- python-xlib: 原生 X11 API (可选)
- pyautogui: 备选方案
- scrot/gnome-screenshot/grim: 截屏

特性:
- 支持 X11 和 Wayland (有限)
- 自动检测最佳工具
- 内置重试机制
"""

import platform
import subprocess
import tempfile
import time
import os
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


class LinuxController(ComputerController):
    """
    Linux控制器
    
    支持 X11 (完整) 和 Wayland (有限)
    
    功能特性:
    - xdotool 支持 (X11)
    - python-xlib 原生支持 (可选)
    - 多种截屏工具自动选择
    - 内置重试机制
    """
    
    def __init__(self, retry_attempts: int = 3):
        """
        初始化 Linux 控制器
        
        Args:
            retry_attempts: 重试次数
        """
        super().__init__()
        
        if platform.system() != "Linux":
            raise RuntimeError("LinuxController can only run on Linux")
        
        self._retry_attempts = retry_attempts
        
        # 检测显示服务器类型
        self._display_server = self._detect_display_server()
        logger.info(f"检测到显示服务器: {self._display_server}")
        
        # 检查可用工具
        self._has_xdotool = self._check_command("xdotool")
        self._has_xclip = self._check_command("xclip")
        
        # 检测截屏工具 (按优先级)
        self._screenshot_tools = self._detect_screenshot_tools()
        logger.info(f"可用截屏工具: {self._screenshot_tools}")
        
        # 尝试导入 python-xlib
        self._has_xlib = False
        try:
            from Xlib import display, X
            self._xlib_display = display
            self._xlib_X = X
            self._has_xlib = True
            logger.info("python-xlib 已加载")
        except ImportError:
            logger.debug("python-xlib 未安装")
        
        # 导入pyautogui作为备选
        self._has_pyautogui = False
        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._pyautogui.FAILSAFE = False
            self._has_pyautogui = True
            logger.debug("pyautogui 已加载")
        except ImportError:
            pass
        
        # 导入 mss 用于高性能截屏
        self._has_mss = False
        try:
            import mss
            self._mss = mss
            self._has_mss = True
            logger.debug("mss 已加载")
        except ImportError:
            pass
        
        # 验证必要工具
        if not self._has_xdotool and not self._has_pyautogui and not self._has_xlib:
            raise RuntimeError(
                "需要至少安装以下工具之一: xdotool, pyautogui, python-xlib\n"
                "建议: sudo apt install xdotool"
            )
        
        if not self._screenshot_tools and not self._has_mss:
            raise RuntimeError(
                "没有可用的截屏工具\n"
                "建议: sudo apt install scrot 或 pip install mss"
            )
        
        self._screen_size = self.get_screen_size()
        logger.info(f"Linux 控制器初始化完成，屏幕尺寸: {self._screen_size}")
    
    def _detect_display_server(self) -> str:
        """检测显示服务器类型"""
        xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if xdg_session == "wayland":
            return "wayland"
        elif xdg_session == "x11":
            return "x11"
        
        # 检查 WAYLAND_DISPLAY
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        
        # 检查 DISPLAY
        if os.environ.get("DISPLAY"):
            return "x11"
        
        return "unknown"
    
    def _check_command(self, cmd: str) -> bool:
        """检查命令是否可用"""
        try:
            result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except Exception:
            return False
    
    def _detect_screenshot_tools(self) -> List[str]:
        """检测可用的截屏工具"""
        tools = []
        
        # X11 工具
        if self._check_command("scrot"):
            tools.append("scrot")
        if self._check_command("maim"):
            tools.append("maim")
        if self._check_command("import"):  # ImageMagick
            tools.append("import")
        
        # GNOME
        if self._check_command("gnome-screenshot"):
            tools.append("gnome-screenshot")
        
        # Wayland 工具
        if self._check_command("grim"):
            tools.append("grim")
        if self._check_command("spectacle"):
            tools.append("spectacle")
        
        return tools
    
    def _run_command(self, cmd: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
        """运行命令并返回结果"""
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    
    def _run_xdotool(self, *args, timeout: int = 5) -> str:
        """运行xdotool命令"""
        result = self._run_command(["xdotool"] + list(args), timeout=timeout)
        if result.returncode != 0 and result.stderr:
            logger.debug(f"xdotool 警告: {result.stderr}")
        return result.stdout.strip()
    
    # ==================== 屏幕信息 ====================
    
    def get_screen_size(self) -> Size:
        """获取屏幕尺寸"""
        # 方法1: xdotool
        if self._has_xdotool:
            try:
                output = self._run_xdotool("getdisplaygeometry")
                parts = output.split()
                if len(parts) >= 2:
                    return Size(int(parts[0]), int(parts[1]))
            except Exception as e:
                logger.debug(f"xdotool 获取屏幕尺寸失败: {e}")
        
        # 方法2: xrandr
        try:
            result = self._run_command(["xrandr", "--current"])
            for line in result.stdout.split('\n'):
                if ' connected ' in line and 'primary' in line:
                    # 解析类似 "1920x1080+0+0" 的格式
                    import re
                    match = re.search(r'(\d+)x(\d+)\+', line)
                    if match:
                        return Size(int(match.group(1)), int(match.group(2)))
        except Exception as e:
            logger.debug(f"xrandr 获取屏幕尺寸失败: {e}")
        
        # 方法3: python-xlib
        if self._has_xlib:
            try:
                d = self._xlib_display.Display()
                screen = d.screen()
                return Size(screen.width_in_pixels, screen.height_in_pixels)
            except Exception as e:
                logger.debug(f"xlib 获取屏幕尺寸失败: {e}")
        
        # 方法4: pyautogui
        if self._has_pyautogui:
            w, h = self._pyautogui.size()
            return Size(w, h)
        
        raise RuntimeError("无法获取屏幕尺寸")
    
    def get_mouse_position(self) -> Point:
        """获取当前鼠标位置"""
        # 方法1: xdotool
        if self._has_xdotool:
            try:
                output = self._run_xdotool("getmouselocation", "--shell")
                x, y = 0, 0
                for line in output.split('\n'):
                    if line.startswith('X='):
                        x = int(line[2:])
                    elif line.startswith('Y='):
                        y = int(line[2:])
                return Point(x, y, CoordinateType.ABSOLUTE)
            except Exception as e:
                logger.debug(f"xdotool 获取鼠标位置失败: {e}")
        
        # 方法2: python-xlib
        if self._has_xlib:
            try:
                d = self._xlib_display.Display()
                data = d.screen().root.query_pointer()._data
                return Point(data["root_x"], data["root_y"], CoordinateType.ABSOLUTE)
            except Exception as e:
                logger.debug(f"xlib 获取鼠标位置失败: {e}")
        
        # 方法3: pyautogui
        if self._has_pyautogui:
            x, y = self._pyautogui.position()
            return Point(x, y, CoordinateType.ABSOLUTE)
        
        raise RuntimeError("无法获取鼠标位置")
    
    # ==================== 截屏功能 ====================
    
    @retry_on_failure(max_attempts=3)
    def screenshot(self, region: Optional[Rect] = None) -> bytes:
        """
        截取屏幕
        
        自动选择最佳截屏工具
        """
        # 方法1: mss (最快，跨平台)
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
                        monitor = sct.monitors[0]
                    
                    img = sct.grab(monitor)
                    
                    from PIL import Image
                    pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                    buffer = BytesIO()
                    pil_img.save(buffer, format='PNG')
                    return buffer.getvalue()
            except Exception as e:
                logger.debug(f"mss 截屏失败: {e}")
        
        # 方法2: 命令行工具
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            screenshot_taken = False
            
            for tool in self._screenshot_tools:
                try:
                    if tool == "scrot":
                        if region:
                            cmd = ["scrot", "-a", f"{region.left},{region.top},{region.width},{region.height}", tmp_path]
                        else:
                            cmd = ["scrot", tmp_path]
                        self._run_command(cmd)
                        screenshot_taken = True
                        break
                    
                    elif tool == "maim":
                        if region:
                            cmd = ["maim", "-g", f"{region.width}x{region.height}+{region.left}+{region.top}", tmp_path]
                        else:
                            cmd = ["maim", tmp_path]
                        self._run_command(cmd)
                        screenshot_taken = True
                        break
                    
                    elif tool == "import":
                        if region:
                            geometry = f"{region.width}x{region.height}+{region.left}+{region.top}"
                            cmd = ["import", "-window", "root", "-crop", geometry, tmp_path]
                        else:
                            cmd = ["import", "-window", "root", tmp_path]
                        self._run_command(cmd)
                        screenshot_taken = True
                        break
                    
                    elif tool == "gnome-screenshot":
                        # gnome-screenshot 不太支持精确区域
                        cmd = ["gnome-screenshot", "-f", tmp_path]
                        self._run_command(cmd)
                        screenshot_taken = True
                        break
                    
                    elif tool == "grim":  # Wayland
                        if region:
                            cmd = ["grim", "-g", f"{region.left},{region.top} {region.width}x{region.height}", tmp_path]
                        else:
                            cmd = ["grim", tmp_path]
                        self._run_command(cmd)
                        screenshot_taken = True
                        break
                    
                    elif tool == "spectacle":
                        cmd = ["spectacle", "-b", "-n", "-o", tmp_path]
                        self._run_command(cmd)
                        screenshot_taken = True
                        break
                    
                except Exception as e:
                    logger.debug(f"{tool} 截屏失败: {e}")
                    continue
            
            # 方法3: pyautogui 备选
            if not screenshot_taken and self._has_pyautogui:
                if region:
                    bbox = (region.left, region.top, region.width, region.height)
                    img = self._pyautogui.screenshot(region=bbox)
                else:
                    img = self._pyautogui.screenshot()
                img.save(tmp_path)
                screenshot_taken = True
            
            if not screenshot_taken:
                raise RuntimeError("所有截屏方法都失败了")
            
            with open(tmp_path, 'rb') as f:
                return f.read()
        
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    # ==================== 鼠标控制 ====================
    
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
                
                if self._has_xdotool:
                    self._run_xdotool("mousemove", "--sync", str(cur_x), str(cur_y))
                elif self._has_pyautogui:
                    self._pyautogui.moveTo(cur_x, cur_y, _pause=False)
                
                time.sleep(duration / steps)
        else:
            if self._has_xdotool:
                self._run_xdotool("mousemove", "--sync", str(x), str(y))
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
            time.sleep(0.02)
        
        if self._has_xdotool:
            btn_num = {
                MouseButton.LEFT: "1",
                MouseButton.MIDDLE: "2",
                MouseButton.RIGHT: "3"
            }[button]
            
            for i in range(clicks):
                self._run_xdotool("click", btn_num)
                if i < clicks - 1:
                    time.sleep(interval)
        elif self._has_pyautogui:
            self._pyautogui.click(clicks=clicks, interval=interval, button=button.value)
    
    @retry_on_failure(max_attempts=3)
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> None:
        """按下鼠标"""
        if self._has_xdotool:
            btn_num = {
                MouseButton.LEFT: "1",
                MouseButton.MIDDLE: "2",
                MouseButton.RIGHT: "3"
            }[button]
            self._run_xdotool("mousedown", btn_num)
        elif self._has_pyautogui:
            self._pyautogui.mouseDown(button=button.value)
    
    @retry_on_failure(max_attempts=3)
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> None:
        """释放鼠标"""
        if self._has_xdotool:
            btn_num = {
                MouseButton.LEFT: "1",
                MouseButton.MIDDLE: "2",
                MouseButton.RIGHT: "3"
            }[button]
            self._run_xdotool("mouseup", btn_num)
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
        
        if self._has_xdotool:
            # xdotool: button 4=up, 5=down, 6=left, 7=right
            if horizontal:
                btn = "6" if clicks < 0 else "7"
            else:
                btn = "4" if clicks > 0 else "5"
            
            for _ in range(abs(clicks)):
                self._run_xdotool("click", btn)
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
    
    def _xdotool_key_name(self, key: str) -> str:
        """转换按键名为 xdotool 格式"""
        key_map = {
            'enter': 'Return',
            'return': 'Return',
            'tab': 'Tab',
            'space': 'space',
            'backspace': 'BackSpace',
            'delete': 'Delete',
            'escape': 'Escape',
            'esc': 'Escape',
            'shift': 'shift',
            'shiftleft': 'shift',
            'shiftright': 'shift',
            'ctrl': 'ctrl',
            'control': 'ctrl',
            'ctrlleft': 'ctrl',
            'ctrlright': 'ctrl',
            'alt': 'alt',
            'altleft': 'alt',
            'altright': 'alt',
            'win': 'super',
            'super': 'super',
            'command': 'super',
            'cmd': 'super',
            'left': 'Left',
            'right': 'Right',
            'up': 'Up',
            'down': 'Down',
            'home': 'Home',
            'end': 'End',
            'pageup': 'Page_Up',
            'pgup': 'Page_Up',
            'pagedown': 'Page_Down',
            'pgdn': 'Page_Down',
            'insert': 'Insert',
            'f1': 'F1', 'f2': 'F2', 'f3': 'F3', 'f4': 'F4',
            'f5': 'F5', 'f6': 'F6', 'f7': 'F7', 'f8': 'F8',
            'f9': 'F9', 'f10': 'F10', 'f11': 'F11', 'f12': 'F12',
        }
        return key_map.get(key.lower(), key)
    
    @retry_on_failure(max_attempts=3)
    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本"""
        if self._has_xdotool:
            if interval > 0:
                self._run_xdotool("type", "--delay", str(int(interval * 1000)), "--", text)
            else:
                self._run_xdotool("type", "--", text)
        elif self._has_pyautogui:
            self._pyautogui.write(text, interval=interval)
    
    @retry_on_failure(max_attempts=3)
    def key_press(self, key: str) -> None:
        """按键"""
        if self._has_xdotool:
            xkey = self._xdotool_key_name(key)
            self._run_xdotool("key", xkey)
        elif self._has_pyautogui:
            self._pyautogui.press(key)
    
    @retry_on_failure(max_attempts=3)
    def key_down(self, key: str) -> None:
        """按下按键"""
        if self._has_xdotool:
            xkey = self._xdotool_key_name(key)
            self._run_xdotool("keydown", xkey)
        elif self._has_pyautogui:
            self._pyautogui.keyDown(key)
    
    @retry_on_failure(max_attempts=3)
    def key_up(self, key: str) -> None:
        """释放按键"""
        if self._has_xdotool:
            xkey = self._xdotool_key_name(key)
            self._run_xdotool("keyup", xkey)
        elif self._has_pyautogui:
            self._pyautogui.keyUp(key)
    
    def hotkey(self, *keys: str) -> None:
        """组合键"""
        if self._has_xdotool:
            # xdotool格式: key ctrl+c
            xkeys = [self._xdotool_key_name(k) for k in keys]
            key_combo = "+".join(xkeys)
            self._run_xdotool("key", key_combo)
        elif self._has_pyautogui:
            self._pyautogui.hotkey(*keys)
    
    # ==================== Linux 特有功能 ====================
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """获取当前活动窗口"""
        if self._has_xdotool:
            try:
                window_id = self._run_xdotool("getactivewindow")
                if window_id:
                    name = self._run_xdotool("getwindowname", window_id)
                    geometry = self._run_xdotool("getwindowgeometry", "--shell", window_id)
                    
                    info = {"id": window_id, "name": name}
                    
                    for line in geometry.split('\n'):
                        if line.startswith('X='):
                            info['x'] = int(line[2:])
                        elif line.startswith('Y='):
                            info['y'] = int(line[2:])
                        elif line.startswith('WIDTH='):
                            info['width'] = int(line[6:])
                        elif line.startswith('HEIGHT='):
                            info['height'] = int(line[7:])
                    
                    if all(k in info for k in ['x', 'y', 'width', 'height']):
                        info['rect'] = Rect(
                            info['x'], info['y'],
                            info['x'] + info['width'],
                            info['y'] + info['height']
                        )
                    
                    return info
            except Exception as e:
                logger.debug(f"获取活动窗口失败: {e}")
        
        return None
    
    def focus_window(self, title: str = None, window_id: str = None) -> bool:
        """聚焦到指定窗口"""
        if not self._has_xdotool:
            return False
        
        try:
            if window_id:
                self._run_xdotool("windowactivate", "--sync", window_id)
                return True
            elif title:
                self._run_xdotool("search", "--name", title, "windowactivate", "--sync")
                return True
        except Exception as e:
            logger.debug(f"聚焦窗口失败: {e}")
        
        return False
    
    def list_windows(self) -> List[Dict[str, Any]]:
        """列出所有窗口"""
        windows = []
        
        if self._has_xdotool:
            try:
                output = self._run_xdotool("search", "--onlyvisible", "--name", "")
                for window_id in output.split('\n'):
                    if window_id.strip():
                        try:
                            name = self._run_xdotool("getwindowname", window_id)
                            windows.append({
                                "id": window_id,
                                "name": name
                            })
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"列出窗口失败: {e}")
        
        return windows
    
    def get_clipboard(self) -> Optional[str]:
        """获取剪贴板内容"""
        if self._has_xclip:
            try:
                result = self._run_command(["xclip", "-selection", "clipboard", "-o"])
                return result.stdout
            except Exception:
                pass
        return None
    
    def set_clipboard(self, text: str) -> bool:
        """设置剪贴板内容"""
        if self._has_xclip:
            try:
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE
                )
                process.communicate(input=text.encode())
                return process.returncode == 0
            except Exception:
                pass
        return False
    
    def minimize_window(self, window_id: str = None) -> bool:
        """最小化窗口"""
        if self._has_xdotool:
            try:
                if window_id is None:
                    window_id = self._run_xdotool("getactivewindow")
                if window_id:
                    self._run_xdotool("windowminimize", window_id)
                    return True
            except Exception:
                pass
        return False
    
    def maximize_window(self, window_id: str = None) -> bool:
        """最大化窗口"""
        if self._has_xdotool:
            try:
                if window_id is None:
                    window_id = self._run_xdotool("getactivewindow")
                if window_id:
                    # 使用 wmctrl 或模拟按键
                    self._run_command([
                        "wmctrl", "-i", "-r", window_id, "-b", "add,maximized_vert,maximized_horz"
                    ])
                    return True
            except Exception:
                pass
        return False
