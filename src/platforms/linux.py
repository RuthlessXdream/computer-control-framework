"""
Linux Platform Controller
Linux平台控制器实现

使用技术栈:
- xdotool: 主要控制方式
- pyautogui: 备选方案
- scrot/gnome-screenshot: 截屏
"""

import platform
import subprocess
import tempfile
import time
from typing import Optional
from io import BytesIO

from ..core.base import ComputerController
from ..core.types import Point, Size, Rect, MouseButton, CoordinateType


class LinuxController(ComputerController):
    """
    Linux控制器
    
    优先使用xdotool，回退到pyautogui
    """
    
    def __init__(self):
        super().__init__()
        
        if platform.system() != "Linux":
            raise RuntimeError("LinuxController can only run on Linux")
        
        # 检查xdotool
        self._has_xdotool = self._check_command("xdotool")
        
        # 检查截屏工具
        self._screenshot_cmd = None
        if self._check_command("gnome-screenshot"):
            self._screenshot_cmd = "gnome-screenshot"
        elif self._check_command("scrot"):
            self._screenshot_cmd = "scrot"
        
        # 导入pyautogui作为备选
        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._pyautogui.FAILSAFE = False
            self._has_pyautogui = True
        except ImportError:
            self._has_pyautogui = False
        
        if not self._has_xdotool and not self._has_pyautogui:
            raise RuntimeError("Either xdotool or pyautogui is required")
        
        self._screen_size = self.get_screen_size()
    
    def _check_command(self, cmd: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except:
            return False
    
    def _run_xdotool(self, *args) -> str:
        """运行xdotool命令"""
        result = subprocess.run(["xdotool"] + list(args), capture_output=True, text=True)
        return result.stdout.strip()
    
    # ==================== 屏幕信息 ====================
    
    def get_screen_size(self) -> Size:
        """获取屏幕尺寸"""
        if self._has_xdotool:
            output = self._run_xdotool("getdisplaygeometry")
            parts = output.split()
            return Size(int(parts[0]), int(parts[1]))
        elif self._has_pyautogui:
            w, h = self._pyautogui.size()
            return Size(w, h)
        raise RuntimeError("Cannot get screen size")
    
    def get_mouse_position(self) -> Point:
        """获取当前鼠标位置"""
        if self._has_xdotool:
            output = self._run_xdotool("getmouselocation", "--shell")
            # 解析输出: X=123\nY=456\n...
            x, y = 0, 0
            for line in output.split('\n'):
                if line.startswith('X='):
                    x = int(line[2:])
                elif line.startswith('Y='):
                    y = int(line[2:])
            return Point(x, y, CoordinateType.ABSOLUTE)
        elif self._has_pyautogui:
            x, y = self._pyautogui.position()
            return Point(x, y, CoordinateType.ABSOLUTE)
        raise RuntimeError("Cannot get mouse position")
    
    # ==================== 截屏功能 ====================
    
    def screenshot(self, region: Optional[Rect] = None) -> bytes:
        """截取屏幕"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            if self._screenshot_cmd == "gnome-screenshot":
                if region:
                    # gnome-screenshot -a 需要交互，暂时不支持区域截图
                    subprocess.run(["gnome-screenshot", "-f", tmp_path], check=True)
                else:
                    subprocess.run(["gnome-screenshot", "-f", tmp_path], check=True)
            elif self._screenshot_cmd == "scrot":
                subprocess.run(["scrot", tmp_path], check=True)
            elif self._has_pyautogui:
                img = self._pyautogui.screenshot()
                img.save(tmp_path)
            else:
                raise RuntimeError("No screenshot tool available")
            
            with open(tmp_path, 'rb') as f:
                return f.read()
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    # ==================== 鼠标控制 ====================
    
    def mouse_move(self, x: int, y: int, duration: float = 0.0) -> None:
        """移动鼠标"""
        if self._has_xdotool:
            self._run_xdotool("mousemove", "--sync", str(x), str(y))
        elif self._has_pyautogui:
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
        
        if self._has_xdotool:
            btn_num = {MouseButton.LEFT: "1", MouseButton.MIDDLE: "2", MouseButton.RIGHT: "3"}[button]
            for i in range(clicks):
                self._run_xdotool("click", btn_num)
                if i < clicks - 1:
                    time.sleep(interval)
        elif self._has_pyautogui:
            self._pyautogui.click(clicks=clicks, interval=interval, button=button.value)
    
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> None:
        """按下鼠标"""
        if self._has_xdotool:
            btn_num = {MouseButton.LEFT: "1", MouseButton.MIDDLE: "2", MouseButton.RIGHT: "3"}[button]
            self._run_xdotool("mousedown", btn_num)
        elif self._has_pyautogui:
            self._pyautogui.mouseDown(button=button.value)
    
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> None:
        """释放鼠标"""
        if self._has_xdotool:
            btn_num = {MouseButton.LEFT: "1", MouseButton.MIDDLE: "2", MouseButton.RIGHT: "3"}[button]
            self._run_xdotool("mouseup", btn_num)
        elif self._has_pyautogui:
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
    
    # ==================== 键盘控制 ====================
    
    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本"""
        if self._has_xdotool:
            if interval > 0:
                self._run_xdotool("type", "--delay", str(int(interval * 1000)), text)
            else:
                self._run_xdotool("type", text)
        elif self._has_pyautogui:
            self._pyautogui.write(text, interval=interval)
    
    def key_press(self, key: str) -> None:
        """按键"""
        if self._has_xdotool:
            self._run_xdotool("key", key)
        elif self._has_pyautogui:
            self._pyautogui.press(key)
    
    def key_down(self, key: str) -> None:
        """按下按键"""
        if self._has_xdotool:
            self._run_xdotool("keydown", key)
        elif self._has_pyautogui:
            self._pyautogui.keyDown(key)
    
    def key_up(self, key: str) -> None:
        """释放按键"""
        if self._has_xdotool:
            self._run_xdotool("keyup", key)
        elif self._has_pyautogui:
            self._pyautogui.keyUp(key)
    
    def hotkey(self, *keys: str) -> None:
        """组合键"""
        if self._has_xdotool:
            # xdotool格式: key ctrl+c
            key_combo = "+".join(keys)
            self._run_xdotool("key", key_combo)
        elif self._has_pyautogui:
            self._pyautogui.hotkey(*keys)

