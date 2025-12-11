"""
Computer Control Framework - 日志系统
统一的日志管理，支持控制台输出和文件记录

使用方式:
    from src.utils.logger import get_logger, get_action_logger

    logger = get_logger(__name__)
    logger.info("操作开始")
    logger.debug("详细信息", extra={"action": "click", "x": 100, "y": 200})
    logger.error("操作失败", exc_info=True)

    # Action 专用日志
    action_logger = get_action_logger(__name__)
    action_logger.action(
        action_type="click",
        coordinate=(100, 200),
        success=True,
        duration=0.05
    )

特性:
- 彩色控制台输出
- JSON 格式文件日志 (可选)
- 自动日志轮转
- 结构化 Action 日志
- 环境变量配置
"""

import json
import logging
import os
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Union

# ==================== 配置常量 ====================

# 日志级别配置（可通过环境变量覆盖）
DEFAULT_LOG_LEVEL = os.environ.get("CCF_LOG_LEVEL", "INFO").upper()
DEFAULT_LOG_DIR = os.environ.get("CCF_LOG_DIR", "logs")
DEFAULT_LOG_FORMAT = os.environ.get(
    "CCF_LOG_FORMAT",
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 文件日志配置
LOG_FILE_MAX_BYTES = int(os.environ.get("CCF_LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
LOG_FILE_BACKUP_COUNT = int(os.environ.get("CCF_LOG_BACKUP_COUNT", 5))

# 是否启用文件日志
ENABLE_FILE_LOG = os.environ.get("CCF_ENABLE_FILE_LOG", "true").lower() == "true"

# 是否使用 JSON 格式
USE_JSON_FORMAT = os.environ.get("CCF_JSON_LOG", "true").lower() == "true"

# 日志颜色（仅控制台）
COLORS = {
    "DEBUG": "\033[36m",     # 青色
    "INFO": "\033[32m",      # 绿色
    "WARNING": "\033[33m",   # 黄色
    "ERROR": "\033[31m",     # 红色
    "CRITICAL": "\033[35m",  # 紫色
    "RESET": "\033[0m",      # 重置
}

# 级别图标
LEVEL_ICONS = {
    "DEBUG": "🔍",
    "INFO": "ℹ️ ",
    "WARNING": "⚠️ ",
    "ERROR": "❌",
    "CRITICAL": "💥",
}

# ==================== 格式化器 ====================


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""

    def __init__(
        self,
        fmt: str = None,
        datefmt: str = None,
        use_colors: bool = True,
        use_icons: bool = False
    ):
        super().__init__(fmt or DEFAULT_LOG_FORMAT, datefmt or DEFAULT_DATE_FORMAT)
        self.use_colors = use_colors and sys.stdout.isatty()
        self.use_icons = use_icons

    def format(self, record: logging.LogRecord) -> str:
        # 保存原始级别名
        original_levelname = record.levelname

        if self.use_colors:
            color = COLORS.get(record.levelname, COLORS["RESET"])
            record.levelname = f"{color}{record.levelname}{COLORS['RESET']}"

        if self.use_icons:
            icon = LEVEL_ICONS.get(original_levelname, "")
            record.levelname = f"{icon} {record.levelname}"

        result = super().format(record)

        # 恢复原始级别名
        record.levelname = original_levelname

        return result


class JSONFormatter(logging.Formatter):
    """JSON 格式的日志格式化器（用于文件记录）"""

    STANDARD_FIELDS = {
        "timestamp", "level", "logger", "message",
        "module", "function", "line", "exception"
    }

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

        # 添加线程信息
        if record.thread:
            log_data["thread"] = record.thread
            log_data["thread_name"] = record.threadName

        # 添加额外字段 (来自 extra 参数)
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in self.STANDARD_FIELDS:
                if not key.startswith('_'):
                    log_data[key] = value

        # 异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class StructuredFormatter(logging.Formatter):
    """结构化文本格式化器（可读性更好的文件日志）"""

    def format(self, record: logging.LogRecord) -> str:
        # 基础信息
        timestamp = datetime.fromtimestamp(record.created).strftime(DEFAULT_DATE_FORMAT)
        base = f"[{timestamp}] [{record.levelname:8}] [{record.name}] {record.getMessage()}"

        # 添加额外字段
        extras = []
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith('_'):
                extras.append(f"{key}={value}")

        if extras:
            base += f" | {', '.join(extras)}"

        # 异常信息
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


# ==================== Action 日志适配器 ====================


class ActionLogAdapter(logging.LoggerAdapter):
    """
    Action 日志适配器

    专门用于记录 AI Agent 的每一步操作
    """

    def __init__(self, logger: logging.Logger, extra: dict = None):
        super().__init__(logger, extra or {})
        self._step_counter = 0

    def action(
        self,
        action_type: str,
        coordinate: tuple = None,
        element_label: str = None,
        success: bool = True,
        duration: float = 0.0,
        message: str = "",
        step: int = None,
        **kwargs
    ):
        """
        记录一次 Action 执行

        Args:
            action_type: 动作类型 (click, type_text, etc.)
            coordinate: 坐标 (x, y)
            element_label: 元素标签
            success: 是否成功
            duration: 执行耗时 (秒)
            message: 附加消息
            step: 步骤编号
            **kwargs: 其他额外字段
        """
        if step is None:
            self._step_counter += 1
            step = self._step_counter

        extra = {
            "action_type": action_type,
            "success": success,
            "duration": duration,
            "step": step,
            **kwargs
        }

        if coordinate:
            extra["coordinate"] = coordinate
        if element_label:
            extra["element_label"] = element_label

        # 构建消息
        level = logging.INFO if success else logging.ERROR
        status = "✓" if success else "✗"
        msg = f"[Step {step}] [{action_type}] {status}"

        if message:
            msg += f" {message}"

        if coordinate:
            msg += f" @ ({coordinate[0]}, {coordinate[1]})"
        elif element_label:
            msg += f" @ {element_label}"

        if duration > 0:
            msg += f" ({duration:.3f}s)"

        self.log(level, msg, extra=extra)

    def step_start(self, step: int, task: str):
        """记录步骤开始"""
        self.info(f"[Step {step}] 开始执行: {task}", extra={"step": step, "event": "step_start"})

    def step_end(self, step: int, success: bool, duration: float):
        """记录步骤结束"""
        status = "成功" if success else "失败"
        self.info(
            f"[Step {step}] {status} ({duration:.3f}s)",
            extra={"step": step, "event": "step_end", "success": success, "duration": duration}
        )

    def task_start(self, task: str):
        """记录任务开始"""
        self._step_counter = 0
        self.info(f"=== 任务开始: {task} ===", extra={"event": "task_start", "task": task})

    def task_end(self, task: str, success: bool, total_steps: int, total_duration: float):
        """记录任务结束"""
        status = "成功" if success else "失败"
        self.info(
            f"=== 任务{status}: {task} (共 {total_steps} 步, 耗时 {total_duration:.2f}s) ===",
            extra={
                "event": "task_end",
                "task": task,
                "success": success,
                "total_steps": total_steps,
                "total_duration": total_duration
            }
        )


# ==================== Logger 管理 ====================

# 全局 logger 缓存
_loggers: Dict[str, logging.Logger] = {}
_lock = threading.Lock()


def setup_logger(
    name: str,
    level: str = None,
    log_dir: str = None,
    enable_file: bool = None,
    enable_json: bool = None,
    enable_console: bool = True,
) -> logging.Logger:
    """
    配置并返回一个 Logger 实例

    Args:
        name: Logger 名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志文件目录
        enable_file: 是否启用文件日志
        enable_json: 是否使用 JSON 格式记录到文件
        enable_console: 是否启用控制台输出

    Returns:
        配置好的 Logger 实例
    """
    with _lock:
        # 检查缓存
        if name in _loggers:
            return _loggers[name]

        logger = logging.getLogger(name)

        # 避免重复配置
        if logger.handlers:
            _loggers[name] = logger
            return logger

        # 应用默认值
        level = level or DEFAULT_LOG_LEVEL
        enable_file = enable_file if enable_file is not None else ENABLE_FILE_LOG
        enable_json = enable_json if enable_json is not None else USE_JSON_FORMAT

        logger.setLevel(getattr(logging, level, logging.INFO))
        logger.propagate = False  # 避免重复日志

        # 控制台 Handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(ColoredFormatter(use_colors=True))
            logger.addHandler(console_handler)

        # 文件 Handler
        if enable_file:
            log_dir = log_dir or DEFAULT_LOG_DIR
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)

            # 主日志文件（按大小轮转）
            log_file = log_path / "ccf.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=LOG_FILE_MAX_BYTES,
                backupCount=LOG_FILE_BACKUP_COUNT,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)

            if enable_json:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(StructuredFormatter())

            logger.addHandler(file_handler)

            # 错误日志单独文件
            error_file = log_path / "ccf_error.log"
            error_handler = RotatingFileHandler(
                error_file,
                maxBytes=LOG_FILE_MAX_BYTES,
                backupCount=3,
                encoding="utf-8"
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(JSONFormatter() if enable_json else StructuredFormatter())
            logger.addHandler(error_handler)

        _loggers[name] = logger
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
    return ActionLogAdapter(logger)


# ==================== 全局初始化 ====================

_initialized = False


def init_logging(
    level: str = None,
    log_dir: str = None,
    enable_file: bool = True,
    enable_json: bool = True,
) -> logging.Logger:
    """
    初始化全局日志配置

    在应用启动时调用一次
    """
    global _initialized

    if _initialized:
        return get_logger("ccf")

    root_logger = setup_logger(
        "ccf",
        level=level,
        log_dir=log_dir,
        enable_file=enable_file,
        enable_json=enable_json
    )

    _initialized = True
    return root_logger


# ==================== 上下文管理器 ====================

@contextmanager
def log_context(logger: logging.Logger, operation: str, **extra):
    """
    日志上下文管理器

    使用方式:
        with log_context(logger, "screenshot") as ctx:
            # 执行操作
            ctx["result"] = "success"
    """
    start_time = datetime.now()
    context = {"operation": operation, **extra}

    logger.debug(f"开始: {operation}", extra=context)

    try:
        yield context
        duration = (datetime.now() - start_time).total_seconds()
        context["duration"] = duration
        context["success"] = True
        logger.debug(f"完成: {operation} ({duration:.3f}s)", extra=context)
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        context["duration"] = duration
        context["success"] = False
        context["error"] = str(e)
        logger.error(f"失败: {operation} ({duration:.3f}s) - {e}", extra=context)
        raise


# ==================== 便捷函数 ====================

def debug(msg: str, *args, **kwargs):
    """快捷 debug 日志"""
    get_logger("ccf").debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """快捷 info 日志"""
    get_logger("ccf").info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """快捷 warning 日志"""
    get_logger("ccf").warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """快捷 error 日志"""
    get_logger("ccf").error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """快捷 critical 日志"""
    get_logger("ccf").critical(msg, *args, **kwargs)


def set_level(level: Union[str, int]):
    """设置全局日志级别"""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    for logger in _loggers.values():
        logger.setLevel(level)
