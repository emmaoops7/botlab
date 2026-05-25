#!/usr/bin/env python3
"""
AkShare-first market data for the fund-agent simulation ledger.

Rules:
- AkShare is the primary quote/NAV source.
- MX/MX-MONI is optional fallback only; local sim-trades.json remains the audit ledger.
- Never touches data/positions.json (real portfolio).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
SIM_TRADE_LOG = DATA_DIR / "sim-trades.json"
REPORT_FILE = DATA_DIR / "sim-daily-report.md"

MX_APIKEY = os.environ.get("MX_APIKEY", "")
MX_MONI = Path("/root/clawd/shared-skills/mx-moni/mx_moni.py")


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_trades() -> List[Dict[str, Any]]:
    if not SIM_TRADE_LOG.exists():
        return []
    try:
        data = json.loads(SIM_TRADE_LOG.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_trades(trades: List[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SIM_TRADE_LOG.write_text(json.dumps(trades, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _price_from_scaled(raw: Any, dec: Any) -> Optional[float]:
    try:
        return round(float(raw) / (10 ** int(dec)), 4)
    except Exception:
        return None


def ak_stock_quotes(codes: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """Return A-share spot quotes keyed by 6-digit code."""
    codes = {str(c).zfill(6) for c in codes}
    if not codes:
        return {}
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        out: Dict[str, Dict[str, Any]] = {}
        for _, row in df[df["代码"].astype(str).isin(codes)].iterrows():
            code = str(row.get("代码", "")).zfill(6)
            price = float(row.get("最新价")) if row.get("最新价") not in (None, "-") else None
            out[code] = {
                "code": code,
                "name": str(row.get("名称", "")),
                "price": price,
                "pct_chg": float(row.get("涨跌幅", 0) or 0),
                "source": "AkShare stock_zh_a_spot_em",
                "quote_time": now(),
            }
        return out
    except Exception as e:
        return {"__error__": {"error": repr(e), "source": "AkShare stock_zh_a_spot_em"}}


def ak_fund_nav(code: str) -> Dict[str, Any]:
    """Return latest open-fund NAV from AkShare."""
    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol=str(code).zfill(6), indicator="单位净值走势")
        if df.empty:
            raise RuntimeError("empty NAV dataframe")
        row = df.tail(1).iloc[0]
        return {
            "code": str(code).zfill(6),
            "nav_date": str(row.get("净值日期")),
            "nav": float(row.get("单位净值")),
            "day_growth_pct": float(row.get("日增长率", 0) or 0),
            "source": "AkShare fund_open_fund_info_em",
        }
    except Exception as e:
        return {"code": str(code).zfill(6), "error": repr(e), "source": "AkShare fund_open_fund_info_em"}


def fetch_mx_moni_positions() -> Optional[Dict[str, Any]]:
    """Optional MX-MONI fallback for existing stock simulation state."""
    if not MX_APIKEY or not MX_MONI.exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(MX_MONI), "我的持仓"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "MX_APIKEY": MX_APIKEY},
        )
        if result.returncode != 0:
            return None
        match = re.search(r"(/\S*mx_moni\S*_raw\.json)", result.stdout)
        if not match:
            return None
        raw = Path(match.group(1))
        if not raw.exists():
            return None
        data = json.loads(raw.read_text(encoding="utf-8"))
        d = data.get("data", {})
        return {
            "posList": d.get("posList", []),
            "totalAssets": float(d.get("totalAssets", 0) or 0),
            "availBalance": float(d.get("availBalance", 0) or 0),
            "totalProfit": float(d.get("totalProfit", 0) or 0),
            "source": "MX-MONI fallback",
        }
    except Exception:
        return None


def local_portfolio_from_trades(trades: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Rebuild local simulation state from sim-trades.json."""
    trades = trades if trades is not None else load_trades()
    positions: Dict[str, Dict[str, Any]] = {}
    cash = 1_000_000.0
    realized_pnl = 0.0

    for t in trades:
        action = t.get("action")
        code = str(t.get("code", "")).zfill(6) if t.get("code") else ""
        if not code or action not in {"buy", "sell"}:
            continue
        qty = int(float(t.get("qty", 0) or 0))
        price = float(t.get("price", 0) or 0)
        amount = float(t.get("amount", price * qty) or 0)
        if qty <= 0 or price <= 0:
            continue
        pos = positions.setdefault(code, {"code": code, "name": t.get("name", ""), "qty": 0, "cost": 0.0})
        if action == "buy":
            pos["qty"] += qty
            pos["cost"] += amount
            pos["name"] = t.get("name") or pos.get("name", "")
            cash -= amount
        elif action == "sell":
            avg = pos["cost"] / pos["qty"] if pos["qty"] else 0
            sell_qty = min(qty, pos["qty"])
            cost_out = avg * sell_qty
            pos["qty"] -= sell_qty
            pos["cost"] -= cost_out
            cash += amount
            realized_pnl += amount - cost_out

    positions = {k: v for k, v in positions.items() if v["qty"] > 0.000001}
    return {"cash": cash, "positions": list(positions.values()), "realized_pnl": realized_pnl, "source": "local sim-trades.json"}


def append_trade(item: Dict[str, Any]) -> None:
    trades = load_trades()
    trades.append(item)
    save_trades(trades)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "portfolio"
    if cmd == "quote-stock":
        print(json.dumps(ak_stock_quotes(sys.argv[2:]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "quote-fund" and len(sys.argv) >= 3:
        for code in sys.argv[2:]:
            print(json.dumps(ak_fund_nav(code), ensure_ascii=False))
        return 0
    if cmd == "mx-positions":
        print(json.dumps(fetch_mx_moni_positions(), ensure_ascii=False, indent=2))
        return 0
    if cmd in {"portfolio", "local-portfolio"}:
        print(json.dumps(local_portfolio_from_trades(), ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
