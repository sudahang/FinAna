#!/bin/bash
# FinAna 命令行快捷方式
# 用法：./cli.sh "分析腾讯"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行 CLI 分析器
python cli_analyzer.py "$@"
