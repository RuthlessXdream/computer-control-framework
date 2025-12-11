"""
示例3: AI Agent

演示如何创建一个AI Agent来控制电脑

这个示例展示了框架的核心设计：
1. AIBrain: 你的AI逻辑
2. ComputerAgent: 框架的执行循环
3. ScreenState: 截屏+元素信息
4. Action: 标准化的动作指令

你需要实现 AIBrain.think() 方法，接入你自己的AI模型
"""

import sys
sys.path.insert(0, '..')

from src import (
    AIBrain,
    ComputerAgent,
    AgentConfig,
    ScreenState,
    Action,
    ActionType,
    Point,
    CoordinateType,
)


class SimpleSearchBrain(AIBrain):
    """
    一个简单的AI示例 - 在屏幕上搜索特定文本
    
    实际使用时，你会在这里调用你的LLM/Vision模型
    """
    
    def __init__(self, target_text: str):
        self.target_text = target_text
        self.found = False
        self.click_count = 0
        self.max_clicks = 3
    
    def think(self, screen_state: ScreenState, task: str) -> Action:
        """
        AI思考函数
        
        Args:
            screen_state: 当前屏幕状态
                - screen_state.screenshot_base64: 截屏的base64
                - screen_state.annotated_screenshot_base64: 标注后的截屏
                - screen_state.elements: UI元素列表
                - screen_state.label_to_rect: 标签到坐标的映射
            task: 任务描述
            
        Returns:
            下一步要执行的动作
        """
        print(f"AI思考中... 任务: {task}")
        print(f"检测到 {len(screen_state.elements)} 个UI元素")
        
        # 这里应该是你的AI逻辑
        # 例如：将截屏发送给GPT-4V，获取下一步操作
        
        # 示例：简单地在元素中查找目标文本
        for elem in screen_state.elements:
            if elem.text and self.target_text.lower() in elem.text.lower():
                print(f"找到目标元素: {elem.label} - {elem.text}")
                self.found = True
                
                # 返回点击该元素的动作
                return Action(
                    action_type=ActionType.CLICK,
                    element_label=elem.label,  # 通过标签定位
                )
        
        # 没找到目标，尝试点击屏幕中央
        if self.click_count < self.max_clicks:
            self.click_count += 1
            size = screen_state.screen_size
            
            return Action(
                action_type=ActionType.CLICK,
                coordinate=Point(
                    size.width // 2,
                    size.height // 2,
                    CoordinateType.ABSOLUTE
                )
            )
        
        # 放弃
        return None
    
    def should_continue(self, step: int, screen_state: ScreenState) -> bool:
        """判断是否继续执行"""
        if self.found:
            print("目标已找到，停止执行")
            return False
        return True


class LLMBrain(AIBrain):
    """
    LLM驱动的AI大脑模板
    
    这是你接入实际AI模型的地方
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4-vision-preview"):
        self.api_key = api_key
        self.model = model
        # self.client = OpenAI(api_key=api_key)  # 你的AI客户端
    
    def think(self, screen_state: ScreenState, task: str) -> Action:
        """
        调用LLM进行决策
        
        伪代码示例:
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个电脑操作助手，根据截屏决定下一步操作"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"任务: {task}"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{screen_state.annotated_screenshot_base64}"
                        }}
                    ]
                }
            ]
        )
        
        # 解析响应并返回Action
        return self._parse_response(response)
        """
        
        # 占位实现
        print("LLMBrain.think() 需要实现实际的AI调用")
        return None
    
    def _parse_response(self, response) -> Action:
        """解析AI响应为Action"""
        # 实现你的解析逻辑
        pass


def main():
    # 创建一个简单的AI
    brain = SimpleSearchBrain("Chrome")
    
    # 配置
    config = AgentConfig(
        action_delay=1.0,       # 每次动作后等待1秒
        screenshot_delay=0.5,   # 截屏前等待0.5秒
        max_steps=10,           # 最多执行10步
        annotate_screenshot=False,  # 暂时禁用标注（需要检测器）
    )
    
    # 创建Agent
    agent = ComputerAgent(brain, config=config)
    
    # 运行任务
    # agent.run("找到并点击Chrome图标")
    
    print("示例代码准备完成!")
    print("取消注释 agent.run() 来实际运行")
    print("\n要接入你自己的AI，请实现 AIBrain.think() 方法")

if __name__ == "__main__":
    main()

