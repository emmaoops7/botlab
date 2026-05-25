#!/usr/bin/env python3
"""
模拟交易系统 — AkShare 主行情 + 本地审计日志

用法:
  python3 sim-trade.py screen "市盈率<20 净利润增长>20%"
  python3 sim-trade.py buy 600519 1700 100
  python3 sim-trade.py sell 600519 1750 100
  python3 sim-trade.py hold 600519 贵州茅台 "信号中性，继续观察"
  python3 sim-trade.py fail "MX_APIKEY 未配置"
  python3 sim-trade.py portfolio
  python3 sim-trade.py status

硬规则：
- 本脚本只写 data/sim-trades.json，不写用户实盘 positions.json。
- AkShare 是行情主源；MX/MX-MONI 仅作为真实股票模拟盘 fallback。
- buy/sell 默认先写本地审计日志；如 MX_MONI 可用，会附带 mx_audit。
- hold/fail 是每日模拟仓审计记录，用于证明“不交易也有判断”。
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
SIM_TRADE_LOG = DATA_DIR / "sim-trades.json"

MX_APIKEY = os.environ.get("MX_APIKEY", "")
MX_SEARCH = Path("/root/clawd/shared-skills/mx-search/mx_search.py")
MX_XUANGU = Path("/root/clawd/shared-skills/mx-xuangu/mx_xuangu.py")
MX_DATA = Path("/root/clawd/shared-skills/mx-data/mx_data.py")
MX_MONI = Path("/root/clawd/shared-skills/mx-moni/mx_moni.py")


def run_mx(script, query, timeout=30):
    if not MX_APIKEY:
        return {"error": "MX_APIKEY 未配置", "stdout": "", "stderr": "", "rc": 2}
    try:
        env = {**os.environ, "MX_APIKEY": MX_APIKEY}
        result = subprocess.run(
            [sys.executable, str(script), query],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "调用超时", "stdout": "", "stderr": "", "rc": 124}
    except Exception as e:
        return {"error": str(e), "stdout": "", "stderr": "", "rc": 1}


def load_trades():
    if SIM_TRADE_LOG.exists():
        try:
            with open(SIM_TRADE_LOG, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def save_trade(trade):
    trades = load_trades()
    trades.append(trade)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SIM_TRADE_LOG, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def trade_base(action, code="", name=""):
    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "code": str(code),
        "name": name,
        "source": "sim-trade.py",
    }


def cmd_screen(criteria):
    print(f"📊 选股条件: {criteria}")
    result = run_mx(MX_XUANGU, criteria)
    if result.get("error"):
        print(f"❌ {result['error']}")
        return 2
    print(result["stdout"][:1500])
    if result["stderr"]:
        print(f"⚠️ {result['stderr'][:200]}")
    return result.get("rc", 0)


def cmd_buy(code, price, qty, name=""):
    price = float(price)
    qty = int(qty)
    if qty % 100 != 0:
        print("❌ 数量必须是100的整数倍")
        return 2

    query = f"买入 {code} 价格 {price} 数量 {qty} 股"
    print(f"📈 执行: {query}")
    result = run_mx(MX_MONI, query) if MX_MONI.exists() else {"error": "MX_MONI 不存在", "rc": 2, "stdout": ""}
    print(result.get("stdout", "")[:500])

    trade = trade_base("buy", code, name)
    trade.update({
        "price": price,
        "qty": qty,
        "amount": round(price * qty, 2),
        "data_source": "AkShare primary + local ledger; MX_MONI fallback audit",
        "mx_audit": {"query": query, "rc": result.get("rc"), "error": result.get("error"), "stdout_head": result.get("stdout", "")[:200]},
    })
    save_trade(trade)
    print(f"✅ 已记录本地模拟买入: {code} {qty}股 @ ¥{price}（MX 仅审计/fallback）")
    return 0


def cmd_sell(code, price, qty, name=""):
    price = float(price)
    qty = int(qty)
    if qty % 100 != 0:
        print("❌ 数量必须是100的整数倍")
        return 2

    query = f"卖出 {code} 价格 {price} 数量 {qty} 股"
    print(f"📉 执行: {query}")
    result = run_mx(MX_MONI, query) if MX_MONI.exists() else {"error": "MX_MONI 不存在", "rc": 2, "stdout": ""}
    print(result.get("stdout", "")[:500])

    trade = trade_base("sell", code, name)
    trade.update({
        "price": price,
        "qty": qty,
        "amount": round(price * qty, 2),
        "data_source": "AkShare primary + local ledger; MX_MONI fallback audit",
        "mx_audit": {"query": query, "rc": result.get("rc"), "error": result.get("error"), "stdout_head": result.get("stdout", "")[:200]},
    })
    save_trade(trade)
    print(f"✅ 已记录本地模拟卖出: {code} {qty}股 @ ¥{price}（MX 仅审计/fallback）")
    return 0


def cmd_hold(code, name, reason, price=0, qty=0, extra=None):
    item = trade_base("hold", code, name)
    item.update({
        "price": float(price or 0),
        "qty": int(qty or 0),
        "amount": 0,
        "reason": reason,
        "mx_audit": extra or {},
    })
    save_trade(item)
    print(f"📌 已记录 HOLD: {name}({code})｜{reason}")
    return 0


def cmd_fail(reason, extra=None):
    item = trade_base("daily_fail")
    item.update({"reason": reason, "amount": 0, "mx_audit": extra or {}})
    save_trade(item)
    print(f"⚠️ 已记录模拟仓失败状态: {reason}")
    return 0


def cmd_portfolio():
    result = run_mx(MX_MONI, "我的持仓")
    print("📦 MX模拟盘持仓:")
    if result.get("error"):
        print(f"❌ {result['error']}")
    else:
        print(result.get("stdout", "")[:800])

    trades = load_trades()
    if trades:
        print(f"\n📝 模拟交易/审计记录 ({len(trades)} 笔):")
        for t in trades[-15:]:
            print(f"  {t.get('time')} {t.get('action','').upper()} {t.get('code','')} {t.get('name','')} {t.get('qty',0)} @ {t.get('price',0)} {t.get('reason','')}")
    else:
        print("\n📝 暂无交易记录")
    return 0


def cmd_status():
    try:
        import importlib.util
        p = SCRIPT_DIR / "sim-market-data.py"
        spec = importlib.util.spec_from_file_location("sim_market_data", p)
        md = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(md)
        print("💰 本地模拟仓资金（sim-trades.json）:")
        print(json.dumps(md.local_portfolio_from_trades(), ensure_ascii=False, indent=2)[:1000])
        return 0
    except Exception as e:
        print(f"❌ 本地状态计算失败: {e}")
        return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0

    cmd = sys.argv[1]
    if cmd == "screen" and len(sys.argv) >= 3:
        return cmd_screen(" ".join(sys.argv[2:]))
    if cmd == "buy" and len(sys.argv) >= 5:
        return cmd_buy(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
    if cmd == "sell" and len(sys.argv) >= 5:
        return cmd_sell(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
    if cmd == "hold" and len(sys.argv) >= 5:
        return cmd_hold(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
    if cmd == "fail" and len(sys.argv) >= 3:
        return cmd_fail(" ".join(sys.argv[2:]))
    if cmd == "portfolio":
        return cmd_portfolio()
    if cmd == "status":
        return cmd_status()

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
