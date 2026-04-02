# tuya-smart-control — OpenClaw 智能家居控制技能

tuya-smart-control 是面向 OpenClaw 平台推出的官方 AI Agent 技能，基于涂鸦智能 Tuya 2C 终端用户 API 构建。为开发者带来业界最广泛的 AI+设备交互能力——3,000+ 智能硬件品类、覆盖 200+ 国家和地区，让 AI Agent 开箱即控万物。登录 tuya.ai 一键获取，无需繁琐认证。安装后，即可通过自然语言实现设备查询、智能控制、消息通知、天气查询、数据统计等全场景能力。
> **试运行声明**
>
> 当前所有开放的 API 接口均处于**试运行阶段**，每个接口存在调用次数、调用频率、配额等限制。具体限制信息将陆续更新，请关注本仓库的后续公告。如在使用过程中遇到限流或配额不足的情况，请稍后重试。

---

## 功能概览

| 模块 | 能力 | 说明 |
|------|------|------|
| 家庭管理 | 查询所有家庭、查询家庭下的房间 | 获取家庭和房间层级结构 |
| 设备查询 | 全部设备、按家庭查询、按房间查询、单设备详情 | 支持获取设备当前属性状态 |
| 设备控制 | 查询物模型、下发属性指令 | 支持开关、亮度、温度、模式等控制 |
| 设备管理 | 设备重命名 | 修改设备显示名称 |
| 天气服务 | 当前天气和逐小时预报 | 温度、湿度、天气状况等 |
| 消息通知 | 短信、语音电话、邮件、App 推送 | 仅支持向当前登录用户自发送 |
| 数据统计 | 按小时统计配置查询、统计数据查询 | 支持用电量等指标的统计分析 |
| IPC 云端抓拍 | 云端截图和短视频录制 | 从摄像头设备抓拍图片/视频并获取可播放 URL |
| IPC 视觉识别 | 摄像头画面理解 | 抓拍快照后发送给 AI 视觉大模型识别画面内容 |

---

## 快速开始

### 1. 获取 API Key

| 用户类型 | 获取地址 |
|---------|----------|
| 中国大陆用户 | [tuyasmart.com](https://tuyasmart.com/) |
| 国际用户 | [tuya.ai](https://tuya.ai/) |

> API Key 格式为 `sk-<PREFIX><rest>`，其中前缀用于自动识别数据中心。请确保 API Key 的区域与您的涂鸦账号注册区域匹配。

### 2. API Key 前缀与数据中心映射

API Key 中 `sk-` 之后的前两个字符自动映射到对应的数据中心：

| 前缀 | 区域 | Base URL |
|------|------|----------|
| `AY` | 中国数据中心 | `https://openapi.tuyacn.com` |
| `AZ` | 美西数据中心 | `https://openapi.tuyaus.com` |
| `EU` | 中欧数据中心 | `https://openapi.tuyaeu.com` |
| `IN` | 印度数据中心 | `https://openapi.tuyain.com` |
| `UE` | 美东数据中心 | `https://openapi-ueaz.tuyaus.com` |
| `WE` | 西欧数据中心 | `https://openapi-weaz.tuyaeu.com` |
| `SG` | 新加坡数据中心 | `https://openapi-sg.iotbing.com` |

### 3. 在 OpenClaw 中安装技能

1. 在 OpenClaw 平台中添加 `tuya-smart-control` 技能
2. 在技能配置中填入您的 `TUYA_API_KEY`（必填）
3. 安装完成后，AI Agent 自动获得智能家居控制能力

**运行环境要求：**
- Python 3.7+
- `requests` 库（`pip install requests`）

---

## 使用方式

### 自然语言交互（推荐）

技能安装后，用户可直接通过自然语言与 AI Agent 交互：

- "打开客厅的灯"
- "把空调温度调到 26 度"
- "查询今天的天气"
- "给我发一条短信提醒"
- "把卧室灯改名为床头灯"
- "查看这个月的用电量"
- "用门口的摄像头拍张照片"
- "用客厅摄像头录一段 5 秒的视频"
- "看看门口摄像头前面有什么"
- "门口有人吗？"

### Python SDK 调用

技能内置 `scripts/tuya_api.py`，提供封装好的 `TuyaAPI` 类：

```python
from tuya_api import TuyaAPI

api = TuyaAPI()  # 自动从环境变量读取配置

# 查询所有家庭
homes = api.get_homes()

# 查询所有设备
devices = api.get_all_devices()

# 查询设备详情（含当前属性状态）
detail = api.get_device_detail("your_device_id")

# 控制设备 — 开灯并设置亮度
result = api.issue_properties("your_device_id", {
    "switch_led": True,
    "bright_value": 500
})

# 查询天气
weather = api.get_weather(lat="39.90", lon="116.40")

# 发送短信通知
api.send_sms("设备异常提醒：客厅灯已离线")

# IPC 云端抓拍 — 拍摄快照并获取解密 URL
capture = api.ipc_ai_capture_pic_allocate_and_fetch("your_device_id", user_privacy_consent_accepted=True)

# IPC 云端抓拍 — 录制 5 秒短视频
video = api.ipc_ai_capture_video_allocate_and_fetch("your_device_id", video_duration_seconds=5, user_privacy_consent_accepted=True)
```

### 命令行工具

```bash
# 家庭与设备
python3 tuya_api.py homes                              # 查询所有家庭
python3 tuya_api.py rooms <home_id>                    # 查询家庭下的房间
python3 tuya_api.py devices                            # 查询所有设备
python3 tuya_api.py home_devices <home_id>             # 查询家庭下的设备
python3 tuya_api.py room_devices <room_id>             # 查询房间下的设备
python3 tuya_api.py device_detail <device_id>          # 查询设备详情

# 设备控制
python3 tuya_api.py model <device_id>                  # 查询设备物模型
python3 tuya_api.py control <device_id> '{"switch_led":true,"bright_value":500}'

# 设备管理
python3 tuya_api.py rename <device_id> "新名称"

# 天气查询
python3 tuya_api.py weather 39.90 116.40

# 消息通知
python3 tuya_api.py sms "提醒消息"
python3 tuya_api.py voice "语音消息"
python3 tuya_api.py mail "邮件标题" "邮件内容"
python3 tuya_api.py push "推送标题" "推送内容"

# 数据统计
python3 tuya_api.py stats_config                       # 查询统计配置
python3 tuya_api.py stats_data <dev_id> ele_usage SUM 2026031600 2026031623

# IPC 云端抓拍
python3 tuya_api.py ipc_pic_fetch <device_id> 1              # 拍照（consent=1 获取解密 URL）
python3 tuya_api.py ipc_video_fetch <device_id> 5 1           # 录制 5 秒视频（consent=1）
```

---

## API 接口参考

所有接口使用统一认证方式：`Authorization: Bearer {Api-key}`

各接口的完整请求参数、响应字段和示例详见 `references/` 目录下的文档：

| 模块 | 接口 | 方法 | 路径 | 参考文档 |
|------|------|------|------|----------|
| 家庭管理 | 查询所有家庭 | GET | `/v1.0/end-user/homes/all` | [home-and-space.md](Tuya%20Smart%20control/references/home-and-space.md) |
| 家庭管理 | 查询家庭下的房间 | GET | `/v1.0/end-user/homes/{home_id}/rooms` | [home-and-space.md](Tuya%20Smart%20control/references/home-and-space.md) |
| 设备查询 | 查询所有设备 | GET | `/v1.0/end-user/devices/all` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| 设备查询 | 查询家庭下的设备 | GET | `/v1.0/end-user/homes/{home_id}/devices` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| 设备查询 | 查询房间下的设备 | GET | `/v1.0/end-user/homes/room/{room_id}/devices` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| 设备查询 | 查询单设备详情 | GET | `/v1.0/end-user/devices/{device_id}/detail` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| 设备控制 | 查询设备物模型 | GET | `/v1.0/end-user/devices/{device_id}/model` | [device-control.md](Tuya%20Smart%20control/references/device-control.md) |
| 设备控制 | 下发属性指令 | POST | `/v1.0/end-user/devices/{device_id}/shadow/properties/issue` | [device-control.md](Tuya%20Smart%20control/references/device-control.md) |
| 设备管理 | 设备重命名 | POST | `/v1.0/end-user/devices/{device_id}/attribute` | [device-management.md](Tuya%20Smart%20control/references/device-management.md) |
| 天气服务 | 查询天气 | GET | `/v1.0/end-user/services/weather/recent` | [weather.md](Tuya%20Smart%20control/references/weather.md) |
| 消息通知 | 发送短信 | POST | `/v1.0/end-user/services/sms/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| 消息通知 | 发送语音电话 | POST | `/v1.0/end-user/services/voice/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| 消息通知 | 发送邮件 | POST | `/v1.0/end-user/services/mail/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| 消息通知 | 发送 App 推送 | POST | `/v1.0/end-user/services/push/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| 数据统计 | 查询统计配置 | GET | `/v1.0/end-user/statistics/hour/config` | [statistics.md](Tuya%20Smart%20control/references/statistics.md) |
| 数据统计 | 查询统计数据 | GET | `/v1.0/end-user/statistics/hour/data` | [statistics.md](Tuya%20Smart%20control/references/statistics.md) |
| IPC 云端抓拍 | 分配云端抓拍 | POST | `/v1.0/end-user/ipc/{device_id}/capture/allocate` | [ipc-cloud-capture.md](Tuya%20Smart%20control/references/ipc-cloud-capture.md) |
| IPC 云端抓拍 | 解析抓拍 URL | POST | `/v1.0/end-user/ipc/{device_id}/capture/resolve` | [ipc-cloud-capture.md](Tuya%20Smart%20control/references/ipc-cloud-capture.md) |

---

## 支持与限制

### 支持的属性类型

| 类型 | 说明 | 示例 |
|------|------|------|
| bool | 布尔开关 | 灯开关、空调开关、插座开关 |
| enum | 枚举选择 | 空调模式（自动/制冷/制热）、风速（低/中/高） |
| value | 数值调节 | 亮度（0-1000）、温度（16-30） |
| string | 字符串值 | 设备显示文本 |

### 不支持的操作

以下操作涉及敏感权限或复杂数据类型，**暂不支持**：

- **门锁控制** — 开锁、上锁等安全敏感操作
- **实时视频流** — 拉取实时视频流、查看实时画面（云端截图/短视频录制已支持）
- **图片操作** — 设备图片的上传与下载
- **复杂数据类型控制** — `raw`、`bitmap`、`struct`、`array` 类型的属性下发
- **固件升级** — OTA 固件更新操作
- **设备配网/移除** — 添加新设备或移除已有设备

如需以上操作，请使用涂鸦 App 直接完成。

---

## 项目结构

```
tuya-smart-control/
├── SKILL.md                       # OpenClaw Skill 定义（含元数据）
├── scripts/
│   └── tuya_api.py                # Python SDK + CLI 工具
└── references/                    # API 参考文档
    ├── home-and-space.md          # 家庭与空间管理
    ├── device-query.md            # 设备查询
    ├── device-control.md          # 设备控制
    ├── device-management.md       # 设备管理
    ├── weather.md                 # 天气服务
    ├── notifications.md           # 消息通知
    ├── statistics.md              # 数据统计
    └── ipc-cloud-capture.md       # IPC 云端抓拍
```

---

## License

MIT

## 加入微信讨论群
扫码加入tuya-openclaw-skills技能交流群：

<!-- 微信二维码：控制宽度+居中显示，提升美观度 -->
<img src="./images/wechat-group-qrcode.png" alt="tuya-openclaw-skills微信交流群" width="250" style="display:block; margin:0 auto;">

