# tuya-smart-control — OpenClaw Smart Home Skill

tuya-smart-control is an AI Agent skill for the [OpenClaw](https://openclaw.ai) platform, built on the [Tuya Open Platform](https://developer.tuya.com/) 2C End-User API. Once installed, the AI Agent can perform smart home device querying, control, notifications, weather queries, data statistics, and more through natural language.

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

---

## Getting Started

### 1. Obtain an API Key

| User Type | Where to Get |
|-----------|-------------|
| China Mainland | [smartlife.ai](https://tuyasmart.com/) |
| International | [tuya.ai](https://tuya.ai/) |

> The API Key format is `sk-<PREFIX><rest>`, where the prefix is used to automatically identify the data center. Make sure the API Key region matches your Tuya account registration region.

### 2. API Key Prefix to Data Center Mapping

The first two characters after `sk-` in the API Key are automatically mapped to the corresponding data center:

| Prefix | Region | Base URL |
|--------|--------|----------|
| `AY` | China Data Center | `https://openapi.tuyacn.com` |
| `AZ` | US West Data Center | `https://openapi.tuyaus.com` |
| `EU` | Central Europe Data Center | `https://openapi.tuyaeu.com` |
| `IN` | India Data Center | `https://openapi.tuyain.com` |
| `UE` | US East Data Center | `https://openapi-ueaz.tuyaus.com` |
| `WE` | Western Europe Data Center | `https://openapi-weaz.tuyaeu.com` |
| `SG` | Singapore Data Center | `https://openapi-sg.iotbing.com` |

### 3. Install the Skill in OpenClaw

1. Add the `tuya-smart-control` skill on the OpenClaw platform
2. Enter your `TUYA_API_KEY` in the skill configuration (required)
3. Once installed, the AI Agent automatically gains smart home control capabilities

**Prerequisites:**
- Python 3.7+
- `requests` library (`pip install requests`)

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
weather = api.get_weather(lat="39.9042", lon="116.4074")

# Send SMS notification
api.send_sms("Alert: Living room light is offline")
```

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
python3 tuya_api.py weather 39.9042 116.4074

# Notifications
python3 tuya_api.py sms "Reminder message"
python3 tuya_api.py voice "Voice message"
python3 tuya_api.py mail "Email Subject" "Email body"
python3 tuya_api.py push "Push Title" "Push content"

# Data Statistics
python3 tuya_api.py stats_config                       # Query statistics config
python3 tuya_api.py stats_data <dev_id> ele_usage SUM 2026031600 2026031623
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
- **Video/Camera** — Pull live video streams, view recordings, capture screenshots
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
│   └── tuya_api.py                # Python SDK + CLI tool
└── references/                    # API reference documents
    ├── home-and-space.md          # Home and space management
    ├── device-query.md            # Device query
    ├── device-control.md          # Device control
    ├── device-management.md       # Device management
    ├── weather.md                 # Weather service
    ├── notifications.md           # Notifications
    └── statistics.md              # Data statistics
```

---

## License

MIT
