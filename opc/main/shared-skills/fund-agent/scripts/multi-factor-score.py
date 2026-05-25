#!/usr/bin/env python3
"""
多因子评分模型（Multi-Factor Score Engine）

真正的量化评分，不是看盈亏百分比。

因子：
  - 动量（Momentum）：近1/3/6月涨跌幅趋势
  - 稳定性（Stability）：最大回撤、波动率
  - 排名（Ranking）：同类排名分位
  - 规模（Size）：基金规模，太小有清盘风险
  - 经理（Manager）：任期、历史业绩
  - 板块强度（Sector Strength）：所属板块资金流向

输出：0-100 分，不是 1-10 分。
"""

import json
import subprocess
import os
import sys
from datetime import datetime, date
from pathlib import Path
import math

SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
POS_FILE = DATA_DIR / "positions.json"
SCORE_FILE = DATA_DIR / "multi-factor-scores.json"
MX_DATA_SCRIPT = Path("/root/clawd/shared-skills/mx-data/scripts/mx_data.py")

# ─── 因子权重 ─────────────────────────────────────────────────────
FACTOR_WEIGHTS = {
    "momentum": 0.25,      # 动量因子
    "stability": 0.20,     # 稳定性因子
    "ranking": 0.15,       # 排名因子
    "size": 0.10,          # 规模因子
    "manager": 0.10,       # 经理因子
    "sector_strength": 0.20,  # 板块强度因子
}

# ─── 因子计算函数 ───────────────────────────────────────────────────

def calc_momentum_score(return_1m, return_3m, return_6m):
    """
    动量因子评分（0-100）

    核心：不是看赚了多少，是看趋势是否持续。
    """
    score = 50  # 基准分

    # 短期动量（1个月）
    if return_1m > 5:   score += 15
    elif return_1m > 2: score += 8
    elif return_1m > 0: score += 3
    elif return_1m < -5: score -= 15
    elif return_1m < -2: score -= 8

    # 中期动量（3个月）—— 权重更高
    if return_3m > 10:  score += 20
    elif return_3m > 5: score += 12
    elif return_3m > 0: score += 5
    elif return_3m < -10: score -= 20
    elif return_3m < -5: score -= 12

    # 长期动量（6个月）—— 判断趋势持续性
    if return_6m > 15:  score += 15
    elif return_6m > 8: score += 8
    elif return_6m > 0: score += 3
    elif return_6m < -15: score -= 15

    # 动量一致性加分（三段时间同向）
    if return_1m > 0 and return_3m > 0 and return_6m > 0:
        score += 10  # 持续上涨，加分
    elif return_1m < 0 and return_3m < 0 and return_6m < 0:
        score -= 10  # 持续下跌，减分

    return max(0, min(100, score))


def calc_stability_score(max_drawdown, volatility):
    """
    稳定性因子评分（0-100）

    核心：回撤越小越好，波动率适中最好（太小没弹性，太大风险高）
    """
    score = 50

    # 最大回撤（越小越好）
    if max_drawdown < -5:   score += 20  # 回撤小于5%，非常稳
    elif max_drawdown < -10: score += 10
    elif max_drawdown < -15: score += 0
    elif max_drawdown < -20: score -= 10
    else:                    score -= 20  # 回撤超过20%，危险

    # 波动率（适中最好，15-25%区间）
    if 10 <= volatility <= 20:
        score += 10  # 波动适中，有弹性但不疯
    elif volatility < 10:
        score -= 5   # 太稳，可能是货币基金，没进攻性
    elif volatility > 30:
        score -= 15  # 波动太大，风险高

    return max(0, min(100, score))


def calc_ranking_score(rank_percentile):
    """
    排名因子评分（0-100）

    rank_percentile: 同类排名分位（0-100，数值越小越好）
    """
    # 排名分位转评分：前10%得90分，后10%得10分
    if rank_percentile <= 10:  return 90
    elif rank_percentile <= 25: return 75
    elif rank_percentile <= 50: return 50
    elif rank_percentile <= 75: return 25
    else:                       return 10


def calc_size_score(aum):
    """
    规模因子评分（0-100）

    aum: 基金规模（亿元）

    太小（<2亿）有清盘风险
    太大（>100亿）可能打新受限
    适中（2-50亿）最好
    """
    if aum < 0.5:  return 10   # 规模太小，清盘风险高
    elif aum < 2:  return 30   # 规模偏小，有风险
    elif aum < 10: return 70   # 规模适中，好
    elif aum < 50: return 80   # 规模适中偏大，好
    elif aum < 100: return 60  # 规模较大，打新受限
    else:          return 50   # 规模太大，灵活度下降


def calc_manager_score(tenure_years, historical_return):
    """
    经理因子评分（0-100）

    tenure_years: 任期年数
    historical_return: 历史年化回报（%）
    """
    score = 50

    # 任期（越长越稳）
    if tenure_years >= 5:  score += 15
    elif tenure_years >= 3: score += 8
    elif tenure_years >= 1: score += 3
    else:                   score -= 10  # 新经理，不确定

    # 历史业绩
    if historical_return > 15:  score += 15
    elif historical_return > 10: score += 8
    elif historical_return > 5:  score += 3
    elif historical_return < 0:  score -= 15

    return max(0, min(100, score))


def calc_sector_strength_score(category, sector_data):
    """
    板块强度因子评分（0-100）

    sector_data: 板块资金流向数据
    {
      "新能源": {"flow": 50亿, "trend": "up"},
      "科技": {"flow": -20亿, "trend": "down"},
      ...
    }
    """
    score = 50

    if category in sector_data:
        flow = sector_data[category].get("flow", 0)
        trend = sector_data[category].get("trend", "neutral")

        # 资金流入加分
        if flow > 30:  score += 20
        elif flow > 10: score += 10
        elif flow > 0:  score += 5
        elif flow < -30: score -= 20
        elif flow < -10: score -= 10

        # 趋势加分
        if trend == "up":   score += 10
        elif trend == "down": score -= 10

    return max(0, min(100, score))


# ─── 综合评分 ──────────────────────────────────────────────────────

def calc_total_score(factors):
    """
    综合评分（0-100）

    加权求和，不是简单平均。
    """
    total = 0
    for factor_name, weight in FACTOR_WEIGHTS.items():
        score = factors.get(factor_name, 50)
        total += score * weight
    return round(total, 1)


def get_grade(total_score):
    """
    评级（S/A/B/C/D/F）

    不是简单的 8分=A+，而是：
    - S: 90+（顶级，可重仓）
    - A: 75-89（优质，可加仓）
    - B: 60-74（中等，持有）
    - C: 45-59（较弱，观察）
    - D: 30-44（差，考虑减仓）
    - F: <30（垃圾，清仓）
    """
    if total_score >= 90: return "S"
    elif total_score >= 75: return "A"
    elif total_score >= 60: return "B"
    elif total_score >= 45: return "C"
    elif total_score >= 30: return "D"
    else: return "F"


def get_action(total_score, grade):
    """
    操作建议

    基于 评分 + 评级，不是基于 盈亏百分比。
    """
    if grade == "S":
        return "✅ 可重仓（板块强+动量强+稳定）"
    elif grade == "A":
        return "✅ 可加仓（趋势好，质量优）"
    elif grade == "B":
        return "⚠️ 持有观望（信号中性）"
    elif grade == "C":
        return "🟡 观察减仓（趋势不明朗）"
    elif grade == "D":
        return "🔴 建议减仓（质量差）"
    else:
        return "🚨 强制清仓（垃圾基金）"


# ─── 数据获取（真实环境接 mx-data）────────────────────────────────

def fetch_fund_data_from_mx(code):
    """
    从 mx-data 获取基金真实数据

    返回：
    {
      "return_1m": 近1月涨跌幅,
      "return_3m": 近3月涨跌幅,
      "return_6m": 近6月涨跌幅,
      "max_drawdown": 最大回撤,
      "volatility": 波动率,
      "rank_percentile": 同类排名分位,
      "aum": 基金规模(亿),
      "tenure_years": 经理任期,
      "historical_return": 经理历史回报,
    }
    """
    # 目前用模拟数据，真实环境接 mx-data
    # 这里返回一个默认值，让评分能跑
    return {
        "return_1m": 0,
        "return_3m": 0,
        "return_6m": 0,
        "max_drawdown": -10,
        "volatility": 18,
        "rank_percentile": 50,
        "aum": 5,
        "tenure_years": 2,
        "historical_return": 5,
    }


# ─── 主流程 ────────────────────────────────────────────────────────

def score_fund(pos, sector_data=None):
    """单只基金多因子评分"""
    name = pos["name"]
    code = pos.get("code", "")
    category = pos.get("category", "其他")

    # 获取基金数据（真实环境接 mx-data）
    fund_data = fetch_fund_data_from_mx(code)

    # 用持仓数据补充（当前盈亏）
    holding_pnl = pos.get("holding_pnl", 0)
    market_value = pos.get("market_value", 0)
    pnl_ratio = (holding_pnl / market_value * 100) if market_value > 0 else 0

    # 计算各因子评分
    factors = {
        "momentum": calc_momentum_score(
            fund_data["return_1m"],
            fund_data["return_3m"],
            fund_data["return_6m"]
        ),
        "stability": calc_stability_score(
            fund_data["max_drawdown"],
            fund_data["volatility"]
        ),
        "ranking": calc_ranking_score(fund_data["rank_percentile"]),
        "size": calc_size_score(fund_data["aum"]),
        "manager": calc_manager_score(
            fund_data["tenure_years"],
            fund_data["historical_return"]
        ),
    }

    # 板块强度（需要外部数据）
    if sector_data:
        factors["sector_strength"] = calc_sector_strength_score(category, sector_data)
    else:
        factors["sector_strength"] = 50  # 默认中性

    # 综合评分
    total_score = calc_total_score(factors)
    grade = get_grade(total_score)
    action = get_action(total_score, grade)

    return {
        "name": name,
        "code": code,
        "category": category,
        "market_value": market_value,
        "holding_pnl": holding_pnl,
        "pnl_ratio": round(pnl_ratio, 2),
        "factors": factors,
        "total_score": total_score,
        "grade": grade,
        "action": action,
        "timestamp": datetime.now().isoformat(),
    }


def run_multi_factor_scoring():
    """运行多因子评分"""
    with open(POS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    positions = data["positions"]
    total_mv = data.get("total_market_value", 0)

    # 板块数据（真实环境接 mx-data 板块资金流）
    # 这里用模拟数据
    sector_data = {
        "新能源": {"flow": 20, "trend": "up"},
        "科技": {"flow": -15, "trend": "down"},
        "贵金属": {"flow": 5, "trend": "neutral"},
        "美股": {"flow": 10, "trend": "up"},
        "能源": {"flow": -5, "trend": "down"},
        "其他": {"flow": 0, "trend": "neutral"},
    }

    scores = [score_fund(pos, sector_data) for pos in positions]
    scores.sort(key=lambda x: x["total_score"], reverse=True)

    # 统计
    avg_score = sum(s["total_score"] for s in scores) / len(scores)
    grade_counts = {}
    for s in scores:
        g = s["grade"]
        grade_counts[g] = grade_counts.get(g, 0) + 1

    # 输出
    print("=" * 70)
    print(f"📊 多因子评分 | {date.today()}")
    print("=" * 70)
    print(f"{'基金':<25} {'代码':<10} {'评分':>6} {'评级':>4} {'建议':<20}")
    print("-" * 70)
    for s in scores:
        print(
            f"{s['name'][:22]:<25} {s['code']:<10} "
            f"{s['total_score']:>6.1f} {s['grade']:>4} {s['action'][:17]:<20}"
        )

    print("=" * 70)
    print(f"平均评分: {avg_score:.1f} | S:{grade_counts.get('S',0)} A:{grade_counts.get('A',0)} B:{grade_counts.get('B',0)} C:{grade_counts.get('C',0)} D:{grade_counts.get('D',0)} F:{grade_counts.get('F',0)}")

    # 保存
    output = {
        "timestamp": datetime.now().isoformat(),
        "date": str(date.today()),
        "positions_count": len(positions),
        "total_market_value": total_mv,
        "average_score": round(avg_score, 1),
        "grade_distribution": grade_counts,
        "scores": scores,
        "factor_weights": FACTOR_WEIGHTS,
    }

    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 评分已保存: {SCORE_FILE}")

    return output


if __name__ == "__main__":
    run_multi_factor_scoring()