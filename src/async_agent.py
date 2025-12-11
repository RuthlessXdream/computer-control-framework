"""
Async AI Agent - 异步 AI 代理

支持异步执行的 ComputerAgent 实现，适用于:
- 高并发场景
- 非阻塞 UI 应用
- 与异步 AI API 集成

使用方式:
    from src.async_agent import AsyncComputerAgent, AsyncAIBrain
    
    class MyAsyncBrain(AsyncAIBrain):
        async def think(self, screen_state, task):
            # 异步调用 AI API
            response = await my_async_llm.generate(...)
            return parse_action(response)
    
    agent = AsyncComputerAgent(MyAsyncBrain())
    await agent.run("执行任务")
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Callable, Awaitable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .core.types import (
    Action,
    ActionResult,
    ScreenState,
    ScreenElement,
    Size,
)
from .core.base import ComputerController, ActionExecutor
from .platforms import get_controller
from .vision.annotator import ScreenAnnotator
from .vision.detector import ElementDetector, DummyDetector
from .utils.logger import get_logger, get_action_logger

logger = get_logger(__name__)
action_logger = get_action_logger(__name__)


@dataclass
class AsyncAgentConfig:
    """异步 Agent 配置"""
    # 每次动作后的等待时间
    action_delay: float = 1.0
    
    # 每次截屏后的等待时间
    screenshot_delay: float = 0.5
    
    # 最大执行步数
    max_steps: int = 100
    
    # 是否在每次动作后截屏
    screenshot_after_action: bool = True
    
    # 是否标注截屏
    annotate_screenshot: bool = True
    
    # 并行执行的线程池大小
    thread_pool_size: int = 4
    
    # 单步超时时间 (秒)
    step_timeout: float = 60.0


class AsyncAIBrain(ABC):
    """
    异步 AI 大脑接口
    
    用于需要异步调用 AI API 的场景
    """
    
    @abstractmethod
    async def think(self, screen_state: ScreenState, task: str) -> Optional[Action]:
        """
        异步思考，返回下一步动作
        
        Args:
            screen_state: 当前屏幕状态
            task: 任务描述
            
        Returns:
            下一步动作，None 表示任务完成
        """
        pass
    
    async def on_action_result(self, action: Action, result: ActionResult) -> None:
        """动作执行结果回调"""
        pass
    
    async def should_continue(self, step: int, screen_state: ScreenState) -> bool:
        """判断是否继续执行"""
        return True


class AsyncComputerAgent:
    """
    异步电脑代理
    
    支持异步执行的 Agent，适用于:
    - 异步 AI API 调用
    - 非阻塞应用集成
    - 高并发场景
    """
    
    def __init__(
        self,
        brain: AsyncAIBrain,
        controller: Optional[ComputerController] = None,
        detector: Optional[ElementDetector] = None,
        config: Optional[AsyncAgentConfig] = None,
    ):
        """
        初始化异步 Agent
        
        Args:
            brain: 异步 AI 大脑
            controller: 控制器实例
            detector: 元素检测器
            config: 配置
        """
        self.brain = brain
        self.controller = controller or get_controller()
        self.detector = detector or DummyDetector()
        self.config = config or AsyncAgentConfig()
        
        self.executor = ActionExecutor(self.controller)
        self.annotator = ScreenAnnotator()
        
        # 线程池用于执行同步控制器操作
        self._thread_pool = ThreadPoolExecutor(max_workers=self.config.thread_pool_size)
        
        # 状态
        self._current_step = 0
        self._history: List[tuple] = []
        self._running = False
        self._cancelled = False
    
    async def _run_in_thread(self, func: Callable, *args, **kwargs):
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._thread_pool,
            lambda: func(*args, **kwargs)
        )
    
    async def capture_screen_state(self) -> ScreenState:
        """异步捕获屏幕状态"""
        # 在线程中执行截屏 (避免阻塞事件循环)
        screenshot_bytes = await self._run_in_thread(self.controller.screenshot)
        screenshot_base64 = await self._run_in_thread(self.controller.screenshot_base64)
        
        # 检测元素
        elements = await self._run_in_thread(self.detector.detect, screenshot_bytes)
        
        # 标注截屏
        annotated_base64 = None
        label_map = {}
        
        if self.config.annotate_screenshot and elements:
            annotated_base64, label_map = await self._run_in_thread(
                self.annotator.annotate_base64,
                screenshot_base64,
                elements
            )
        
        return ScreenState(
            screenshot_base64=screenshot_base64,
            annotated_screenshot_base64=annotated_base64,
            elements=elements,
            label_to_rect=label_map,
            screen_size=self.controller.get_screen_size(),
            timestamp=time.time(),
        )
    
    async def step(self, task: str) -> tuple:
        """
        执行单步
        
        Args:
            task: 任务描述
            
        Returns:
            (action, result, screen_state)
        """
        self._current_step += 1
        
        # 等待
        await asyncio.sleep(self.config.screenshot_delay)
        
        # 截屏
        screen_state = await self.capture_screen_state()
        
        # 设置元素列表
        self.executor.set_elements(screen_state.elements)
        
        # AI 决策 (异步)
        try:
            action = await asyncio.wait_for(
                self.brain.think(screen_state, task),
                timeout=self.config.step_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"AI 思考超时 ({self.config.step_timeout}s)")
            return None, None, screen_state
        
        if action is None:
            return None, None, screen_state
        
        # 执行动作 (在线程中)
        result = await self._run_in_thread(self.executor.execute, action)
        
        # 回调
        await self.brain.on_action_result(action, result)
        
        # 记录历史
        self._history.append((action, result))
        
        # 等待
        await asyncio.sleep(self.config.action_delay)
        
        return action, result, screen_state
    
    async def run(self, task: str) -> bool:
        """
        运行 Agent 直到任务完成
        
        Args:
            task: 任务描述
            
        Returns:
            任务是否成功完成
        """
        self._current_step = 0
        self._history = []
        self._running = True
        self._cancelled = False
        
        logger.info(f"开始异步任务: {task}")
        
        try:
            while self._current_step < self.config.max_steps and not self._cancelled:
                action, result, screen_state = await self.step(task)
                
                # AI 决定结束
                if action is None:
                    logger.info("AI 决定完成任务")
                    return True
                
                # 记录日志
                coord = None
                if action.coordinate:
                    coord = (int(action.coordinate.x), int(action.coordinate.y))
                
                action_logger.action(
                    action_type=action.action_type.value,
                    coordinate=coord,
                    element_label=action.element_label,
                    success=result.success,
                    duration=result.duration,
                    message=f"Step {self._current_step}"
                )
                
                if not result.success:
                    logger.error(f"动作执行失败: {result.error}")
                
                # 检查是否继续
                if not await self.brain.should_continue(self._current_step, screen_state):
                    logger.info("AI 决定停止")
                    return True
            
            if self._cancelled:
                logger.info("任务被取消")
                return False
            
            logger.warning(f"达到最大步数限制 ({self.config.max_steps})")
            return False
            
        finally:
            self._running = False
    
    def cancel(self) -> None:
        """取消当前任务"""
        self._cancelled = True
        logger.info("请求取消任务")
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    @property
    def history(self) -> List[tuple]:
        """获取执行历史"""
        return self._history
    
    @property
    def current_step(self) -> int:
        """获取当前步数"""
        return self._current_step
    
    async def close(self) -> None:
        """关闭资源"""
        self._thread_pool.shutdown(wait=False)


# ==================== 同步 Brain 适配器 ====================

class SyncBrainAdapter(AsyncAIBrain):
    """
    将同步 AIBrain 适配为异步版本
    
    用于在异步 Agent 中使用同步 Brain
    """
    
    def __init__(self, sync_brain):
        """
        Args:
            sync_brain: 同步的 AIBrain 实例
        """
        from .ai_interface import AIBrain
        if not isinstance(sync_brain, AIBrain):
            raise TypeError("sync_brain 必须是 AIBrain 实例")
        self._sync_brain = sync_brain
    
    async def think(self, screen_state: ScreenState, task: str) -> Optional[Action]:
        # 在线程中运行同步方法
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_brain.think,
            screen_state,
            task
        )
    
    async def on_action_result(self, action: Action, result: ActionResult) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._sync_brain.on_action_result,
            action,
            result
        )
    
    async def should_continue(self, step: int, screen_state: ScreenState) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_brain.should_continue,
            step,
            screen_state
        )


# ==================== 便捷函数 ====================

def create_async_agent(
    think_fn: Callable[[ScreenState, str], Awaitable[Optional[Action]]],
    config: Optional[AsyncAgentConfig] = None,
) -> AsyncComputerAgent:
    """
    创建异步 Agent 的快捷方式
    
    Args:
        think_fn: 异步思考函数
        config: 配置
        
    Returns:
        AsyncComputerAgent 实例
    """
    
    class FunctionalAsyncBrain(AsyncAIBrain):
        async def think(self, screen_state: ScreenState, task: str) -> Optional[Action]:
            return await think_fn(screen_state, task)
    
    return AsyncComputerAgent(FunctionalAsyncBrain(), config=config)


async def run_task(task: str, brain: AsyncAIBrain, **kwargs) -> bool:
    """
    运行单个任务的便捷函数
    
    Args:
        task: 任务描述
        brain: AI 大脑
        **kwargs: 传递给 AsyncComputerAgent 的参数
        
    Returns:
        任务是否成功
    """
    agent = AsyncComputerAgent(brain, **kwargs)
    try:
        return await agent.run(task)
    finally:
        await agent.close()
