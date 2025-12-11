# Computer Control Framework

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/RuthlessXdream/computer-control-framework/actions/workflows/test.yml/badge.svg)](https://github.com/RuthlessXdream/computer-control-framework/actions)

**跨平台电脑控制框架 - 为 AI Agent 设计的纯控制层**

> 让 AI 模型像人一样操作电脑：截屏、识别 UI 元素、执行鼠标键盘操作

## 🎯 设计理念

这是一个 **纯控制层框架**，不包含 AI 逻辑。它的核心职责是：

```
AI 决策 (你实现) → 控制框架 (本项目) → 操作系统
```

| 职责 | 说明 |
|-----|------|
| 📸 截屏 | 捕获屏幕状态 |
| 🔍 检测 | 识别可交互 UI 元素 |
| 🖱️ 控制 | 执行鼠标键盘操作 |
| 🔌 接口 | 预留 AI 接口，即插即用 |

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         你的 AI 模型                             │
│  (GPT-4V / Claude / Qwen-VL / 自训练模型)                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │ think(ScreenState) -> Action
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ComputerAgent                               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │  Detector   │ → │  Annotator  │ → │  ActionExecutor     │   │
│  │             │   │             │   │                     │   │
│  │ • OmniParser│   │ 标注截图     │   │ 坐标解析 + 执行      │   │
│  │ • EasyOCR   │   │ 生成标签映射 │   │                     │   │
│  │ • A11y API  │   │             │   │                     │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Platform Controller                           │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │    macOS      │  │   Windows     │  │      Linux        │   │
│  │               │  │               │  │                   │   │
│  │ • Quartz      │  │ • PyAutoGUI   │  │ • xdotool         │   │
│  │ • AppKit      │  │ • PyWinAuto   │  │ • scrot           │   │
│  │ • screencapture│ │               │  │                   │   │
│  │ • A11y API    │  │               │  │                   │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 安装

```bash
cd computer-control-framework

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 开发模式 (包含测试工具)
pip install -r requirements-dev.txt

# 运行测试验证安装
pytest tests/ -v
```

### OmniParser 集成 (推荐)

OmniParser 已作为 Git Submodule 集成，提供完整的 UI 元素检测能力：

```bash
# 克隆时一并获取 OmniParser
git clone --recurse-submodules https://github.com/RuthlessXdream/computer-control-framework.git

# 或者已克隆后初始化 submodule
git submodule update --init --recursive

# 安装 OmniParser 依赖
pip install torch torchvision transformers timm einops supervision

# 下载模型权重 (约 1.5GB)
cd OmniParser
# 参考 OmniParser/README.md 下载权重到 weights/ 目录
```

### 其他可选依赖

```bash
# Windows UI 自动化
pip install pywinauto

# UI 元素检测 (OCR)
pip install easyocr
```

## 🚀 快速开始

### 1. 直接使用控制器

```python
from src import get_controller

controller = get_controller()  # 自动检测平台

# 屏幕信息
print(f"屏幕: {controller.get_screen_size()}")
print(f"鼠标: {controller.get_mouse_position()}")

# 截屏
screenshot_bytes = controller.screenshot()
screenshot_base64 = controller.screenshot_base64()

# 鼠标
controller.mouse_move(100, 200, duration=0.5)
controller.mouse_click(100, 200)
controller.mouse_click(100, 200, clicks=2)  # 双击
controller.mouse_scroll(3)  # 向上滚动

# 键盘
controller.type_text("Hello World")
controller.key_press("enter")
controller.hotkey("command", "c")  # macOS
controller.hotkey("ctrl", "c")     # Windows
```

### 2. 通过 Agent 使用 (推荐)

```python
from src import AIBrain, ComputerAgent, ScreenState, Action, ActionType, Point

class MyAIBrain(AIBrain):
    def think(self, screen_state: ScreenState, task: str) -> Action:
        """
        screen_state 包含:
        - screenshot_base64: 原始截屏
        - annotated_screenshot_base64: 标注后截屏
        - elements: UI 元素列表 [ScreenElement, ...]
        - label_to_rect: {"~0": Rect, "~1": Rect, ...}
        - screen_size: Size(width, height)
        """
        
        # 调用你的 AI 模型
        # response = your_ai.generate(screen_state.annotated_screenshot_base64, task)
        
        return Action(
            action_type=ActionType.CLICK,
            coordinate=Point(100, 200)
        )

brain = MyAIBrain()
agent = ComputerAgent(brain)
agent.run("打开 Chrome 浏览器")
```

## 🔍 UI 元素检测

框架提供多种检测方式，可组合使用：

### 1. OmniParser (完整检测，推荐)

```python
from src.vision.omniparser_detector import OmniParserDetector

detector = OmniParserDetector(
    omniparser_path="/path/to/OmniParser",
    weights_path="/path/to/OmniParser/weights"
)

elements = detector.detect(screenshot_bytes)
# 或获取标注图
elements, labeled_img = detector.detect_with_image(screenshot_bytes)
```

检测能力：
- ✅ 按钮、图标
- ✅ 输入框
- ✅ 文字
- ✅ 菜单项
- ✅ 所有可交互元素

### 2. EasyOCR (文字检测)

```python
from src.vision.detector import EasyOCRDetector

detector = EasyOCRDetector(languages=['en', 'ch_sim'])
elements = detector.detect(screenshot_bytes)
```

### 3. Accessibility API (系统级元素，macOS)

```python
from src.vision.accessibility_detector import AccessibilityDetector

detector = AccessibilityDetector()
elements = detector.detect(b'')  # 不需要截图

# 获取窗口控制按钮 (🔴🟡🟢)
window_controls = detector._get_window_controls()

# 获取菜单栏
menu_items = detector._get_menu_bar_items()
```

### 4. 混合检测器

```python
from src.vision.accessibility_detector import HybridDetector
from src.vision.omniparser_detector import OmniParserDetector

omni = OmniParserDetector(...)
hybrid = HybridDetector(omni, use_accessibility=True)

# 结合 OmniParser + Accessibility API
elements = hybrid.detect(screenshot_bytes)
```

### 5. 自定义检测器

```python
from src.vision.detector import CustomDetector, ScreenElement, Rect

def my_detect(image_bytes):
    return [
        ScreenElement(label="~0", rect=Rect(10, 20, 100, 50), text="Button"),
    ]

detector = CustomDetector(my_detect)
```

## 📐 坐标系统

框架支持三种坐标定位：

```python
from src import Action, ActionType, Point, CoordinateType

# 1. 绝对像素坐标
Action(
    action_type=ActionType.CLICK,
    coordinate=Point(100, 200, CoordinateType.ABSOLUTE)
)

# 2. 百分比坐标 (屏幕中央)
Action(
    action_type=ActionType.CLICK,
    coordinate=Point(0.5, 0.5, CoordinateType.PERCENTAGE)
)

# 3. 元素标签 (推荐)
Action(
    action_type=ActionType.CLICK,
    element_label="~3"  # 点击检测到的第3个元素
)
```

## 📋 Action 类型

| 类型 | 说明 | 关键参数 |
|-----|------|---------|
| `CLICK` | 单击 | `coordinate`, `element_label`, `button` |
| `DOUBLE_CLICK` | 双击 | `coordinate`, `element_label` |
| `RIGHT_CLICK` | 右键 | `coordinate`, `element_label` |
| `MOUSE_MOVE` | 移动鼠标 | `coordinate`, `duration` |
| `DRAG` | 拖拽 | `coordinate`, `end_coordinate` |
| `SCROLL` | 滚动 | `scroll_amount`, `scroll_direction` |
| `TYPE_TEXT` | 输入文本 | `text` |
| `KEY_PRESS` | 按键 | `keys` |
| `HOTKEY` | 组合键 | `keys` |
| `WAIT` | 等待 | `duration` |

## 🖥️ 平台支持

| 平台 | 截屏 | 鼠标 | 键盘 | UI 检测 |
|-----|-----|-----|-----|---------|
| **macOS** | ✅ screencapture | ✅ Quartz | ✅ Quartz | ✅ Accessibility API |
| **Windows** | ✅ PyAutoGUI | ✅ PyAutoGUI | ✅ PyAutoGUI | ✅ PyWinAuto |
| **Linux** | ✅ scrot | ✅ xdotool | ✅ xdotool | - |

## 📁 项目结构

```
computer-control-framework/
├── .github/
│   └── workflows/
│       └── test.yml             # GitHub Actions CI
│
├── src/                         # 核心源码
│   ├── __init__.py              # 主入口，导出所有公开 API
│   ├── ai_interface.py          # AI 接口 (AIBrain, ComputerAgent)
│   ├── core/                    # 核心类型和基类
│   │   ├── types.py             # 类型定义 (Action, Point, ScreenState...)
│   │   ├── base.py              # 控制器基类
│   │   └── actions.py           # 动作执行器
│   ├── platforms/               # 平台适配层
│   │   ├── macos.py             # macOS 实现 (Quartz)
│   │   ├── windows.py           # Windows 实现 (PyAutoGUI + PyWinAuto)
│   │   └── linux.py             # Linux 实现 (xdotool)
│   ├── vision/                  # 视觉检测模块
│   │   ├── annotator.py         # 截屏标注器
│   │   ├── detector.py          # 检测器基类 + EasyOCR/YOLO
│   │   ├── omniparser_detector.py  # OmniParser 集成
│   │   └── accessibility_detector.py  # macOS Accessibility API
│   └── utils/                   # 工具模块
│       └── logger.py            # 日志系统
│
├── tests/                       # 单元测试 & 集成测试
│   ├── test_core.py             # 核心类型单元测试
│   └── test_controller.py       # 控制器集成测试
│
├── scripts/                     # 工具脚本
│   ├── check_permission.py      # macOS 权限检查
│   └── verify_all_features.py   # 功能验证脚本
│
├── examples/                    # 使用示例
│   ├── 01_basic_control.py
│   ├── 02_screenshot.py
│   └── 03_ai_agent.py
│
├── OmniParser/                  # Git Submodule - 微软 OmniParser
│
├── .gitignore                   # Git 忽略配置
├── LICENSE                      # MIT 许可证
├── pyproject.toml               # 项目配置 (PEP 621)
├── requirements.txt             # 核心依赖
├── requirements-dev.txt         # 开发依赖
├── env.example                  # 环境变量配置示例 (OmniParser 等)
├── CONTRIBUTING.md              # 贡献指南
└── README.md                    # 项目文档
```

## 🧠 接入你的 AI

框架的核心是 `AIBrain` 接口，你只需实现 `think()` 方法：

```python
from openai import OpenAI
from src import AIBrain, ScreenState, Action, ActionType, Point

class GPT4VBrain(AIBrain):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def think(self, screen_state: ScreenState, task: str) -> Action:
        # 1. 构造 prompt
        messages = [
            {"role": "system", "content": "你是电脑操作助手。根据截图和任务，返回下一步操作。"},
            {"role": "user", "content": [
                {"type": "text", "text": f"任务: {task}\n\n可点击元素: {screen_state.elements}"},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{screen_state.annotated_screenshot_base64}"
                }}
            ]}
        ]
        
        # 2. 调用 AI
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        # 3. 解析响应
        return self._parse_response(response.choices[0].message.content)
    
    def _parse_response(self, text: str) -> Action:
        # 解析 AI 返回的文本为 Action
        # 例如: "click ~3" -> Action(ActionType.CLICK, element_label="~3")
        ...
```

## 🔗 参考项目

本框架整合了以下项目的设计思想：

| 项目 | 贡献 |
|-----|------|
| [Self-Operating Computer](https://github.com/OthersideAI/self-operating-computer) | 百分比坐标、YOLO 检测 |
| [Anthropic Computer Use](https://github.com/anthropics/anthropic-quickstarts) | 坐标缩放、xdotool |
| [UFO](https://github.com/microsoft/UFO) | Windows PyWinAuto 集成 |
| [OmniParser](https://github.com/microsoft/OmniParser) | 完整 UI 元素检测 |
| [PyAutoGUI](https://github.com/asweigart/pyautogui) | 跨平台控制基础 |

## ⚙️ 配置

### Agent 配置

```python
from src import ComputerAgent, AgentConfig

config = AgentConfig(
    action_delay=1.0,           # 每次动作后等待
    screenshot_delay=0.5,       # 截屏前等待
    max_steps=100,              # 最大执行步数
    annotate_screenshot=True,   # 是否标注截屏
)

agent = ComputerAgent(brain, config=config)
```

### 环境变量配置

框架支持通过环境变量进行配置：

```bash
# 日志配置
export CCF_LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
export CCF_LOG_DIR=logs             # 日志文件目录

# OmniParser 配置
export OMNIPARSER_PATH=/path/to/OmniParser
export OMNIPARSER_WEIGHTS_PATH=/path/to/weights
export OMNIPARSER_BOX_THRESHOLD=0.05
```

参考 `env.example` 文件了解所有可配置项。

### 日志系统

框架内置结构化日志系统：

```python
from src.utils.logger import get_logger, get_action_logger

# 普通日志
logger = get_logger(__name__)
logger.info("操作开始")
logger.error("操作失败", exc_info=True)

# Action 专用日志
action_logger = get_action_logger(__name__)
action_logger.action(
    action_type="click",
    coordinate=(100, 200),
    success=True,
    duration=0.05
)
```

日志文件默认保存在 `logs/` 目录，包含：
- `ccf.log`: 全部日志 (JSON 格式，自动轮转)
- `ccf_error.log`: 仅错误日志

## 🔐 权限 (macOS)

macOS 需要授予辅助功能权限：

```
系统设置 → 隐私与安全性 → 辅助功能 → 添加 Cursor/Terminal
```

## License

MIT
