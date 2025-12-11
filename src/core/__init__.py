"""
Core Module - 核心模块

包含:
- types: 类型定义
- base: 控制器基类
- actions: 动作执行器 (从 base 重导出)
- retry: 重试机制
"""

from .base import (
    ActionExecutor,
    ComputerController,
)
from .retry import (
    AGGRESSIVE_RETRY,
    CONSERVATIVE_RETRY,
    NETWORK_RETRY,
    STANDARD_RETRY,
    RetryConfig,
    RetryExecutor,
    constant_backoff,
    exponential_backoff,
    fibonacci_backoff,
    jittered_backoff,
    linear_backoff,
    random_backoff,
    retry,
)
from .types import (
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

__all__ = [
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
    # Retry
    "RetryConfig",
    "RetryExecutor",
    "retry",
    "exponential_backoff",
    "constant_backoff",
    "linear_backoff",
    "fibonacci_backoff",
    "random_backoff",
    "jittered_backoff",
    "STANDARD_RETRY",
    "AGGRESSIVE_RETRY",
    "CONSERVATIVE_RETRY",
    "NETWORK_RETRY",
]
