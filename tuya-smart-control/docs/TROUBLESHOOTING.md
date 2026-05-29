# Troubleshooting

Common issues and solutions for Tuya Smart Home with OpenClaw.

---

## Setup Issues

### "No credentials configured at all!"

**Problem**: `check_setup.py` reports no credentials found.

**Solution**:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and fill in at least one credential set:
   - **Recommended**: `TUYA_ACCESS_ID` + `TUYA_ACCESS_SECRET` + `TUYA_ENDPOINT`
   - **Legacy**: `TUYA_API_KEY`
3. Re-run `check_setup.py`

---

### "Missing Tuya Cloud credentials"

**Problem**: `TuyaCloudAPI` raises `ValueError: Missing Tuya Cloud credentials`.

**Solution**:
1. Ensure `TUYA_ACCESS_ID` and `TUYA_ACCESS_SECRET` are set in `.env`
2. Check for typos or extra spaces in the values
3. Verify you copied from the correct Cloud Project in [Tuya IoT Platform](https://iot.tuya.com/)

---

### "Missing Tuya Cloud endpoint"

**Problem**: `TuyaCloudAPI` raises `ValueError: Missing Tuya Cloud endpoint`.

**Solution**:
1. Set `TUYA_ENDPOINT` in `.env` to match your Cloud Project's data center
2. Common endpoints:
   - China: `https://openapi.tuyacn.com`
   - US West: `https://openapi.tuyaus.com`
   - Europe: `https://openapi.tuyaeu.com`

---

### "Cannot determine data center from API key prefix"

**Problem**: Using `TUYA_API_KEY` but the prefix isn't recognized.

**Solution**:
1. Check your API key format: should be `sk-<PREFIX><rest>`
2. Supported prefixes: `AY`, `AZ`, `EU`, `IN`, `UE`, `WE`, `SG`
3. If your prefix isn't listed, set `TUYA_BASE_URL` manually in `.env`

---

## API Connectivity Issues

### "Cloud OpenAPI token — Invalid client_id"

**Problem**: Token request fails with "Invalid client_id" or error code 1010.

**Solution**:
1. Double-check `TUYA_ACCESS_ID` matches your Cloud Project's Access ID exactly
2. Ensure no extra spaces or newlines in the value
3. Verify the Cloud Project is active (not suspended or deleted)
4. Check that you're using the correct `TUYA_ENDPOINT` for your project's data center

---

### "Cloud OpenAPI token — Sign invalid"

**Problem**: Token request fails with signature validation error.

**Solution**:
1. Verify `TUYA_ACCESS_SECRET` is correct
2. Check your system clock is synchronized (NTP)
3. Ensure no special characters in the secret got corrupted during copy-paste

---

### "Bearer API — Token invalid/expired"

**Problem**: Using `TUYA_API_KEY` but getting token errors.

**Solution**:
1. The Bearer API key doesn't expire, but the session might
2. Check your network connection
3. Verify the API key is still active in [tuya.ai](https://tuya.ai/) or [tuyasmart.com](https://tuyasmart.com/)
4. Try regenerating the API key if issues persist

---

### "Unable to connect to Tuya API"

**Problem**: Connection errors or timeouts.

**Solution**:
1. Check your internet connection
2. Verify the endpoint URL is correct and reachable:
   ```bash
   curl -I https://openapi.tuyacn.com
   ```
3. Check for firewall or proxy blocking outbound HTTPS
4. Try a different DNS server (e.g., 8.8.8.8)

---

## Device Issues

### No devices showing in list

**Problem**: `tuya_api.py devices` returns empty list or no devices.

**Solution**:
1. **For Cloud API (Access ID/Secret)**:
   - Verify you linked your app account to the Cloud Project
   - Go to IoT Platform → Devices → Link Tuya App Account
   - Scan the QR code with your Tuya Smart / Smart Life app
   - Wait 2-3 minutes for devices to sync

2. **For Bearer API (TUYA_API_KEY)**:
   - Ensure the API key region matches your app account region
   - Check that devices are added in the Tuya Smart / Smart Life app

---

### "Device does not exist" (error 40000901)

**Problem**: Trying to control a device that doesn't exist or you don't have permission.

**Solution**:
1. Re-fetch the device list: `python tuya_api.py devices`
2. Verify the `device_id` is correct (no typos)
3. Check that the device is linked to your account
4. If device was recently added, wait a few minutes for it to appear

---

### Device is offline

**Problem**: `device_detail` shows `"online": false`.

**Solution**:
1. Check the device's power supply
2. Verify Wi-Fi signal strength at the device location
3. Restart the device (unplug/replug or toggle power)
4. Check if your router is blocking the device's MAC address
5. Re-pair the device if it still won't connect

---

### "Control command sent but device doesn't respond"

**Problem**: API returns success but device state doesn't change.

**Solution**:
1. Check device is online: `python tuya_api.py device_detail <device_id>`
2. Verify property names match the device's Thing Model:
   ```bash
   python tuya_api.py model <device_id>
   ```
3. Check property value ranges (e.g., brightness 0-1000, not 0-100)
4. Some devices have a delay — wait 2-3 seconds and check again
5. Try controlling via the Tuya Smart app to verify the device works

---

## Property Control Issues

### "Property not found" or "Invalid property"

**Problem**: Trying to set a property that doesn't exist on the device.

**Solution**:
1. Query the device's Thing Model:
   ```bash
   python tuya_api.py model <device_id>
   ```
2. Parse the `model` JSON string to see available properties
3. Use exact property codes (e.g., `switch_led`, not `switch`)
4. Check `accessMode` — `ro` properties are read-only

---

### "Value out of range"

**Problem**: Property value is outside the allowed range.

**Solution**:
1. Check the Thing Model for `typeSpec` min/max values
2. Common ranges:
   - Brightness: 0-1000 (not 0-100)
   - Temperature: device-specific (e.g., 16-30 for AC)
   - Color temp: 0-1000 or 2700-6500 (Kelvin)
3. Clamp your values to the valid range

---

### Enum property doesn't accept value

**Problem**: Trying to set an enum property with an invalid value.

**Solution**:
1. Check the Thing Model for allowed enum values
2. Example for AC mode:
   ```json
   "typeSpec": {"type": "enum", "range": ["auto", "cold", "hot", "wet", "wind"]}
   ```
3. Use exact string values (case-sensitive)

---

## Notification Issues

### "No bound contact for current user" (error 10011)

**Problem**: Trying to send SMS/voice/email but no contact info is bound.

**Solution**:
1. Open Tuya Smart / Smart Life app
2. Go to Profile → Settings → Account
3. Bind your phone number and/or email address
4. Verify the contact info
5. Retry the notification

---

### Notifications not received

**Problem**: API returns success but notification doesn't arrive.

**Solution**:
1. Check spam/junk folders (email)
2. Verify phone number includes country code (SMS/voice)
3. Check notification permissions in phone settings (push)
4. Wait up to 5 minutes for delivery
5. Check IoT Platform logs for delivery status

---

## WebSocket / Real-Time Issues

### WebSocket connection fails

**Problem**: `TuyaDeviceMQClient` can't connect.

**Solution**:
1. Ensure `websockets` is installed: `pip install websockets`
2. Check `TUYA_API_KEY` is set and valid
3. Verify network allows outbound WSS connections
4. Check firewall isn't blocking WebSocket traffic

---

### No events received

**Problem**: Connected but no property changes or status updates.

**Solution**:
1. Verify device IDs are correct (or use `None` for all devices)
2. Check devices are online and actively reporting
3. Trigger a manual change (e.g., turn light on/off via app)
4. Check IoT Platform logs for message delivery

---

## Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 1010 | Token invalid/expired | Refresh token or check credentials |
| 10011 | No bound contact | Bind phone/email in app |
| 40000901 | Device not found | Verify device_id and permissions |
| 1106 | Permission denied | Check API authorization in IoT Platform |
| 500 | Server error | Retry after delay; check Tuya status page |
| 429 | Rate limited | Wait and retry; reduce request frequency |

---

## Debugging Tips

### Enable verbose logging

Add debug output to see what's happening:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check IoT Platform logs

1. Go to [Tuya IoT Platform](https://iot.tuya.com/)
2. Navigate to your Cloud Project → Logs
3. Filter by time range and API endpoint
4. Look for error codes and request details

### Test with curl

Verify API connectivity directly:

```bash
# Test endpoint reachability
curl -I https://openapi.tuyacn.com

# Test token endpoint (replace with your credentials)
curl -X GET "https://openapi.tuyacn.com/v1.0/token?grant_type=1" \
  -H "client_id: YOUR_ACCESS_ID" \
  -H "sign: COMPUTED_SIGNATURE" \
  -H "t: TIMESTAMP" \
  -H "sign_method: HMAC-SHA256"
```

### Inspect device Thing Model

```bash
# Get raw Thing Model
python tuya_api.py model <device_id> | jq -r '.result.model' | jq

# Check specific property
python tuya_api.py model <device_id> | jq -r '.result.model' | jq '.properties[] | select(.code == "switch_led")'
```

---

## Getting Help

If you've tried everything above and still have issues:

1. **Check the docs**:
   - [QUICKSTART.md](../../QUICKSTART.md)
   - [TUYA_CLOUD_SETUP.md](TUYA_CLOUD_SETUP.md)
   - [SKILL.md](../SKILL.md)

2. **Search issues**: [GitHub Issues](https://github.com/emmaoops7/botlab/issues)

3. **Open a new issue** with:
   - Error message and code
   - `check_setup.py` output (with secrets redacted)
   - Steps to reproduce
   - Device category and model (if device-specific)

4. **Community support**:
   - Discord: scan QR in README
   - WeChat: scan QR in README

---

## Security Reminders

- **Never share** your Access ID, Access Secret, or API Key in issues or logs
- **Redact secrets** before posting output: replace with `***` or `REDACTED`
- **Rotate credentials** if you accidentally expose them
- **Check `.gitignore`** includes `.env` before committing
