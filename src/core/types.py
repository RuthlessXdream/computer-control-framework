"""
Computer Control Framework - Type Definitions
核心类型定义 - 标准化输入输出格式

设计原则：
1. 坐标支持三种模式：绝对像素、百分比、元素标签
2. 所有操作返回统一的ActionResult
3. 截屏返回base64 + 元素标注信息
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Union, Tuple
import base64


class CoordinateType(Enum):
    """坐标类型"""
    ABSOLUTE = auto()       # 绝对像素坐标 (x=100, y=200)
    PERCENTAGE = auto()     # 百分比坐标 (x=0.5, y=0.3 表示屏幕50%和30%位置)
    ELEMENT_LABEL = auto()  # 元素标签 (label="~1" 表示标注的第1个元素)


class MouseButton(Enum):
    """鼠标按键"""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class ActionType(Enum):
    """操作类型"""
    # 鼠标操作
    MOUSE_MOVE = "mouse_move"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    SCROLL = "scroll"
    
    # 键盘操作
    TYPE_TEXT = "type_text"
    KEY_PRESS = "key_press"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    HOTKEY = "hotkey"
    
    # 系统操作
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    
    # 窗口操作
    FOCUS_WINDOW = "focus_window"
    GET_WINDOW_INFO = "get_window_info"


@dataclass
class Point:
    """坐标点"""
    x: float
    y: float
    coordinate_type: CoordinateType = CoordinateType.ABSOLUTE
    
    def to_absolute(self, screen_width: int, screen_height: int) -> "Point":
        """转换为绝对坐标"""
        if self.coordinate_type == CoordinateType.ABSOLUTE:
            return Point(int(self.x), int(self.y), CoordinateType.ABSOLUTE)
        elif self.coordinate_type == CoordinateType.PERCENTAGE:
            return Point(
                int(self.x * screen_width),
                int(self.y * screen_height),
                CoordinateType.ABSOLUTE
            )
        else:
            raise ValueError("Cannot convert ELEMENT_LABEL to absolute without element info")
    
    def to_percentage(self, screen_width: int, screen_height: int) -> "Point":
        """转换为百分比坐标"""
        if self.coordinate_type == CoordinateType.PERCENTAGE:
            return self
        elif self.coordinate_type == CoordinateType.ABSOLUTE:
            return Point(
                self.x / screen_width,
                self.y / screen_height,
                CoordinateType.PERCENTAGE
            )
        else:
            raise ValueError("Cannot convert ELEMENT_LABEL to percentage without element info")


@dataclass
class Size:
    """尺寸"""
    width: int
    height: int


@dataclass
class Rect:
    """矩形区域"""
    left: int
    top: int
    right: int
    bottom: int
    
    @property
    def width(self) -> int:
        return self.right - self.left
    
    @property
    def height(self) -> int:
        return self.bottom - self.top
    
    @property
    def center(self) -> Point:
        return Point(
            (self.left + self.right) / 2,
            (self.top + self.bottom) / 2,
            CoordinateType.ABSOLUTE
        )
    
    def to_percentage(self, screen_width: int, screen_height: int) -> "Rect":
        """转换为百分比矩形"""
        return Rect(
            self.left / screen_width,
            self.top / screen_height,
            self.right / screen_width,
            self.bottom / screen_height
        )


@dataclass
class ScreenElement:
    """
    屏幕元素 - AI识别到的UI元素
    
    支持两种定位方式：
    1. label: 用于AI模型通过标签引用 (如 "~1", "~2")
    2. rect: 边界框坐标
    """
    label: str                          # 元素标签 (如 "~1", "A", "1")
    rect: Rect                          # 边界框 (绝对坐标)
    element_type: Optional[str] = None  # 元素类型 (button, text, icon等)
    text: Optional[str] = None          # 元素文本内容 (OCR识别)
    confidence: float = 1.0             # 检测置信度
    
    @property
    def center_point(self) -> Point:
        """获取元素中心点"""
        return self.rect.center


@dataclass 
class Action:
    """
    操作指令 - AI的输出格式
    
    这是AI模型输出的标准格式，控制层负责执行
    """
    action_type: ActionType
    
    # 坐标相关 (鼠标操作)
    coordinate: Optional[Point] = None
    element_label: Optional[str] = None  # 通过标签定位元素
    
    # 文本相关 (键盘操作)
    text: Optional[str] = None
    keys: Optional[List[str]] = None
    
    # 其他参数
    button: MouseButton = MouseButton.LEFT
    scroll_amount: int = 0
    scroll_direction: str = "down"  # up, down, left, right
    duration: float = 0.0
    
    # 拖拽相关
    end_coordinate: Optional[Point] = None
    end_element_label: Optional[str] = None
    
    # 额外参数
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """
    操作结果 - 返回给AI的反馈
    
    包含执行状态和可选的截屏
    """
    success: bool
    message: str = ""
    error: Optional[str] = None
    
    # 截屏 (base64编码)
    screenshot_base64: Optional[str] = None
    
    # 检测到的UI元素列表
    elements: List[ScreenElement] = field(default_factory=list)
    
    # 元素标签到坐标的映射 (方便AI查询)
    label_to_rect: Dict[str, Rect] = field(default_factory=dict)
    
    # 屏幕信息
    screen_size: Optional[Size] = None
    
    # 执行耗时 (秒)
    duration: float = 0.0
    
    # 原始数据 (调试用)
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class ScreenState:
    """
    屏幕状态 - 截屏 + 元素识别结果
    
    这是发送给AI的输入格式
    """
    # 原始截屏 (base64)
    screenshot_base64: str
    
    # 标注后的截屏 (base64) - 带有元素标签框
    annotated_screenshot_base64: Optional[str] = None
    
    # 识别到的元素列表
    elements: List[ScreenElement] = field(default_factory=list)
    
    # 标签到坐标映射
    label_to_rect: Dict[str, Rect] = field(default_factory=dict)
    
    # 屏幕尺寸
    screen_size: Size = None
    
    # 时间戳
    timestamp: float = 0.0
    
    def get_element_by_label(self, label: str) -> Optional[ScreenElement]:
        """通过标签获取元素"""
        for elem in self.elements:
            if elem.label == label:
                return elem
        return None
    
    def get_click_point(self, label: str) -> Optional[Point]:
        """获取元素的点击坐标"""
        elem = self.get_element_by_label(label)
        if elem:
            return elem.center_point
        return None

