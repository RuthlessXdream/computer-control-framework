"""
Screen Annotator - 截屏标注器

将检测到的元素标注在截图上
"""

import base64
from io import BytesIO
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from ..core.types import Rect, ScreenElement


class ScreenAnnotator:
    """
    截屏标注器

    将检测到的元素用边框和标签标注在截图上
    """

    def __init__(
        self,
        font_size: int = 14,
        box_color: tuple = (255, 0, 0),  # 红色
        text_color: tuple = (255, 255, 255),  # 白色
        box_width: int = 2,
    ):
        self.font_size = font_size
        self.box_color = box_color
        self.text_color = text_color
        self.box_width = box_width

        # 加载字体
        try:
            self._font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            try:
                self._font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except OSError:
                self._font = ImageFont.load_default()

    def annotate(
        self,
        image_bytes: bytes,
        elements: List[ScreenElement],
        label_prefix: str = "~"
    ) -> Tuple[bytes, Dict[str, Rect]]:
        """
        在截图上标注元素

        Args:
            image_bytes: PNG图片字节
            elements: 要标注的元素列表
            label_prefix: 标签前缀

        Returns:
            (标注后的图片字节, 标签到坐标的映射)
        """
        # 加载图片
        img = Image.open(BytesIO(image_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(img)

        label_to_rect = {}

        for i, elem in enumerate(elements):
            # 使用元素自带的标签或生成新标签
            label = elem.label if elem.label else f"{label_prefix}{i}"
            rect = elem.rect

            # 绘制边框
            draw.rectangle(
                [rect.left, rect.top, rect.right, rect.bottom],
                outline=self.box_color,
                width=self.box_width
            )

            # 绘制标签背景
            text_bbox = draw.textbbox((0, 0), label, font=self._font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            label_x = rect.left
            label_y = rect.top - text_height - 4

            # 如果标签会超出图片顶部，放到框内
            if label_y < 0:
                label_y = rect.top + 2

            # 绘制标签背景
            draw.rectangle(
                [label_x, label_y, label_x + text_width + 4, label_y + text_height + 4],
                fill=self.box_color
            )

            # 绘制标签文字
            draw.text(
                (label_x + 2, label_y + 2),
                label,
                fill=self.text_color,
                font=self._font
            )

            # 记录标签到坐标映射
            label_to_rect[label] = rect

        # 转换回字节
        output = BytesIO()
        img.convert("RGB").save(output, format="PNG")
        return output.getvalue(), label_to_rect

    def annotate_base64(
        self,
        image_base64: str,
        elements: List[ScreenElement],
        label_prefix: str = "~"
    ) -> Tuple[str, Dict[str, Rect]]:
        """
        标注base64图片

        Args:
            image_base64: base64编码的图片
            elements: 要标注的元素列表
            label_prefix: 标签前缀

        Returns:
            (标注后的base64图片, 标签到坐标的映射)
        """
        image_bytes = base64.b64decode(image_base64)
        annotated_bytes, label_to_rect = self.annotate(image_bytes, elements, label_prefix)
        return base64.b64encode(annotated_bytes).decode('utf-8'), label_to_rect
