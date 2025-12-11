"""
核心模块单元测试

运行方式:
    pytest tests/test_core.py -v
    pytest tests/test_core.py -v --tb=short  # 简短错误信息
"""

import pytest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.types import (
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


class TestPoint:
    """Point 类测试"""
    
    def test_absolute_point(self):
        """测试绝对坐标点"""
        p = Point(100, 200)
        assert p.x == 100
        assert p.y == 200
        assert p.coordinate_type == CoordinateType.ABSOLUTE
    
    def test_percentage_point(self):
        """测试百分比坐标点"""
        p = Point(0.5, 0.3, CoordinateType.PERCENTAGE)
        assert p.x == 0.5
        assert p.y == 0.3
        assert p.coordinate_type == CoordinateType.PERCENTAGE
    
    def test_to_absolute_from_percentage(self):
        """测试百分比转绝对坐标"""
        p = Point(0.5, 0.25, CoordinateType.PERCENTAGE)
        abs_p = p.to_absolute(1920, 1080)
        
        assert abs_p.x == 960  # 1920 * 0.5
        assert abs_p.y == 270  # 1080 * 0.25
        assert abs_p.coordinate_type == CoordinateType.ABSOLUTE
    
    def test_to_percentage_from_absolute(self):
        """测试绝对转百分比坐标"""
        p = Point(960, 540, CoordinateType.ABSOLUTE)
        pct_p = p.to_percentage(1920, 1080)
        
        assert pct_p.x == 0.5
        assert pct_p.y == 0.5
        assert pct_p.coordinate_type == CoordinateType.PERCENTAGE


class TestRect:
    """Rect 类测试"""
    
    def test_rect_properties(self):
        """测试矩形属性"""
        r = Rect(10, 20, 110, 70)
        
        assert r.width == 100  # 110 - 10
        assert r.height == 50  # 70 - 20
    
    def test_rect_center(self):
        """测试矩形中心点"""
        r = Rect(0, 0, 100, 100)
        center = r.center
        
        assert center.x == 50
        assert center.y == 50
        assert center.coordinate_type == CoordinateType.ABSOLUTE
    
    def test_rect_to_percentage(self):
        """测试矩形转百分比"""
        r = Rect(0, 0, 960, 540)
        pct_r = r.to_percentage(1920, 1080)
        
        assert pct_r.left == 0.0
        assert pct_r.top == 0.0
        assert pct_r.right == 0.5
        assert pct_r.bottom == 0.5


class TestScreenElement:
    """ScreenElement 类测试"""
    
    def test_element_creation(self):
        """测试元素创建"""
        elem = ScreenElement(
            label="~0",
            rect=Rect(100, 100, 200, 150),
            element_type="button",
            text="Click Me",
            confidence=0.95
        )
        
        assert elem.label == "~0"
        assert elem.element_type == "button"
        assert elem.text == "Click Me"
        assert elem.confidence == 0.95
    
    def test_element_center_point(self):
        """测试元素中心点"""
        elem = ScreenElement(
            label="~1",
            rect=Rect(0, 0, 100, 100)
        )
        
        center = elem.center_point
        assert center.x == 50
        assert center.y == 50


class TestAction:
    """Action 类测试"""
    
    def test_click_action(self):
        """测试点击动作"""
        action = Action(
            action_type=ActionType.CLICK,
            coordinate=Point(100, 200)
        )
        
        assert action.action_type == ActionType.CLICK
        assert action.coordinate.x == 100
        assert action.coordinate.y == 200
        assert action.button == MouseButton.LEFT  # 默认左键
    
    def test_type_text_action(self):
        """测试输入文本动作"""
        action = Action(
            action_type=ActionType.TYPE_TEXT,
            text="Hello World"
        )
        
        assert action.action_type == ActionType.TYPE_TEXT
        assert action.text == "Hello World"
    
    def test_hotkey_action(self):
        """测试组合键动作"""
        action = Action(
            action_type=ActionType.HOTKEY,
            keys=["command", "c"]
        )
        
        assert action.action_type == ActionType.HOTKEY
        assert action.keys == ["command", "c"]
    
    def test_scroll_action(self):
        """测试滚动动作"""
        action = Action(
            action_type=ActionType.SCROLL,
            scroll_amount=5,
            scroll_direction="down"
        )
        
        assert action.action_type == ActionType.SCROLL
        assert action.scroll_amount == 5
        assert action.scroll_direction == "down"


class TestScreenState:
    """ScreenState 类测试"""
    
    def test_get_element_by_label(self):
        """测试通过标签获取元素"""
        elements = [
            ScreenElement(label="~0", rect=Rect(0, 0, 50, 50)),
            ScreenElement(label="~1", rect=Rect(100, 100, 150, 150)),
            ScreenElement(label="~2", rect=Rect(200, 200, 250, 250)),
        ]
        
        state = ScreenState(
            screenshot_base64="",
            elements=elements
        )
        
        elem = state.get_element_by_label("~1")
        assert elem is not None
        assert elem.label == "~1"
        assert elem.rect.left == 100
        
        # 测试不存在的标签
        assert state.get_element_by_label("~999") is None
    
    def test_get_click_point(self):
        """测试获取点击坐标"""
        elements = [
            ScreenElement(label="btn", rect=Rect(0, 0, 100, 100)),
        ]
        
        state = ScreenState(
            screenshot_base64="",
            elements=elements
        )
        
        point = state.get_click_point("btn")
        assert point is not None
        assert point.x == 50  # 中心点
        assert point.y == 50


class TestActionResult:
    """ActionResult 类测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = ActionResult(
            success=True,
            message="Click executed",
            duration=0.05
        )
        
        assert result.success is True
        assert result.error is None
        assert result.duration == 0.05
    
    def test_failure_result(self):
        """测试失败结果"""
        result = ActionResult(
            success=False,
            error="Element not found",
            message="Click failed"
        )
        
        assert result.success is False
        assert result.error == "Element not found"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
