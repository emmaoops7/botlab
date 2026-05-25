---
name: fund-agent
version: 1.0.0
display_name: 基金智能分析助手
description: 基金/股票持仓管理 + 实时行情分析 + 操作建议 + 特朗普政策追踪。基于自建决策引擎，支持基金/股票分析、风险评估和操作建议。
category: finance
tags: [fund, portfolio, trading, analysis, risk, trump-monitor]
dependencies: []
---

# Fund Agent — 基金智能分析助手

## 概述

基金投资助手模板：每个容器使用自己的 data/positions.json，提供行情分析、风险评估、操作建议。

**核心原则：不能亏钱。**

## 架构（3 层）

```
数据层 (MX Skills)

研究层 (Analysis)
  ├── event-impact.py   → 特朗普政策追踪 + 事件影响
  └── factor-score.py   → 基金评分卡 (1-10 分)

决策层 (Decision)
  ├── analyze.py        → 持仓分析主脚本
  ├── report-gen.py     → 结构化报告生成
  └── send_mail.py      → 日报邮件推送
```

## 使用方式

### QQ 消息触发
| 触发词 | 动作 |
|--------|------|
| "看看基金"/"持仓"/"今天怎么样" | 分析持仓 + 实时行情 |
| "买xxx"/"卖xxx" | 评估风险 + 给建议 |
| "理财日报" | 生成报告 + 发邮件 |
| "特朗普影响" | 扫描政策风险 |
| "基金评分" | 显示评分卡 |

### 脚本调用
```bash
cd /root/clawd/skills/fund-agent

# 完整分析
python3 scripts/analyze.py

# 基金评分
python3 scripts/factor-score.py --rank

# 特朗普追踪
python3 scripts/event-impact.py --trump

# 生成报告
python3 scripts/report-gen.py --full
```

## 数据文件

| 文件 | 说明 |
|------|------|
| `data/positions.json` | 持仓数据（含 code + category） |
| `data/risk-state.json` | 风险状态 |
| `data/factor-scores.json` | 基金评分 |
| `data/event-log.json` | 事件影响日志 |
| `data/trade-log.json` | 交易日志 |
| `data/daily-report.md` | 每日报告 |

## 环境变量

```
MX_APIKEY=<用户自己的妙想 API Key>
```

## 安全规则

1. **不能亏钱** — 第一原则
2. **不自动交易** — 只建议，用户确认才执行
3. **不追高不抄底** — 保守优先
4. **止损纪律** — 亏 10% 提醒，15% 强制建议
5. **单只≤10%** — 不 all in

## ⚠️ 副作用评估

| 副作用 | 缓解 |
|--------|------|
| 修改 positions.json | 用户确认后执行，先备份 |
| 调用外部 API | 仅东方财富官方域名 |
| 发邮件 | 仅预设邮箱，不泄露 |
| 读 .env | 仅解密 可选邮件凭证（默认不包含） |

风险等级：**🟡 MEDIUM**（涉及金融数据；公共模板不包含任何私人持仓或邮件凭证）
