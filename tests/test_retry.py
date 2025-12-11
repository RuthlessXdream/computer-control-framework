"""
重试机制测试

运行方式:
    pytest tests/test_retry.py -v
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.retry import (
    RetryConfig,
    RetryExecutor,
    retry,
    constant_backoff,
    linear_backoff,
    exponential_backoff,
    fibonacci_backoff,
    jittered_backoff,
    STANDARD_RETRY,
    AGGRESSIVE_RETRY,
    CONSERVATIVE_RETRY,
)


class TestBackoffStrategies:
    """退避策略测试"""
    
    def test_constant_backoff(self):
        """测试固定间隔退避"""
        strategy = constant_backoff(0.5)
        
        assert strategy(0) == 0.5
        assert strategy(1) == 0.5
        assert strategy(10) == 0.5
    
    def test_linear_backoff(self):
        """测试线性增长退避"""
        strategy = linear_backoff(base=0.1, increment=0.2, max_delay=1.0)
        
        assert strategy(0) == 0.1
        assert strategy(1) == 0.3
        assert strategy(2) == 0.5
        assert strategy(10) == 1.0  # 受 max_delay 限制
    
    def test_exponential_backoff(self):
        """测试指数退避"""
        strategy = exponential_backoff(base=0.1, multiplier=2.0, max_delay=5.0)
        
        assert strategy(0) == 0.1
        assert strategy(1) == 0.2
        assert strategy(2) == 0.4
        assert strategy(3) == 0.8
        assert strategy(10) == 5.0  # 受 max_delay 限制
    
    def test_fibonacci_backoff(self):
        """测试斐波那契退避"""
        strategy = fibonacci_backoff(base=0.1, max_delay=10.0)
        
        # Fibonacci: 1, 1, 2, 3, 5, 8, 13...
        assert strategy(0) == 0.1
        assert strategy(1) == 0.1
        assert strategy(2) == 0.1  # base * 1
        assert strategy(3) == 0.2  # base * 2
        assert strategy(4) == 0.3  # base * 3
    
    def test_jittered_backoff(self):
        """测试带抖动的退避"""
        base_strategy = constant_backoff(1.0)
        strategy = jittered_backoff(base_strategy, jitter_factor=0.1)
        
        # 多次调用应该产生不同的值
        values = [strategy(0) for _ in range(10)]
        
        # 所有值应该在 0.9 - 1.1 范围内
        assert all(0.89 <= v <= 1.11 for v in values)
        
        # 应该有变化（不全相同）
        assert len(set(values)) > 1


class TestRetryDecorator:
    """重试装饰器测试"""
    
    def test_successful_execution(self):
        """测试成功执行不重试"""
        call_count = 0
        
        @retry(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure(self):
        """测试失败后重试"""
        call_count = 0
        
        @retry(max_attempts=3, backoff=constant_backoff(0.01))
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 3
    
    def test_max_attempts_exceeded(self):
        """测试超过最大重试次数"""
        call_count = 0
        
        @retry(max_attempts=3, backoff=constant_backoff(0.01))
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_failing()
        
        assert call_count == 3
    
    def test_specific_exception_retry(self):
        """测试特定异常重试"""
        call_count = 0
        
        @retry(max_attempts=3, retryable_exceptions=[ValueError], backoff=constant_backoff(0.01))
        def specific_failure():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retryable")
            return "success"
        
        result = specific_failure()
        assert result == "success"
        assert call_count == 2
    
    def test_non_retryable_exception(self):
        """测试不可重试异常"""
        call_count = 0
        
        @retry(max_attempts=3, retryable_exceptions=[ValueError], backoff=constant_backoff(0.01))
        def non_retryable():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")
        
        with pytest.raises(TypeError):
            non_retryable()
        
        assert call_count == 1  # 不重试


class TestRetryConfig:
    """重试配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.log_retries is True
    
    def test_should_retry_retryable(self):
        """测试可重试判断"""
        config = RetryConfig(retryable_exceptions=[ValueError, TypeError])
        
        assert config.should_retry(ValueError("test")) is True
        assert config.should_retry(TypeError("test")) is True
        assert config.should_retry(KeyError("test")) is False
    
    def test_should_retry_non_retryable(self):
        """测试不可重试判断"""
        config = RetryConfig(
            retryable_exceptions=[Exception],
            non_retryable_exceptions=[KeyError]
        )
        
        assert config.should_retry(ValueError("test")) is True
        assert config.should_retry(KeyError("test")) is False
    
    def test_predefined_configs(self):
        """测试预定义配置"""
        assert CONSERVATIVE_RETRY.max_attempts == 2
        assert STANDARD_RETRY.max_attempts == 3
        assert AGGRESSIVE_RETRY.max_attempts == 5


class TestRetryExecutor:
    """重试执行器测试"""
    
    def test_stats_tracking(self):
        """测试统计跟踪"""
        from src.core.base import ActionExecutor, ComputerController
        from src.core.types import Action, ActionType, Point, ActionResult
        
        # 创建模拟执行器
        class MockController(ComputerController):
            def get_screen_size(self):
                from src.core.types import Size
                return Size(1920, 1080)
            
            def get_mouse_position(self):
                return Point(0, 0)
            
            def screenshot(self, region=None):
                return b""
            
            def mouse_move(self, x, y, duration=0):
                pass
            
            def mouse_click(self, x=None, y=None, button=None, clicks=1, interval=0.1):
                pass
            
            def mouse_down(self, button=None):
                pass
            
            def mouse_up(self, button=None):
                pass
            
            def mouse_scroll(self, clicks, x=None, y=None, horizontal=False):
                pass
            
            def type_text(self, text, interval=0):
                pass
            
            def key_press(self, key):
                pass
            
            def key_down(self, key):
                pass
            
            def key_up(self, key):
                pass
        
        controller = MockController()
        base_executor = ActionExecutor(controller)
        retry_executor = RetryExecutor(base_executor, RetryConfig(max_attempts=2))
        
        # 执行成功动作
        action = Action(action_type=ActionType.WAIT, duration=0.01)
        result = retry_executor.execute_with_retry(action)
        
        assert result.success
        stats = retry_executor.stats
        assert stats["successful_attempts"] == 1
        assert stats["total_attempts"] == 1


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
