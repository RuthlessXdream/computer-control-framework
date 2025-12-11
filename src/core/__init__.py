"""
Core Module - 核心模块

包含:
- types: 类型定义
- base: 控制器基类
- actions: 动作执行器 (从 base 重导出)
- retry: 重试机制
"""

from .types import (
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

from .base import (
    ComputerController,
    ActionExecutor,
)

from .retry import (
    RetryConfig,
    RetryExecutor,
    retry,
    exponential_backoff,
    constant_backoff,
    linear_backoff,
    fibonacci_backoff,
    random_backoff,
    jittered_backoff,
    STANDARD_RETRY,
    AGGRESSIVE_RETRY,
    CONSERVATIVE_RETRY,
    NETWORK_RETRY,
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
