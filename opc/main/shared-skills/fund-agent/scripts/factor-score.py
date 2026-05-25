#!/usr/bin/env python3
"""
基金评分卡（Factor Score Engine）
基于收益、稳定性、排名、规模、经理 5 个维度，生成 1-10 分

用法：
  python3 factor-score.py              # 所有持仓评分
  python3 factor-score.py --code 002207  # 单只基金评分
  python3 factor-score.py --rank        # 按评分排序
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
POS_FILE = DATA_DIR / "positions.json"
SCORE_FILE = DATA_DIR / "factor-scores.json"


# ─── 评分权重 ─────────────────────────────────────────────────────
WEIGHTS = {
    "收益能力": 0.30,    # 近 1/3/6 月回报
    "稳定性": 0.25,     # 最大回撤、波动率
    "排名": 0.20,       # 同类排名分位
    "规模": 0.15,       # 基金规模
    "经理": 0.10,       # 任期、历史业绩
}


def load_positions():
    with open(POS_FILE, encoding="utf-8") as f:
        return json.load(f)


def score_position(p: dict) -> dict:
    """单只基金评分"""
    name = p["name"]
    code = p.get("code", "unknown")
    category = p.get("category", "其他")

    holding_pnl = p.get("holding_pnl", 0)
    market_value = p.get("market_value", 0)
    cumulative_pnl = p.get("cumulative_pnl", 0)

    # 1. 收益能力（0-10 分）
    pnl_ratio = (holding_pnl / market_value * 100) if market_value > 0 else 0
    if pnl_ratio >= 15:
        score_return = 10
    elif pnl_ratio >= 10:
        score_return = 8
    elif pnl_ratio >= 5:
        score_return = 6
    elif pnl_ratio >= 0:
        score_return = 4
    elif pnl_ratio >= -5:
        score_return = 3
    else:
        score_return = 1

    # 2. 稳定性（简化：基于波动判断）
    # 有真实数据后用 mx-data 补充，现在用持仓盈亏趋势估算
    if abs(pnl_ratio) <= 5:
        score_stability = 8
    elif abs(pnl_ratio) <= 10:
        score_stability = 6
    elif abs(pnl_ratio) <= 20:
        score_stability = 4
    else:
        score_stability = 2

    # 3. 排名（基于今年以来排名估算）
    # 赚钱的默认中上，亏钱的默认中下
    if pnl_ratio > 0:
        score_rank = 7
    else:
        score_rank = 4

    # 4. 规模（按持仓金额估算，大仓位=信任度高）
    if market_value >= 3000:
        score_size = 8
    elif market_value >= 1500:
        score_size = 6
    elif market_value >= 800:
        score_size = 5
    elif market_value >= 300:
        score_size = 3
    else:
        score_size = 1

    # 5. 经理（暂用固定分，后续可接入 mx-data 查经理信息）
    score_manager = 5

    # 加权总分
    total = (
        score_return * WEIGHTS["收益能力"] +
        score_stability * WEIGHTS["稳定性"] +
        score_rank * WEIGHTS["排名"] +
        score_size * WEIGHTS["规模"] +
        score_manager * WEIGHTS["经理"]
    )

    # 1-10 分（保留一位小数）
    total = round(max(1, min(10, total)), 1)

    # 评级
    if total >= 8:
        grade = "A+"
        action = "✅ 可加仓"
    elif total >= 6.5:
        grade = "B+"
        action = "⚠️ 持有观望"
    elif total >= 5:
        grade = "C"
        action = "🟡 考虑减仓"
    elif total >= 3.5:
        grade = "D"
        action = "🔴 建议清仓"
    else:
        grade = "F"
        action = "🔴 立即清仓"

    return {
        "name": name,
        "code": code,
        "category": category,
        "market_value": market_value,
        "holding_pnl": holding_pnl,
        "pnl_ratio": round(pnl_ratio, 2),
        "scores": {
            "收益能力": score_return,
            "稳定性": score_stability,
            "排名": score_rank,
            "规模": score_size,
            "经理": score_manager,
        },
        "total_score": total,
        "grade": grade,
        "action": action,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="基金评分卡")
    parser.add_argument("--code", help="单只基金代码")
    parser.add_argument("--rank", action="store_true", help="按评分排序")
    args = parser.parse_args()

    data = load_positions()
    positions = data["positions"]

    if args.code:
        # 单只评分
        p = next((x for x in positions if x.get("code") == args.code), None)
        if not p:
            print(f"❌ 找不到代码 {args.code}")
            return
        result = score_position(p)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 全部评分
        scores = [score_position(p) for p in positions]

        if args.rank:
            scores.sort(key=lambda x: x["total_score"], reverse=True)

        # 输出表格
        print(f"{'基金':<25} {'代码':<8} {'评分':>5} {'评级':>4} {'建议':<15} {'盈亏%':>7}")
        print("=" * 75)
        for s in scores:
            print(
                f"{s['name'][:22]:<25} {s['code']:<8} "
                f"{s['total_score']:>5.1f} {s['grade']:>4} "
                f"{s['action'][:12]:<15} {s['pnl_ratio']:>+6.1f}%"
            )

        # 统计
        avg_score = sum(s["total_score"] for s in scores) / len(scores)
        a_plus = sum(1 for s in scores if s["grade"] == "A+")
        b_plus = sum(1 for s in scores if s["grade"] == "B+")
        c_or_below = sum(1 for s in scores if s["grade"] in ("C", "D", "F"))

        print("=" * 75)
        print(f"平均评分: {avg_score:.1f} | A+: {a_plus} | B+: {b_plus} | C及以下: {c_or_below}")

        # 保存
        output = {
            "update_time": datetime.now().isoformat(),
            "scores": scores,
            "average_score": round(avg_score, 1),
        }
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 评分已保存: {SCORE_FILE}")


if __name__ == "__main__":
    main()