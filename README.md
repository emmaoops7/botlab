# tuya-smart-control — OpenClaw Smart Home Skill

tuya-smart-control is an official AI Agent skill for the OpenClaw platform, built on Tuya's 2C end-user APIs. It brings developers the industry's broadest AI + device interaction capabilities — 3,000+ smart hardware categories, covering 200+ countries and regions, enabling AI Agents to control everything out of the box. Get started with one click at tuya.ai — no complex authentication required. Once installed, use natural language to query devices, control smart hardware, send notifications, check weather, view data statistics, and more.

> **Trial Notice**
>
> All currently available API endpoints are in a **trial phase**. Each endpoint is subject to rate limits, call quotas, and other usage restrictions. Specific limits will be updated progressively — please watch this repository for announcements. If you encounter rate limiting or quota errors, please retry after a short delay.

---

## Feature Overview

| Module | Capabilities | Description |
|--------|-------------|-------------|
| Home Management | List all homes, list rooms in a home | Retrieve home and room hierarchy |
| Device Query | All devices, by home, by room, single device detail | Includes current property states |
| Device Control | Query Thing Model, issue property commands | Supports switch, brightness, temperature, mode, etc. |
| Device Management | Rename device | Update device display name |
| Weather Service | Current weather and hourly forecast | Temperature, humidity, conditions, and more |
| Notifications | SMS, voice call, email, App push | Self-send only (to the current logged-in user) |
| Data Statistics | Hourly statistics config and data query | Energy usage and other metric analysis |
| IPC Cloud Capture | Cloud snapshot and short video capture | Capture images/videos from IPC cameras and get playable URLs |
| IPC Visual Recognition | Camera scene understanding | Capture a snapshot and send it to an AI vision model for content description |
| Device Message Subscription | Real-time property change and online/offline event monitoring via WebSocket | Event-driven automation, real-time dashboards, status alerts |

---

## Getting Started

### 1. Obtain an API Key

| User Type | Where to Get |
|-----------|-------------|
| China Mainland | [tuyasmart.com](https://tuyasmart.com/) |
| International | [tuya.ai](https://tuya.ai/) |

> The API Key format is `sk-<PREFIX><rest>`, where the prefix is used to automatically identify the data center. Make sure the API Key region matches your Tuya account registration region.

### 2. API Key Prefix to Data Center Mapping

The first two characters after `sk-` in the API Key are automatically mapped to the corresponding data center:

| Prefix | Region | REST API Base URL | WebSocket URI |
|--------|--------|----------|---------------|
| `AY` | China Data Center | `https://openapi.tuyacn.com` | `wss://wsmsgs.tuyacn.com` |
| `AZ` | US West Data Center | `https://openapi.tuyaus.com` | `wss://wsmsgs.iot-wus.com` |
| `EU` | Central Europe Data Center | `https://openapi.tuyaeu.com` | `wss://wsmsgs.iot-eu.com` |
| `IN` | India Data Center | `https://openapi.tuyain.com` | `wss://wsmsgs.iot-ap.com` |
| `UE` | US East Data Center | `https://openapi-ueaz.tuyaus.com` | `wss://wsmsgs.iot-eus.com` |
| `WE` | Western Europe Data Center | `https://openapi-weaz.tuyaeu.com` | `wss://wsmsgs.iot-weu.com` |
| `SG` | Singapore Data Center | `https://openapi-sg.iotbing.com` | `wss://wsmsgs.iot-sea.com` |

### 3. Install the Skill in OpenClaw

1. Add the `tuya-smart-control` skill on the OpenClaw platform
2. Enter your `TUYA_API_KEY` in the skill configuration (required)
3. Once installed, the AI Agent automatically gains smart home control capabilities

**Prerequisites:**
- Python 3.7+
- `requests` library (`pip install requests`)
- `websockets` library (`pip install websockets`) — for real-time device message subscription

---

## Usage

### Natural Language Interaction (Recommended)

After the skill is installed, users can interact with the AI Agent using natural language:

- "Turn on the living room light"
- "Set the AC temperature to 26 degrees"
- "What's the weather today?"
- "Send me an SMS reminder"
- "Rename the bedroom light to bedside lamp"
- "Check this month's electricity usage"
- "Take a snapshot from the front door camera"
- "Record a 5-second video from the living room camera"
- "What's in front of the door camera?"
- "Is there anyone at the front door?"
- "Monitor all device status changes in real time"
- "Notify me when the living room light goes offline"
- "Turn on the hallway light automatically when the door opens"

### Python SDK

The skill includes `scripts/tuya_api.py`, which provides an encapsulated `TuyaAPI` class:

```python
from tuya_api import TuyaAPI

api = TuyaAPI()  # Auto-reads configuration from environment variables

# List all homes
homes = api.get_homes()

# List all devices
devices = api.get_all_devices()

# Get device detail (including current property states)
detail = api.get_device_detail("your_device_id")

# Control device — turn on light and set brightness
result = api.issue_properties("your_device_id", {
    "switch_led": True,
    "bright_value": 500
})

# Query weather
weather = api.get_weather(lat="39.90", lon="116.40")

# Send SMS notification
api.send_sms("Alert: Living room light is offline")

# IPC cloud capture — take a snapshot and get decrypted URL
capture = api.ipc_ai_capture_pic_allocate_and_fetch("your_device_id", user_privacy_consent_accepted=True)

# IPC cloud capture — record a 5-second video
video = api.ipc_ai_capture_video_allocate_and_fetch("your_device_id", video_duration_seconds=5, user_privacy_consent_accepted=True)
```

### Real-Time Device Message Subscription

The skill includes `scripts/tuya_device_mq_client.py`, a WebSocket client for subscribing to real-time device events. It uses the same `TUYA_API_KEY` — the WebSocket URI is auto-detected from the key prefix.

```python
import asyncio
import os
from tuya_device_mq_client import TuyaDeviceMQClient

async def main():
    client = TuyaDeviceMQClient(api_key=os.environ["TUYA_API_KEY"])

    @client.on_property_change
    async def on_prop(device_id, properties):
        for prop in properties:
            t = TuyaDeviceMQClient.format_timestamp(prop["time"])
            print(f"[{t}] Device {device_id}: {prop['code']} = {prop['value']}")

    @client.on_online_status
    async def on_status(device_id, status, timestamp_ms):
        t = TuyaDeviceMQClient.format_timestamp(timestamp_ms)
        print(f"[{t}] Device {device_id} is now {status}")

    await client.connect()

asyncio.run(main())
```

Key features:
- **Decorator-style handler registration** — `@client.on_property_change`, `@client.on_online_status`, `@client.on_raw_message`
- **Device filtering** — pass `device_ids=["id1", "id2"]` to monitor specific devices only
- **Auto-reconnect** — automatically reconnects on transient failures; stops on fatal close codes
- **Event-driven automation** — combine with `TuyaAPI` to trigger device control or notifications on events (notification throttling of 30+ minutes is mandatory)

### Command-Line Tool

```bash
# Home & Devices
python3 tuya_api.py homes                              # List all homes
python3 tuya_api.py rooms <home_id>                    # List rooms in a home
python3 tuya_api.py devices                            # List all devices
python3 tuya_api.py home_devices <home_id>             # List devices in a home
python3 tuya_api.py room_devices <room_id>             # List devices in a room
python3 tuya_api.py device_detail <device_id>          # Get device detail

# Device Control
python3 tuya_api.py model <device_id>                  # Query device Thing Model
python3 tuya_api.py control <device_id> '{"switch_led":true,"bright_value":500}'

# Device Management
python3 tuya_api.py rename <device_id> "New Name"

# Weather
python3 tuya_api.py weather 39.90 116.40

# Notifications
python3 tuya_api.py sms "Reminder message"
python3 tuya_api.py voice "Voice message"
python3 tuya_api.py mail "Email Subject" "Email body"
python3 tuya_api.py push "Push Title" "Push content"

# Data Statistics
python3 tuya_api.py stats_config                       # Query statistics config
python3 tuya_api.py stats_data <dev_id> ele_usage SUM 2026031600 2026031623

# IPC Cloud Capture
python3 tuya_api.py ipc_pic_fetch <device_id> 1              # Snapshot (consent=1 for decrypted URL)
python3 tuya_api.py ipc_video_fetch <device_id> 5 1           # 5-second video (consent=1)
```

---

## API Reference

All endpoints use unified authentication: `Authorization: Bearer {Api-key}`

For complete request parameters, response fields, and examples, see the documentation under the `references/` directory:

| Module | Endpoint | Method | Path | Reference |
|--------|----------|--------|------|-----------|
| Home Management | List all homes | GET | `/v1.0/end-user/homes/all` | [home-and-space.md](Tuya%20Smart%20control/references/home-and-space.md) |
| Home Management | List rooms in a home | GET | `/v1.0/end-user/homes/{home_id}/rooms` | [home-and-space.md](Tuya%20Smart%20control/references/home-and-space.md) |
| Device Query | List all devices | GET | `/v1.0/end-user/devices/all` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| Device Query | List devices in a home | GET | `/v1.0/end-user/homes/{home_id}/devices` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| Device Query | List devices in a room | GET | `/v1.0/end-user/homes/room/{room_id}/devices` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| Device Query | Get single device detail | GET | `/v1.0/end-user/devices/{device_id}/detail` | [device-query.md](Tuya%20Smart%20control/references/device-query.md) |
| Device Control | Query device Thing Model | GET | `/v1.0/end-user/devices/{device_id}/model` | [device-control.md](Tuya%20Smart%20control/references/device-control.md) |
| Device Control | Issue properties | POST | `/v1.0/end-user/devices/{device_id}/shadow/properties/issue` | [device-control.md](Tuya%20Smart%20control/references/device-control.md) |
| Device Management | Rename device | POST | `/v1.0/end-user/devices/{device_id}/attribute` | [device-management.md](Tuya%20Smart%20control/references/device-management.md) |
| Weather Service | Query weather | GET | `/v1.0/end-user/services/weather/recent` | [weather.md](Tuya%20Smart%20control/references/weather.md) |
| Notifications | Send SMS | POST | `/v1.0/end-user/services/sms/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| Notifications | Send voice call | POST | `/v1.0/end-user/services/voice/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| Notifications | Send email | POST | `/v1.0/end-user/services/mail/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| Notifications | Send App push | POST | `/v1.0/end-user/services/push/self-send` | [notifications.md](Tuya%20Smart%20control/references/notifications.md) |
| Data Statistics | Query statistics config | GET | `/v1.0/end-user/statistics/hour/config` | [statistics.md](Tuya%20Smart%20control/references/statistics.md) |
| Data Statistics | Query statistics data | GET | `/v1.0/end-user/statistics/hour/data` | [statistics.md](Tuya%20Smart%20control/references/statistics.md) |
| IPC Cloud Capture | Allocate cloud capture | POST | `/v1.0/end-user/ipc/{device_id}/capture/allocate` | [ipc-cloud-capture.md](Tuya%20Smart%20control/references/ipc-cloud-capture.md) |
| IPC Cloud Capture | Resolve capture URL | POST | `/v1.0/end-user/ipc/{device_id}/capture/resolve` | [ipc-cloud-capture.md](Tuya%20Smart%20control/references/ipc-cloud-capture.md) |

---

## Supported Features & Limitations

### Supported Property Types

| Type | Description | Examples |
|------|-------------|----------|
| bool | Boolean switch | Light on/off, AC on/off, plug on/off |
| enum | Enumeration selection | AC mode (auto/cool/heat), fan speed (low/mid/high) |
| value | Numeric adjustment | Brightness (0-1000), temperature (16-30) |
| string | String value | Device display text |

### Unsupported Operations

The following operations involve sensitive permissions or complex data types and are **not supported**:

- **Lock control** — Unlock doors, lock/unlock smart locks (security-sensitive)
- **Live video streaming** — Pull real-time video streams or view live camera footage (cloud snapshot/short video capture IS supported)
- **Image operations** — Upload or download device images
- **Complex data type control** — Properties with `raw`, `bitmap`, `struct`, or `array` typeSpec
- **Firmware upgrades** — OTA firmware update operations
- **Device pairing/removal** — Adding new devices or removing existing devices

For these operations, please use the Tuya App directly.

---

## Project Structure

```
tuya-smart-control/
├── SKILL.md                       # OpenClaw Skill definition (with metadata)
├── scripts/
│   ├── tuya_api.py                # Python SDK + CLI tool (REST API)
│   └── tuya_device_mq_client.py   # WebSocket client for real-time device events
└── references/                    # API reference documents
    ├── home-and-space.md          # Home and space management
    ├── device-query.md            # Device query
    ├── device-control.md          # Device control
    ├── device-management.md       # Device management
    ├── device-message.md          # Device message subscription (WebSocket)
    ├── weather.md                 # Weather service
    ├── notifications.md           # Notifications
    ├── statistics.md              # Data statistics
    └── ipc-cloud-capture.md       # IPC cloud capture
```

---

## License

MIT

## Community
Join our communities for support and discussions!

### Discord Server
Scan the QR code to join our Discord community:

<img src="./images/discord-qrcode.png" alt="Discord QR Code" width="250" style="display:block; margin:0 auto;">

### WeChat Group
Scan the QR code to join the WeChat group:

<img src="./images/wechat-group-qrcode.png" alt="WeChat Group QR Code" width="250" style="display:block; margin:0 auto;">
