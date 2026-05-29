# Quick Start — Tuya Smart Home with OpenClaw

Get your Tuya smart home up and running with OpenClaw in about 15 minutes.

---

## What You'll Need

- A Tuya-compatible smart device (light, plug, AC, camera, etc.)
- The **Tuya Smart** or **Smart Life** app on your phone
- A computer with **Python 3.7+** installed
- An OpenClaw instance (or just this repo for standalone use)

---

## Step 1: Set Up Your Tuya Account & Devices

1. Download the **Tuya Smart** or **Smart Life** app (iOS / Android)
2. Create an account and sign in
3. Add your smart devices using the app (follow the device's pairing instructions)
4. Organize devices into rooms (e.g., "Living Room", "Bedroom") — this makes voice control easier later

> **Tip:** Give your devices clear, descriptive names like "Living Room Light" instead of "Smart Bulb 0x3F".

---

## Step 2: Create a Tuya IoT Cloud Project

This gives you API access to control your devices programmatically.

1. Go to [Tuya IoT Platform](https://iot.tuya.com/) and sign in with the **same account** you use in the app
2. Click **Cloud** → **Development** → **Create Cloud Project**
3. Fill in:
   - **Project Name**: anything you like (e.g., "My Smart Home")
   - **Development Method**: Smart Home
   - **Data Center**: choose the region matching your app account (China / US / Europe / etc.)
4. After creation, go to **Authorization Key** — you'll see:
   - **Access ID** (also called Client ID)
   - **Access Secret** (also called Client Secret)
5. Keep this page open — you'll need these values in Step 4

> **Important:** The Data Center you select determines your `TUYA_ENDPOINT`. See the mapping below.

### Data Center → Endpoint Mapping

| Region | TUYA_ENDPOINT |
|--------|---------------|
| China | `https://openapi.tuyacn.com` |
| US West | `https://openapi.tuyaus.com` |
| Central Europe | `https://openapi.tuyaeu.com` |
| India | `https://openapi.tuyain.com` |
| US East | `https://openapi-ueaz.tuyaus.com` |
| Western Europe | `https://openapi-weaz.tuyaeu.com` |
| Singapore | `https://openapi-sg.iotbing.com` |

---

## Step 3: Link Your App Account to the Cloud Project

Your Cloud Project needs permission to see your app's devices.

1. In your Cloud Project, go to **Devices** → **Link Tuya App Account**
2. Click **Add App Account** — a QR code will appear
3. Open the **Tuya Smart** / **Smart Life** app on your phone
4. Go to **Profile** → tap the settings icon (⚙️) → **Scan QR Code** (or "Third-party Voice Services")
5. Scan the QR code from the IoT Platform
6. Confirm the authorization

> After linking, your app devices will appear in the Cloud Project's device list.

---

## Step 4: Configure Your Environment

1. Clone this repo (or download it):
   ```bash
   git clone https://github.com/emmaoops7/botlab.git
   cd botlab
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and fill in your values:
   ```bash
   # Required — from your Cloud Project's Authorization Key page
   TUYA_ACCESS_ID=your_access_id_here
   TUYA_ACCESS_SECRET=your_access_secret_here
   TUYA_ENDPOINT=https://openapi.tuyacn.com   # match your data center

   # Optional — your Tuya user ID (found in IoT Platform → Users)
   TUYA_UID=

   # Optional — legacy Bearer API key (from tuya.ai or tuyasmart.com)
   TUYA_API_KEY=
   ```

> **Security:** Never commit `.env` with real values. It's already in `.gitignore`.

---

## Step 5: Install Dependencies

```bash
pip install -r tuya-smart-control/scripts/requirements.txt
```

This installs `requests` (required) and `websockets` (optional, for real-time events).

---

## Step 6: Verify Your Setup

Run the setup checker:

```bash
python tuya-smart-control/scripts/check_setup.py
```

You should see:
```
🐍 Python Environment
  ✅ Python version ≥ 3.7 — running 3.11.x

📦 Required Packages
  ✅ requests — v2.31.0
  ⚠️ websockets — not installed (optional)

🔑 Environment Variables
  ✅ TUYA_ACCESS_ID — abcd***ef
  ✅ TUYA_ACCESS_SECRET — 1234***89
  ✅ TUYA_ENDPOINT — https://openapi.tuyacn.com
  ⚠️ TUYA_UID — not set (optional)

🌐 API Connectivity
  ✅ Cloud OpenAPI token — got token eyJhbG***

🎉 All checks passed! You're ready to use Tuya Smart Home.
```

If something fails, check [TROUBLESHOOTING.md](tuya-smart-control/docs/TROUBLESHOOTING.md).

---

## Step 7: List Your Devices

```bash
# Using the Cloud API (recommended)
python tuya-smart-control/scripts/tuya_api.py homes
python tuya-smart-control/scripts/tuya_api.py devices
```

You should see your homes and devices listed as JSON. Note the `device_id` values — you'll need them for control commands.

---

## Step 8: Control a Device

```bash
# Turn on a light
python tuya-smart-control/scripts/tuya_api.py control <device_id> '{"switch_led": true}'

# Set brightness to 50%
python tuya-smart-control/scripts/tuya_api.py control <device_id> '{"bright_value": 500}'

# Check device status
python tuya-smart-control/scripts/tuya_api.py device_detail <device_id>
```

---

## Step 9: Set Up Home Scenes (Optional)

You can create automation scenes like "Coming Home" or "Bedtime":

- **Coming Home**: Turn on hallway light + set AC to 24°C
- **Bedtime**: Turn off all lights + lock doors (if supported) + set AC to sleep mode

See [HOME_SCENES.md](tuya-smart-control/docs/HOME_SCENES.md) for detailed scene configuration examples.

---

## Step 10: Use with OpenClaw (Optional)

If you're running OpenClaw, install this as a skill:

1. Add the `tuya-smart-control` skill in your OpenClaw configuration
2. Set the environment variables in your OpenClaw env config
3. Start chatting: "Turn on the living room light" / "What's the temperature?"

---

## What's Next?

- **[TUYA_CLOUD_SETUP.md](tuya-smart-control/docs/TUYA_CLOUD_SETUP.md)** — Detailed Cloud Project setup guide
- **[HOME_SCENES.md](tuya-smart-control/docs/HOME_SCENES.md)** — Scene and automation examples
- **[TROUBLESHOOTING.md](tuya-smart-control/docs/TROUBLESHOOTING.md)** — Common issues and fixes
- **[SKILL.md](tuya-smart-control/SKILL.md)** — Full API reference and workflow documentation

---

## Quick Reference

| Task | Command |
|------|---------|
| Check setup | `python tuya-smart-control/scripts/check_setup.py` |
| List homes | `python tuya-smart-control/scripts/tuya_api.py homes` |
| List devices | `python tuya-smart-control/scripts/tuya_api.py devices` |
| Device detail | `python tuya-smart-control/scripts/tuya_api.py device_detail <id>` |
| Control device | `python tuya-smart-control/scripts/tuya_api.py control <id> '{"key": value}'` |
| Weather | `python tuya-smart-control/scripts/tuya_api.py weather <lat> <lon>` |
| Help | `python tuya-smart-control/scripts/tuya_api.py --help` |
