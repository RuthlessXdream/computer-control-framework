"""
Computer Control Framework
跨平台电脑控制框架

一个为AI Agent设计的电脑控制层，支持：
- macOS / Windows / Linux
- 截屏和UI元素检测
- 鼠标键盘控制
- 预留AI接口
- 异步执行
- 重试机制
- 调试工具

快速开始:
    from src import get_controller, ComputerAgent, AIBrain

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

    # 方式3: 异步Agent
    from src import AsyncComputerAgent, AsyncAIBrain

    class MyAsyncBrain(AsyncAIBrain):
        async def think(self, screen_state, task):
            return Action(...)

    agent = AsyncComputerAgent(MyAsyncBrain())
    await agent.run("执行任务")
"""

__version__ = "0.2.0"

# 核心类型
from .core.types import (
    Action,
    ActionResult,
    ActionType,
    CoordinateType,
    MouseButton,
    Point,
    Rect,
    ScreenElement,
    ScreenState,
    Size,
)

# 控制器
from .core.base import ActionExecutor, ComputerController
from .core.retry import (
    AGGRESSIVE_RETRY,
    CONSERVATIVE_RETRY,
    STANDARD_RETRY,
    RetryConfig,
    RetryExecutor,
    constant_backoff,
    exponential_backoff,
    jittered_backoff,
    linear_backoff,
    retry,
)
from .platforms import get_controller

# AI接口 (同步)
from .ai_interface import (
    AgentConfig,
    AIBrain,
    ComputerAgent,
    create_agent,
    SimpleClickBrain,
)

# AI接口 (异步)
from .async_agent import (
    AsyncAgentConfig,
    AsyncAIBrain,
    AsyncComputerAgent,
    create_async_agent,
    run_task,
    SyncBrainAdapter,
)

# 视觉模块
from .vision.accessibility_detector import (
    AccessibilityDetector,
    HybridDetector,
)
from .vision.annotator import ScreenAnnotator
from .vision.detector import (
    CompositeDetector,
    CustomDetector,
    DummyDetector,
    EasyOCRDetector,
    ElementDetector,
    OmniParserDetector as OmniParserDetectorRemote,
    YOLODetector,
)
from .vision.omniparser_detector import OmniParserDetector

# 日志和调试
from .utils.debug import (
    annotate_screenshot,
    create_debug_agent,
    DebugAgent,
    DebugViewer,
    quick_screenshot_debug,
    save_debug_screenshot,
)
from .utils.logger import (
    get_action_logger,
    get_logger,
    init_logging,
    set_level,
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
    # Retry
    "RetryConfig",
    "RetryExecutor",
    "retry",
    "exponential_backoff",
    "constant_backoff",
    "linear_backoff",
    "jittered_backoff",
    "STANDARD_RETRY",
    "AGGRESSIVE_RETRY",
    "CONSERVATIVE_RETRY",
    # AI Interface (Sync)
    "AIBrain",
    "ComputerAgent",
    "AgentConfig",
    "create_agent",
    "SimpleClickBrain",
    # AI Interface (Async)
    "AsyncAIBrain",
    "AsyncComputerAgent",
    "AsyncAgentConfig",
    "SyncBrainAdapter",
    "create_async_agent",
    "run_task",
    # Vision
    "ScreenAnnotator",
    "ElementDetector",
    "DummyDetector",
    "YOLODetector",
    "EasyOCRDetector",
    "CustomDetector",
    "CompositeDetector",
    "OmniParserDetector",
    "OmniParserDetectorRemote",
    "AccessibilityDetector",
    "HybridDetector",
    # Logging & Debug
    "get_logger",
    "get_action_logger",
    "init_logging",
    "set_level",
    "DebugViewer",
    "DebugAgent",
    "save_debug_screenshot",
    "annotate_screenshot",
    "create_debug_agent",
    "quick_screenshot_debug",
]
