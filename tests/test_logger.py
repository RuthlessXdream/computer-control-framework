"""
日志系统测试

运行方式:
    pytest tests/test_logger.py -v
"""

import pytest
import logging
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.logger import (
    get_logger,
    get_action_logger,
    setup_logger,
    ColoredFormatter,
    JSONFormatter,
    StructuredFormatter,
    ActionLogAdapter,
    log_context,
)


class TestColoredFormatter:
    """彩色格式化器测试"""
    
    def test_format_info(self):
        """测试 INFO 级别格式化"""
        formatter = ColoredFormatter(use_colors=False)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        assert "INFO" in result
        assert "Test message" in result
    
    def test_format_error(self):
        """测试 ERROR 级别格式化"""
        formatter = ColoredFormatter(use_colors=False)
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        assert "ERROR" in result
        assert "Error message" in result


class TestJSONFormatter:
    """JSON 格式化器测试"""
    
    def test_basic_format(self):
        """测试基本格式化"""
        import json
        
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_func"
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test.module"
        assert data["message"] == "Test message"
        assert data["line"] == 42
        assert data["function"] == "test_func"
    
    def test_extra_fields(self):
        """测试额外字段"""
        import json
        
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.custom_field = "custom_value"
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data.get("custom_field") == "custom_value"


class TestActionLogAdapter:
    """Action 日志适配器测试"""
    
    def test_action_logging(self):
        """测试 Action 日志"""
        logger = logging.getLogger("test_action")
        logger.setLevel(logging.DEBUG)
        
        # 添加处理器来捕获日志
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        adapter = ActionLogAdapter(logger)
        
        adapter.action(
            action_type="click",
            coordinate=(100, 200),
            success=True,
            duration=0.05
        )
        
        # 检查日志被记录
        assert len(handler.buffer) > 0
        
        record = handler.buffer[0]
        assert "click" in record.getMessage()
    
    def test_step_counter(self):
        """测试步骤计数器"""
        logger = logging.getLogger("test_counter")
        adapter = ActionLogAdapter(logger)
        
        # 第一次调用
        adapter.action(action_type="click", success=True)
        assert adapter._step_counter == 1
        
        # 第二次调用
        adapter.action(action_type="type", success=True)
        assert adapter._step_counter == 2


class TestGetLogger:
    """获取 Logger 测试"""
    
    def test_get_logger_by_name(self):
        """测试通过名称获取"""
        logger = get_logger("test.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
    
    def test_get_logger_cached(self):
        """测试 Logger 缓存"""
        logger1 = get_logger("test.cached")
        logger2 = get_logger("test.cached")
        
        assert logger1 is logger2


class TestSetupLogger:
    """设置 Logger 测试"""
    
    def test_setup_with_file(self):
        """测试文件日志设置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(
                "test.file",
                level="DEBUG",
                log_dir=tmpdir,
                enable_file=True,
                enable_console=False
            )
            
            logger.info("Test message")
            
            # 检查日志文件是否创建
            log_file = os.path.join(tmpdir, "ccf.log")
            assert os.path.exists(log_file)
    
    def test_setup_console_only(self):
        """测试仅控制台日志"""
        logger = setup_logger(
            "test.console",
            enable_file=False,
            enable_console=True
        )
        
        # 应该只有控制台处理器
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) >= 1


class TestLogContext:
    """日志上下文测试"""
    
    def test_successful_context(self):
        """测试成功上下文"""
        logger = get_logger("test.context.success")
        
        with log_context(logger, "test_operation") as ctx:
            ctx["result"] = "done"
        
        assert ctx["success"] is True
        assert "duration" in ctx
    
    def test_failed_context(self):
        """测试失败上下文"""
        logger = get_logger("test.context.fail")
        
        with pytest.raises(ValueError):
            with log_context(logger, "failing_operation") as ctx:
                raise ValueError("Test error")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
