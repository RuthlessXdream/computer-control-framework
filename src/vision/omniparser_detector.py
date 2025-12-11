"""
OmniParser 集成模块

使用微软 OmniParser V2 进行完整的 UI 元素检测
包括：按钮、图标、输入框、文字等所有可交互元素

配置方式（优先级从高到低）:
1. 构造函数参数
2. 环境变量: OMNIPARSER_PATH, OMNIPARSER_WEIGHTS_PATH
3. 默认路径: 同级目录的 OmniParser 文件夹
"""

import base64
import logging
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import List

from PIL import Image

from ..core.types import Rect, ScreenElement
from .detector import ElementDetector

# 获取日志器
logger = logging.getLogger(__name__)

# 环境变量名
ENV_OMNIPARSER_PATH = "OMNIPARSER_PATH"
ENV_OMNIPARSER_WEIGHTS = "OMNIPARSER_WEIGHTS_PATH"
ENV_OMNIPARSER_THRESHOLD = "OMNIPARSER_BOX_THRESHOLD"


def _get_default_omniparser_path() -> str:
    """获取默认的 OmniParser 路径"""
    # 1. 检查环境变量
    env_path = os.environ.get(ENV_OMNIPARSER_PATH)
    if env_path and os.path.isdir(env_path):
        return env_path

    # 2. 检查项目内的 submodule（推荐）
    project_root = Path(__file__).parent.parent.parent
    submodule_path = project_root / "OmniParser"
    if submodule_path.is_dir():
        return str(submodule_path)

    # 3. 检查同级目录（兼容旧配置）
    sibling_path = project_root.parent / "OmniParser"
    if sibling_path.is_dir():
        return str(sibling_path)

    # 4. 检查用户目录
    home_path = Path.home() / "OmniParser"
    if home_path.is_dir():
        return str(home_path)

    # 5. 返回 submodule 路径（可能不存在，会在初始化时报错提示）
    return str(submodule_path)


def _get_default_weights_path(omniparser_path: str) -> str:
    """获取默认的权重路径"""
    # 1. 检查环境变量
    env_path = os.environ.get(ENV_OMNIPARSER_WEIGHTS)
    if env_path and os.path.isdir(env_path):
        return env_path

    # 2. 默认在 OmniParser/weights
    return os.path.join(omniparser_path, "weights")


class OmniParserDetector(ElementDetector):
    """
    OmniParser V2 检测器

    使用微软 OmniParser 检测屏幕上的所有 UI 元素

    配置方式:
        1. 直接传参:
           detector = OmniParserDetector(omniparser_path="/path/to/OmniParser")

        2. 环境变量:
           export OMNIPARSER_PATH=/path/to/OmniParser
           export OMNIPARSER_WEIGHTS_PATH=/path/to/weights
           export OMNIPARSER_BOX_THRESHOLD=0.05
    """

    def __init__(
        self,
        omniparser_path: str = None,
        weights_path: str = None,
        box_threshold: float = None
    ):
        """
        Args:
            omniparser_path: OmniParser 项目路径 (可通过 OMNIPARSER_PATH 环境变量设置)
            weights_path: 模型权重路径 (可通过 OMNIPARSER_WEIGHTS_PATH 环境变量设置)
            box_threshold: 检测阈值 (可通过 OMNIPARSER_BOX_THRESHOLD 环境变量设置)
        """
        # 获取路径配置
        if omniparser_path is None:
            omniparser_path = _get_default_omniparser_path()

        if weights_path is None:
            weights_path = _get_default_weights_path(omniparser_path)

        # 获取阈值配置
        if box_threshold is None:
            env_threshold = os.environ.get(ENV_OMNIPARSER_THRESHOLD)
            box_threshold = float(env_threshold) if env_threshold else 0.05

        self.omniparser_path = omniparser_path
        self.weights_path = weights_path
        self.box_threshold = box_threshold

        self._parser = None
        self._initialized = False

        # 记录配置信息
        logger.debug(f"OmniParser config: path={omniparser_path}, weights={weights_path}, threshold={box_threshold}")

    def _ensure_initialized(self):
        """懒加载初始化"""
        if self._initialized:
            return

        # 检查路径是否存在
        if not os.path.isdir(self.omniparser_path):
            raise FileNotFoundError(
                f"OmniParser 路径不存在: {self.omniparser_path}\n"
                f"请设置环境变量 {ENV_OMNIPARSER_PATH} 或传入正确路径"
            )

        if not os.path.isdir(self.weights_path):
            raise FileNotFoundError(
                f"模型权重路径不存在: {self.weights_path}\n"
                f"请设置环境变量 {ENV_OMNIPARSER_WEIGHTS} 或下载模型权重"
            )

        # 添加 OmniParser 到 Python 路径
        if self.omniparser_path not in sys.path:
            sys.path.insert(0, self.omniparser_path)

        try:
            from util.omniparser import Omniparser

            config = {
                'som_model_path': os.path.join(self.weights_path, 'icon_detect', 'model.pt'),
                'caption_model_name': 'florence2',
                'caption_model_path': os.path.join(self.weights_path, 'icon_caption_florence'),
                'BOX_TRESHOLD': self.box_threshold
            }

            logger.info("初始化 OmniParser...")
            logger.info(f"  OmniParser 路径: {self.omniparser_path}")
            logger.info(f"  模型权重路径: {self.weights_path}")
            logger.info(f"  检测阈值: {self.box_threshold}")

            self._parser = Omniparser(config)
            self._initialized = True
            logger.info("OmniParser 初始化完成!")

        except ImportError as e:
            logger.error(f"导入 OmniParser 失败: {e}")
            logger.error("请确保 OmniParser 已正确安装")
            raise
        except Exception as e:
            logger.error(f"初始化 OmniParser 失败: {e}", exc_info=True)
            raise

    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """
        使用 OmniParser 检测 UI 元素

        Args:
            image_bytes: PNG 图片字节

        Returns:
            检测到的元素列表
        """
        self._ensure_initialized()

        # 转换为 base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # 调用 OmniParser
        labeled_img_base64, parsed_content_list = self._parser.parse(image_base64)

        # 获取图片尺寸
        img = Image.open(BytesIO(image_bytes))
        img_width, img_height = img.size

        # 转换结果
        elements = []
        for i, item in enumerate(parsed_content_list):
            # OmniParser 返回的坐标是比例格式 [x1, y1, x2, y2]
            bbox = item.get('bbox', [0, 0, 0, 0])

            # 转换为像素坐标
            x1 = int(bbox[0] * img_width)
            y1 = int(bbox[1] * img_height)
            x2 = int(bbox[2] * img_width)
            y2 = int(bbox[3] * img_height)

            # 获取元素描述
            content = item.get('content', '')
            element_type = item.get('type', 'unknown')

            element = ScreenElement(
                label=f"~{i}",
                rect=Rect(x1, y1, x2, y2),
                element_type=element_type,
                text=content,
                confidence=1.0  # OmniParser 不返回置信度
            )
            elements.append(element)

        return elements

    def detect_with_image(self, image_bytes: bytes) -> tuple:
        """
        检测并返回标注后的图片

        Args:
            image_bytes: PNG 图片字节

        Returns:
            (元素列表, 标注图片字节)
        """
        self._ensure_initialized()

        # 转换为 base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # 调用 OmniParser
        labeled_img_base64, parsed_content_list = self._parser.parse(image_base64)

        # 获取图片尺寸
        img = Image.open(BytesIO(image_bytes))
        img_width, img_height = img.size

        # 转换结果
        elements = []
        for i, item in enumerate(parsed_content_list):
            bbox = item.get('bbox', [0, 0, 0, 0])

            x1 = int(bbox[0] * img_width)
            y1 = int(bbox[1] * img_height)
            x2 = int(bbox[2] * img_width)
            y2 = int(bbox[3] * img_height)

            content = item.get('content', '')
            element_type = item.get('type', 'unknown')

            element = ScreenElement(
                label=f"~{i}",
                rect=Rect(x1, y1, x2, y2),
                element_type=element_type,
                text=content,
                confidence=1.0
            )
            elements.append(element)

        # 解码标注图片
        labeled_img_bytes = base64.b64decode(labeled_img_base64)

        return elements, labeled_img_bytes


def create_omniparser_detector(
    omniparser_path: str = None,
    weights_path: str = None,
    box_threshold: float = 0.05
) -> OmniParserDetector:
    """
    创建 OmniParser 检测器的便捷函数

    Args:
        omniparser_path: OmniParser 项目路径
        weights_path: 模型权重路径
        box_threshold: 检测阈值

    Returns:
        OmniParserDetector 实例
    """
    return OmniParserDetector(
        omniparser_path=omniparser_path,
        weights_path=weights_path,
        box_threshold=box_threshold
    )
