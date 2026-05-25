#!/usr/bin/env python3
"""
fund-agent 分析脚本 v5 — 主 AkShare，异常用 MX 备份

路由策略：
  主: AkShare (代码查询) → 失败 → 备: MX API (全称+"最新价")

优点：
- AkShare 免费、稳定、并发快，覆盖所有基金
- MX API 作为兜底，确保数据不丢
- 无需 API Key（AkShare），MX 仅异常时消耗额度

用法：
  python3 analyze.py                    # 分析全部持仓
  python3 analyze.py --code 018826      # 单只基金
  python3 analyze.py --output report.md # 指定输出
"""

import json
import sys
import os
import time
from datetime import datetime, date
from pathlib import Path

# 配置
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
POS_FILE = DATA_DIR / "positions.json"
RISK_FILE = DATA_DIR / "risk-state.json"
ANALYSIS_FILE = DATA_DIR / "analysis-today.md"
MX_APIKEY = os.environ.get("MX_APIKEY", "")

# === AkShare ===
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

# === MX Data ===
MX_DATA_SCRIPT = None  # mx-data not configured
HAS_MX = False


def load_positions():
    with open(POS_FILE, encoding="utf-8") as f:
        return json.load(f)


# ─── AkShare 查询（主） ───────────────────────────────────

def query_akshare(code: str, name: str) -> dict:
    """用 AkShare 查基金净值（开放式基金，代码查询）"""
    if not HAS_AKSHARE:
        return {"error": "akshare 未安装"}

    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            return {"error": "无净值数据"}

        latest = df.iloc[-1]
        recent = df.tail(5)

        return {
            "source": "akshare",
            "单位净值": float(latest["单位净值"]),
            "日增长率": float(latest["日增长率"]) if "日增长率" in latest else 0.0,
            "日期": str(latest["净值日期"]),
            "近5日": [
                {"日期": str(r["净值日期"]), "净值": float(r["单位净值"])}
                for _, r in recent.iterrows()
            ],
        }
    except Exception as e:
        return {"error": str(e)[:50]}


# ─── MX API 查询（备） ────────────────────────────────────

def query_mx(mx, code: str, name: str) -> dict:
    """用 MX API 查基金行情（必须用'最新价'关键字）"""
    if not mx:
        return {"error": "MXData 不可用"}

    try:
        result = mx.query(f"{name} 最新价")
        status = result.get("status")
        if status != 0:
            return {"error": f"API {status}"}

        data = result.get("data", {}) or {}
        inner = data.get("data", {}) or {}
        search = inner.get("searchDataResultDTO", {}) or {}
        dto_list = search.get("dataTableDTOList", []) or []

        if not dto_list:
            return {"error": "无数据"}

        first = dto_list[0]
        table = first.get("table", {})
        name_map = first.get("nameMap", {})
        indicator_order = first.get("indicatorOrder", [])

        nav_data = {"source": "mx", "entity": first.get("entityName", "")}

        for key in indicator_order:
            if key == "headName":
                continue
            values = table.get(key, [])
            label = name_map.get(str(key), name_map.get(int(key) if str(key).isdigit() else key, str(key)))
            val = values[0] if isinstance(values, list) and len(values) > 0 else ""
            nav_data[label] = val

        dates = table.get("headName", [])
        if dates:
            nav_data["日期"] = dates[0]

        return nav_data

    except Exception as e:
        return {"error": str(e)[:40]}


# ─── 路由器：主 AkShare → 备 MX ─────────────────────────

def query_fund_nav(mx, code: str, name: str) -> dict:
    """路由器：AkShare 优先，失败用 MX 补"""

    # 主：AkShare
    result = query_akshare(code, name)
    if "error" not in result:
        return result

    # 备：MX API
    mx_result = query_mx(mx, code, name)
    if "error" not in mx_result:
        return mx_result

    # 两个都失败
    return {
        "error": f"AkShare:{result['error'][:20]} | MX:{mx_result['error'][:20]}"
    }


# ─── 分析逻辑 ─────────────────────────────────────────────

def analyze_positions(positions_data: dict) -> dict:
    positions = positions_data["positions"]
    results = []

    print(f"📊 分析 {len(positions)} 只基金（AkShare→MX 路由）...")

    # 初始化 MX（仅作为 fallback）
    mx = None
    if HAS_MX:
        try:
            mx = MXData(api_key=MX_APIKEY)
        except Exception as e:
            print(f"⚠️ MX 初始化失败（不影响主路径）: {e}")

    ak_ok = 0
    mx_ok = 0
    fail = 0

    for i, p in enumerate(positions):
        code = p.get("code", "")
        name = p["name"]

        nav_data = query_fund_nav(mx, code, name)

        # 统计数据源
        src = nav_data.get("source", "")
        if "error" not in nav_data:
            if src == "akshare":
                ak_ok += 1
            elif src == "mx":
                mx_ok += 1
        else:
            fail += 1

        results.append({
            "name": p["name"],
            "code": p.get("code", ""),
            "market_value": p.get("market_value", 0),
            "holding_pnl": p.get("holding_pnl", 0),
            "holding_pct": p.get("holding_pct", 0),
            "cumulative_pnl": p.get("cumulative_pnl", 0),
            "pct_of_portfolio": p.get("pct_of_portfolio", 0),
            "category": p.get("category", ""),
            "nav_data": nav_data,
        })

        # AkShare 并发安全，不需要延时
        # MX fallback 时加 1s 避免限频
        if "error" in nav_data or src == "mx":
            if i < len(positions) - 1:
                time.sleep(1)

    results.sort(key=lambda x: x.get("market_value", 0), reverse=True)

    print(f"📊 数据源统计: AkShare={ak_ok} | MX={mx_ok} | 失败={fail}")

    return {
        "positions": results,
        "total_market_value": positions_data.get("total_market_value", 0),
        "total_cumulative_loss": positions_data.get("total_cumulative_loss", 0),
        "risk_level": positions_data.get("risk_level", "unknown"),
        "risk_score": positions_data.get("risk_score", 0),
        "analysis_time": datetime.now().isoformat(),
        "stats": {"akshare": ak_ok, "mx": mx_ok, "fail": fail},
    }


# ─── 报告生成 ─────────────────────────────────────────────

def generate_report(analysis: dict) -> str:
    today = date.today().strftime("%Y-%m-%d")
    stats = analysis.get("stats", {})

    report = f"""## 📊 基金持仓分析 ({today})

### 总览
| 总市值 | 累计盈亏 | 风险分 | 持仓数 |
|--------|----------|--------|--------|
| ¥{analysis['total_market_value']:,.0f} | ¥{analysis['total_cumulative_loss']:+,.0f} | {analysis['risk_score']} | {len(analysis['positions'])} |

> 数据源: AkShare={stats.get('akshare', 0)} | MX备份={stats.get('mx', 0)} | 失败={stats.get('fail', 0)}

### 板块分布
"""

    categories = {}
    for p in analysis["positions"]:
        cat = p.get("category", "其他")
        if cat not in categories:
            categories[cat] = {"市值": 0, "盈亏": 0, "holding_pct": 0}
        categories[cat]["市值"] += p.get("market_value", 0)
        categories[cat]["盈亏"] += p.get("holding_pnl", 0)
        categories[cat]["holding_pct"] += p.get("holding_pct", 0)

    report += "| 板块 | 市值 | 持仓盈亏 | 盈亏率 |\n|------|------|----------|--------|\n"
    for cat, data in sorted(categories.items(), key=lambda x: x[1]["市值"], reverse=True):
        pct = data["holding_pct"]
        report += f"| {cat} | ¥{data['市值']:,.0f} | ¥{data['盈亏']:+,.0f} | {pct:+.1f}% |\n"

    report += "\n### 持仓详情（按市值排序）\n"
    report += "| 基金 | 代码 | 市值 | 持仓盈亏 | 净值/行情 | 涨跌 | 来源 |\n"
    report += "|------|------|------|----------|----------|------|------|\n"

    for p in analysis["positions"]:
        nav = p.get("nav_data", {})
        error = nav.get("error", "")
        src = nav.get("source", "")
        if error:
            净值 = f"⚠️ {error[:18]}"
            涨跌 = "-"
            src_label = "-"
        else:
            净值_val = nav.get("单位净值", nav.get("最新价", "-"))
            涨跌_val = nav.get("日增长率", nav.get("涨跌幅", ""))
            净值 = f"{净值_val:.4f}" if isinstance(净值_val, (int, float)) else f"{净值_val}"
            涨跌 = f"{涨跌_val:+.2f}%" if isinstance(涨跌_val, (int, float)) else f"{涨跌_val}" if 涨跌_val else "-"
            src_label = "AK" if src == "akshare" else "MX"

        report += f"| {p['name'][:20]} | {p.get('code', '-')} | ¥{p['market_value']:,.0f} | {p['holding_pct']:+.1f}% | {净值} | {涨跌} | {src_label} |\n"

    # 止损预警
    report += "\n### 🔴 止损监控\n"
    warn_found = False
    for p in analysis["positions"]:
        pct = p.get("holding_pct", 0)
        if pct < -5:
            report += f"- ⚠️ **{p['name']}**: 持仓 {pct:+.1f}%，距止损线 {-10 - pct:.1f}%\n"
            warn_found = True
    if not warn_found:
        report += "- ✅ 无触发止损预警（-10% 预警线）\n"

    # 止盈建议
    report += "\n### 🟢 止盈建议（持仓盈亏 > +5%）\n"
    profit_found = False
    for p in analysis["positions"]:
        pct = p.get("holding_pct", 0)
        if pct > 10:
            report += f"- 💰 **{p['name']}**: 持仓 {pct:+.1f}%，建议止盈 1/3 或 1/2\n"
            profit_found = True
        elif pct > 5:
            report += f"- 🟡 **{p['name']}**: 持仓 {pct:+.1f}%，可考虑减仓 1/4 锁定利润\n"
            profit_found = True
    if not profit_found:
        report += "- 暂无盈利超 5% 的持仓，全部持有观望\n"

    # 风险提示
    report += "\n### ⚠️ 风险提示\n"
    if analysis["risk_score"] > 70:
        report += f"- 🔴 风险分 {analysis['risk_score']} > 70，建议控制总仓位，不再新增持仓\n"
    if analysis["total_cumulative_loss"] < -1000:
        report += f"- 🔴 累计亏损 ¥{abs(analysis['total_cumulative_loss']):,.0f}，审视弱势基金去留\n"
    for p in analysis["positions"]:
        if p.get("pct_of_portfolio", 0) > 10:
            report += f"- 🟡 {p['name']} 占总资产 {p['pct_of_portfolio']:.1f}%，超 10% 上限建议减持至 10% 以内\n"

    report += f"\n---\n分析时间: {analysis['analysis_time']}\n"
    return report


def save_report(report: str, output_path: Path = None):
    path = output_path or ANALYSIS_FILE
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 报告保存: {path}")


def update_risk_state(analysis: dict):
    risk_data = {
        "risk_score": analysis["risk_score"],
        "risk_level": analysis["risk_level"],
        "total_market_value": analysis["total_market_value"],
        "total_cumulative_loss": analysis["total_cumulative_loss"],
        "last_update": analysis["analysis_time"],
        "positions_count": len(analysis["positions"])
    }
    with open(RISK_FILE, "w", encoding="utf-8") as f:
        json.dump(risk_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 风险状态: {RISK_FILE}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="fund-agent 分析")
    parser.add_argument("--code", default=None, help="单只基金代码")
    parser.add_argument("--output", default=None, help="输出路径")
    args = parser.parse_args()

    print("🚀 fund-agent 分析开始（AkShare→MX 路由）...")

    positions = load_positions()
    print(f"✅ 持仓: {len(positions['positions'])} 只")

    if args.code:
        p = next((x for x in positions["positions"] if x.get("code") == args.code), None)
        if not p:
            print(f"❌ 找不到 {args.code}")
            return
        mx = MXData(api_key=MX_APIKEY) if HAS_MX else None
        nav = query_fund_nav(mx, args.code, p["name"])
        print(json.dumps(nav, ensure_ascii=False, indent=2))
        return

    analysis = analyze_positions(positions)
    report = generate_report(analysis)
    save_report(report, Path(args.output) if args.output else None)
    update_risk_state(analysis)

    print("🎉 分析完成!")
    return report


if __name__ == "__main__":
    main()
