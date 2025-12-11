# Contributing to Computer Control Framework

感谢你对本项目的关注！欢迎贡献代码。

## 开发环境设置

```bash
# 克隆项目
git clone --recurse-submodules https://github.com/RuthlessXdream/computer-control-framework.git
cd computer-control-framework

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v
```

## 代码规范

- 使用 Ruff 进行代码检查: `ruff check src/`
- 使用 MyPy 进行类型检查: `mypy src/`
- 所有公开 API 必须有类型注解和文档字符串

## 提交规范

提交信息格式：

```
<type>: <description>

[optional body]
```

Type 类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

## Pull Request

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feat/your-feature`
3. 提交更改: `git commit -m "feat: add some feature"`
4. 推送分支: `git push origin feat/your-feature`
5. 创建 Pull Request

## 问题反馈

如果发现 Bug 或有功能建议，请在 [Issues](https://github.com/RuthlessXdream/computer-control-framework/issues) 中提出。

