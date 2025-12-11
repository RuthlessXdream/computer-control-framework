"""
Element Detector - UI元素检测器

功能：
1. 使用YOLO模型检测UI元素
2. 使用OCR识别文本
3. 预留自定义检测器接口

注意：这个模块是占位实现，实际使用需要：
1. 安装并加载YOLO模型
2. 或者使用OmniParser
3. 或者使用Windows UI Automation
"""

import base64
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from io import BytesIO

from ..core.types import ScreenElement, Rect


class ElementDetector(ABC):
    """
    元素检测器基类
    
    子类需要实现 detect 方法
    """
    
    @abstractmethod
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """
        检测图片中的UI元素
        
        Args:
            image_bytes: PNG图片字节
            
        Returns:
            检测到的元素列表
        """
        pass
    
    def detect_base64(self, image_base64: str) -> List[ScreenElement]:
        """检测base64图片中的元素"""
        image_bytes = base64.b64decode(image_base64)
        return self.detect(image_bytes)


class DummyDetector(ElementDetector):
    """
    占位检测器
    
    用于测试，不执行实际检测
    """
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        return []


class YOLODetector(ElementDetector):
    """
    YOLO模型检测器
    
    使用YOLO模型检测UI元素
    需要安装: ultralytics
    """
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
        self._load_model()
    
    def _load_model(self):
        """加载YOLO模型"""
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
        except ImportError:
            print("Warning: ultralytics not installed, YOLO detection unavailable")
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """使用YOLO检测元素"""
        if self._model is None:
            return []
        
        from PIL import Image
        img = Image.open(BytesIO(image_bytes))
        
        # 运行检测
        results = self._model(img)
        
        elements = []
        label_counter = 0
        
        for result in results:
            if hasattr(result, 'boxes'):
                for det in result.boxes:
                    bbox = det.xyxy[0].tolist()
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    
                    confidence = float(det.conf[0]) if hasattr(det, 'conf') else 1.0
                    
                    element = ScreenElement(
                        label=f"~{label_counter}",
                        rect=Rect(x1, y1, x2, y2),
                        element_type="detected",
                        confidence=confidence
                    )
                    elements.append(element)
                    label_counter += 1
        
        return elements


class CustomDetector(ElementDetector):
    """
    自定义检测器
    
    允许用户提供自定义检测函数
    """
    
    def __init__(self, detect_fn: Callable[[bytes], List[ScreenElement]]):
        """
        Args:
            detect_fn: 检测函数，接收图片字节，返回元素列表
        """
        self._detect_fn = detect_fn
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        return self._detect_fn(image_bytes)


class CompositeDetector(ElementDetector):
    """
    组合检测器
    
    合并多个检测器的结果
    """
    
    def __init__(self, detectors: List[ElementDetector]):
        self._detectors = detectors
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        all_elements = []
        label_counter = 0
        
        for detector in self._detectors:
            elements = detector.detect(image_bytes)
            
            # 重新编号标签，避免冲突
            for elem in elements:
                elem.label = f"~{label_counter}"
                label_counter += 1
                all_elements.append(elem)
        
        return all_elements


# ==================== EasyOCR检测器 ====================

class EasyOCRDetector(ElementDetector):
    """
    EasyOCR文字检测器
    
    使用EasyOCR检测屏幕上的文字及其位置
    """
    
    def __init__(self, languages: List[str] = ['en', 'ch_sim']):
        """
        Args:
            languages: 要识别的语言列表
        """
        self._languages = languages
        self._reader = None
        self._load_reader()
    
    def _load_reader(self):
        """懒加载OCR reader"""
        try:
            import easyocr
            self._reader = easyocr.Reader(self._languages, gpu=False)
            print(f"EasyOCR loaded with languages: {self._languages}")
        except ImportError:
            print("Warning: easyocr not installed")
        except Exception as e:
            print(f"Warning: Failed to load EasyOCR: {e}")
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """使用OCR检测文字元素"""
        if self._reader is None:
            return []
        
        from PIL import Image
        import numpy as np
        
        img = Image.open(BytesIO(image_bytes))
        img_array = np.array(img)
        
        # 运行OCR
        results = self._reader.readtext(img_array)
        
        elements = []
        for i, (bbox, text, conf) in enumerate(results):
            # bbox是4个角的坐标 [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            
            x1, x2 = int(min(x_coords)), int(max(x_coords))
            y1, y2 = int(min(y_coords)), int(max(y_coords))
            
            element = ScreenElement(
                label=f"~{i}",
                rect=Rect(x1, y1, x2, y2),
                element_type="text",
                text=text,
                confidence=conf
            )
            elements.append(element)
        
        return elements


# ==================== OmniParser集成 ====================

class OmniParserDetector(ElementDetector):
    """
    OmniParser检测器
    
    使用微软OmniParser进行UI元素检测
    需要安装并配置OmniParser服务
    """
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """调用OmniParser服务检测元素"""
        try:
            import requests
            
            # 将图片转为base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 调用服务
            response = requests.post(
                f"{self.server_url}/parse",
                json={"image": image_base64}
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_result(result)
            else:
                print(f"OmniParser error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"OmniParser connection error: {e}")
            return []
    
    def _parse_result(self, result: dict) -> List[ScreenElement]:
        """解析OmniParser返回结果"""
        elements = []
        
        if "parsed_content_list" in result:
            for i, item in enumerate(result["parsed_content_list"]):
                # OmniParser返回的坐标是百分比格式
                # 需要根据图片尺寸转换
                bbox = item.get("bbox", [0, 0, 0, 0])
                
                element = ScreenElement(
                    label=f"~{i}",
                    rect=Rect(
                        int(bbox[0]),
                        int(bbox[1]),
                        int(bbox[2]),
                        int(bbox[3])
                    ),
                    element_type=item.get("type", "unknown"),
                    text=item.get("text", ""),
                    confidence=item.get("confidence", 1.0)
                )
                elements.append(element)
        
        return elements

