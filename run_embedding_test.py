#!/usr/bin/env python3
"""
简化的embedding测试运行脚本
使用方法: uv run python run_embedding_test.py
"""

import os
import sys

# 确保当前目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并运行测试
from backend.test_embedding_model import main

if __name__ == "__main__":
    exit(main()) 