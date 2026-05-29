# Home Scenes & Automation

Create smart home scenes that trigger multiple actions with a single command.

---

## What Are Home Scenes?

A "scene" is a collection of device actions that execute together. Examples:

- **Coming Home**: Turn on hallway light + set AC to 24°C + unlock door
- **Bedtime**: Turn off all lights + set AC to sleep mode + lock doors
- **Movie Night**: Dim living room lights to 20% + turn on TV + close curtains
- **Leaving Home**: Turn off all lights + turn off AC + arm security system

---

## Scene Examples

### Scene 1: Coming Home

**Trigger**: Manual command or geofence (when you arrive home)

**Actions**:
1. Turn on hallway light
2. Set living room AC to 24°C (cooling mode)
3. Turn on living room light to 50% brightness

**Implementation**:

```bash
# Get device IDs first
python tuya-smart-control/scripts/tuya_api.py devices

# Execute scene (replace <device_id> with actual IDs)
python tuya-smart-control/scripts/tuya_api.py control <hallway_light_id> '{"switch_led": true}'
python tuya-smart-control/scripts/tuya_api.py control <ac_id> '{"switch": true, "temp": 24, "mode": "cold"}'
python tuya-smart-control/scripts/tuya_api.py control <living_room_light_id> '{"switch_led": true, "bright_value": 500}'
```

**Python Script**:

```python
import sys
sys.path.insert(0, "tuya-smart-control/scripts")
from tuya_api import TuyaAPI

api = TuyaAPI()

# Device IDs (replace with your actual device IDs)
HALLWAY_LIGHT = "bf1234567890abcdef"
LIVING_ROOM_AC = "bf0987654321fedcba"
LIVING_ROOM_LIGHT = "bf1122334455667788"

def coming_home_scene():
    """Turn on lights and set AC when arriving home."""
    print("🏠 Executing 'Coming Home' scene...")
    
    # Hallway light on
    api.issue_properties(HALLWAY_LIGHT, {"switch_led": True})
    print("  ✅ Hallway light: ON")
    
    # AC to 24°C cooling
    api.issue_properties(LIVING_ROOM_AC, {
        "switch": True,
        "temp": 24,
        "mode": "cold"
    })
    print("  ✅ Living room AC: 24°C cooling")
    
    # Living room light to 50%
    api.issue_properties(LIVING_ROOM_LIGHT, {
        "switch_led": True,
        "bright_value": 500  # 0-1000 scale
    })
    print("  ✅ Living room light: 50% brightness")
    
    print("🎉 Welcome home!")

if __name__ == "__main__":
    coming_home_scene()
```

---

### Scene 2: Bedtime

**Trigger**: Manual command or scheduled time (e.g., 11:00 PM)

**Actions**:
1. Turn off all lights
2. Set bedroom AC to 26°C (sleep mode)
3. Turn on night light to 10% brightness

**Python Script**:

```python
def bedtime_scene():
    """Prepare home for sleep."""
    print("🌙 Executing 'Bedtime' scene...")
    
    # Get all devices
    devices = api.get_all_devices()
    
    # Turn off all lights
    for device in devices:
        if device.get("category") == "light" or device.get("category") == "switch":
            try:
                api.issue_properties(device["id"], {"switch_led": False, "switch": False})
                print(f"  ✅ {device['name']}: OFF")
            except:
                pass  # Skip devices that don't support this
    
    # Bedroom AC to sleep mode
    BEDROOM_AC = "bf9988776655443322"
    api.issue_properties(BEDROOM_AC, {
        "switch": True,
        "temp": 26,
        "mode": "sleep"
    })
    print("  ✅ Bedroom AC: 26°C sleep mode")
    
    # Night light to 10%
    NIGHT_LIGHT = "bf5544332211009988"
    api.issue_properties(NIGHT_LIGHT, {
        "switch_led": True,
        "bright_value": 100  # 10% of 1000
    })
    print("  ✅ Night light: 10% brightness")
    
    print("😴 Good night!")
```

---

### Scene 3: Movie Night

**Trigger**: Manual command

**Actions**:
1. Dim living room lights to 20%
2. Turn on TV (via IR control if supported)
3. Close curtains (if motorized)

**Python Script**:

```python
def movie_night_scene():
    """Set up living room for movie watching."""
    print("🎬 Executing 'Movie Night' scene...")
    
    LIVING_ROOM_LIGHT = "bf1122334455667788"
    
    # Dim lights to 20%
    api.issue_properties(LIVING_ROOM_LIGHT, {
        "switch_led": True,
        "bright_value": 200  # 20% of 1000
    })
    print("  ✅ Living room light: 20% brightness")
    
    # Note: TV control via IR requires TuyaCloudAPI and IR hub
    # See SKILL.md for IR control examples
    
    print("🍿 Enjoy your movie!")
```

---

### Scene 4: Leaving Home

**Trigger**: Manual command or geofence (when you leave)

**Actions**:
1. Turn off all lights
2. Turn off all ACs
3. Turn off all plugs (except essential ones like fridge)

**Python Script**:

```python
def leaving_home_scene():
    """Secure home when leaving."""
    print("🚪 Executing 'Leaving Home' scene...")
    
    devices = api.get_all_devices()
    
    # Devices to keep on (e.g., fridge, security camera)
    KEEP_ON = ["fridge", "camera", "router"]
    
    for device in devices:
        # Skip devices that should stay on
        if any(keyword in device["name"].lower() for keyword in KEEP_ON):
            print(f"  ⏭️  {device['name']}: keeping ON")
            continue
        
        # Turn off lights, ACs, and plugs
        if device.get("category") in ["light", "switch", "ac", "plug"]:
            try:
                api.issue_properties(device["id"], {
                    "switch_led": False,
                    "switch": False
                })
                print(f"  ✅ {device['name']}: OFF")
            except:
                pass
    
    print("👋 See you later!")
```

---

## Advanced: Event-Driven Automation

Combine device monitoring with automatic scene triggering.

### Example: Turn on hallway light when door opens

```python
import asyncio
import sys
sys.path.insert(0, "tuya-smart-control/scripts")
from tuya_api import TuyaAPI, TuyaDeviceMQClient

api = TuyaAPI()

DOOR_SENSOR = "bf1234567890abcdef"
HALLWAY_LIGHT = "bf0987654321fedcba"

async def door_automation():
    """Turn on hallway light when door opens."""
    client = TuyaDeviceMQClient(
        api_key=os.environ["TUYA_API_KEY"],
        device_ids=[DOOR_SENSOR]
    )
    
    @client.on_property_change
    async def on_door_change(device_id, properties):
        for prop in properties:
            if prop["code"] == "doorcontact_state" and prop["value"] == True:
                print("🚪 Door opened — turning on hallway light")
                api.issue_properties(HALLWAY_LIGHT, {"switch_led": True})
            
            elif prop["code"] == "doorcontact_state" and prop["value"] == False:
                print("🚪 Door closed — turning off hallway light after 30s")
                await asyncio.sleep(30)
                api.issue_properties(HALLWAY_LIGHT, {"switch_led": False})
    
    await client.connect()

if __name__ == "__main__":
    asyncio.run(door_automation())
```

---

## Scheduling Scenes

Use cron jobs or task schedulers to run scenes at specific times.

### Example: Bedtime scene at 11 PM every day

**Linux/macOS (cron)**:
```bash
# Edit crontab
crontab -e

# Add this line to run bedtime scene at 11 PM daily
0 23 * * * cd /path/to/botlab && python scenes/bedtime.py
```

**Windows (Task Scheduler)**:
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 23:00
4. Action: Start program `python` with arguments `scenes/bedtime.py`

---

## Scene Organization

Create a `scenes/` directory to organize your automation scripts:

```
botlab/
├── scenes/
│   ├── coming_home.py
│   ├── bedtime.py
│   ├── movie_night.py
│   ├── leaving_home.py
│   └── door_automation.py
├── tuya-smart-control/
│   └── scripts/
│       └── tuya_api.py
└── .env
```

---

## Tips for Building Scenes

1. **Test individual commands first** — make sure each device responds correctly before combining them
2. **Add delays between commands** — some devices need time to process; add `time.sleep(0.5)` between actions
3. **Handle errors gracefully** — wrap each action in try/except so one failure doesn't stop the whole scene
4. **Use descriptive device names** — makes scripts easier to read and maintain
5. **Document your scenes** — add comments explaining what each scene does and when to use it
6. **Start simple** — begin with 2-3 actions per scene, then expand as you learn

---

## Troubleshooting Scenes

### Scene runs but some devices don't respond
- Check device is online: `python tuya_api.py device_detail <device_id>`
- Verify property names match your device's Thing Model
- Add delays between commands

### "Permission Denied" errors
- Ensure your Cloud Project has API permissions enabled
- Check that devices are linked to your app account

### Scene runs too slowly
- Reduce number of devices in scene
- Use batch control if available
- Check network latency

---

## Next Steps

- **[QUICKSTART.md](../../QUICKSTART.md)** — Basic setup and device control
- **[TUYA_CLOUD_SETUP.md](TUYA_CLOUD_SETUP.md)** — Cloud Project configuration
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — Fix common problems
- **[SKILL.md](../SKILL.md)** — Full API reference
