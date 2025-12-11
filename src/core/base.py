"""
Computer Control Framework - Base Controller
控制器基类 - 定义控制接口

这是所有平台特定实现的基类
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from .types import (
    Action,
    ActionResult,
    ActionType,
    CoordinateType,
    MouseButton,
    Point,
    Rect,
    ScreenElement,
    Size,
)

# 获取日志器
logger = logging.getLogger(__name__)


class ComputerController(ABC):
    """
    电脑控制器基类

    定义了所有平台必须实现的接口
    子类需要实现具体的平台代码 (macOS/Windows/Linux)
    """

    def __init__(self):
        self._screen_size: Optional[Size] = None

    # ==================== 屏幕信息 ====================

    @abstractmethod
    def get_screen_size(self) -> Size:
        """获取屏幕尺寸"""
        pass

    @abstractmethod
    def get_mouse_position(self) -> Point:
        """获取当前鼠标位置"""
        pass

    # ==================== 截屏功能 ====================

    @abstractmethod
    def screenshot(self, region: Optional[Rect] = None) -> bytes:
        """
        截取屏幕

        Args:
            region: 截取区域，None表示全屏

        Returns:
            PNG格式的图片字节数据
        """
        pass

    def screenshot_base64(self, region: Optional[Rect] = None) -> str:
        """截屏并返回base64编码"""
        import base64
        img_bytes = self.screenshot(region)
        return base64.b64encode(img_bytes).decode('utf-8')

    # ==================== 鼠标控制 ====================

    @abstractmethod
    def mouse_move(self, x: int, y: int, duration: float = 0.0) -> None:
        """
        移动鼠标到指定位置

        Args:
            x: 目标X坐标 (绝对像素)
            y: 目标Y坐标 (绝对像素)
            duration: 移动耗时 (秒)，0表示瞬移
        """
        pass

    @abstractmethod
    def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: MouseButton = MouseButton.LEFT,
        clicks: int = 1,
        interval: float = 0.1
    ) -> None:
        """
        鼠标点击

        Args:
            x, y: 点击位置，None表示当前位置
            button: 鼠标按键
            clicks: 点击次数
            interval: 多次点击间隔
        """
        pass

    @abstractmethod
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> None:
        """按下鼠标按键"""
        pass

    @abstractmethod
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> None:
        """释放鼠标按键"""
        pass

    @abstractmethod
    def mouse_scroll(
        self,
        clicks: int,
        x: Optional[int] = None,
        y: Optional[int] = None,
        horizontal: bool = False
    ) -> None:
        """
        鼠标滚轮

        Args:
            clicks: 滚动量，正数向上/向右，负数向下/向左
            x, y: 滚动位置
            horizontal: 是否水平滚动
        """
        pass

    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: MouseButton = MouseButton.LEFT,
        duration: float = 0.5
    ) -> None:
        """
        鼠标拖拽

        默认实现使用 move + down + move + up
        子类可以覆盖以使用平台原生拖拽
        """
        self.mouse_move(start_x, start_y)
        self.mouse_down(button)
        time.sleep(0.1)
        self.mouse_move(end_x, end_y, duration=duration)
        time.sleep(0.1)
        self.mouse_up(button)

    # ==================== 键盘控制 ====================

    @abstractmethod
    def type_text(self, text: str, interval: float = 0.0) -> None:
        """
        输入文本

        Args:
            text: 要输入的文本
            interval: 按键间隔
        """
        pass

    @abstractmethod
    def key_press(self, key: str) -> None:
        """
        按下并释放单个按键

        Args:
            key: 按键名称 (如 'enter', 'tab', 'a', 'ctrl')
        """
        pass

    @abstractmethod
    def key_down(self, key: str) -> None:
        """按下按键"""
        pass

    @abstractmethod
    def key_up(self, key: str) -> None:
        """释放按键"""
        pass

    def hotkey(self, *keys: str) -> None:
        """
        组合键

        Args:
            keys: 按键序列，如 hotkey('ctrl', 'c') 表示 Ctrl+C
        """
        for key in keys:
            self.key_down(key)
        time.sleep(0.05)
        for key in reversed(keys):
            self.key_up(key)

    # ==================== 坐标转换 ====================

    def resolve_point(
        self,
        point: Optional[Point] = None,
        element_label: Optional[str] = None,
        elements: Optional[List[ScreenElement]] = None
    ) -> Tuple[int, int]:
        """
        解析坐标点，支持多种输入格式

        Args:
            point: Point对象
            element_label: 元素标签
            elements: 元素列表 (用于标签查找)

        Returns:
            (x, y) 绝对像素坐标
        """
        screen = self.get_screen_size()

        # 通过标签查找
        if element_label and elements:
            for elem in elements:
                if elem.label == element_label:
                    center = elem.rect.center
                    return int(center.x), int(center.y)
            raise ValueError(f"Element with label '{element_label}' not found")

        # 直接使用Point
        if point:
            if point.coordinate_type == CoordinateType.ABSOLUTE:
                return int(point.x), int(point.y)
            elif point.coordinate_type == CoordinateType.PERCENTAGE:
                return int(point.x * screen.width), int(point.y * screen.height)
            else:
                raise ValueError("Point with ELEMENT_LABEL type requires elements list")

        # 返回当前鼠标位置
        pos = self.get_mouse_position()
        return int(pos.x), int(pos.y)

    # ==================== 等待 ====================

    def wait(self, seconds: float) -> None:
        """等待指定时间"""
        time.sleep(seconds)


class ActionExecutor:
    """
    动作执行器

    将标准化的Action转换为具体的控制操作
    """

    def __init__(self, controller: ComputerController):
        self.controller = controller
        self._current_elements: List[ScreenElement] = []

    def set_elements(self, elements: List[ScreenElement]) -> None:
        """设置当前屏幕元素 (用于标签解析)"""
        self._current_elements = elements

    def execute(self, action: Action) -> ActionResult:
        """
        执行动作

        Args:
            action: Action对象

        Returns:
            ActionResult
        """
        start_time = time.time()

        try:
            logger.debug(f"Executing action: {action.action_type.value}")
            self._execute_action(action)
            duration = time.time() - start_time

            logger.debug(f"Action completed in {duration:.3f}s")
            return ActionResult(
                success=True,
                message=f"Action {action.action_type.value} executed successfully",
                duration=duration,
                screen_size=self.controller.get_screen_size()
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Action {action.action_type.value} failed: {e}", exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                message=f"Action {action.action_type.value} failed",
                duration=duration
            )

    def _execute_action(self, action: Action) -> None:
        """执行具体动作"""

        # 解析坐标
        x, y = None, None
        if action.coordinate or action.element_label:
            x, y = self.controller.resolve_point(
                point=action.coordinate,
                element_label=action.element_label,
                elements=self._current_elements
            )

        # 执行对应动作
        if action.action_type == ActionType.MOUSE_MOVE:
            self.controller.mouse_move(x, y, duration=action.duration)

        elif action.action_type == ActionType.CLICK:
            self.controller.mouse_click(x, y, button=action.button, clicks=1)

        elif action.action_type == ActionType.DOUBLE_CLICK:
            self.controller.mouse_click(x, y, button=action.button, clicks=2)

        elif action.action_type == ActionType.RIGHT_CLICK:
            self.controller.mouse_click(x, y, button=MouseButton.RIGHT, clicks=1)

        elif action.action_type == ActionType.DRAG:
            end_x, end_y = self.controller.resolve_point(
                point=action.end_coordinate,
                element_label=action.end_element_label,
                elements=self._current_elements
            )
            self.controller.mouse_drag(x, y, end_x, end_y, button=action.button, duration=action.duration)

        elif action.action_type == ActionType.SCROLL:
            amount = action.scroll_amount
            if action.scroll_direction in ("down", "left"):
                amount = -amount
            horizontal = action.scroll_direction in ("left", "right")
            self.controller.mouse_scroll(amount, x, y, horizontal=horizontal)

        elif action.action_type == ActionType.TYPE_TEXT:
            self.controller.type_text(action.text or "")

        elif action.action_type == ActionType.KEY_PRESS:
            if action.keys:
                for key in action.keys:
                    self.controller.key_press(key)
            elif action.text:
                self.controller.key_press(action.text)

        elif action.action_type == ActionType.KEY_DOWN:
            self.controller.key_down(action.text or action.keys[0] if action.keys else "")

        elif action.action_type == ActionType.KEY_UP:
            self.controller.key_up(action.text or action.keys[0] if action.keys else "")

        elif action.action_type == ActionType.HOTKEY:
            if action.keys:
                self.controller.hotkey(*action.keys)

        elif action.action_type == ActionType.WAIT:
            self.controller.wait(action.duration)

        elif action.action_type == ActionType.SCREENSHOT:
            # 截屏在 execute 方法中单独处理
            pass

        else:
            raise ValueError(f"Unknown action type: {action.action_type}")
