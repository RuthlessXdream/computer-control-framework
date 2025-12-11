"""
AI Interface - AI模型接口

这是给AI"大脑"预留的接口层

使用方式：
1. AI模型实现 AIBrain 接口
2. ComputerAgent 负责循环执行: 截屏 -> AI决策 -> 执行动作

示例：
    class MyAIBrain(AIBrain):
        def think(self, screen_state: ScreenState, task: str) -> Action:
            # 调用你的AI模型
            response = my_llm.generate(...)
            return parse_response_to_action(response)
    
    brain = MyAIBrain()
    agent = ComputerAgent(brain)
    agent.run("打开Chrome浏览器并搜索Python")
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, List, Callable
from dataclasses import dataclass

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

# 初始化日志
logger = get_logger(__name__)
action_logger = get_action_logger(__name__)


@dataclass
class AgentConfig:
    """Agent配置"""
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


class AIBrain(ABC):
    """
    AI大脑接口
    
    你需要实现这个接口，将你的AI模型接入
    """
    
    @abstractmethod
    def think(self, screen_state: ScreenState, task: str) -> Optional[Action]:
        """
        根据屏幕状态和任务，决定下一步动作
        
        Args:
            screen_state: 当前屏幕状态（截屏 + 元素列表）
            task: 要完成的任务描述
            
        Returns:
            下一步要执行的动作，返回None表示任务完成或放弃
        """
        pass
    
    def on_action_result(self, action: Action, result: ActionResult) -> None:
        """
        动作执行结果回调（可选实现）
        
        Args:
            action: 执行的动作
            result: 执行结果
        """
        pass
    
    def should_continue(self, step: int, screen_state: ScreenState) -> bool:
        """
        判断是否继续执行（可选实现）
        
        默认返回True，子类可以覆盖以实现自定义终止条件
        """
        return True


class ComputerAgent:
    """
    电脑代理 - 连接AI大脑和控制层
    
    工作流程:
    1. 截屏并检测UI元素
    2. 将屏幕状态发送给AI
    3. AI返回动作指令
    4. 执行动作
    5. 重复直到任务完成
    """
    
    def __init__(
        self,
        brain: AIBrain,
        controller: Optional[ComputerController] = None,
        detector: Optional[ElementDetector] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        初始化Agent
        
        Args:
            brain: AI大脑实例
            controller: 控制器实例，None则自动检测平台
            detector: 元素检测器，None则使用空检测器
            config: 配置
        """
        self.brain = brain
        self.controller = controller or get_controller()
        self.detector = detector or DummyDetector()
        self.config = config or AgentConfig()
        
        self.executor = ActionExecutor(self.controller)
        self.annotator = ScreenAnnotator()
        
        # 状态
        self._current_step = 0
        self._history: List[tuple] = []  # [(action, result), ...]
    
    def capture_screen_state(self) -> ScreenState:
        """
        捕获当前屏幕状态
        
        Returns:
            ScreenState对象，包含截屏和元素信息
        """
        # 截屏
        screenshot_bytes = self.controller.screenshot()
        screenshot_base64 = self.controller.screenshot_base64()
        
        # 检测元素
        elements = self.detector.detect(screenshot_bytes)
        
        # 标注截屏
        annotated_base64 = None
        label_map = {}
        
        if self.config.annotate_screenshot and elements:
            annotated_base64, label_map = self.annotator.annotate_base64(
                screenshot_base64, elements
            )
        
        # 构建状态
        return ScreenState(
            screenshot_base64=screenshot_base64,
            annotated_screenshot_base64=annotated_base64,
            elements=elements,
            label_to_rect=label_map,
            screen_size=self.controller.get_screen_size(),
            timestamp=time.time(),
        )
    
    def step(self, task: str) -> tuple:
        """
        执行单步
        
        Args:
            task: 任务描述
            
        Returns:
            (action, result, screen_state)
        """
        self._current_step += 1
        
        # 截屏
        time.sleep(self.config.screenshot_delay)
        screen_state = self.capture_screen_state()
        
        # 设置元素列表用于坐标解析
        self.executor.set_elements(screen_state.elements)
        
        # AI决策
        action = self.brain.think(screen_state, task)
        
        if action is None:
            return None, None, screen_state
        
        # 执行动作
        result = self.executor.execute(action)
        
        # 回调
        self.brain.on_action_result(action, result)
        
        # 记录历史
        self._history.append((action, result))
        
        # 等待
        time.sleep(self.config.action_delay)
        
        return action, result, screen_state
    
    def run(self, task: str) -> bool:
        """
        运行Agent直到任务完成
        
        Args:
            task: 任务描述
            
        Returns:
            任务是否成功完成
        """
        self._current_step = 0
        self._history = []
        
        logger.info(f"Starting task: {task}")
        
        while self._current_step < self.config.max_steps:
            action, result, screen_state = self.step(task)
            
            # AI决定结束
            if action is None:
                logger.info("Task completed by AI decision")
                return True
            
            # 记录操作日志
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
                logger.error(f"Action failed: {result.error}")
            
            # 检查是否继续
            if not self.brain.should_continue(self._current_step, screen_state):
                logger.info("Task stopped by AI")
                return True
        
        logger.warning(f"Max steps ({self.config.max_steps}) reached")
        return False
    
    @property
    def history(self) -> List[tuple]:
        """获取执行历史"""
        return self._history
    
    @property
    def current_step(self) -> int:
        """获取当前步数"""
        return self._current_step


# ==================== 简化的函数式接口 ====================

def create_agent(
    think_fn: Callable[[ScreenState, str], Optional[Action]],
    config: Optional[AgentConfig] = None,
) -> ComputerAgent:
    """
    创建Agent的快捷方式
    
    Args:
        think_fn: 思考函数，签名为 (ScreenState, str) -> Optional[Action]
        config: 配置
        
    Returns:
        ComputerAgent实例
        
    示例:
        def my_think(state, task):
            # 你的AI逻辑
            return Action(action_type=ActionType.CLICK, coordinate=Point(100, 200))
        
        agent = create_agent(my_think)
        agent.run("点击屏幕中央")
    """
    
    class FunctionalBrain(AIBrain):
        def think(self, screen_state: ScreenState, task: str) -> Optional[Action]:
            return think_fn(screen_state, task)
    
    return ComputerAgent(FunctionalBrain(), config=config)


# ==================== 测试用的简单AI ====================

class SimpleClickBrain(AIBrain):
    """
    简单的点击AI - 用于测试
    
    根据用户提供的坐标列表依次点击
    """
    
    def __init__(self, click_points: List[tuple]):
        self.click_points = click_points
        self._index = 0
    
    def think(self, screen_state: ScreenState, task: str) -> Optional[Action]:
        from .core.types import ActionType, Point
        
        if self._index >= len(self.click_points):
            return None
        
        x, y = self.click_points[self._index]
        self._index += 1
        
        return Action(
            action_type=ActionType.CLICK,
            coordinate=Point(x, y)
        )

