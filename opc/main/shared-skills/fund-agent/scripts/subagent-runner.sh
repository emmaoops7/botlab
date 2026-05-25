#!/bin/bash
# Fund-Agent Sub Agent Runner
# 被 sub-agent spawn 后调用，执行完整分析流程

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$BASE_DIR/data"

cd "$BASE_DIR"

echo "=== Fund-Agent 分析报告 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. 分析持仓
echo ">>> 运行持仓分析..."
python3 "$SCRIPT_DIR/analyze.py" 2>&1 | head -50

# 2. 读取分析结果
if [ -f "$DATA_DIR/analysis-today.md" ]; then
    echo ""
    echo "=== 今日分析 ==="
    cat "$DATA_DIR/analysis-today.md"
fi

# 3. 读取邮件报告（评分卡）
if [ -f "$DATA_DIR/email-report.md" ]; then
    echo ""
    echo "=== 基金评分 ==="
    cat "$DATA_DIR/email-report.md"
fi

# 4. 风险状态
if [ -f "$DATA_DIR/risk-state.json" ]; then
    echo ""
    echo "=== 风险状态 ==="
    python3 -c "
import json
with open('$DATA_DIR/risk-state.json') as f:
    d = json.load(f)
print(json.dumps(d, indent=2, ensure_ascii=False))
" 2>/dev/null
fi

echo ""
echo "=== 分析完成 ==="
