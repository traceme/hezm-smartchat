# SmartChat项目 Makefile
# 使用uv进行包管理

.PHONY: help install sync dev test clean format lint run celery docs

# 默认目标
help:
	@echo "SmartChat项目 - uv 管理命令"
	@echo ""
	@echo "设置和依赖:"
	@echo "  install     安装uv并设置项目"
	@echo "  sync        同步项目依赖"
	@echo "  dev         安装开发依赖"
	@echo ""
	@echo "运行服务:"
	@echo "  run         启动FastAPI应用"
	@echo "  celery      启动Celery worker"
	@echo "  beat        启动Celery beat"
	@echo ""
	@echo "开发工具:"
	@echo "  test        运行测试套件"
	@echo "  format      格式化代码"
	@echo "  lint        代码质量检查"
	@echo "  type-check  类型检查"
	@echo ""
	@echo "数据库:"
	@echo "  migrate     运行数据库迁移"
	@echo "  migration   创建新迁移"
	@echo "  init-db     初始化数据库"
	@echo ""
	@echo "其他:"
	@echo "  clean       清理缓存和临时文件"
	@echo "  docs        生成文档"
	@echo "  docker      构建Docker镜像"

# 安装和设置
install:
	@echo "🚀 设置SmartChat项目..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "安装uv..."; \
		brew install uv || curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	@echo "✅ uv已安装: $$(uv --version)"
	@uv sync
	@echo "🎉 项目设置完成！"

sync:
	@echo "📥 同步项目依赖..."
	@uv sync

dev:
	@echo "🛠️ 安装开发依赖..."
	@uv sync --extra dev

# 运行服务
run:
	@echo "🚀 启动FastAPI应用..."
	@uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

celery:
	@echo "🔄 启动Celery worker..."
	@uv run celery -A backend.celery_app worker --loglevel=info

beat:
	@echo "⏰ 启动Celery beat..."
	@uv run celery -A backend.celery_app beat --loglevel=info

# 开发工具
test:
	@echo "🧪 运行测试套件..."
	@uv run pytest

test-cov:
	@echo "🧪 运行测试并生成覆盖率报告..."
	@uv run pytest --cov=backend --cov-report=html --cov-report=term

test-watch:
	@echo "👀 监听模式运行测试..."
	@uv run pytest-watch

format:
	@echo "🎨 格式化代码..."
	@uv run black backend/
	@uv run isort backend/
	@echo "✅ 代码格式化完成"

lint:
	@echo "🔍 运行代码质量检查..."
	@uv run flake8 backend/
	@echo "✅ 代码质量检查完成"

type-check:
	@echo "🔍 运行类型检查..."
	@uv run mypy backend/
	@echo "✅ 类型检查完成"

check: format lint type-check
	@echo "✅ 所有代码质量检查完成"

# 数据库
migrate:
	@echo "🗄️ 运行数据库迁移..."
	@uv run alembic upgrade head

migration:
	@echo "📝 创建新数据库迁移..."
	@read -p "迁移描述: " desc; \
	uv run alembic revision --autogenerate -m "$$desc"

init-db:
	@echo "🗄️ 初始化数据库..."
	@uv run python backend/init_db.py

# 清理
clean:
	@echo "🧹 清理项目..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf dist
	@rm -rf build
	@echo "✅ 清理完成"

clean-all: clean
	@echo "🧹 深度清理（包括虚拟环境）..."
	@rm -rf .venv
	@rm -f uv.lock
	@echo "✅ 深度清理完成"

# 文档
docs:
	@echo "📚 生成项目文档..."
	@uv run mkdocs build
	@echo "✅ 文档生成完成，查看 site/ 目录"

docs-serve:
	@echo "📚 启动文档服务器..."
	@uv run mkdocs serve

# Docker
docker:
	@echo "🐳 构建Docker镜像..."
	@docker build -t smartchat:latest .
	@echo "✅ Docker镜像构建完成"

docker-up:
	@echo "🐳 启动Docker Compose服务..."
	@docker-compose up -d

docker-down:
	@echo "🐳 停止Docker Compose服务..."
	@docker-compose down

# 开发环境快速启动
dev-up:
	@echo "🚀 启动完整开发环境..."
	@make docker-up
	@sleep 5
	@make migrate
	@echo "✅ 开发环境已启动"
	@echo "📝 FastAPI应用: make run"
	@echo "🔄 Celery worker: make celery"

# 依赖管理
add:
	@read -p "包名: " pkg; \
	uv add "$$pkg"

add-dev:
	@read -p "开发包名: " pkg; \
	uv add --dev "$$pkg"

remove:
	@read -p "要移除的包名: " pkg; \
	uv remove "$$pkg"

update:
	@echo "📦 更新所有依赖..."
	@uv lock --upgrade
	@uv sync

tree:
	@echo "📋 依赖树..."
	@uv tree

# 特定测试
test-vectorization:
	@echo "🧪 测试向量化功能..."
	@uv run python backend/test_vectorization.py

test-hybrid:
	@echo "🧪 测试混合搜索..."
	@uv run python backend/test_hybrid_search.py

test-document:
	@echo "🧪 测试文档处理..."
	@uv run python backend/test_document_processing.py

# 性能测试
benchmark:
	@echo "⚡ 运行性能基准测试..."
	@uv run python backend/benchmark_search.py

# Git hooks
pre-commit:
	@echo "🔍 运行提交前检查..."
	@make format
	@make lint
	@make type-check
	@make test
	@echo "✅ 提交前检查完成"

# 项目信息
info:
	@echo "📊 项目信息:"
	@echo "Python: $$(uv run python --version)"
	@echo "uv: $$(uv --version)"
	@echo "项目根目录: $$(pwd)"
	@echo "虚拟环境: $$(uv info | grep 'virtual environment' || echo '未创建')"
	@echo ""
	@echo "📦 主要依赖:"
	@uv tree --depth 1 | head -20 