"""
Debug Tools - 可视化调试工具

提供调试和可视化功能:
- 截图预览和标注
- 元素检测可视化
- 执行历史回放
- 性能分析

使用方式:
    from src.utils.debug import DebugViewer, save_debug_screenshot
    
    # 保存调试截图
    save_debug_screenshot(screenshot_bytes, elements, "debug_output.png")
    
    # 使用调试查看器
    viewer = DebugViewer()
    viewer.show_screenshot(screenshot_bytes, elements)
    viewer.show_execution_history(history)
"""

import os
import json
import base64
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
from dataclasses import dataclass, asdict

from PIL import Image, ImageDraw, ImageFont

from ..core.types import ScreenElement, Rect, Action, ActionResult, ScreenState

# ==================== 配置 ====================

DEFAULT_DEBUG_DIR = os.environ.get("CCF_DEBUG_DIR", "debug_output")

# 标注样式
ANNOTATION_COLORS = {
    "default": (255, 0, 0, 180),      # 红色
    "button": (0, 255, 0, 180),       # 绿色
    "text": (0, 0, 255, 180),         # 蓝色
    "input": (255, 165, 0, 180),      # 橙色
    "icon": (128, 0, 128, 180),       # 紫色
    "image": (0, 128, 128, 180),      # 青色
    "link": (255, 192, 203, 180),     # 粉色
    "selected": (255, 255, 0, 200),   # 黄色 (高亮)
}

LABEL_FONT_SIZE = 12
BOX_LINE_WIDTH = 2


# ==================== 调试数据结构 ====================

@dataclass
class DebugFrame:
    """调试帧 - 记录单步执行状态"""
    step: int
    timestamp: float
    screenshot_base64: str
    elements: List[Dict[str, Any]]
    action: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    duration: float
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "DebugFrame":
        return cls(**data)


@dataclass  
class DebugSession:
    """调试会话 - 记录完整任务执行"""
    session_id: str
    task: str
    start_time: float
    end_time: Optional[float]
    frames: List[DebugFrame]
    success: bool
    total_steps: int
    
    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "frames": [f.to_dict() for f in self.frames]
        }
    
    def save(self, path: str) -> None:
        """保存会话到文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "DebugSession":
        """从文件加载会话"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data["frames"] = [DebugFrame.from_dict(f) for f in data["frames"]]
        return cls(**data)


# ==================== 图像标注工具 ====================

def get_element_color(element_type: str) -> Tuple[int, int, int, int]:
    """根据元素类型获取颜色"""
    element_type = (element_type or "default").lower()
    return ANNOTATION_COLORS.get(element_type, ANNOTATION_COLORS["default"])


def annotate_image(
    image: Image.Image,
    elements: List[ScreenElement],
    highlight_label: str = None,
    show_labels: bool = True,
    show_confidence: bool = False,
) -> Image.Image:
    """
    在图像上标注元素
    
    Args:
        image: PIL Image 对象
        elements: 元素列表
        highlight_label: 要高亮的元素标签
        show_labels: 是否显示标签
        show_confidence: 是否显示置信度
        
    Returns:
        标注后的图像
    """
    # 创建可绘制的副本
    annotated = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 尝试加载字体
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", LABEL_FONT_SIZE)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", LABEL_FONT_SIZE)
        except Exception:
            font = ImageFont.load_default()
    
    # 绘制每个元素
    for elem in elements:
        rect = elem.rect
        
        # 选择颜色
        if elem.label == highlight_label:
            color = ANNOTATION_COLORS["selected"]
            line_width = BOX_LINE_WIDTH + 2
        else:
            color = get_element_color(elem.element_type)
            line_width = BOX_LINE_WIDTH
        
        # 绘制边框
        draw.rectangle(
            [rect.left, rect.top, rect.right, rect.bottom],
            outline=color[:3],
            width=line_width
        )
        
        # 绘制半透明填充
        fill_color = (*color[:3], 30)  # 很淡的填充
        draw.rectangle(
            [rect.left, rect.top, rect.right, rect.bottom],
            fill=fill_color
        )
        
        # 绘制标签
        if show_labels:
            label_text = elem.label
            if show_confidence and elem.confidence < 1.0:
                label_text += f" ({elem.confidence:.0%})"
            
            # 标签背景
            bbox = font.getbbox(label_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            label_x = rect.left
            label_y = rect.top - text_height - 4
            if label_y < 0:
                label_y = rect.bottom + 2
            
            draw.rectangle(
                [label_x, label_y, label_x + text_width + 4, label_y + text_height + 4],
                fill=color[:3]
            )
            
            draw.text(
                (label_x + 2, label_y + 2),
                label_text,
                fill=(255, 255, 255),
                font=font
            )
    
    # 合并图层
    annotated = Image.alpha_composite(annotated, overlay)
    return annotated.convert("RGB")


def annotate_screenshot(
    screenshot_bytes: bytes,
    elements: List[ScreenElement],
    **kwargs
) -> bytes:
    """
    标注截图
    
    Args:
        screenshot_bytes: PNG 截图字节
        elements: 元素列表
        **kwargs: 传递给 annotate_image 的参数
        
    Returns:
        标注后的 PNG 字节
    """
    image = Image.open(BytesIO(screenshot_bytes))
    annotated = annotate_image(image, elements, **kwargs)
    
    buffer = BytesIO()
    annotated.save(buffer, format='PNG')
    return buffer.getvalue()


def save_debug_screenshot(
    screenshot_bytes: bytes,
    elements: List[ScreenElement],
    output_path: str,
    **kwargs
) -> str:
    """
    保存调试截图
    
    Args:
        screenshot_bytes: PNG 截图字节
        elements: 元素列表
        output_path: 输出路径
        **kwargs: 传递给 annotate_image 的参数
        
    Returns:
        保存的文件路径
    """
    annotated_bytes = annotate_screenshot(screenshot_bytes, elements, **kwargs)
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'wb') as f:
        f.write(annotated_bytes)
    
    return str(output_path)


# ==================== 调试查看器 ====================

class DebugViewer:
    """
    调试查看器
    
    用于可视化调试 AI Agent 的执行过程
    """
    
    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: 调试输出目录
        """
        self.output_dir = Path(output_dir or DEFAULT_DEBUG_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._current_session: Optional[DebugSession] = None
        self._frame_count = 0
    
    def start_session(self, task: str) -> str:
        """开始新的调试会话"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self._current_session = DebugSession(
            session_id=session_id,
            task=task,
            start_time=time.time(),
            end_time=None,
            frames=[],
            success=False,
            total_steps=0
        )
        self._frame_count = 0
        
        # 创建会话目录
        session_dir = self.output_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        return session_id
    
    def record_frame(
        self,
        screenshot_base64: str,
        elements: List[ScreenElement],
        action: Optional[Action] = None,
        result: Optional[ActionResult] = None,
    ) -> None:
        """记录一帧"""
        if not self._current_session:
            return
        
        self._frame_count += 1
        
        frame = DebugFrame(
            step=self._frame_count,
            timestamp=time.time(),
            screenshot_base64=screenshot_base64,
            elements=[
                {
                    "label": e.label,
                    "rect": {"left": e.rect.left, "top": e.rect.top, 
                             "right": e.rect.right, "bottom": e.rect.bottom},
                    "type": e.element_type,
                    "text": e.text,
                    "confidence": e.confidence
                }
                for e in elements
            ],
            action={
                "type": action.action_type.value,
                "coordinate": (action.coordinate.x, action.coordinate.y) if action.coordinate else None,
                "element_label": action.element_label,
                "text": action.text,
            } if action else None,
            result={
                "success": result.success,
                "error": result.error,
                "duration": result.duration
            } if result else None,
            duration=result.duration if result else 0
        )
        
        self._current_session.frames.append(frame)
        
        # 保存截图
        self._save_frame_screenshot(frame)
    
    def _save_frame_screenshot(self, frame: DebugFrame) -> None:
        """保存帧截图"""
        if not self._current_session:
            return
        
        session_dir = self.output_dir / self._current_session.session_id
        
        # 解码截图
        screenshot_bytes = base64.b64decode(frame.screenshot_base64)
        
        # 重建元素列表
        elements = [
            ScreenElement(
                label=e["label"],
                rect=Rect(**e["rect"]),
                element_type=e["type"],
                text=e["text"],
                confidence=e["confidence"]
            )
            for e in frame.elements
        ]
        
        # 确定高亮元素
        highlight = None
        if frame.action and frame.action.get("element_label"):
            highlight = frame.action["element_label"]
        
        # 保存标注截图
        output_path = session_dir / f"step_{frame.step:03d}.png"
        save_debug_screenshot(
            screenshot_bytes,
            elements,
            str(output_path),
            highlight_label=highlight,
            show_labels=True
        )
    
    def end_session(self, success: bool) -> str:
        """结束调试会话"""
        if not self._current_session:
            return ""
        
        self._current_session.end_time = time.time()
        self._current_session.success = success
        self._current_session.total_steps = self._frame_count
        
        # 保存会话数据
        session_dir = self.output_dir / self._current_session.session_id
        session_file = session_dir / "session.json"
        self._current_session.save(str(session_file))
        
        # 生成 HTML 报告
        self._generate_html_report()
        
        session_id = self._current_session.session_id
        self._current_session = None
        
        return session_id
    
    def _generate_html_report(self) -> None:
        """生成 HTML 报告"""
        if not self._current_session:
            return
        
        session_dir = self.output_dir / self._current_session.session_id
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>调试报告 - {self._current_session.session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #333; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; }}
        .summary {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .frame {{ background: white; padding: 15px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .frame img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
        .frame-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .step-badge {{ background: #007bff; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold; }}
        .success {{ color: #28a745; }}
        .failure {{ color: #dc3545; }}
        .action-info {{ background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px; font-family: monospace; }}
        .elements-count {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 调试报告</h1>
        <p>会话 ID: {self._current_session.session_id}</p>
    </div>
    
    <div class="summary">
        <h2>📊 任务概览</h2>
        <p><strong>任务:</strong> {self._current_session.task}</p>
        <p><strong>状态:</strong> <span class="{'success' if self._current_session.success else 'failure'}">
            {'✓ 成功' if self._current_session.success else '✗ 失败'}
        </span></p>
        <p><strong>总步数:</strong> {self._current_session.total_steps}</p>
        <p><strong>总耗时:</strong> {(self._current_session.end_time or time.time()) - self._current_session.start_time:.2f}s</p>
    </div>
    
    <h2>📝 执行步骤</h2>
"""
        
        for frame in self._current_session.frames:
            action_info = ""
            if frame.action:
                action_info = f"""
                <div class="action-info">
                    <strong>动作:</strong> {frame.action.get('type', 'N/A')}<br>
                    {"<strong>坐标:</strong> " + str(frame.action.get('coordinate', 'N/A')) + "<br>" if frame.action.get('coordinate') else ""}
                    {"<strong>元素:</strong> " + str(frame.action.get('element_label', 'N/A')) + "<br>" if frame.action.get('element_label') else ""}
                    {"<strong>文本:</strong> " + str(frame.action.get('text', '')) + "<br>" if frame.action.get('text') else ""}
                </div>
                """
            
            result_status = ""
            if frame.result:
                result_status = f"<span class='{'success' if frame.result['success'] else 'failure'}'>{'✓' if frame.result['success'] else '✗'}</span>"
            
            html_content += f"""
    <div class="frame">
        <div class="frame-header">
            <span class="step-badge">Step {frame.step}</span>
            <span class="elements-count">检测到 {len(frame.elements)} 个元素</span>
            {result_status}
        </div>
        <img src="step_{frame.step:03d}.png" alt="Step {frame.step}">
        {action_info}
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        report_path = session_dir / "report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def show_screenshot(
        self,
        screenshot_bytes: bytes,
        elements: List[ScreenElement],
        title: str = "Screenshot"
    ) -> None:
        """显示截图 (仅在支持图形界面时有效)"""
        image = Image.open(BytesIO(screenshot_bytes))
        annotated = annotate_image(image, elements)
        
        try:
            annotated.show(title=title)
        except Exception as e:
            print(f"无法显示图像: {e}")
            # 保存到文件作为备选
            output_path = self.output_dir / f"preview_{int(time.time())}.png"
            annotated.save(output_path)
            print(f"已保存到: {output_path}")


# ==================== 调试装饰器 ====================

class DebugAgent:
    """
    调试代理包装器
    
    包装 ComputerAgent 以添加调试功能
    """
    
    def __init__(self, agent, viewer: DebugViewer = None):
        """
        Args:
            agent: ComputerAgent 实例
            viewer: DebugViewer 实例
        """
        self._agent = agent
        self._viewer = viewer or DebugViewer()
    
    def run(self, task: str) -> bool:
        """运行并记录调试信息"""
        session_id = self._viewer.start_session(task)
        print(f"🔍 调试会话已开始: {session_id}")
        
        try:
            # 修改 agent 的 step 方法以记录
            original_step = self._agent.step
            
            def debug_step(task_str):
                action, result, screen_state = original_step(task_str)
                
                if screen_state:
                    self._viewer.record_frame(
                        screenshot_base64=screen_state.screenshot_base64,
                        elements=screen_state.elements,
                        action=action,
                        result=result
                    )
                
                return action, result, screen_state
            
            self._agent.step = debug_step
            
            # 运行任务
            success = self._agent.run(task)
            
            # 恢复原始方法
            self._agent.step = original_step
            
            return success
            
        finally:
            session_id = self._viewer.end_session(success if 'success' in dir() else False)
            print(f"📊 调试报告已生成: {self._viewer.output_dir / session_id / 'report.html'}")


# ==================== 便捷函数 ====================

def create_debug_agent(agent) -> DebugAgent:
    """创建调试代理"""
    return DebugAgent(agent)


def quick_screenshot_debug(controller, detector, output_path: str = None) -> str:
    """
    快速调试截图
    
    截取屏幕并保存标注后的调试图
    """
    screenshot_bytes = controller.screenshot()
    elements = detector.detect(screenshot_bytes)
    
    if output_path is None:
        output_path = f"debug_{int(time.time())}.png"
    
    return save_debug_screenshot(screenshot_bytes, elements, output_path)
