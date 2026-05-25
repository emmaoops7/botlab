#!/usr/bin/env python3
"""
事件影响分析（Event Impact Analyzer）
重点：特朗普讲话/政策扫描 → 关联持仓影响 → 风险评估

用法：
  python3 event-impact.py              # 扫描当前事件
  python3 event-impact.py --trump      # 专注特朗普追踪
  python3 event-impact.py --check FUND_CODE  # 查某只基金受事件影响
"""

import json
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

# 配置
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
POS_FILE = DATA_DIR / "positions.json"
EVENT_LOG = DATA_DIR / "event-log.json"
MX_SEARCH_SCRIPT = Path("/root/clawd/shared-skills/mx-search/mx_search.py")
MX_APIKEY = os.environ.get("MX_APIKEY", "YOUR_MX_API_KEY_HERE")

# ─── 特朗普政策关键词扫描（不做硬编码判断，只做关联）────────
TRUMP_KEYWORDS = [
    {"keyword": "关税", "en": "tariff", "related": ["新能源", "科技", "出口", "贸易"]},
    {"keyword": "制裁", "en": "sanction", "related": ["科技", "通信", "半导体", "芯片"]},
    {"keyword": "贸易战", "en": "trade war", "related": ["新能源", "科技", "通信", "高端制造", "宽基"]},
    {"keyword": "美元", "en": "dollar", "related": ["贵金属", "美股", "宽基"]},
    {"keyword": "降息", "en": "rate cut", "related": ["贵金属", "美股", "宽基"]},
    {"keyword": "石油", "en": "oil", "related": ["能源"]},
    {"keyword": "新能源", "en": "green energy", "related": ["新能源", "光伏", "电池"]},
]

# 市场反应逻辑（动态判断，不硬编码）：
# 1. 同一消息第一次发生 → 市场恐慌，先跌
# 2. 同一消息重复发生 → 市场免疫，可能不跌反涨
# 3. 超预期 → 大幅波动
# 4. 符合预期 → 小波动或无反应
# 5. 反转预期 → 反向波动
# 判断依据：实时搜索 + 资金流向 + 板块表现

# ─── 持仓板块 → 基金映射 ─────────────────────────────────────────
def load_positions():
    """读取持仓，按板块分组"""
    with open(POS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    
    by_category = {}
    for p in data["positions"]:
        cat = p.get("category", "其他")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "name": p["name"],
            "code": p.get("code", ""),
            "market_value": p.get("market_value", 0),
            "holding_pnl": p.get("holding_pnl", 0)
        })
    
    return by_category, data


def search_trump_news():
    """搜索特朗普相关新闻"""
    search_terms = [
        "特朗普 关税",
        "Trump tariff",
        "特朗普 制裁",
        "Trump sanctions",
        "特朗普 贸易战",
        "Trump trade war",
        "特朗普 能源",
        "Trump oil",
        "特朗普 美元",
        "Trump dollar",
        "特朗普 新能源",
        "Trump green energy",
    ]

    results = []
    for term in search_terms:
        try:
            result = subprocess.run(
                ["python3", str(MX_SEARCH_SCRIPT), term],
                capture_output=True, text=True, timeout=20,
                env={**os.environ, "MX_APIKEY": MX_APIKEY}
            )
            if result.returncode == 0 and result.stdout.strip():
                results.append({"term": term, "output": result.stdout[:500]})
        except Exception as e:
            results.append({"term": term, "error": str(e)})

    return results


def analyze_impact(news_results):
    """分析事件对持仓的影响（动态判断，不硬编码）"""
    categories, data = load_positions()
    impacts = []

    for kw in TRUMP_KEYWORDS:
        # 检查新闻中是否提到关键词
        mentioned = any(
            kw["keyword"].lower() in r.get("term", "").lower()
            or kw["keyword"].lower() in r.get("output", "").lower()
            or kw["en"].lower() in r.get("term", "").lower()
            or kw["en"].lower() in r.get("output", "").lower()
            for r in news_results
        )

        if not mentioned:
            continue

        # 找关联板块
        affected = []
        for cat in kw["related"]:
            if cat in categories:
                affected.extend(categories[cat])

        if affected:
            total_value = sum(f["market_value"] for f in affected)
            # 不硬编码"利空/利好"，只输出关联和涉及金额
            # 具体影响由 trading-engine 结合实时行情判断
            impacts.append({
                "keyword": kw["keyword"],
                "related_categories": kw["related"],
                "affected_funds": affected,
                "affected_value": total_value,
                "risk_level": "高" if total_value > 5000 else "中" if total_value > 2000 else "低",
                "note": "市场影响需结合实时资金流向判断，不硬编码利好/利空",
                "time": datetime.now().isoformat()
            })

    return impacts


def save_event_log(impacts):
    """保存事件日志"""
    log = {
        "scan_time": datetime.now().isoformat(),
        "events": impacts,
        "summary": {
            "total_events": len(impacts),
            "high_risk": sum(1 for i in impacts if i["risk_level"] == "高"),
            "medium_risk": sum(1 for i in impacts if i["risk_level"] == "中"),
            "low_risk": sum(1 for i in impacts if i["risk_level"] == "低"),
        }
    }

    # 追加到日志
    if EVENT_LOG.exists():
        with open(EVENT_LOG, encoding="utf-8") as f:
            try:
                history = json.load(f)
                if isinstance(history, list):
                    history.append(log)
                else:
                    history = [history, log]
            except:
                history = [log]
    else:
        history = [log]

    with open(EVENT_LOG, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def generate_report(impacts):
    """生成事件影响报告"""
    if not impacts:
        return "✅ 无重大事件影响\n\n当前持仓未检测到特朗普相关政策风险。"

    report = "## 🇺🇸 特朗普政策影响分析\n\n"
    report += f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    for impact in impacts:
        report += f"### {impact['keyword']}\n"
        report += f"- 关联板块: {', '.join(impact['related_categories'])}\n"
        report += f"- 风险等级: {impact['risk_level']}\n"
        report += f"- 涉及金额: ¥{impact['affected_value']:,.0f}\n"
        report += f"- 说明: {impact['note']}\n"
        report += f"- 关联基金:\n"
        for f in impact["affected_funds"]:
            report += f"  - {f['name']} (¥{f['market_value']:,.0f})\n"
        report += "\n"

    return report


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="事件影响分析")
    parser.add_argument("--trump", action="store_true", help="专注特朗普追踪")
    parser.add_argument("--check", help="检查特定基金代码")
    args = parser.parse_args()

    print("🔍 事件影响分析开始...")

    if args.trump:
        # 搜索特朗普新闻
        news = search_trump_news()
        print(f"📰 搜索到 {len(news)} 条相关结果")

        # 分析影响
        impacts = analyze_impact(news)
        print(f"⚠️ 发现 {len(impacts)} 个影响事件")

        # 保存日志
        save_event_log(impacts)

        # 生成报告
        report = generate_report(impacts)
        print("\n" + report)

        return report
    else:
        # 默认：加载已有事件日志
        if EVENT_LOG.exists():
            with open(EVENT_LOG, encoding="utf-8") as f:
                log = json.load(f)
            print(json.dumps(log[-1] if isinstance(log, list) else log, ensure_ascii=False, indent=2))
        else:
            print("📭 无事件记录，运行 --trump 开始扫描")


if __name__ == "__main__":
    main()