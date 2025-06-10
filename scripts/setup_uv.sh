#!/bin/bash

# SmartChat项目 uv 设置脚本
# 使用方法: chmod +x scripts/setup_uv.sh && ./scripts/setup_uv.sh

set -e

echo "🚀 SmartChat项目 uv 设置开始..."

# 检查是否安装了uv
if ! command -v uv &> /dev/null; then
    echo "❌ uv未安装，正在安装..."
    echo "请选择安装方式:"
    echo "1) Homebrew (推荐 macOS 用户)"
    echo "2) 官方安装脚本"
    echo "3) pip 安装"
    read -p "请输入选择 (1-3): " choice
    
    case $choice in
        1)
            echo "使用 Homebrew 安装 uv..."
            brew install uv
            ;;
        2)
            echo "使用官方脚本安装 uv..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            ;;
        3)
            echo "使用 pip 安装 uv..."
            pip install uv
            ;;
        *)
            echo "无效选择，退出..."
            exit 1
            ;;
    esac
fi

echo "✅ uv 已安装，版本: $(uv --version)"

# 移动到项目根目录
cd "$(dirname "$0")/.."

# 备份现有的 requirements.txt
if [ -f "backend/requirements.txt" ]; then
    echo "📦 备份现有依赖文件..."
    cp backend/requirements.txt backend/requirements.txt.backup
    echo "✅ 已备份到 backend/requirements.txt.backup"
fi

# 初始化 uv 项目（如果还没有 pyproject.toml）
if [ ! -f "pyproject.toml" ]; then
    echo "🔧 初始化 uv 项目..."
    uv init --no-readme
fi

# 同步依赖
echo "📥 安装项目依赖..."
uv sync

# 安装开发依赖
echo "🛠️ 安装开发依赖..."
uv sync --extra dev

echo "🎉 uv 设置完成！"
echo ""
echo "📋 常用命令:"
echo "  uv run python backend/main.py          # 运行应用"
echo "  uv run pytest                          # 运行测试"
echo "  uv run celery -A backend.celery_app worker  # 运行Celery worker"
echo "  uv add package_name                    # 添加依赖"
echo "  uv add --dev package_name              # 添加开发依赖"
echo "  uv sync                                # 同步依赖"
echo "  uv lock                                # 更新锁定文件"
echo ""
echo "🔗 详细使用说明请查看 docs/uv-guide.md" 