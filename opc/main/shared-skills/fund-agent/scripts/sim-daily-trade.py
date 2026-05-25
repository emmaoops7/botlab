#!/usr/bin/env python3
"""
每日模拟交易 — 基金模拟盘闭环

流程：
1. market-news.py   → MX API 新闻/行情（新闻仍走 MX，失败必须标注）
2. factor-score.py  → 单因子评分（持仓评分，基于 positions.json 分析真实持仓）
3. multi-factor-score.py → 多因子评分（同上，分析真实持仓）
4. event-impact.py  → 事件/政策影响
5. AkShare          → 主行情/NAV 数据源；MX-MONI 仅作股票模拟仓 fallback
6. sim-trade.py     → 模拟交易/不交易记录写入 sim-trades.json

硬规则：
- 模拟仓审计权威 = data/sim-trades.json；行情主源 = AkShare。
- MX-MONI 只能作为股票模拟仓 fallback；不可再因 MX-MONI 挂掉阻断日报。
- positions.json 是用户真实基金持仓，仅供真实持仓分析，不混入模拟仓日报。
- 交易日不交易必须写 hold 记录 + 理由。
- 数据源失败必须写 fail 状态 + 原因，禁止编造。
"""

import sys
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
SCRIPTS_DIR = SKILL_DIR / "scripts"

SIM_TRADE_LOG = DATA_DIR / "sim-trades.json"

REPORT_FILE = DATA_DIR / "sim-daily-report.md"

import importlib.util

_market_data_path = SCRIPTS_DIR / "sim-market-data.py"
_spec = importlib.util.spec_from_file_location("sim_market_data", _market_data_path)
sim_market_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sim_market_data)

MX_APIKEY = os.environ.get("MX_APIKEY", "")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def run_script(script_name, args=None, timeout=60):
    """运行同目录下的脚本，返回 stdout 文本"""
    sp = SCRIPTS_DIR / script_name
    if not sp.exists():
        return {"error": f"{script_name} 不存在"}
    cmd = [sys.executable, str(sp)]
    if args:
        cmd.extend(args)
    try:
        env = {**os.environ, "MX_APIKEY": MX_APIKEY}
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "rc": result.returncode,
            "error": None if result.returncode == 0 else f"rc={result.returncode}",
        }
    except subprocess.TimeoutExpired:
        return {"error": "超时", "rc": 124}
    except Exception as e:
        return {"error": str(e), "rc": 1}


def load_trades():
    if SIM_TRADE_LOG.exists():
        try:
            data = json.load(open(SIM_TRADE_LOG, encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def fetch_mx_moni_positions():
    """MX-MONI fallback：能用则补充股票模拟仓状态，失败不阻断日报。"""
    pos_info = sim_market_data.fetch_mx_moni_positions()
    if pos_info:
        log(f"✅ MX-MONI fallback posList: {len(pos_info.get('posList', []))} 只持仓")
        return pos_info
    log("⚠️ MX-MONI fallback 不可用，改用本地 sim-trades.json 维护模拟仓")
    return None


def write_hold_record(pos_info, factor_output=None, multi_factor_output=None, event_output=None):
    """写 hold 记录：基于 MX-MONI 模拟仓真实数据源，不碰用户实盘。"""
    trades = load_trades()

    # 检查今天是否已有 hold/buy/sell/fail 记录
    today = datetime.now().strftime("%Y-%m-%d")
    today_actions = [t for t in trades if t.get("time", "").startswith(today)]
    if today_actions:
        has_action = any(t.get("action") in ("buy", "sell", "hold", "daily_fail") for t in today_actions)
        if has_action:
            log(f"今日已有 {len(today_actions)} 条记录，跳过重复 hold")
            return

    # 从 MX-MONI API 的真实 posList 分析信号
    pos_list = pos_info.get("posList", []) if pos_info else []
    total_profit = pos_info.get("totalProfit", 0) if pos_info else 0
    total_assets = pos_info.get("totalAssets", 0) if pos_info else 0

    # 逐只检查盈亏信号
    signal_items = []
    for p in pos_list:
        name = p.get("secName", "?")
        code = p.get("secCode", "?")
        profit = float(p.get("profit", 0) or 0)
        profit_pct = float(p.get("profitPct", 0) or 0)
        value = float(p.get("value", 0) or 0)

        if profit <= -200:
            signal_items.append(f"🛑 {name}({code}) 亏损 ¥{profit:.1f}({profit_pct:+.2f}%)，建议减仓")
        elif profit <= -100:
            signal_items.append(f"⚠️ {name}({code}) 亏损 ¥{profit:.1f}({profit_pct:+.2f}%)，观察")
        elif profit >= 300:
            signal_items.append(f"✅ {name}({code}) 盈利 ¥{profit:.1f}({profit_pct:+.2f}%)，可考虑止盈")
        else:
            signal_items.append(f"📌 {name}({code}) ¥{value:.0f} {profit_pct:+.2f}%，持有关注")

    if signal_items:
        reason = "MX-MONI 模拟仓状态（各股盈亏）:\n" + "\n".join(signal_items)
        reason += f"\n\n总收益: ¥{total_profit:+.2f} | 总资产: ¥{total_assets:,.2f}"
    elif factor_output:
        reason = "所有持仓评分中性，无强买入/卖出信号"
    else:
        reason = "评分/信号流程正常，当前无触发信号，策略维持"

    item = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "hold",
        "source": "sim-daily-trade.py",
        "data_source": "AkShare primary + local sim-trades.json ledger + MX-MONI fallback",
        "reason": reason,
        "context": {
            "factor_score_rc": factor_output.get("rc") if factor_output else None,
            "multi_factor_rc": multi_factor_output.get("rc") if multi_factor_output else None,
            "event_rc": event_output.get("rc") if event_output else None,
            "mx_moni_posCount": len(pos_list),
            "total_profit": round(total_profit, 2),
        },
    }
    trades.append(item)
    with open(SIM_TRADE_LOG, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    log(f"📌 hold 已记录: {reason[:120]}")


def write_fail_record(mx_status, stage, reason_detail=""):
    """MX 失败必须写 fail 记录，禁止编造数据。"""
    trades = load_trades()
    today = datetime.now().strftime("%Y-%m-%d")
    today_actions = [t for t in trades if t.get("time", "").startswith(today)]

    item = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "daily_fail",
        "source": "sim-daily-trade.py",
        "reason": f"MX {mx_status} — {stage} 阶段失败" + (f" ({reason_detail})" if reason_detail else ""),
        "context": {
            "mx_apikey_configured": bool(MX_APIKEY),
            "stage": stage,
        },
    }
    trades.append(item)
    with open(SIM_TRADE_LOG, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    log(f"⚠️ fail 已记录: {item['reason']}")


def save_report(sections):
    """保存每日模拟报告到 data/sim-daily-report.md"""
    lines = []
    lines.append(f"# 模拟盘每日报告 — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    for title, content in sections:
        lines.append(f"## {title}\n")
        lines.append(content.strip() + "\n")
    text = "\n".join(lines)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    log(f"✅ 报告已保存: {REPORT_FILE}")


def daily_run():
    """主流程：按序执行各环节"""
    log("=" * 50)
    log("模拟盘每日交易 — 启动")

    # 0. MX API 可用性检查
    if not MX_APIKEY:
        log("❌ MX_APIKEY 未配置")
        write_fail_record("MX_APIKEY 未配置", "precheck")
        save_report([("状态", "❌ MX_APIKEY 未配置，每日流程阻断")])
        return 2

    sections = []
    all_ok = True

    # Step 1: market-news.py — MX 新闻/行情
    log("\n[Step 1] market-news.py — MX 新闻/行情")
    news_out = run_script("market-news.py", timeout=60)
    if news_out.get("error"):
        log(f"❌ market-news.py 失败: {news_out['error']}")
        sections.append(("市场新闻/行情", f"❌ MX API 调用失败: {news_out['error']}\n\n> MX_QUERY: 指数行情+持仓板块新闻\n> 状态: 失败，不编造"))
        all_ok = False
    else:
        log(f"✅ market-news.py 完成")
        sections.append(("市场新闻/行情", news_out.get("stdout", "无输出")[:1500]))

    # Step 2: factor-score.py — 单因子评分
    log("\n[Step 2] factor-score.py — 单因子评分")
    factor_out = run_script("factor-score.py", ["--rank"], timeout=60)
    if factor_out.get("error"):
        log(f"❌ factor-score.py 失败: {factor_out['error']}")
        sections.append(("单因子评分", f"❌ 评分失败: {factor_out['error']}"))
        all_ok = False
    else:
        log(f"✅ factor-score.py 完成")
        sections.append(("单因子评分", factor_out.get("stdout", "无输出")[:1500]))

    # Step 3: multi-factor-score.py — 多因子评分
    log("\n[Step 3] multi-factor-score.py — 多因子评分")
    multi_factor_out = run_script("multi-factor-score.py", timeout=60)
    if multi_factor_out.get("error"):
        log(f"❌ multi-factor-score.py 失败: {multi_factor_out['error']}")
        sections.append(("多因子评分", f"❌ 评分失败: {multi_factor_out['error']}"))
        all_ok = False
    else:
        log(f"✅ multi-factor-score.py 完成")
        sections.append(("多因子评分", multi_factor_out.get("stdout", "无输出")[:1500]))

    # Step 4: event-impact.py — 事件/政策影响
    log("\n[Step 4] event-impact.py — 事件影响")
    event_out = run_script("event-impact.py", ["--trump"], timeout=80)
    if event_out.get("error"):
        log(f"❌ event-impact.py 失败: {event_out['error']}")
        sections.append(("事件/政策影响", f"❌ 失败: {event_out['error']}\nMX 未能返回新闻，不编造影响分析"))
        all_ok = False
    else:
        log(f"✅ event-impact.py 完成")
        sections.append(("事件/政策影响", event_out.get("stdout", "无输出")[:1500]))

    # Step 5: AkShare 主行情 + MX-MONI fallback
    log("\n[Step 5] AkShare — 主行情；MX-MONI — fallback")
    pos_info = fetch_mx_moni_positions()
    if pos_info:
        total_assets = pos_info.get("totalAssets", 0)
        avail_balance = pos_info.get("availBalance", 0)
        total_profit = pos_info.get("totalProfit", 0)
        pos_list = pos_info.get("posList", [])
        ak_quotes = sim_market_data.ak_stock_quotes([p.get("secCode") for p in pos_list])
        summary = f"数据源: AkShare 主行情 + MX-MONI fallback 持仓\n"
        summary += f"总资产: ¥{total_assets:,.2f} | 可用: ¥{avail_balance:,.2f} | 总盈亏: ¥{total_profit:+.2f}\n"
        summary += f"持仓: {len(pos_list)} 只\n"
        for p in pos_list:
            name = p.get("secName", "?")
            code = p.get("secCode", "?")
            profit = float(p.get("profit", 0) or 0)
            profit_pct = float(p.get("profitPct", 0) or 0)
            value = float(p.get("value", 0) or 0)
            ak = ak_quotes.get(str(code).zfill(6), {}) if isinstance(ak_quotes, dict) else {}
            ak_price = ak.get("price")
            ak_txt = f" | AkShare现价 ¥{ak_price:.2f}" if isinstance(ak_price, (int, float)) else ""
            summary += f"- {name}({code}): ¥{value:.0f} {profit_pct:+.2f}%(¥{profit:+.2f}){ak_txt}\n"
        log("✅ AkShare/MX-MONI 模拟仓数据完成")
        sections.append(("模拟仓持仓（AkShare 主行情 / MX-MONI fallback）", summary))
    else:
        local = sim_market_data.local_portfolio_from_trades()
        summary = f"数据源: 本地 sim-trades.json（MX-MONI 不可用）\n现金: ¥{local.get('cash', 0):,.2f} | 已实现盈亏: ¥{local.get('realized_pnl', 0):+,.2f}\n"
        positions = local.get("positions", [])
        quotes = sim_market_data.ak_stock_quotes([p.get("code") for p in positions])
        for p in positions:
            code = p.get("code")
            q = quotes.get(code, {}) if isinstance(quotes, dict) else {}
            price = q.get("price") or 0
            mv = price * float(p.get("qty", 0) or 0)
            summary += f"- {p.get('name','')}({code}): {p.get('qty')} 股 | 成本 ¥{p.get('cost',0):,.2f} | AkShare估值 ¥{mv:,.2f}\n"
        sections.append(("模拟仓持仓（本地 ledger + AkShare）", summary))

    # Step 6: 决策输出 — MX 可用用 fallback，否则用本地 ledger
    log("\n[Step 6] 模拟仓动作")
    if all_ok:
        write_hold_record(pos_info, factor_out, multi_factor_out, event_out)
    else:
        fail_paths = []
        if news_out.get("error"): fail_paths.append("market-news")
        if factor_out.get("error"): fail_paths.append("factor-score")
        if multi_factor_out.get("error"): fail_paths.append("multi-factor-score")
        if event_out.get("error"): fail_paths.append("event-impact")
        if not pos_info: fail_paths.append("mx-moni-fallback（已用本地ledger，不阻断）")
        write_fail_record("部分管道失败", f"失败环节: {', '.join(fail_paths)}")
        sections.append(("模拟仓状态", f"❌ 部分管道失败 ({', '.join(fail_paths)})，已写 fail 记录"))

    # 保存交易日报告
    save_report(sections)

    log("=" * 50)
    log("模拟盘每日交易 — 完成")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(daily_run())
