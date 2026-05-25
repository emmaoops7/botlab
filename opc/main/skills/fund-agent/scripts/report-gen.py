#!/usr/bin/env python3
"""
报告生成器（Report Generator）
整合所有分析结果 → 结构化报告 → 可用于邮件/推送

用法：
  python3 report-gen.py              # 生成今日报告
  python3 report-gen.py --full       # 完整报告（含评分+事件）
  python3 report-gen.py --output md  # 输出 markdown
  python3 report-gen.py --output json # 输出 JSON
"""

import json
import sys
from datetime import datetime, date
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
POS_FILE = DATA_DIR / "positions.json"
SCORE_FILE = DATA_DIR / "factor-scores.json"
REPORT_FILE = DATA_DIR / "daily-report.md"


def load_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return None


def generate_report(full=False, output_format="md", news="", sim=""):
    """生成报告"""
    today = date.today().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 加载数据
    positions_data = load_json(POS_FILE)
    scores_data = load_json(SCORE_FILE)

    if not positions_data:
        return "❌ 持仓数据不存在"

    positions = positions_data["positions"]
    total_mv = positions_data.get("total_market_value", 0)
    total_loss = positions_data.get("total_cumulative_loss", 0)
    risk_level = positions_data.get("risk_level", "unknown")
    risk_score = positions_data.get("risk_score", 0)

    if output_format == "md":
        # ─── Markdown 报告 ─────────────────────────────────────
        report = f"""# ⚡ Fund-Agent 日报 | {today}

> 生成时间: {time_str}

---

## 📊 盈亏概览

| 总市值 | 累计盈亏 | 风险等级 | 持仓数 |
|--------|----------|----------|--------|
| ¥{total_mv:,.0f} | ¥{total_loss:+,.0f} | {risk_level} ({risk_score}分) | {len(positions)} |

---

## 🏷️ 板块分布

"""
        # 按板块汇总
        categories = {}
        for p in positions:
            cat = p.get("category", "其他")
            if cat not in categories:
                categories[cat] = {"市值": 0, "盈亏": 0, "数量": 0}
            categories[cat]["市值"] += p.get("market_value", 0)
            categories[cat]["盈亏"] += p.get("holding_pnl", 0)
            categories[cat]["数量"] += 1

        report += "| 板块 | 市值 | 盈亏 | 数量 |\n|------|------|------|------|\n"
        for cat, d in sorted(categories.items(), key=lambda x: x[1]["市值"], reverse=True):
            pnl_icon = "🟢" if d["盈亏"] >= 0 else "🔴"
            report += f"| {cat} | ¥{d['市值']:,.0f} | {pnl_icon}¥{d['盈亏']:+,.0f} | {d['数量']} |\n"

        report += "\n---\n\n## 📋 持仓明细\n\n"
        report += "| 基金 | 代码 | 市值 | 盈亏 | 分类 |\n"
        report += "|------|------|------|------|------|\n"
        for p in sorted(positions, key=lambda x: x.get("market_value", 0), reverse=True):
            pnl = p.get("holding_pnl", 0)
            pnl_str = f"¥{pnl:+,.0f}"
            report += f"| {p['name'][:20]} | {p.get('code', '-')} | ¥{p['market_value']:,.0f} | {pnl_str} | {p.get('category', '-')} |\n"

        # 完整版：加评分和事件
        if full:
            report += "\n---\n\n## 📈 基金评分卡\n\n"

            if scores_data:
                scores = scores_data.get("scores", [])
                report += "| 基金 | 评分 | 评级 | 建议 |\n|------|------|------|------|\n"
                for s in sorted(scores, key=lambda x: x["total_score"], reverse=True):
                    report += f"| {s['name'][:20]} | {s['total_score']:.1f} | {s['grade']} | {s['action']} |\n"

                report += f"\n平均评分: {scores_data.get('average_score', 0):.1f}\n"
            else:
                report += "⏳ 暂无评分数据\n"

            # 不再包含假的事件分析，由 AI 生成真实要闻

            # 市场要闻（如果有）
            if news:
                report += "\n---\n\n## 📰 市场要闻\n\n"
                report += news + "\n"

            # 模拟盘（如果有）
            if sim:
                report += "\n---\n\n## 🎮 模拟盘交易\n\n"
                report += "```\n" + sim + "\n```\n"

        # 风险提示
        report += "\n---\n\n## ⚠️ 风险提示\n\n"
        if risk_score > 70:
            report += "- 🔴 风险分 > 70，建议控制仓位在 50% 以内\n"
        if total_loss < -1000:
            report += f"- 🔴 累计亏损 ¥{total_loss:+,.0f}，超过 ¥1000 阈值，审视持仓策略\n"

        # 止损提醒
        for p in positions:
            pnl_ratio = (p.get("holding_pnl", 0) / p.get("market_value", 1)) * 100
            if pnl_ratio < -15:
                report += f"- 🚨 {p['name']} 亏损 {pnl_ratio:.1f}%，超过 15%，**强烈建议止损**\n"
            elif pnl_ratio < -10:
                report += f"- ⚠️ {p['name']} 亏损 {pnl_ratio:.1f}%，超过 10%，建议审视是否止损\n"

        report += "\n---\n"
        report += f"*Fund-Agent 自动生成 | ⚡ 第一原则：不能亏钱*\n"

        return report

    elif output_format == "json":
        return {
            "date": today,
            "time": time_str,
            "summary": {
                "total_market_value": total_mv,
                "cumulative_loss": total_loss,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "positions_count": len(positions),
            },
            "categories": {
                cat: {
                    "market_value": d["市值"],
                    "holding_pnl": d["盈亏"],
                    "count": d["数量"]
                }
                for cat, d in categories.items()
            },
            "positions": [
                {
                    "name": p["name"],
                    "code": p.get("code"),
                    "category": p.get("category"),
                    "market_value": p.get("market_value", 0),
                    "holding_pnl": p.get("holding_pnl", 0),
                }
                for p in positions
            ],
            "scores": scores_data,
        }


def generate_qq_short():
    """生成 QQ 精简版（适合 QQ 消息，不超过 500 字）"""
    positions_data = load_json(POS_FILE)
    scores_data = load_json(SCORE_FILE)

    if not positions_data:
        return "❌ 持仓数据不存在"

    positions = positions_data["positions"]
    total_mv = positions_data.get("total_market_value", 0)
    total_loss = positions_data.get("total_cumulative_loss", 0)
    risk_level = positions_data.get("risk_level", "unknown")
    risk_score = positions_data.get("risk_score", 0)

    # 计算今日涨跌估算（如果有 scores_data）
    today_change = 0
    if scores_data:
        for s in scores_data.get("scores", []):
            today_change += s.get("holding_pnl", 0)

    # 板块汇总（只显示盈亏最大的3个）
    categories = {}
    for p in positions:
        cat = p.get("category", "其他")
        if cat not in categories:
            categories[cat] = {"市值": 0, "盈亏": 0}
        categories[cat]["市值"] += p.get("market_value", 0)
        categories[cat]["盈亏"] += p.get("holding_pnl", 0)

    top_cats = sorted(categories.items(), key=lambda x: abs(x[1]["盈亏"]), reverse=True)[:3]

    # 风险提示（只显示最严重的）
    alerts = []
    for p in positions:
        pnl_ratio = (p.get("holding_pnl", 0) / p.get("market_value", 1)) * 100
        if pnl_ratio < -15:
            alerts.append(f"🚨 {p['name'][:15]} -{abs(pnl_ratio):.0f}%")
        elif pnl_ratio < -10:
            alerts.append(f"⚠️ {p['name'][:15]} -{abs(pnl_ratio):.0f}%")

    # 组装精简版
    short = f"""⚡ Fund-Agent 日报

📊 总市值 ¥{total_mv:,.0f} | 累计盈亏 ¥{total_loss:+,.0f}
风险等级: {risk_level} ({risk_score}分) | 持仓 {len(positions)} 只

🏷️ 板块盈亏 TOP3:
"""
    for cat, d in top_cats:
        icon = "🟢" if d["盈亏"] >= 0 else "🔴"
        short += f"{icon} {cat}: ¥{d['盈亏']:+,.0f}\n"

    if alerts:
        short += "\n⚠️ 风险提醒:\n"
        short += "\n".join(alerts[:3]) + "\n"

    short += "\n💡 完整报告已发送邮箱"

    return short


def main():
    import argparse
    parser = argparse.ArgumentParser(description="报告生成器")
    parser.add_argument("--full", action="store_true", help="完整报告（含评分+事件）")
    parser.add_argument("--qq", action="store_true", help="QQ 精简版（不超过 500 字）")
    parser.add_argument("--email", action="store_true", help="邮件完整版（保存文件）")
    parser.add_argument("--news", type=str, default="", help="市场要闻内容（由 market-news.py 生成）")
    parser.add_argument("--sim", type=str, default="", help="模拟盘交易输出")
    parser.add_argument("--output", default="md", choices=["md", "json"], help="输出格式")
    args = parser.parse_args()

    # QQ 精简版
    if args.qq:
        print(generate_qq_short())
        return

    # 邮件完整版
    if args.email or args.full:
        report = generate_report(full=True, output_format="md", news=args.news, sim=args.sim)
        # 保存到文件（供邮件发送）
        email_file = DATA_DIR / "email-report.md"
        with open(email_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 邮件报告保存: {email_file}")
        return

    # 默认：完整报告
    report = generate_report(full=args.full, output_format=args.output, news=args.news)

    if args.output == "md":
        # 保存并打印
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 报告保存: {REPORT_FILE}")
        print("\n" + report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()