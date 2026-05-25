#!/bin/bash
# Fund-Agent 每日邮件发送脚本
set -e

# 加载环境变量（cron 不会加载 .bashrc）
if [ -f /root/.bashrc ]; then
    . /root/.bashrc
fi
if [ -f /root/clawd/.env ]; then
    export $(grep -v '^#' /root/clawd/.env | xargs)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$(dirname "$SCRIPT_DIR")/data"

echo "=== Fund-Agent 每日邮件 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 运行分析脚本（更新数据）
echo "📊 运行分析..."
python3 "$SCRIPT_DIR/analyze.py" --quiet 2>/dev/null || true

# 2. 运行评分脚本
echo "📈 计算评分..."
python3 "$SCRIPT_DIR/factor-score.py" --rank --quiet 2>/dev/null || true

# 3. 获取市场要闻（真实 mx-search 数据）
echo "📰 市场要闻..."
NEWS_OUTPUT=$(python3 "$SCRIPT_DIR/market-news.py" 2>/dev/null)

# 4. 模拟盘每日交易
echo "🎯 模拟盘交易..."
SIM_OUTPUT=$(python3 "$SCRIPT_DIR/sim-daily-trade.py" 2>/dev/null)

# 5. 生成邮件报告
echo "📝 生成报告..."
python3 "$SCRIPT_DIR/report-gen.py" --email --news "$NEWS_OUTPUT" --sim "$SIM_OUTPUT"

# 5. 发送邮件
EMAIL_FILE="$DATA_DIR/email-report.md"
if [ -f "$EMAIL_FILE" ]; then
    REPORT_CONTENT=$(cat "$EMAIL_FILE")
    echo "📧 发送邮件..."
    python3 "$SCRIPT_DIR/send_mail.py" \
        "Fund-Agent 理财日报 | $(date '+%Y-%m-%d')" \
        "$REPORT_CONTENT" \
        --html
    echo "✅ 邮件发送完成"
else
    echo "❌ 报告文件不存在"
    exit 1
fi
