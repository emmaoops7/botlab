#!/usr/bin/env python3
"""Tuya Smart Home API SDK

Provides the TuyaAPI class, encapsulating all Tuya Open Platform 2C end-user
API call logic. Supports both Python code invocation and command-line mode.

Credentials are read from environment variables. TUYA_API_KEY is required;
TUYA_BASE_URL is optional — the base URL is auto-detected from the API key
prefix (e.g. sk-AY... → China, sk-AZ... → US, sk-EU... → Europe).
"""

import json
import os
import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# API key prefix → data center base URL mapping
_PREFIX_TO_BASE_URL = {
    "AY": "https://openapi.tuyacn.com",   # China Data Center
    "AZ": "https://openapi.tuyaus.com",   # US West Data Center
    "EU": "https://openapi.tuyaeu.com",   # Central Europe Data Center
    "IN": "https://openapi.tuyain.com",   # India Data Center
    "UE": "https://openapi-ueaz.tuyaus.com",  # US East Data Center
    "WE": "https://openapi-weaz.tuyaeu.com",  # Western Europe Data Center
    "SG": "https://openapi-sg.iotbing.com",   # Singapore Data Center
}

# CLI command → minimum required argument count
_COMMAND_ARG_COUNT = {
    "rooms": 1,
    "device_detail": 1, "model": 1, "sms": 1, "voice": 1,
    "control": 2, "rename": 2, "mail": 2, "push": 2,
    "weather": 2, "stats_data": 5,
}


def _resolve_base_url(api_key: str) -> str:
    """Resolve base URL from the API key prefix.

    API key format: sk-<PREFIX><rest>
    Example: sk-AY12c7ee31ae19*********57d → prefix AY → China
    """
    key = api_key
    if key.startswith("sk-"):
        key = key[3:]
    prefix = key[:2].upper()
    if prefix in _PREFIX_TO_BASE_URL:
        return _PREFIX_TO_BASE_URL[prefix]
    raise ValueError(
        f"Cannot determine data center from API key prefix '{prefix}'. "
        f"Supported prefixes: {', '.join(sorted(_PREFIX_TO_BASE_URL.keys()))}. "
        f"Please set TUYA_BASE_URL explicitly."
    )


class TuyaAPIError(Exception):
    """Raised when the Tuya API returns success=false."""

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
        super().__init__(f"Tuya API error {code}: {msg}")


class TuyaAPI:
    """Tuya Open Platform 2C end-user API client"""

    def __init__(self, api_key: str = None, base_url: str = None,
                 timeout: int = 30):
        if api_key is None:
            api_key = os.environ.get("TUYA_API_KEY")
        if base_url is None:
            base_url = os.environ.get("TUYA_BASE_URL")
        if not api_key:
            raise ValueError(
                "Missing API key. Set environment variable TUYA_API_KEY, "
                "or pass api_key argument."
            )
        if not base_url:
            base_url = _resolve_base_url(api_key)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
        })
        # Retry on transient server errors
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    # ─── Common Requests ───

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise TuyaAPIError(data.get("code"), data.get("msg"))
        return data

    def _post(self, path: str, data: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=data, timeout=self.timeout)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("success"):
            raise TuyaAPIError(result.get("code"), result.get("msg"))
        return result

    # ─── Home Management ───

    def get_homes(self) -> dict:
        """Query all homes for the user"""
        return self._get("/v1.0/end-user/homes/all")

    def get_rooms(self, home_id: str) -> dict:
        """Query all rooms in a home"""
        return self._get(f"/v1.0/end-user/homes/{home_id}/rooms")

    # ─── Device Query ───

    def get_all_devices(self) -> dict:
        """Query all devices for the user"""
        return self._get("/v1.0/end-user/devices/all")

    def get_home_devices(self, home_id: str) -> dict:
        """Query all devices in a home"""
        return self._get(f"/v1.0/end-user/homes/{home_id}/devices")

    def get_room_devices(self, room_id: str) -> dict:
        """Query all devices in a room"""
        return self._get(f"/v1.0/end-user/homes/room/{room_id}/devices")

    def get_device_detail(self, device_id: str) -> dict:
        """Query single device detail (including current property states)"""
        return self._get(f"/v1.0/end-user/devices/{device_id}/detail")

    # ─── Device Control ───

    def get_device_model(self, device_id: str) -> dict:
        """Query device Thing Model"""
        return self._get(f"/v1.0/end-user/devices/{device_id}/model")

    def issue_properties(self, device_id: str, properties: dict) -> dict:
        """Issue property commands to a device

        Args:
            device_id: Device ID
            properties: Property key-value pairs, e.g. {"switch_led": True, "bright_value": 500}
                       Automatically serialized to a JSON string
        """
        return self._post(
            f"/v1.0/end-user/devices/{device_id}/shadow/properties/issue",
            data={"properties": json.dumps(properties)},
        )

    # ─── Device Management ───

    def rename_device(self, device_id: str, name: str) -> dict:
        """Rename a device"""
        return self._post(
            f"/v1.0/end-user/devices/{device_id}/attribute",
            data={"name": name},
        )

    # ─── Weather Service ───

    def get_weather(self, lat: str, lon: str, codes: list = None) -> dict:
        """Query weather information

        Args:
            lat: Latitude
            lon: Longitude
            codes: Weather attribute list, defaults to temperature, humidity,
                   and condition for the next 7 hours
        """
        if codes is None:
            codes = ["w.temp", "w.humidity", "w.condition", "w.hour.7"]
        return self._get(
            "/v1.0/end-user/services/weather/recent",
            params={"lat": lat, "lon": lon, "codes": json.dumps(codes)},
        )

    # ─── Notifications ───

    def send_sms(self, message: str) -> dict:
        """Send an SMS to the current user"""
        return self._post(
            "/v1.0/end-user/services/sms/self-send",
            data={"message": message},
        )

    def send_voice(self, message: str) -> dict:
        """Send a voice notification to the current user"""
        return self._post(
            "/v1.0/end-user/services/voice/self-send",
            data={"message": message},
        )

    def send_mail(self, subject: str, content: str) -> dict:
        """Send an email to the current user"""
        return self._post(
            "/v1.0/end-user/services/mail/self-send",
            data={"subject": subject, "content": content},
        )

    def send_push(self, subject: str, content: str) -> dict:
        """Send an App push notification to the current user"""
        return self._post(
            "/v1.0/end-user/services/push/self-send",
            data={"subject": subject, "content": content},
        )

    # ─── Data Statistics ───

    def get_statistics_config(self) -> dict:
        """Query hourly statistics configuration for all user devices"""
        return self._get("/v1.0/end-user/statistics/hour/config")

    def get_statistics_data(self, dev_id: str, dp_code: str,
                           statistic_type: str, start_time: str,
                           end_time: str) -> dict:
        """Query hourly statistics values for a device

        Args:
            dev_id: Device ID
            dp_code: Data point code (e.g. ele_usage)
            statistic_type: Statistic type (SUM, COUNT, MAX, MIN, MINUX)
            start_time: Start time, format yyyyMMddHH
            end_time: End time, format yyyyMMddHH (max 24-hour span from start)
        """
        return self._get(
            "/v1.0/end-user/statistics/hour/data",
            params={
                "dev_id": dev_id,
                "dp_code": dp_code,
                "statistic_type": statistic_type,
                "start_time": start_time,
                "end_time": end_time,
            },
        )


# ─── Command-Line Mode ───

def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _parse_flags(args: list) -> tuple:
    """Parse optional --flag value pairs from args, return (flags_dict, positional_args)."""
    flags = {}
    positional = []
    i = 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            flags[args[i][2:]] = args[i + 1]
            i += 2
        else:
            positional.append(args[i])
            i += 1
    return flags, positional


def _cmd_devices(api: TuyaAPI, flags: dict) -> dict:
    """Handle the 'devices' command with optional --home / --room filters."""
    if "room" in flags:
        return api.get_room_devices(flags["room"])
    if "home" in flags:
        return api.get_home_devices(flags["home"])
    return api.get_all_devices()


def main():
    if len(sys.argv) < 2:
        print("Usage: python tuya_api.py <command> [params...]")
        print()
        print("TUYA_API_KEY is required. TUYA_BASE_URL is optional (auto-detected from key prefix).")
        print()
        print("Commands:")
        print("  homes                                  List all homes")
        print("  rooms <home_id>                        List rooms in a home")
        print("  devices [--home <id>] [--room <id>]    List devices (all / by home / by room)")
        print("  device_detail <device_id>              Get device detail")
        print("  model <device_id>                      Get device Thing Model")
        print("  control <device_id> <properties_json>  Control a device")
        print("  rename <device_id> <new_name>          Rename a device")
        print("  weather <lat> <lon> [codes_json]       Query weather")
        print("  sms <message>                          Send SMS")
        print("  voice <message>                        Send voice call")
        print("  mail <subject> <content>               Send email")
        print("  push <subject> <content>               Send push notification")
        print("  stats_config                           Query statistics config")
        print("  stats_data <dev_id> <dp_code> <type> <start> <end>  Query statistics")
        sys.exit(1)

    command = sys.argv[1]
    raw_args = sys.argv[2:]
    flags, args = _parse_flags(raw_args)

    # Validate argument count (for commands that use positional args)
    required = _COMMAND_ARG_COUNT.get(command, 0)
    if len(args) < required:
        print(f"Error: '{command}' requires {required} argument(s), got {len(args)}")
        sys.exit(1)

    api = TuyaAPI()

    commands = {
        "homes": lambda: api.get_homes(),
        "rooms": lambda: api.get_rooms(args[0]),
        "devices": lambda: _cmd_devices(api, flags),
        "device_detail": lambda: api.get_device_detail(args[0]),
        "model": lambda: api.get_device_model(args[0]),
        "control": lambda: api.issue_properties(args[0], json.loads(args[1])),
        "rename": lambda: api.rename_device(args[0], args[1]),
        "weather": lambda: api.get_weather(
            args[0], args[1],
            json.loads(args[2]) if len(args) > 2 else None
        ),
        "sms": lambda: api.send_sms(args[0]),
        "voice": lambda: api.send_voice(args[0]),
        "mail": lambda: api.send_mail(args[0], args[1]),
        "push": lambda: api.send_push(args[0], args[1]),
        "stats_config": lambda: api.get_statistics_config(),
        "stats_data": lambda: api.get_statistics_data(
            args[0], args[1], args[2], args[3], args[4]
        ),
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        sys.exit(1)

    try:
        _print_json(commands[command]())
    except TuyaAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request timed out. Please try again later.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Unable to connect to Tuya API. Please check your network.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
