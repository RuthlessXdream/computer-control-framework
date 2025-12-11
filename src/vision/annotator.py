"""
Screen Annotator - 截屏标注器

功能：
1. 在截屏上绘制元素边界框和标签
2. 生成标签到坐标的映射
"""

import base64
from io import BytesIO
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

from ..core.types import ScreenElement, Rect


class ScreenAnnotator:
    """
    截屏标注器
    
    在截屏图片上绘制UI元素的边界框和标签，方便AI识别
    """
    
    def __init__(
        self,
        box_color: str = "red",
        label_color: str = "red",
        label_bg_color: str = "#FFFF00",
        box_width: int = 2,
        font_size: int = 16,
    ):
        self.box_color = box_color
        self.label_color = label_color
        self.label_bg_color = label_bg_color
        self.box_width = box_width
        self.font_size = font_size
        
        # 尝试加载字体
        self._font = None
        try:
            self._font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                self._font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                self._font = ImageFont.load_default()
    
    def annotate(
        self,
        image_bytes: bytes,
        elements: List[ScreenElement]
    ) -> Tuple[bytes, Dict[str, Rect]]:
        """
        在图片上标注元素
        
        Args:
            image_bytes: PNG图片字节
            elements: 要标注的元素列表
            
        Returns:
            (标注后的图片字节, 标签到Rect的映射)
        """
        # 打开图片
        img = Image.open(BytesIO(image_bytes))
        draw = ImageDraw.Draw(img)
        
        label_map: Dict[str, Rect] = {}
        
        for element in elements:
            rect = element.rect
            label = element.label
            
            # 绘制边界框
            draw.rectangle(
                [(rect.left, rect.top), (rect.right, rect.bottom)],
                outline=self.box_color,
                width=self.box_width
            )
            
            # 绘制标签
            self._draw_label(draw, label, rect.left, rect.top)
            
            # 记录映射
            label_map[label] = rect
        
        # 保存图片
        output = BytesIO()
        img.save(output, format='PNG')
        return output.getvalue(), label_map
    
    def annotate_base64(
        self,
        image_base64: str,
        elements: List[ScreenElement]
    ) -> Tuple[str, Dict[str, Rect]]:
        """
        标注base64图片
        
        Args:
            image_base64: base64编码的PNG图片
            elements: 要标注的元素列表
            
        Returns:
            (标注后的图片base64, 标签到Rect的映射)
        """
        image_bytes = base64.b64decode(image_base64)
        annotated_bytes, label_map = self.annotate(image_bytes, elements)
        annotated_base64 = base64.b64encode(annotated_bytes).decode('utf-8')
        return annotated_base64, label_map
    
    def _draw_label(self, draw: ImageDraw, label: str, x: int, y: int) -> None:
        """绘制标签"""
        # 计算文本大小
        bbox = draw.textbbox((0, 0), label, font=self._font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        padding = 2
        
        # 绘制标签背景
        draw.rectangle(
            [
                (x, y - text_height - padding * 2),
                (x + text_width + padding * 2, y)
            ],
            fill=self.label_bg_color,
            outline=self.box_color
        )
        
        # 绘制标签文本
        draw.text(
            (x + padding, y - text_height - padding),
            label,
            fill=self.label_color,
            font=self._font
        )
    
    @staticmethod
    def generate_labels(count: int, prefix: str = "~") -> List[str]:
        """
        生成标签序列
        
        Args:
            count: 标签数量
            prefix: 标签前缀
            
        Returns:
            标签列表 ["~0", "~1", "~2", ...]
        """
        return [f"{prefix}{i}" for i in range(count)]
    
    @staticmethod
    def generate_letter_labels(count: int) -> List[str]:
        """
        生成字母标签
        
        Args:
            count: 标签数量
            
        Returns:
            标签列表 ["A", "B", "C", ..., "AA", "AB", ...]
        """
        labels = []
        for i in range(count):
            label = ""
            n = i
            while True:
                label = chr(65 + n % 26) + label
                n = n // 26 - 1
                if n < 0:
                    break
            labels.append(label)
        return labels

