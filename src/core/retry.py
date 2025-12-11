"""
Retry Mechanism - 重试机制和错误恢复

提供灵活的重试策略，用于处理:
- 临时性失败 (网络、系统繁忙)
- 竞态条件
- 不稳定的 UI 状态

使用方式:
    from src.core.retry import RetryExecutor, RetryConfig, exponential_backoff
    
    config = RetryConfig(
        max_attempts=3,
        backoff_strategy=exponential_backoff(base=0.1, max_delay=2.0)
    )
    
    executor = RetryExecutor(action_executor, config)
    result = executor.execute_with_retry(action)
"""

import time
import logging
import random
from typing import Callable, Optional, List, Type, TypeVar, Generic
from dataclasses import dataclass, field
from functools import wraps
from enum import Enum, auto

from .types import Action, ActionResult
from .base import ActionExecutor

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """重试策略类型"""
    CONSTANT = auto()      # 固定间隔
    LINEAR = auto()        # 线性增长
    EXPONENTIAL = auto()   # 指数退避
    FIBONACCI = auto()     # 斐波那契
    RANDOM = auto()        # 随机间隔


# ==================== 退避策略函数 ====================

def constant_backoff(delay: float = 0.1) -> Callable[[int], float]:
    """固定间隔退避"""
    def strategy(attempt: int) -> float:
        return delay
    return strategy


def linear_backoff(base: float = 0.1, increment: float = 0.1, max_delay: float = 5.0) -> Callable[[int], float]:
    """线性增长退避"""
    def strategy(attempt: int) -> float:
        return min(base + increment * attempt, max_delay)
    return strategy


def exponential_backoff(base: float = 0.1, multiplier: float = 2.0, max_delay: float = 30.0) -> Callable[[int], float]:
    """指数退避 (推荐)"""
    def strategy(attempt: int) -> float:
        delay = base * (multiplier ** attempt)
        return min(delay, max_delay)
    return strategy


def fibonacci_backoff(base: float = 0.1, max_delay: float = 30.0) -> Callable[[int], float]:
    """斐波那契退避"""
    def strategy(attempt: int) -> float:
        if attempt <= 1:
            return base
        
        a, b = 1, 1
        for _ in range(attempt - 1):
            a, b = b, a + b
        
        return min(base * b, max_delay)
    return strategy


def random_backoff(min_delay: float = 0.1, max_delay: float = 1.0) -> Callable[[int], float]:
    """随机间隔退避"""
    def strategy(attempt: int) -> float:
        return random.uniform(min_delay, max_delay)
    return strategy


def jittered_backoff(base_strategy: Callable[[int], float], jitter_factor: float = 0.1) -> Callable[[int], float]:
    """
    带抖动的退避策略
    
    在基础策略上添加随机抖动，避免惊群效应
    """
    def strategy(attempt: int) -> float:
        delay = base_strategy(attempt)
        jitter = delay * jitter_factor * random.uniform(-1, 1)
        return max(0, delay + jitter)
    return strategy


# ==================== 重试配置 ====================

@dataclass
class RetryConfig:
    """重试配置"""
    # 最大重试次数
    max_attempts: int = 3
    
    # 退避策略函数
    backoff_strategy: Callable[[int], float] = field(
        default_factory=lambda: exponential_backoff(base=0.1, max_delay=2.0)
    )
    
    # 可重试的异常类型
    retryable_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [Exception]
    )
    
    # 不可重试的异常类型
    non_retryable_exceptions: List[Type[Exception]] = field(
        default_factory=list
    )
    
    # 重试前回调
    on_retry: Optional[Callable[[int, Exception], None]] = None
    
    # 最终失败回调
    on_failure: Optional[Callable[[Exception], None]] = None
    
    # 是否在日志中记录重试
    log_retries: bool = True
    
    def should_retry(self, exception: Exception) -> bool:
        """判断是否应该重试"""
        # 检查不可重试列表
        for exc_type in self.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # 检查可重试列表
        for exc_type in self.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        return False


# ==================== 重试装饰器 ====================

def retry(
    max_attempts: int = 3,
    backoff: Callable[[int], float] = None,
    retryable_exceptions: List[Type[Exception]] = None,
    on_retry: Callable[[int, Exception], None] = None,
):
    """
    重试装饰器
    
    使用方式:
        @retry(max_attempts=3, backoff=exponential_backoff())
        def unstable_operation():
            ...
    """
    if backoff is None:
        backoff = exponential_backoff()
    if retryable_exceptions is None:
        retryable_exceptions = [Exception]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否可重试
                    is_retryable = any(
                        isinstance(e, exc_type)
                        for exc_type in retryable_exceptions
                    )
                    
                    if not is_retryable or attempt >= max_attempts - 1:
                        raise
                    
                    # 计算延迟
                    delay = backoff(attempt)
                    
                    # 回调
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    logger.debug(f"重试 {attempt + 1}/{max_attempts}, 等待 {delay:.2f}s: {e}")
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# ==================== 重试执行器 ====================

class RetryExecutor:
    """
    带重试功能的动作执行器
    
    包装 ActionExecutor，添加重试和错误恢复能力
    """
    
    def __init__(
        self,
        executor: ActionExecutor,
        config: Optional[RetryConfig] = None,
    ):
        """
        Args:
            executor: 底层动作执行器
            config: 重试配置
        """
        self.executor = executor
        self.config = config or RetryConfig()
        
        # 统计信息
        self._total_attempts = 0
        self._successful_attempts = 0
        self._failed_attempts = 0
        self._retry_count = 0
    
    def execute_with_retry(self, action: Action) -> ActionResult:
        """
        执行动作，带重试机制
        
        Args:
            action: 要执行的动作
            
        Returns:
            ActionResult
        """
        last_error = None
        
        for attempt in range(self.config.max_attempts):
            self._total_attempts += 1
            
            try:
                result = self.executor.execute(action)
                
                if result.success:
                    self._successful_attempts += 1
                    return result
                
                # 执行成功但结果失败，也需要重试
                last_error = Exception(result.error or "Action failed")
                
            except Exception as e:
                last_error = e
            
            # 判断是否应该重试
            if attempt >= self.config.max_attempts - 1:
                break
            
            if not self.config.should_retry(last_error):
                break
            
            self._retry_count += 1
            
            # 计算延迟
            delay = self.config.backoff_strategy(attempt)
            
            # 回调
            if self.config.on_retry:
                self.config.on_retry(attempt + 1, last_error)
            
            if self.config.log_retries:
                logger.warning(
                    f"动作 {action.action_type.value} 失败，"
                    f"重试 {attempt + 1}/{self.config.max_attempts}，"
                    f"等待 {delay:.2f}s: {last_error}"
                )
            
            time.sleep(delay)
        
        # 所有重试都失败
        self._failed_attempts += 1
        
        if self.config.on_failure:
            self.config.on_failure(last_error)
        
        return ActionResult(
            success=False,
            error=str(last_error),
            message=f"Action failed after {self.config.max_attempts} attempts"
        )
    
    def set_elements(self, elements) -> None:
        """代理方法"""
        self.executor.set_elements(elements)
    
    @property
    def stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_attempts": self._total_attempts,
            "successful_attempts": self._successful_attempts,
            "failed_attempts": self._failed_attempts,
            "retry_count": self._retry_count,
            "success_rate": (
                self._successful_attempts / self._total_attempts
                if self._total_attempts > 0 else 0
            ),
        }
    
    def reset_stats(self) -> None:
        """重置统计"""
        self._total_attempts = 0
        self._successful_attempts = 0
        self._failed_attempts = 0
        self._retry_count = 0


# ==================== 带重试的 Agent ====================

class RetryableAgentMixin:
    """
    可重试的 Agent 混入类
    
    为 ComputerAgent 添加重试能力
    """
    
    def _create_retry_executor(
        self,
        executor: ActionExecutor,
        retry_config: Optional[RetryConfig] = None
    ) -> RetryExecutor:
        """创建带重试的执行器"""
        return RetryExecutor(executor, retry_config)


# ==================== 预定义配置 ====================

# 保守策略：少量重试，短延迟
CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    backoff_strategy=constant_backoff(0.1),
)

# 标准策略：适中重试
STANDARD_RETRY = RetryConfig(
    max_attempts=3,
    backoff_strategy=exponential_backoff(base=0.1, max_delay=2.0),
)

# 积极策略：更多重试，用于不稳定环境
AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    backoff_strategy=jittered_backoff(exponential_backoff(base=0.2, max_delay=5.0)),
)

# 网络友好策略：适合涉及网络的操作
NETWORK_RETRY = RetryConfig(
    max_attempts=5,
    backoff_strategy=exponential_backoff(base=1.0, multiplier=2.0, max_delay=30.0),
)
