# Tuya Cloud Project Setup Guide

This guide walks you through creating and configuring a Tuya IoT Cloud Project for API access.

---

## Prerequisites

- A Tuya Smart or Smart Life app account with at least one device added
- Access to a web browser

---

## Step 1: Register for Tuya IoT Platform

1. Go to [https://iot.tuya.com/](https://iot.tuya.com/)
2. Click **Sign Up** (or **Log In** if you already have an account)
3. Use the **same email/phone** as your Tuya Smart / Smart Life app account
4. Complete email/phone verification

> **Important:** Your IoT Platform account must match your app account region. If you registered in the China app, use the China IoT Platform.

---

## Step 2: Create a Cloud Project

1. After logging in, click **Cloud** in the top navigation
2. Click **Development** in the left sidebar
3. Click **Create Cloud Project**
4. Fill in the form:

   | Field | Value |
   |-------|-------|
   | **Project Name** | Any descriptive name (e.g., "My Smart Home API") |
   | **Development Method** | **Smart Home** |
   | **Data Center** | Choose the region matching your app account |

5. Click **Create**

### Choosing the Right Data Center

Your Data Center selection is critical — it must match where your app account is registered:

| App Region | Data Center | Endpoint |
|------------|-------------|----------|
| China (涂鸦智能) | China | `https://openapi.tuyacn.com` |
| US / Canada | US West | `https://openapi.tuyaus.com` |
| Europe (EU) | Central Europe | `https://openapi.tuyaeu.com` |
| India | India | `https://openapi.tuyain.com` |
| US East | US East | `https://openapi-ueaz.tuyaus.com` |
| Western Europe | Western Europe | `https://openapi-weaz.tuyaeu.com` |
| Southeast Asia | Singapore | `https://openapi-sg.iotbing.com` |

> **Tip:** If you're unsure which region your app account is in, check the app's settings or try the most common one for your country.

---

## Step 3: Get Your Access Credentials

1. After creating the project, you'll be taken to the project dashboard
2. Click **Authorization Key** in the left sidebar (or find it on the Overview page)
3. You'll see two important values:

   - **Access ID** (also called **Client ID**)
   - **Access Secret** (also called **Client Secret**)

4. Copy both values and store them securely
5. These are your `TUYA_ACCESS_ID` and `TUYA_ACCESS_SECRET`

> **Security:** Treat these like passwords. Never commit them to version control or share them publicly.

---

## Step 4: Link Your App Account

Your Cloud Project needs permission to access your app's devices.

1. In your Cloud Project, click **Devices** in the left sidebar
2. Click **Link Tuya App Account** (or **Authorize App Account**)
3. Click **Add App Account**
4. A QR code will appear on screen
5. On your phone:
   - Open the **Tuya Smart** or **Smart Life** app
   - Go to **Profile** (bottom right)
   - Tap the **Settings** icon (⚙️, top right)
   - Look for **Scan QR Code**, **Third-party Voice Services**, or **Link with Cloud**
   - Scan the QR code displayed on your computer screen
6. Confirm the authorization in the app

### Verify the Link

After linking:
- The IoT Platform should show your app account as "Authorized"
- Your devices should appear in the **Devices** list within a few minutes
- You can click on individual devices to see their details

> **Troubleshooting:** If devices don't appear, wait 2-3 minutes and refresh. If still nothing, check that you scanned with the correct app account.

---

## Step 5: Enable Required APIs

Some APIs require explicit activation:

1. In your Cloud Project, click **API** in the left sidebar
2. Browse or search for the APIs you need:
   - **Device Management** — for listing and controlling devices
   - **Home Management** — for querying homes and rooms
   - **Message Push** — for sending notifications
   - **Infrared Control** — for IR hub control (if you have one)
3. Click **Subscribe** or **Activate** for each API you want to use

> Most basic device control APIs are enabled by default. You only need to manually enable specialized APIs like IR control or advanced statistics.

---

## Step 6: Configure API Permissions

1. Click **Authorization** → **API Authorization** in the left sidebar
2. Review the permissions granted to your project
3. Ensure the following are allowed:
   - Read device information
   - Control devices
   - Query device status
   - Send notifications (if needed)

> If you see "Permission Denied" errors later, come back here and check permissions.

---

## Step 7: Test Your Setup

Use the `check_setup.py` script to verify everything works:

```bash
# Set your environment variables first
export TUYA_ACCESS_ID="your_access_id"
export TUYA_ACCESS_SECRET="your_access_secret"
export TUYA_ENDPOINT="https://openapi.tuyacn.com"  # match your data center

# Run the checker
python tuya-smart-control/scripts/check_setup.py
```

Expected output:
```
✅ TUYA_ACCESS_ID — abcd***ef
✅ TUYA_ACCESS_SECRET — 1234***89
✅ TUYA_ENDPOINT — https://openapi.tuyacn.com
✅ Cloud OpenAPI token — got token eyJhbG***
```

---

## Step 8: Find Your Tuya UID (Optional)

Some advanced APIs require your Tuya User ID:

1. In the IoT Platform, click **Users** in the left sidebar
2. Find your account in the list
3. The **UID** column shows your numeric user ID
4. This is your `TUYA_UID` value

> Most basic operations don't require UID. You can skip this step unless a specific API asks for it.

---

## Common Issues

### "Invalid client_id" Error
- Double-check your Access ID is copied correctly (no extra spaces)
- Ensure you're using the right Data Center endpoint

### "Permission Denied" Error
- Go to **API Authorization** and ensure the required APIs are enabled
- Check that your app account is properly linked

### No Devices Showing
- Verify you linked the correct app account (same email/phone)
- Wait a few minutes for devices to sync
- Try refreshing the device list in the IoT Platform

### "Token Expired" Error
- Access tokens expire after 2 hours
- The SDK automatically refreshes tokens — this error usually means a network issue
- Check your internet connection and endpoint URL

---

## Next Steps

- **[QUICKSTART.md](../../QUICKSTART.md)** — Continue with device control
- **[HOME_SCENES.md](HOME_SCENES.md)** — Set up automation scenes
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — Fix common problems

---

## Security Best Practices

1. **Never commit `.env`** — it's already in `.gitignore`
2. **Rotate credentials** — if you suspect your Access Secret is compromised, regenerate it in the IoT Platform
3. **Use environment variables** — don't hardcode credentials in scripts
4. **Limit permissions** — only enable the APIs you actually need
5. **Monitor usage** — check the IoT Platform's **Logs** section for unusual activity

---

## Getting Help

- **Tuya IoT Documentation**: [https://developer.tuya.com/en/docs/iot/](https://developer.tuya.com/en/docs/iot/)
- **Tuya Developer Forum**: [https://developer.tuya.com/en/](https://developer.tuya.com/en/)
- **This Repo Issues**: [https://github.com/emmaoops7/botlab/issues](https://github.com/emmaoops7/botlab/issues)
