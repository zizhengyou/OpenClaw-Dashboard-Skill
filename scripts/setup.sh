#!/bin/bash
# ============================================================
# dashboard-gen Skill 依赖安装脚本
# 用途：一键安装本Skill所需的Python依赖
# 使用：bash scripts/setup.sh
# ============================================================

echo "🦞 OpenClaw dashboard-gen Skill 依赖安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查 Python3 是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

echo "✅ Python版本: $(python3 --version)"

# 安装依赖
echo ""
echo "📦 正在安装依赖..."
pip install pandas openpyxl pyecharts

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 依赖安装完成！"
    echo ""
    echo "📖 使用方法："
    echo "  探查数据: python3 scripts/dashboard_generator.py --probe '你的文件.xlsx'"
    echo "  生成看板: python3 scripts/dashboard_generator.py --config '{...}' --output output.html"
else
    echo ""
    echo "❌ 安装失败，请检查网络或pip配置"
    exit 1
fi
