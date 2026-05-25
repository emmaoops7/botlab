# botlab 项目结构

`botlab` 是当前 OpenClaw 容器的项目集仓库。

## 目录

- `opc/` — 韵狐一人公司项目
  - `main/` — 当前 main 容器的通用项目、skills、脚本、华亚物业原型
  - `sales/` — sales 客服销售 agent 配置/知识
  - `legal/` — legal 法务总监 agent 配置/知识
- `tuya-smart-control/` — 涂鸦智能家居/红外控制 skill
- `tests/` — Tuya skill 测试

## 不提交内容

- `.env`、`.secrets/`：密钥凭证
- `memory/`：长期记忆和隐私上下文
- `state/`、`tmp/`、`.openclaw/`：运行态/临时文件
