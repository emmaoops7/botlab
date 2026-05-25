#!/usr/bin/env python3
"""
市场概览 v3 — 实时A股指数 + 持仓板块新闻

变化：
- 使用 MX Data 获取实时指数数据（9:30-15:00 交易时段）
- 使用 MX Search 获取持仓板块新闻
- MX 失败时只输出失败说明，禁止编造新闻
"""
import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 时区配置
CN_TZ = timezone(timedelta(hours=8))
def cn_now():
    return datetime.now(CN_TZ)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
POS_FILE = DATA_DIR / "positions.json"
MX_SEARCH = Path("/root/clawd/shared-skills/mx-search/mx_search.py")
MX_DATA = Path("/root/clawd/shared-skills/mx-data/mx_data.py")
MX_APIKEY = os.getenv("MX_APIKEY", "")

# 指数配置
INDICES = [
    {"name": "上证指数", "code": "000001"},
    {"name": "深证成指", "code": "399001"},
    {"name": "创业板指", "code": "399006"},
]


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


def mx_run(script, args, timeout=30):
    """调用 MX 脚本"""
    if not MX_APIKEY:
        return "[MX_APIKEY 未配置]"
    try:
        env = {**os.environ, "MX_APIKEY": MX_APIKEY}
        result = subprocess.run(
            [sys.executable, str(script)] + args,
            capture_output=True, text=True, timeout=timeout, env=env
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[超时]"
    except Exception as e:
        return f"[异常: {e}]"


def get_realtime_indices():
    """获取A股主要指数实时行情（MX Data 转置格式解析）"""
    # 增加关键词获取更多字段
    query = "上证指数 深证成指 创业板指 最新价 涨跌幅 成交量 最高价 最低价 成交额"
    output = mx_run(MX_DATA, [query], timeout=40)
    
    # 从输出中提取 raw JSON 路径
    json_path = None
    for line in output.split("\n"):
        if "mx_data_" in line and "_raw.json" in line:
            json_path = line.split(": ")[-1].strip()
    
    if not json_path:
        return None
    
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        
        tables = data["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"]
        
        # 找实时数据表（entityName 是日期时间格式）
        realtime_tables = []
        for t in tables:
            e = t.get("entityName", "")
            # 实时表 entityName 格式: "2026-04-29 14:29"
            if "-" in e and ":" in e:
                realtime_tables.append(t)
        
        if not realtime_tables:
            return None
        
        # 合并所有实时表的数据
        combined = {}
        head = None
        for rt in realtime_tables:
            table_data = rt["table"]
            if head is None:
                head = table_data.get("headName", [])
            # 添加所有字段
            for key, values in table_data.items():
                if key != "headName":
                    combined[key] = values
        
        if not head:
            return None
        
        # 字段映射：MX API 字段代码 -> 中文含义
        field_map = {
            "f2": "最新价",
            "f3": "涨跌幅",
            "f15": "最高",
            "f16": "最低",
            "f17": "开盘",
            "f6": "成交额",
            "f5": "成交量",
            "f104": "上涨家数",
            "f105": "下跌家数",
        }
        
        results = []
        for i, h in enumerate(head):
            idx_name = h.split("(")[0] if "(" in h else h
            row = {"指数": idx_name}
            
            # 填充所有已知字段
            for field_code, field_name in field_map.items():
                values = combined.get(field_code)
                if values and i < len(values):
                    row[field_name] = values[i]
                else:
                    row[field_name] = "-"
            
            results.append(row)
        
        return results
    except Exception as e:
        return None


def mx_search(query, timeout=30):
    """调用 mx-search。必须返回真实 MX 结果；失败时返回 None，禁止编造/兜底。"""
    if not MX_APIKEY:
        return None
    try:
        env = {**os.environ, "MX_APIKEY": MX_APIKEY}
        result = subprocess.run(
            [sys.executable, str(MX_SEARCH), query],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        if result.returncode != 0:
            return None
        text = result.stdout.strip()
        if not text or "未找到相关资讯" in text or text.startswith("错误:"):
            return None
        # 保留 MX 工具输出，同时附上可审计的原始 JSON 路径
        raw_paths = []
        content_lines = []
        for line in text.split("\n"):
            if line.startswith("📄 原始结果已保存到:"):
                raw_paths.append(line.split(": ", 1)[-1].strip())
                continue
            if line.startswith("✅ 纯文本结果已保存到:"):
                continue
            content_lines.append(line)
        content = "\n".join(content_lines).strip()
        if not content:
            return None
        audit = f"\n\n> MX_QUERY: {query}"
        if raw_paths:
            audit += f"\n> MX_RAW_JSON: {raw_paths[0]}"
        return (content[:1200] + audit)
    except Exception:
        return None


def generate_market_overview():
    """生成市场概览：实时指数 + 新闻"""
    sections = []
    
    # 1. 实时指数（9:30-15:00）
    now = cn_now()
    hour = now.hour
    if 9 <= hour <= 15:  # 交易时段
        indices = get_realtime_indices()
        if indices:
            section = "## 📊 A股主要指数（实时）\n\n"
            section += "| 指数 | 最新价 | 涨跌幅 | 最高 | 最低 | 成交额 | 上涨/下跌 |\n"
            section += "|------|--------|--------|------|------|--------|-----------|\n"
            for idx in indices:
                section += f"| {idx['指数']} | {idx['最新价']} | {idx['涨跌幅']} | {idx['最高']} | {idx['最低']} | {idx['成交额']} | {idx['上涨家数']}/{idx['下跌家数']} |\n"
            sections.append({"type": "indices", "content": section})
    
    # 2. 持仓板块新闻
    cats = get_categories()
    cat_names = list(cats.keys())
    top_cats = cat_names[:4]
    
    queries = [
        f"{' '.join(top_cats)} 今日行情",
        "今日A股市场要闻",
    ]
    
    for q in queries:
        result = mx_search(q)
        if result:
            sections.append({"type": "news", "query": q, "content": result})
        else:
            sections.append({"type": "news", "query": q, "content": f"⚠️ MX API 未返回有效新闻，本段不生成内容。\n\n> MX_QUERY: {q}"})
    
    return sections


if __name__ == "__main__":
    sections = generate_market_overview()
    for s in sections:
        if s["type"] == "indices":
            print(s["content"])
        else:
            print(f"\n## 📰 {s['query']}\n{s['content']}\n")
