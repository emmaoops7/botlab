#!/usr/bin/env python3
"""
模拟交易系统 — 基于 mx-xuangu 选股 + mx-data 行情 + mx-moni 交易
用法:
  python3 sim-trade.py screen "市盈率<20 净利润增长>20%"   # 选股
  python3 sim-trade.py buy 600519 1700 100               # 买入
  python3 sim-trade.py sell 600519 1750 100              # 卖出
  python3 sim-trade.py portfolio                          # 持仓+盈亏
  python3 sim-trade.py status                             # 账户状态
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
TRADE_LOG = DATA_DIR / "trade-log.json"

MX_APIKEY = os.environ.get("MX_APIKEY", "")
MX_SEARCH = None  # mx-search not configured
MX_XUANGU = None  # mx-xuangu not configured
MX_DATA = None  # mx-data not configured
MX_MONI = None  # mx-moni not configured


def run_mx(script, query, timeout=30):
    """通用 mx 调用"""
    if not MX_APIKEY:
        return {"error": "MX_APIKEY 未配置"}
    try:
        env = {**os.environ, "MX_APIKEY": MX_APIKEY}
        result = subprocess.run(
            [sys.executable, str(script), query],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "调用超时"}
    except Exception as e:
        return {"error": str(e)}


def load_trades():
    """加载交易记录"""
    if TRADE_LOG.exists():
        with open(TRADE_LOG, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_trade(trade):
    """保存交易记录"""
    trades = load_trades()
    trades.append(trade)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRADE_LOG, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def cmd_screen(criteria):
    """选股"""
    print(f"📊 选股条件: {criteria}")
    result = run_mx(MX_XUANGU, criteria)
    if "error" in result:
        print(f"❌ {result['error']}")
        return
    print(result["stdout"][:1500])
    if result["stderr"]:
        print(f"⚠️ {result['stderr'][:200]}")


def cmd_buy(code, price, qty):
    """买入"""
    price = float(price)
    qty = int(qty)
    if qty % 100 != 0:
        print("❌ 数量必须是100的整数倍")
        return

    query = f"买入 {code} 价格 {price} 数量 {qty} 股"
    print(f"📈 执行: {query}")
    result = run_mx(MX_MONI, query)
    print(result["stdout"][:500])

    if "成功" in result.get("stdout", ""):
        trade = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "buy",
            "code": code,
            "price": price,
            "qty": qty,
            "amount": price * qty,
        }
        save_trade(trade)
        print(f"✅ 已记录: 买入 {code} {qty}股 @ ¥{price}")


def cmd_sell(code, price, qty):
    """卖出"""
    price = float(price)
    qty = int(qty)
    if qty % 100 != 0:
        print("❌ 数量必须是100的整数倍")
        return

    query = f"卖出 {code} 价格 {price} 数量 {qty} 股"
    print(f"📉 执行: {query}")
    result = run_mx(MX_MONI, query)
    print(result["stdout"][:500])

    if "成功" in result.get("stdout", ""):
        trade = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "sell",
            "code": code,
            "price": price,
            "qty": qty,
            "amount": price * qty,
        }
        save_trade(trade)
        print(f"✅ 已记录: 卖出 {code} {qty}股 @ ¥{price}")


def cmd_portfolio():
    """持仓+盈亏"""
    # mx-moni 持仓
    result = run_mx(MX_MONI, "我的持仓")
    print("📦 模拟盘持仓:")
    print(result["stdout"][:800])

    # 交易记录
    trades = load_trades()
    if trades:
        print(f"\n📝 交易记录 ({len(trades)} 笔):")
        for t in trades[-10:]:  # 最近10笔
            icon = "📈" if t["action"] == "buy" else "📉"
            print(f"  {icon} {t['time']} {t['action'].upper()} {t['code']} {t['qty']}股 @ ¥{t['price']}")
    else:
        print("\n📝 暂无交易记录")


def cmd_status():
    """账户状态"""
    result = run_mx(MX_MONI, "我的资金")
    print("💰 账户资金:")
    print(result["stdout"][:500])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "screen" and len(sys.argv) >= 3:
        cmd_screen(" ".join(sys.argv[2:]))
    elif cmd == "buy" and len(sys.argv) >= 5:
        cmd_buy(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "sell" and len(sys.argv) >= 5:
        cmd_sell(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "portfolio":
        cmd_portfolio()
    elif cmd == "status":
        cmd_status()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
