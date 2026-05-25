# fund-agent data baseline

本目录是可分发模板，只允许保留示例文件。

禁止放入：
- positions.json（真实持仓）
- smtp.enc / SMTP 凭证
- email-report.md / analysis-today.md / risk-state.json
- trade-log.json / sim-trades.json 等运行数据

每个容器首次使用时必须自己创建本地 `skills/fund-agent/data/positions.json`。
