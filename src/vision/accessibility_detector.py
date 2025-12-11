"""
macOS Accessibility API 检测器

使用 macOS 系统级 API 获取 UI 元素，可以检测到：
- 窗口控制按钮（关闭、最小化、最大化）
- 菜单项
- 按钮、输入框等所有系统级控件
"""

import subprocess
import json
from typing import List, Dict, Any, Optional
from ..core.types import ScreenElement, Rect
from .detector import ElementDetector


class AccessibilityDetector(ElementDetector):
    """
    macOS Accessibility API 检测器
    
    使用 AppleScript 和 System Events 获取 UI 元素
    """
    
    def __init__(self):
        self._check_permission()
    
    def _check_permission(self):
        """检查辅助功能权限"""
        # 权限检查通过尝试运行简单的AppleScript
        pass
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        """
        检测当前活动窗口的UI元素
        
        注意：这个方法不使用图片，而是直接获取系统UI元素
        """
        elements = []
        
        try:
            # 获取前台应用的窗口元素
            elements.extend(self._get_window_controls())
            elements.extend(self._get_menu_bar_items())
        except Exception as e:
            print(f"Accessibility detection error: {e}")
        
        return elements
    
    def _get_window_controls(self) -> List[ScreenElement]:
        """获取窗口控制按钮（关闭、最小化、最大化）"""
        elements = []
        
        # 简化脚本，直接获取窗口位置
        script = '''
        tell application "System Events"
            tell (first application process whose frontmost is true)
                try
                    tell window 1
                        set {x, y} to position
                        return (x as text) & "," & (y as text)
                    end tell
                end try
            end tell
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                if len(parts) >= 2:
                    win_x = int(float(parts[0]))
                    win_y = int(float(parts[1]))
                    
                    # macOS 窗口控制按钮的标准位置（Retina屏幕坐标）
                    # 关闭按钮（红）
                    elements.append(ScreenElement(
                        label="~close",
                        rect=Rect(win_x + 7, win_y + 7, win_x + 19, win_y + 19),
                        element_type="window_control",
                        text="关闭窗口",
                        confidence=1.0
                    ))
                    
                    # 最小化按钮（黄）
                    elements.append(ScreenElement(
                        label="~minimize",
                        rect=Rect(win_x + 27, win_y + 7, win_x + 39, win_y + 19),
                        element_type="window_control",
                        text="最小化窗口",
                        confidence=1.0
                    ))
                    
                    # 最大化/全屏按钮（绿）
                    elements.append(ScreenElement(
                        label="~maximize",
                        rect=Rect(win_x + 47, win_y + 7, win_x + 59, win_y + 19),
                        element_type="window_control",
                        text="最大化/全屏",
                        confidence=1.0
                    ))
                    
        except Exception as e:
            print(f"Failed to get window controls: {e}")
        
        return elements
    
    def _get_menu_bar_items(self) -> List[ScreenElement]:
        """获取菜单栏项目"""
        elements = []
        
        script = '''
        tell application "System Events"
            tell (first application process whose frontmost is true)
                set output to ""
                try
                    repeat with menuItem in menu bar items of menu bar 1
                        set itemName to name of menuItem
                        set {x, y} to position of menuItem
                        set {w, h} to size of menuItem
                        set output to output & itemName & "|" & x & "|" & y & "|" & w & "|" & h & linefeed
                    end repeat
                end try
                return output
            end tell
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 5:
                            name = parts[0]
                            try:
                                x = int(float(parts[1]))
                                y = int(float(parts[2]))
                                w = int(float(parts[3]))
                                h = int(float(parts[4]))
                                
                                elements.append(ScreenElement(
                                    label=f"~menu_{i}",
                                    rect=Rect(x, y, x + w, y + h),
                                    element_type="menu_item",
                                    text=name,
                                    confidence=1.0
                                ))
                            except ValueError:
                                continue
                        
        except Exception as e:
            print(f"Failed to get menu items: {e}")
        
        return elements
    
    def get_all_ui_elements(self, app_name: str = None) -> List[ScreenElement]:
        """
        获取指定应用的所有UI元素
        
        Args:
            app_name: 应用名称，None表示前台应用
        """
        elements = []
        
        if app_name:
            script = f'''
            tell application "System Events"
                tell application process "{app_name}"
                    set allElements to entire contents
                    set result to ""
                    repeat with elem in allElements
                        try
                            set elemRole to role of elem
                            set elemName to name of elem
                            set elemPos to position of elem
                            set elemSize to size of elem
                            set result to result & elemRole & "|" & elemName & "|" & (item 1 of elemPos) & "|" & (item 2 of elemPos) & "|" & (item 1 of elemSize) & "|" & (item 2 of elemSize) & "\\n"
                        end try
                    end repeat
                    return result
                end tell
            end tell
            '''
        else:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                tell frontApp
                    set allElements to entire contents
                    set result to ""
                    repeat with elem in allElements
                        try
                            set elemRole to role of elem
                            set elemName to name of elem
                            set elemPos to position of elem
                            set elemSize to size of elem
                            set result to result & elemRole & "|" & elemName & "|" & (item 1 of elemPos) & "|" & (item 2 of elemPos) & "|" & (item 1 of elemSize) & "|" & (item 2 of elemSize) & "\\n"
                        end try
                    end repeat
                    return result
                end tell
            end tell
            '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30  # 获取所有元素可能需要较长时间
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    parts = line.split('|')
                    if len(parts) >= 6:
                        role = parts[0]
                        name = parts[1] if parts[1] != 'missing value' else ''
                        x = int(float(parts[2]))
                        y = int(float(parts[3]))
                        w = int(float(parts[4]))
                        h = int(float(parts[5]))
                        
                        # 过滤掉无效的元素
                        if w > 0 and h > 0:
                            elements.append(ScreenElement(
                                label=f"~ax_{i}",
                                rect=Rect(x, y, x + w, y + h),
                                element_type=role,
                                text=name,
                                confidence=1.0
                            ))
                        
        except Exception as e:
            print(f"Failed to get UI elements: {e}")
        
        return elements


class HybridDetector(ElementDetector):
    """
    混合检测器
    
    结合 OmniParser 和 Accessibility API 的结果
    """
    
    def __init__(self, omniparser_detector=None, use_accessibility=True):
        self._omniparser = omniparser_detector
        self._accessibility = AccessibilityDetector() if use_accessibility else None
    
    def detect(self, image_bytes: bytes) -> List[ScreenElement]:
        elements = []
        label_counter = 0
        
        # 先用 OmniParser 检测
        if self._omniparser:
            omni_elements = self._omniparser.detect(image_bytes)
            for elem in omni_elements:
                elem.label = f"~{label_counter}"
                elements.append(elem)
                label_counter += 1
        
        # 再用 Accessibility API 补充窗口控制按钮
        if self._accessibility:
            ax_elements = self._accessibility.detect(image_bytes)
            for elem in ax_elements:
                # 检查是否与现有元素重叠
                if not self._is_duplicate(elem, elements):
                    elem.label = f"~{label_counter}"
                    elements.append(elem)
                    label_counter += 1
        
        return elements
    
    def _is_duplicate(self, new_elem: ScreenElement, existing: List[ScreenElement]) -> bool:
        """检查元素是否与现有元素重叠"""
        for elem in existing:
            # 计算重叠面积
            x1 = max(new_elem.rect.left, elem.rect.left)
            y1 = max(new_elem.rect.top, elem.rect.top)
            x2 = min(new_elem.rect.right, elem.rect.right)
            y2 = min(new_elem.rect.bottom, elem.rect.bottom)
            
            if x1 < x2 and y1 < y2:
                overlap_area = (x2 - x1) * (y2 - y1)
                new_area = (new_elem.rect.right - new_elem.rect.left) * (new_elem.rect.bottom - new_elem.rect.top)
                
                # 如果重叠超过50%，认为是重复
                if overlap_area > new_area * 0.5:
                    return True
        
        return False

