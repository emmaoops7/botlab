---
name: multimodal-image
description: 必须用于图片生成和图片理解。触发词：画、帮我画、生成图片、生图、做张图、出图、图片、头像、海报、插画、改图、看图、截图、OCR、提取图片文字。飞书场景生图后图片自动投递；QQ场景用 <qqmedia> 返回图片；不要只文字描述，也不要把主 session 切到 VLM 或图片模型。
metadata: {"openclaw":{"emoji":"🖼️"}}
---

# Multimodal Image Tool Layer

主 session 固定文本模型；图片理解/生图走旁路工具，避免 session swamp。

## 强制触发规则

用户只要表达以下意图，必须调用本 skill，不要只用文字回答：

- 画 / 帮我画 / 生成图片 / 生图 / 做张图 / 出图
- 头像 / 海报 / 插画 / 表情包 / logo / 封面 / 配图
- 改图 / 图生图 / 重绘 / 换风格 / 按这张图生成
- 看图 / 分析截图 / 提取图片文字 / OCR

生图固定动作：

```bash
python3 skills/multimodal-image/scripts/mm_image.py generate --prompt "用户的完整生图需求" --out /root/.openclaw/media/qqbot/outputs
```

生图后图片会自动投递到当前飞书会话，无需手动发送。脚本会自动调用飞书原生 API 上传并发送图片（基于 FEISHU_NOTIFY_OPEN_ID 环境变量）。

飞书场景下不需要手动用 <qqmedia> 发送，脚本已完成自动投递。

QQ 等其他渠道仍需手动发 <qqmedia>：

```text
<qqmedia>/root/.openclaw/media/qqbot/outputs/xxx.png</qqmedia>
```

禁止：
- 不要回答“我可以帮你设计提示词”后停止。
- 不要说“我不能生成图片”。
- 不要切换主 session 模型到 `gpt-image-2` 或其他图片模型。

## 图片理解 / 截图分析 / 图片文字提取

```bash
python3 skills/multimodal-image/scripts/mm_image.py understand --image /absolute/path/or/url.png --prompt "用户的问题"
```

可多图：重复 `--image`。

适用：看图、截图排障、图片文字/表格理解、图片问答、图片对比。不要再用传统 OCR skill；需要提取文字时也用 `understand`。

## 生图

```bash
python3 skills/multimodal-image/scripts/mm_image.py generate --prompt "图片提示词" --out /root/.openclaw/media/qqbot/outputs
```

生图后会自动投递到飞书会话。成功后会输出本地文件路径。

其他渠道回复时用：

```text
<qqmedia>/path/to/generated.png</qqmedia>
```

## 图生图 / 改图

```bash
python3 skills/multimodal-image/scripts/mm_image.py edit --image /absolute/source.png --prompt "改图需求" --out /root/.openclaw/media/qqbot/outputs
```

生图后会自动投递到飞书会话。成功后输出本地文件路径。

其他渠道用 `<qqmedia>路径</qqmedia>` 发回。


## 失败防循环

同一个请求最多尝试 2 次：
- 第一次失败，可以修正明显参数问题后重试一次。
- 第二次仍失败，必须停止并把错误原因告诉用户。
- 不要第三次调用同一个子命令，不要只改 prompt 反复试。
- 失败时不要伪造图片路径或假装已生成。

## 规则

- 不要使用 `/model` 把当前会话切到 `qwen-vl-*`、`gpt-image-*`、`*-image`。
- 简单任务直接用本脚本；复杂多步任务先用脚本获取视觉结果，再在主 session 总结。
- 如果 `gpt-image-2` 失败，脚本会自动返回错误；不要假装已生成。


## ⏳ 生图耗时规则

生图/图生图可能需要 2-3 分钟。QQBot 网关层已优先把明确的生图/图生图请求改为异步任务；如果请求已经进入 agent 并需要手动调用 generate/edit，调用后要等待工具完成，不要因为 60 秒未返回就结束或重复调用。若最终失败，按失败防循环规则最多重试一次。


## 🧪 图生图事实校验

`gpt-image-2` `/images/edits` 已用 QQ 实际 JPG 复测成功。遇到一次 502/上游错误时，不要声称 gpt-image-2 不支持 edits 或“上游没配置”；按失败防循环规则最多重试一次，仍失败才返回具体错误。


## 🧪 图生图事实声明

`gpt-image-2` 的 `/images/edits` 端点**实测可用**（QQ 实际 JPG 文件复测成功，非小 PNG）。

如果调用返回 502 / upstream error，是**上游偶发错误**或 New API 代理偶发问题，不是 gpt-image-2 不支持 edits。

**禁止行为：**
- 不要声称 "gpt-image-2 不支持 edits" 或 "上游没配置"。
- 不要用 exec/curl 自己调 `/images/edits`，走 `multimodal-image` skill 的 `edit` 子命令。
- 502/上游错误时，最多重试一次（等待 10 秒），仍失败则返回具体错误信息，不继续尝试其他端点。
