#!/usr/bin/env python3
"""
交易引擎（Trading Engine）— Fund Agent 核心决策大脑

不是"理财建议"，是**量化交易信号**。
"""

import json
from datetime import datetime, date
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
POS_FILE = DATA_DIR / "positions.json"
RISK_FILE = DATA_DIR / "risk-state.json"
TRADE_LOG = DATA_DIR / "trade-log.json"
SIGNALS_FILE = DATA_DIR / "signals.json"


# ─── 止盈梯度（赚钱比亏钱更难！）────────────────────────────
TAKE_PROFIT_TIERS = [
    (10,  0,    "持有，趋势还在"),
    (15,  0.3,  "减仓30%，锁定部分利润"),
    (25,  0.3,  "再减30%，利润落袋"),
    (40,  1.0,  "清仓，等回调10%再接"),
]

# ─── 止损梯度 ─────────────────────────────────────────────
STOP_LOSS_TIERS = [
    (-5,   0,    "⚠️ 注意，亏损5%"),
    (-10,  0,    "⚠️ 强制提醒，审视是否止损"),
    (-15,  0.5,  "减仓50%，控制损失"),
    (-20,  1.0,  "🚨 清仓止损，不犹豫"),
]

# ─── 宏观状态 → 仓位建议 ─────────────────────────────────
MACRO_REGIMES = {
    "bull":   {"total_position": (0.7, 0.9), "desc": "牛市，积极进攻"},
    "normal": {"total_position": (0.4, 0.6), "desc": "震荡市，精选标的"},
    "bear":   {"total_position": (0.2, 0.3), "desc": "熊市，防守为主"},
}

# ─── 信号强度评估 ─────────────────────────────────────────
def evaluate_signal(pnl_ratio, trend, volume, rsi, macro_state):
    """
    综合信号强度：0-100
    """
    score = 50  # 基准分

    # 盈亏趋势
    if pnl_ratio > 10:  score += 15
    elif pnl_ratio > 5: score += 10
    elif pnl_ratio > 0: score += 5
    elif pnl_ratio < -10: score -= 20
    elif pnl_ratio < -5:  score -= 10

    # 趋势判断
    if trend == "up":    score += 15
    elif trend == "flat": score -= 5
    else:                 score -= 15

    # 量价配合
    if volume == "up":   score += 10
    elif volume == "down": score -= 10

    # RSI
    if rsi < 30:  score += 10  # 超卖反弹机会
    elif rsi > 75: score -= 10  # 超买风险

    # 宏观环境
    if macro_state == "bull":   score += 10
    elif macro_state == "bear": score -= 10

    return max(0, min(100, score))


def analyze_position(pos, macro_state="normal"):
    """单只基金交易分析"""
    name = pos["name"]
    code = pos.get("code", "")
    pnl_ratio = pos.get("holding_pct", 0) * 100
    market_value = pos.get("market_value", 0)

    # 1. 止盈检查
    for threshold, reduce_pct, action in TAKE_PROFIT_TIERS:
        if pnl_ratio >= threshold:
            reduce_amount = market_value * reduce_pct
            return {
                "type": "TAKE_PROFIT",
                "name": name,
                "code": code,
                "pnl_pct": round(pnl_ratio, 1),
                "action": action,
                "reduce_amount": round(reduce_amount, 2),
                "priority": "HIGH" if reduce_pct > 0.5 else "MEDIUM",
            }

    # 2. 止损检查
    for threshold, reduce_pct, action in STOP_LOSS_TIERS:
        if pnl_ratio <= threshold:
            reduce_amount = market_value * reduce_pct
            return {
                "type": "STOP_LOSS",
                "name": name,
                "code": code,
                "pnl_pct": round(pnl_ratio, 1),
                "action": action,
                "reduce_amount": round(reduce_amount, 2),
                "priority": "HIGH" if reduce_pct > 0.5 else "MEDIUM",
            }

    # 3. 趋势跟踪（简化版，真实环境接入 mx-data）
    trend = "up" if pnl_ratio > 0 else "down"
    signal_score = evaluate_signal(pnl_ratio, trend, "up", 50, macro_state)

    if signal_score >= 70:
        return {
            "type": "ADD",
            "name": name,
            "code": code,
            "pnl_pct": round(pnl_ratio, 1),
            "action": f"信号强度{signal_score}，可加仓",
            "suggest_amount": round(market_value * 0.3, 2),
            "priority": "MEDIUM",
        }
    elif signal_score <= 30:
        return {
            "type": "REDUCE",
            "name": name,
            "code": code,
            "pnl_pct": round(pnl_ratio, 1),
            "action": f"信号强度{signal_score}，建议减仓",
            "reduce_amount": round(market_value * 0.3, 2),
            "priority": "MEDIUM",
        }

    return {
        "type": "HOLD",
        "name": name,
        "code": code,
        "pnl_pct": round(pnl_ratio, 1),
        "action": "持有，信号中性",
        "priority": "LOW",
    }


def run_trading_session():
    """运行完整交易会话"""
    with open(POS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    positions = data["positions"]
    total_mv = data.get("total_market_value", 0)

    # 简化：默认震荡市（真实环境接 mx-search 判断）
    macro_state = "normal"

    signals = []
    for pos in positions:
        sig = analyze_position(pos, macro_state)
        signals.append(sig)

    # 按优先级排序
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    signals.sort(key=lambda x: (priority_order.get(x["priority"], 3), -abs(x["pnl_pct"])))

    # 统计
    high_count = sum(1 for s in signals if s["priority"] == "HIGH")
    medium_count = sum(1 for s in signals if s["priority"] == "MEDIUM")

    output = {
        "timestamp": datetime.now().isoformat(),
        "date": date.today().isoformat(),
        "macro_state": macro_state,
        "total_market_value": total_mv,
        "positions_count": len(positions),
        "signals_count": len(signals),
        "high_priority": high_count,
        "medium_priority": medium_count,
        "signals": signals,
    }

    # 保存信号
    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 输出
    print("=" * 60)
    print(f"📈 交易信号 | {date.today()} | 宏观: {MACRO_REGIMES[macro_state]['desc']}")
    print("=" * 60)
    print(f"总市值: ¥{total_mv:,.0f} | 持仓: {len(positions)} 只")
    print(f"高优先级信号: {high_count} | 中优先级: {medium_count}")
    print("-" * 60)

    for s in signals:
        icon = {"TAKE_PROFIT": "💰", "STOP_LOSS": "🛑", "ADD": "➕", "REDUCE": "➖", "HOLD": "📌"}
        pri_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}
        print(
            f"{icon.get(s['type'], '❓')} {pri_icon.get(s['priority'], '')} "
            f"{s['name'][:20]} | {s['pnl_pct']:+.1f}% | {s['action']}"
        )
        if s.get("reduce_amount", 0) > 0:
            print(f"   → 建议减仓: ¥{s['reduce_amount']:,.0f}")
        elif s.get("suggest_amount", 0) > 0:
            print(f"   → 建议加仓: ¥{s['suggest_amount']:,.0f}")

    print("=" * 60)
    print(f"✅ 信号已保存: {SIGNALS_FILE}")

    return output


if __name__ == "__main__":
    run_trading_session()
