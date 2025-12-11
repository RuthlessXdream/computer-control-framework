"""
Computer Control Framework - 日志系统
统一的日志管理，支持控制台输出和文件记录

使用方式:
    from src.utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("操作开始")
    logger.debug("详细信息", extra={"action": "click", "x": 100, "y": 200})
    logger.error("操作失败", exc_info=True)
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler


# 日志级别配置（可通过环境变量覆盖）
DEFAULT_LOG_LEVEL = os.environ.get("CCF_LOG_LEVEL", "INFO").upper()
DEFAULT_LOG_DIR = os.environ.get("CCF_LOG_DIR", "logs")
DEFAULT_LOG_FORMAT = os.environ.get(
    "CCF_LOG_FORMAT", 
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)

# 日志颜色（仅控制台）
COLORS = {
    "DEBUG": "\033[36m",     # 青色
    "INFO": "\033[32m",      # 绿色
    "WARNING": "\033[33m",   # 黄色
    "ERROR": "\033[31m",     # 红色
    "CRITICAL": "\033[35m",  # 紫色
    "RESET": "\033[0m",      # 重置
}


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""
    
    def __init__(self, fmt: str = None, use_colors: bool = True):
        super().__init__(fmt or DEFAULT_LOG_FORMAT)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            color = COLORS.get(record.levelname, COLORS["RESET"])
            record.levelname = f"{color}{record.levelname}{COLORS['RESET']}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON 格式的日志格式化器（用于文件记录）"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加额外字段
        if hasattr(record, "action_type"):
            log_data["action_type"] = record.action_type
        if hasattr(record, "coordinate"):
            log_data["coordinate"] = record.coordinate
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "success"):
            log_data["success"] = record.success
        
        # 异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ActionLogAdapter(logging.LoggerAdapter):
    """
    Action 日志适配器
    
    方便记录 AI Agent 的每一步操作
    """
    
    def action(
        self,
        action_type: str,
        coordinate: tuple = None,
        element_label: str = None,
        success: bool = True,
        duration: float = 0.0,
        message: str = "",
        **kwargs
    ):
        """记录一次 Action 执行"""
        extra = {
            "action_type": action_type,
            "success": success,
            "duration": duration,
            **kwargs
        }
        
        if coordinate:
            extra["coordinate"] = coordinate
        if element_label:
            extra["element_label"] = element_label
        
        level = logging.INFO if success else logging.ERROR
        msg = f"[{action_type}] {message}" if message else f"[{action_type}]"
        
        if coordinate:
            msg += f" @ ({coordinate[0]}, {coordinate[1]})"
        elif element_label:
            msg += f" @ {element_label}"
        
        if duration > 0:
            msg += f" ({duration:.3f}s)"
        
        self.log(level, msg, extra=extra)


def setup_logger(
    name: str,
    level: str = None,
    log_dir: str = None,
    enable_file: bool = True,
    enable_json: bool = True,
) -> logging.Logger:
    """
    配置并返回一个 Logger 实例
    
    Args:
        name: Logger 名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志文件目录
        enable_file: 是否启用文件日志
        enable_json: 是否使用 JSON 格式记录到文件
        
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    level = level or DEFAULT_LOG_LEVEL
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # 文件 Handler
    if enable_file:
        log_dir = log_dir or DEFAULT_LOG_DIR
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 普通日志文件（按大小轮转）
        log_file = log_path / "ccf.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        
        if enable_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        
        logger.addHandler(file_handler)
        
        # 错误日志单独文件
        error_file = log_path / "ccf_error.log"
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter() if enable_json else logging.Formatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    获取 Logger 实例（快捷方式）
    
    Args:
        name: Logger 名称，None 则使用调用者模块名
        
    Returns:
        Logger 实例
    """
    if name is None:
        # 自动获取调用者模块名
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", "ccf")
    
    return setup_logger(name)


def get_action_logger(name: str = None) -> ActionLogAdapter:
    """
    获取 Action 日志适配器
    
    专门用于记录 AI Agent 的操作
    
    Args:
        name: Logger 名称
        
    Returns:
        ActionLogAdapter 实例
    """
    logger = get_logger(name)
    return ActionLogAdapter(logger, {})


# 预配置的全局 Logger
_root_logger: Optional[logging.Logger] = None


def init_logging(
    level: str = None,
    log_dir: str = None,
    enable_file: bool = True,
):
    """
    初始化全局日志配置
    
    在应用启动时调用一次
    """
    global _root_logger
    _root_logger = setup_logger("ccf", level=level, log_dir=log_dir, enable_file=enable_file)
    return _root_logger


# 便捷函数
def debug(msg: str, *args, **kwargs):
    get_logger("ccf").debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    get_logger("ccf").info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    get_logger("ccf").warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    get_logger("ccf").error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    get_logger("ccf").critical(msg, *args, **kwargs)
