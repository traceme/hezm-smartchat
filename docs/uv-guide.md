# SmartChat项目 uv 使用指南

## 目录
- [简介](#简介)
- [安装和设置](#安装和设置)
- [基本用法](#基本用法)
- [依赖管理](#依赖管理)
- [运行项目](#运行项目)
- [开发工作流](#开发工作流)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

## 简介

uv是一个极快的Python包管理器，用Rust编写，为SmartChat项目提供：

- 🚀 **极速安装**: 比pip快10-100倍
- 🔒 **依赖锁定**: 确保可重现的构建
- 🐍 **Python版本管理**: 自动管理Python版本
- 📦 **虚拟环境**: 自动创建和管理虚拟环境
- 🔧 **工具集成**: 与pytest、black、mypy等无缝集成

## 安装和设置

### 1. 安装uv

```bash
# 方式1: Homebrew (macOS推荐)
brew install uv

# 方式2: 官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh

# 方式3: pip安装
pip install uv
```

### 2. 项目设置

```bash
# 使用我们的设置脚本 (推荐)
chmod +x scripts/setup_uv.sh
./scripts/setup_uv.sh

# 或手动设置
uv sync
```

## 基本用法

### 项目初始化

```bash
# 在现有项目中初始化uv
uv init

# 创建新项目
uv init smartchat-new
cd smartchat-new
```

### 虚拟环境管理

```bash
# uv会自动创建和激活虚拟环境
# 无需手动管理venv

# 查看当前环境信息
uv info

# 查看Python版本
uv run python --version
```

## 依赖管理

### 添加依赖

```bash
# 添加生产依赖
uv add fastapi
uv add "sqlalchemy>=2.0.0"

# 添加开发依赖
uv add --dev pytest
uv add --dev black isort mypy

# 从URL安装
uv add "git+https://github.com/user/repo.git"

# 安装本地包
uv add -e ./local-package
```

### 移除依赖

```bash
# 移除依赖
uv remove fastapi

# 移除开发依赖
uv remove --dev pytest
```

### 同步和锁定

```bash
# 同步依赖（安装pyproject.toml中的所有依赖）
uv sync

# 只安装生产依赖
uv sync --no-dev

# 安装特定组的依赖
uv sync --extra dev
uv sync --extra test

# 更新锁定文件
uv lock

# 强制更新所有依赖
uv lock --upgrade
```

### 查看依赖

```bash
# 列出所有依赖
uv tree

# 查看特定包信息
uv show fastapi

# 检查过期依赖
uv list --outdated
```

## 运行项目

### SmartChat应用服务

```bash
# 启动FastAPI服务器
uv run python backend/main.py

# 或使用uvicorn
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 启动Celery worker
uv run celery -A backend.celery_app worker --loglevel=info

# 启动Celery beat (定时任务)
uv run celery -A backend.celery_app beat --loglevel=info
```

### 数据库操作

```bash
# 运行数据库迁移
uv run alembic upgrade head

# 创建新迁移
uv run alembic revision --autogenerate -m "描述"

# 初始化数据库
uv run python backend/init_db.py
```

### 测试和开发工具

```bash
# 运行测试
uv run pytest

# 运行特定测试
uv run pytest backend/test_vectorization.py

# 代码格式化
uv run black backend/
uv run isort backend/

# 类型检查
uv run mypy backend/

# 代码质量检查
uv run flake8 backend/
```

### 自定义脚本

```bash
# 运行文档处理测试
uv run python backend/test_document_processing.py

# 运行向量化测试
uv run python backend/test_vectorization.py

# 运行混合搜索测试
uv run python backend/test_hybrid_search.py

# 启动开发环境
uv run python backend/run_dev.py
```

## 开发工作流

### 1. 日常开发

```bash
# 拉取最新代码后同步依赖
git pull
uv sync

# 添加新功能所需的依赖
uv add new-package

# 运行应用进行测试
uv run python backend/main.py

# 运行测试套件
uv run pytest

# 提交前格式化代码
uv run black backend/
uv run isort backend/
```

### 2. 添加新功能

```bash
# 1. 创建新分支
git checkout -b feature/new-feature

# 2. 添加依赖（如果需要）
uv add new-dependency

# 3. 开发功能
# ... 编写代码 ...

# 4. 运行测试
uv run pytest backend/test_new_feature.py

# 5. 代码质量检查
uv run black backend/
uv run mypy backend/

# 6. 提交更改
git add .
git commit -m "feat: 添加新功能"
```

### 3. 环境同步

```bash
# 团队成员获取最新依赖
git pull
uv sync

# 如果需要清理环境
rm -rf .venv uv.lock
uv sync
```

## 最佳实践

### 1. 依赖管理

```toml
# pyproject.toml 中的依赖应该尽量宽松
dependencies = [
    "fastapi>=0.104.0",  # 使用 >= 而不是 ==
    "sqlalchemy>=2.0.0,<3.0.0",  # 指定兼容范围
]

# 精确版本由 uv.lock 文件管理
```

### 2. 开发环境

```bash
# 始终使用 uv sync 而不是 pip install
uv sync

# 为不同环境创建不同的依赖组
[project.optional-dependencies]
dev = ["pytest", "black", "mypy"]
test = ["pytest", "coverage"]
docs = ["mkdocs", "mkdocs-material"]
```

### 3. 脚本和工具

```bash
# 在 pyproject.toml 中定义脚本
[project.scripts]
smartchat = "backend.main:app"
test = "pytest"
format = "black backend/"
```

### 4. CI/CD集成

```yaml
# .github/workflows/test.yml
- name: Set up uv
  uses: astral-sh/setup-uv@v1

- name: Install dependencies
  run: uv sync --all-extras

- name: Run tests
  run: uv run pytest
```

## 常见问题

### Q: 如何从pip迁移到uv？

A: 按以下步骤：
```bash
# 1. 备份现有环境
pip freeze > requirements-backup.txt

# 2. 创建pyproject.toml
uv init

# 3. 从requirements.txt添加依赖
uv add -r backend/requirements.txt

# 4. 验证依赖
uv run python -c "import fastapi; print('OK')"
```

### Q: 如何处理版本冲突？

A: uv提供详细的冲突信息：
```bash
# 查看冲突详情
uv lock --resolution lowest-direct

# 手动解决冲突
uv add "package>=1.0.0,<2.0.0"
```

### Q: 如何在Docker中使用uv？

A: 更新Dockerfile：
```dockerfile
# 安装uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 复制项目文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN uv sync --frozen --no-cache

# 运行应用
CMD ["uv", "run", "python", "backend/main.py"]
```

### Q: 如何设置IDE集成？

A: 配置IDE使用uv环境：
```bash
# 获取Python路径
uv run which python

# 在IDE中设置此路径作为解释器
# VS Code: 在设置中指定python路径
# PyCharm: 在项目设置中添加已存在的解释器
```

### Q: 如何处理私有包？

A: 配置私有包源：
```bash
# 添加私有源
uv add --index-url https://private.pypi.org/simple/ private-package

# 或在pyproject.toml中配置
[tool.uv.sources]
private-package = { index = "https://private.pypi.org/simple/" }
```

## 性能对比

| 操作 | pip | uv | 提升 |
|------|-----|----|----|
| 安装依赖 | 45s | 3s | 15x |
| 解析依赖 | 12s | 0.5s | 24x |
| 缓存查找 | 2s | 0.1s | 20x |

## 总结

使用uv管理SmartChat项目的优势：

1. **极速**: 大幅提升依赖安装和解析速度
2. **可靠**: 锁定文件确保环境一致性
3. **简单**: 自动管理虚拟环境和Python版本
4. **兼容**: 与现有pip/poetry工作流兼容
5. **现代**: 支持最新Python打包标准

开始使用uv，让您的Python开发更快更可靠！ 