"""
Computer Control Framework
跨平台电脑控制框架

一个为AI Agent设计的电脑控制层，支持：
- macOS / Windows / Linux
- 截屏和UI元素检测
- 鼠标键盘控制
- 预留AI接口

快速开始:
    from computer_control import get_controller, ComputerAgent, AIBrain
    
    # 方式1: 直接使用控制器
    controller = get_controller()
    controller.mouse_click(100, 200)
    controller.type_text("Hello World")
    
    # 方式2: 通过Agent使用
    class MyBrain(AIBrain):
        def think(self, screen_state, task):
            # 你的AI逻辑
            return Action(...)
    
    agent = ComputerAgent(MyBrain())
    agent.run("打开Chrome")
"""

__version__ = "0.1.0"

# 核心类型
from .core.types import (
    Point,
    Size,
    Rect,
    MouseButton,
    Action,
    ActionType,
    ActionResult,
    ScreenElement,
    ScreenState,
    CoordinateType,
)

# 控制器
from .core.base import ComputerController, ActionExecutor
from .platforms import get_controller

# AI接口
from .ai_interface import (
    AIBrain,
    ComputerAgent,
    AgentConfig,
    create_agent,
    SimpleClickBrain,
)

# 视觉模块
from .vision.annotator import ScreenAnnotator
from .vision.detector import (
    ElementDetector,
    DummyDetector,
    YOLODetector,
    EasyOCRDetector,
    CustomDetector,
    CompositeDetector,
    OmniParserDetector as OmniParserDetectorRemote,
)
from .vision.omniparser_detector import OmniParserDetector
from .vision.accessibility_detector import (
    AccessibilityDetector,
    HybridDetector,
)

__all__ = [
    # Version
    "__version__",
    
    # Types
    "Point",
    "Size", 
    "Rect",
    "MouseButton",
    "Action",
    "ActionType",
    "ActionResult",
    "ScreenElement",
    "ScreenState",
    "CoordinateType",
    
    # Controller
    "ComputerController",
    "ActionExecutor",
    "get_controller",
    
    # AI Interface
    "AIBrain",
    "ComputerAgent",
    "AgentConfig",
    "create_agent",
    "SimpleClickBrain",
    
    # Vision
    "ScreenAnnotator",
    "ElementDetector",
    "DummyDetector",
    "YOLODetector",
    "EasyOCRDetector",
    "CustomDetector",
    "CompositeDetector",
    "OmniParserDetector",
    "AccessibilityDetector",
    "HybridDetector",
]

