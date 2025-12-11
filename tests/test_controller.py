"""
控制器集成测试

这些测试需要实际的系统权限，在 CI 环境中可能会跳过
运行方式:
    pytest tests/test_controller.py -v
    pytest tests/test_controller.py -v -k "not requires_permission"  # 跳过需要权限的测试
"""

import pytest
import sys
import os
import platform

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import get_controller
from src.core.types import Size, Point, CoordinateType


# 标记需要实际权限的测试
requires_permission = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Skipping in CI environment - requires system permissions"
)


class TestControllerFactory:
    """控制器工厂测试"""
    
    def test_get_controller_returns_correct_type(self):
        """测试工厂返回正确的控制器类型"""
        controller = get_controller()
        
        system = platform.system()
        if system == "Darwin":
            from src.platforms.macos import MacOSController
            assert isinstance(controller, MacOSController)
        elif system == "Windows":
            from src.platforms.windows import WindowsController
            assert isinstance(controller, WindowsController)
        elif system == "Linux":
            from src.platforms.linux import LinuxController
            assert isinstance(controller, LinuxController)


class TestScreenInfo:
    """屏幕信息测试"""
    
    @requires_permission
    def test_get_screen_size(self):
        """测试获取屏幕尺寸"""
        controller = get_controller()
        size = controller.get_screen_size()
        
        assert isinstance(size, Size)
        assert size.width > 0
        assert size.height > 0
        # 合理的屏幕尺寸范围
        assert 800 <= size.width <= 7680  # 最小 800, 最大 8K
        assert 600 <= size.height <= 4320
    
    @requires_permission
    def test_get_mouse_position(self):
        """测试获取鼠标位置"""
        controller = get_controller()
        pos = controller.get_mouse_position()
        
        assert isinstance(pos, Point)
        assert pos.coordinate_type == CoordinateType.ABSOLUTE
        # 位置应该在屏幕范围内
        size = controller.get_screen_size()
        assert 0 <= pos.x <= size.width
        assert 0 <= pos.y <= size.height


class TestScreenshot:
    """截屏功能测试"""
    
    @requires_permission
    def test_screenshot_returns_bytes(self):
        """测试截屏返回字节数据"""
        controller = get_controller()
        img_bytes = controller.screenshot()
        
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0
        # PNG 文件头检查
        assert img_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    @requires_permission
    def test_screenshot_base64(self):
        """测试截屏返回 base64"""
        controller = get_controller()
        img_base64 = controller.screenshot_base64()
        
        assert isinstance(img_base64, str)
        assert len(img_base64) > 0
        
        # 验证是有效的 base64
        import base64
        decoded = base64.b64decode(img_base64)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'


class TestCoordinateResolution:
    """坐标解析测试"""
    
    @requires_permission
    def test_resolve_absolute_point(self):
        """测试解析绝对坐标"""
        controller = get_controller()
        
        point = Point(100, 200, CoordinateType.ABSOLUTE)
        x, y = controller.resolve_point(point=point)
        
        assert x == 100
        assert y == 200
    
    @requires_permission
    def test_resolve_percentage_point(self):
        """测试解析百分比坐标"""
        controller = get_controller()
        size = controller.get_screen_size()
        
        point = Point(0.5, 0.5, CoordinateType.PERCENTAGE)
        x, y = controller.resolve_point(point=point)
        
        assert x == size.width // 2
        assert y == size.height // 2
    
    @requires_permission
    def test_resolve_element_label(self):
        """测试解析元素标签"""
        from src.core.types import ScreenElement, Rect
        
        controller = get_controller()
        
        elements = [
            ScreenElement(
                label="~0",
                rect=Rect(100, 100, 200, 200)  # 中心点 (150, 150)
            )
        ]
        
        x, y = controller.resolve_point(element_label="~0", elements=elements)
        
        assert x == 150
        assert y == 150


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
