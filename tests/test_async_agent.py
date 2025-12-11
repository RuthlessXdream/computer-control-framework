"""
异步 Agent 测试

运行方式:
    pytest tests/test_async_agent.py -v
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.async_agent import (
    AsyncAIBrain,
    AsyncComputerAgent,
    AsyncAgentConfig,
    SyncBrainAdapter,
    create_async_agent,
)
from src.ai_interface import AIBrain, SimpleClickBrain
from src.core.types import Action, ActionType, Point, ScreenState, Size


class TestAsyncAgentConfig:
    """异步 Agent 配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AsyncAgentConfig()
        
        assert config.action_delay == 1.0
        assert config.screenshot_delay == 0.5
        assert config.max_steps == 100
        assert config.thread_pool_size == 4
        assert config.step_timeout == 60.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = AsyncAgentConfig(
            action_delay=0.5,
            max_steps=50,
            step_timeout=30.0
        )
        
        assert config.action_delay == 0.5
        assert config.max_steps == 50
        assert config.step_timeout == 30.0


class TestSyncBrainAdapter:
    """同步 Brain 适配器测试"""
    
    def test_adapter_creation(self):
        """测试适配器创建"""
        sync_brain = SimpleClickBrain([(100, 200)])
        adapter = SyncBrainAdapter(sync_brain)
        
        assert adapter._sync_brain is sync_brain
    
    def test_adapter_invalid_brain(self):
        """测试无效 Brain"""
        with pytest.raises(TypeError):
            SyncBrainAdapter("not a brain")
    
    @pytest.mark.asyncio
    async def test_adapter_think(self):
        """测试适配器思考"""
        sync_brain = SimpleClickBrain([(100, 200), (300, 400)])
        adapter = SyncBrainAdapter(sync_brain)
        
        # 创建模拟 ScreenState
        screen_state = ScreenState(
            screenshot_base64="",
            elements=[],
            screen_size=Size(1920, 1080)
        )
        
        # 调用 think
        action = await adapter.think(screen_state, "test")
        
        assert action is not None
        assert action.action_type == ActionType.CLICK
        assert action.coordinate.x == 100
        assert action.coordinate.y == 200


class TestCreateAsyncAgent:
    """创建异步 Agent 测试"""
    
    def test_create_with_function(self):
        """测试使用函数创建"""
        async def my_think(state, task):
            return Action(action_type=ActionType.WAIT, duration=0.01)
        
        agent = create_async_agent(my_think)
        assert isinstance(agent, AsyncComputerAgent)


class MockAsyncBrain(AsyncAIBrain):
    """测试用的模拟异步 Brain"""
    
    def __init__(self, max_steps: int = 3):
        self.step_count = 0
        self.max_steps = max_steps
    
    async def think(self, screen_state: ScreenState, task: str):
        self.step_count += 1
        
        if self.step_count >= self.max_steps:
            return None  # 结束
        
        return Action(
            action_type=ActionType.WAIT,
            duration=0.01
        )
    
    async def should_continue(self, step: int, screen_state: ScreenState) -> bool:
        return step < self.max_steps


class TestAsyncComputerAgent:
    """异步 Agent 测试"""
    
    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """测试 Agent 创建"""
        brain = MockAsyncBrain()
        config = AsyncAgentConfig(
            action_delay=0.01,
            screenshot_delay=0.01,
            max_steps=5
        )
        
        agent = AsyncComputerAgent(brain, config=config)
        
        assert agent.brain is brain
        assert agent.config.max_steps == 5
        assert agent.current_step == 0
    
    @pytest.mark.asyncio
    async def test_agent_cancel(self):
        """测试 Agent 取消"""
        brain = MockAsyncBrain(max_steps=100)
        config = AsyncAgentConfig(
            action_delay=0.01,
            screenshot_delay=0.01
        )
        
        agent = AsyncComputerAgent(brain, config=config)
        
        # 在后台运行并取消
        async def run_and_cancel():
            task = asyncio.create_task(agent.run("test"))
            await asyncio.sleep(0.1)
            agent.cancel()
            return await task
        
        result = await run_and_cancel()
        
        # 任务应该被取消
        assert result is False or agent._cancelled
    
    @pytest.mark.asyncio
    async def test_agent_history(self):
        """测试执行历史"""
        brain = MockAsyncBrain(max_steps=3)
        config = AsyncAgentConfig(
            action_delay=0.01,
            screenshot_delay=0.01
        )
        
        agent = AsyncComputerAgent(brain, config=config)
        await agent.run("test")
        
        # 应该有历史记录
        assert len(agent.history) > 0


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
