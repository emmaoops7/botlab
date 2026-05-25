#!/usr/bin/env python3
"""
市场要闻分析 v2 — 调用 mx-search 获取真实资讯，结合持仓生成影响分析

优化：
- 减少串行调用次数，合并搜索
- 超时从 30s 降到 15s
- 失败不影响主流程
"""
import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
POS_FILE = DATA_DIR / "positions.json"
MX_SEARCH = None  # mx-search not configured
MX_APIKEY = os.environ.get("MX_APIKEY", "")


def get_categories():
    """读取持仓板块"""
    if not POS_FILE.exists():
        return {}
    with open(POS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    cats = {}
    for p in data.get("positions", []):
        cat = p.get("category", "其他")
        if cat not in cats:
            cats[cat] = {"funds": [], "total_mv": 0, "total_pnl": 0}
        cats[cat]["funds"].append(p["name"])
        cats[cat]["total_mv"] += p.get("market_value", 0)
        cats[cat]["total_pnl"] += p.get("holding_pnl", 0)
    return cats


def mx_search(query, timeout=15):
    """调用 mx-search，超时 15s"""
    if not MX_APIKEY:
        return "[MX_APIKEY 未配置]"
    try:
        env = {**os.environ, "MX_APIKEY": MX_APIKEY}
        result = subprocess.run(
            [sys.executable, str(MX_SEARCH), query],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            lines = text.split("\n")
            content_lines = [l for l in lines if not l.startswith("搜索结果:")]
            return "\n".join(content_lines)[:500]
        else:
            return f"[搜索失败]"
    except subprocess.TimeoutExpired:
        return "[搜索超时]"
    except Exception:
        return "[搜索异常]"


def generate_market_news():
    """生成市场要闻 + 对持仓的影响"""
    cats = get_categories()
    cat_names = list(cats.keys())
    top_cats = cat_names[:4]  # 只取前4个最大板块

    queries = [
        f"{' '.join(top_cats)} 今日行情",
        "今日A股市场要闻",
    ]

    sections = []
    for q in queries:
        result = mx_search(q)
        sections.append({"query": q, "content": result})

    return sections


if __name__ == "__main__":
    news = generate_market_news()
    for n in news:
        print(f"\n## 📰 {n['query']}\n{n['content']}\n")
