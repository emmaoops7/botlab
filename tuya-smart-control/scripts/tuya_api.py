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
import re
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

__all__ = ["TuyaAPI", "TuyaAPIError"]

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

_KNOWN_FLAGS = {
    "devices": {"home", "room"},
}

_EXIT_CODE_USAGE = 2
_EXIT_CODE_RUNTIME = 1

_API_KEY_RE = re.compile(r"sk-[A-Za-z0-9]+")
_SENSITIVE_COMMANDS = frozenset({"sms", "voice", "mail", "push"})
_MAX_ARG_DISPLAY_LEN = 80


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
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "POST"]),
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    # ─── Common Requests ───

    def _get(self, path: str, params: dict = None):
        """Send GET request and return the ``result`` field directly."""
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise TuyaAPIError(data.get("code"), data.get("msg"))
        return data.get("result")

    def _post(self, path: str, data: dict = None):
        """Send POST request and return the ``result`` field directly."""
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=data, timeout=self.timeout)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise TuyaAPIError(body.get("code"), body.get("msg"))
        return body.get("result")

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


def _sanitize_message(text: str) -> str:
    """Redact sensitive tokens in stderr-friendly messages."""
    return _API_KEY_RE.sub("sk-***", text)


def _redact_args(command: str, args: list) -> list:
    """Truncate notification message content in args for safe display."""
    if command not in _SENSITIVE_COMMANDS:
        return args
    redacted = []
    for arg in args:
        if isinstance(arg, str) and len(arg) > _MAX_ARG_DISPLAY_LEN:
            redacted.append(arg[:_MAX_ARG_DISPLAY_LEN] + "...<truncated>")
        else:
            redacted.append(arg)
    return redacted


def _print_error(command: str, args: list, message: str, code: int = None):
    """Print a standardized error block to stderr."""
    safe_message = _sanitize_message(message)
    safe_args = _redact_args(command, args)
    print(f"Error: {safe_message}", file=sys.stderr)
    print(f"Command: {command}", file=sys.stderr)
    print(f"Args: {json.dumps(safe_args, ensure_ascii=False)}", file=sys.stderr)
    if code is not None:
        print(f"TuyaErrorCode: {code}", file=sys.stderr)
        print(f"Suggestion: {_error_suggestion(code)}", file=sys.stderr)


def _error_suggestion(code: int) -> str:
    """Return actionable guidance for common Tuya API errors."""
    suggestions = {
        1010: "Your API key is invalid or expired. Please update TUYA_API_KEY.",
        10011: "No bound contact for current user. Bind phone/email in Tuya App.",
        40000901: "Device does not exist. Re-check device_id or refresh device list.",
    }
    return suggestions.get(code, "Check parameters/network and retry.")


def _parse_flags(args: list) -> tuple:
    """Parse optional --flag value pairs.

    Returns:
        (flags_dict, positional_args, parse_error)
    """
    flags = {}
    positional = []
    i = 0
    while i < len(args):
        token = args[i]
        if token.startswith("--"):
            flag_name = token[2:]
            if not flag_name:
                return {}, [], "Invalid flag '--'."
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                return {}, [], f"Flag '--{flag_name}' requires a value."
            flags[flag_name] = args[i + 1]
            i += 2
        else:
            positional.append(token)
            i += 1
    return flags, positional, None


def _validate_time_yyyyMMddHH(value: str) -> bool:
    """Validate time text against yyyyMMddHH format."""
    try:
        datetime.strptime(value, "%Y%m%d%H")
        return True
    except ValueError:
        return False


def _validate_stats_time_window(start_time: str, end_time: str) -> bool:
    """Validate statistics time window does not exceed 24 hours."""
    start = datetime.strptime(start_time, "%Y%m%d%H")
    end = datetime.strptime(end_time, "%Y%m%d%H")
    if end < start:
        return False
    return (end - start).total_seconds() <= 24 * 3600


def _validate_lat_lon(lat: str, lon: str) -> bool:
    """Validate geographic coordinates."""
    try:
        lat_v = float(lat)
        lon_v = float(lon)
    except ValueError:
        return False
    return -90.0 <= lat_v <= 90.0 and -180.0 <= lon_v <= 180.0


def _print_help():
    """Print CLI usage and examples."""
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
    print()
    print("Examples:")
    print("  python tuya_api.py devices --home 5053559")
    print("  python tuya_api.py control dev123 '{\"switch_led\": true}'")
    print("  python tuya_api.py weather 39.90 116.40 '[\"w.temp\",\"w.humidity\"]'")
    print("  python tuya_api.py stats_data dev123 ele_usage SUM 2024010100 2024010123")
    print()
    print("Exit codes:")
    print(f"  {_EXIT_CODE_RUNTIME}: runtime/API/network errors")
    print(f"  {_EXIT_CODE_USAGE}: usage/parameter validation errors")


def _validate_flags_for_command(command: str, flags: dict):
    """Validate known flags and command-specific flag rules."""
    allowed = _KNOWN_FLAGS.get(command, set())
    unknown = sorted(set(flags.keys()) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown flag(s) for '{command}': {', '.join('--' + f for f in unknown)}")
    if command != "devices" and flags:
        raise ValueError(f"Flags are not supported for '{command}'.")
    if command == "devices" and "home" in flags and "room" in flags:
        raise ValueError("Use only one scope: --home or --room, not both.")


def _parse_json_arg(raw: str, arg_name: str):
    """Parse JSON and raise user-friendly errors."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for '{arg_name}': {exc.msg}") from exc


def _cmd_devices(api: TuyaAPI, flags: dict) -> dict:
    """Handle the 'devices' command with optional --home / --room filters."""
    if "room" in flags:
        return api.get_room_devices(flags["room"])
    if "home" in flags:
        return api.get_home_devices(flags["home"])
    return api.get_all_devices()


def main():
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        _print_help()
        sys.exit(_EXIT_CODE_USAGE if len(sys.argv) < 2 else 0)

    command = sys.argv[1]
    raw_args = sys.argv[2:]
    flags, args, parse_error = _parse_flags(raw_args)
    if parse_error:
        _print_error(command, raw_args, parse_error)
        sys.exit(_EXIT_CODE_USAGE)

    # Validate argument count (for commands that use positional args)
    required = _COMMAND_ARG_COUNT.get(command, 0)
    if len(args) < required:
        _print_error(command, raw_args, f"'{command}' requires {required} argument(s), got {len(args)}")
        sys.exit(_EXIT_CODE_USAGE)

    try:
        _validate_flags_for_command(command, flags)
    except ValueError as exc:
        _print_error(command, raw_args, str(exc))
        sys.exit(_EXIT_CODE_USAGE)

    if command not in {
        "homes", "rooms", "devices", "device_detail", "model", "control",
        "rename", "weather", "sms", "voice", "mail", "push", "stats_config", "stats_data",
    }:
        _print_error(command, raw_args, f"Unknown command: {command}")
        _print_help()
        sys.exit(_EXIT_CODE_USAGE)

    try:
        api = TuyaAPI()

        if command == "homes":
            result = api.get_homes()
        elif command == "rooms":
            result = api.get_rooms(args[0])
        elif command == "devices":
            result = _cmd_devices(api, flags)
        elif command == "device_detail":
            result = api.get_device_detail(args[0])
        elif command == "model":
            result = api.get_device_model(args[0])
        elif command == "control":
            properties = _parse_json_arg(args[1], "properties_json")
            if not isinstance(properties, dict):
                raise ValueError("control properties_json must be a JSON object.")
            result = api.issue_properties(args[0], properties)
        elif command == "rename":
            result = api.rename_device(args[0], args[1])
        elif command == "weather":
            if not _validate_lat_lon(args[0], args[1]):
                raise ValueError("weather requires valid lat/lon ranges: lat [-90,90], lon [-180,180].")
            codes = _parse_json_arg(args[2], "codes_json") if len(args) > 2 else None
            if codes is not None and not isinstance(codes, list):
                raise ValueError("weather codes_json must be a JSON array.")
            result = api.get_weather(args[0], args[1], codes)
        elif command == "sms":
            result = api.send_sms(args[0])
        elif command == "voice":
            result = api.send_voice(args[0])
        elif command == "mail":
            result = api.send_mail(args[0], args[1])
        elif command == "push":
            result = api.send_push(args[0], args[1])
        elif command == "stats_config":
            result = api.get_statistics_config()
        else:  # stats_data
            start_time = args[3]
            end_time = args[4]
            if not (_validate_time_yyyyMMddHH(start_time) and _validate_time_yyyyMMddHH(end_time)):
                raise ValueError("stats_data start/end must use yyyyMMddHH format.")
            if not _validate_stats_time_window(start_time, end_time):
                raise ValueError("stats_data time window must be within 24 hours and end >= start.")
            result = api.get_statistics_data(args[0], args[1], args[2], start_time, end_time)

        _print_json(result)
    except ValueError as e:
        _print_error(command, raw_args, str(e))
        sys.exit(_EXIT_CODE_USAGE)
    except TuyaAPIError as e:
        _print_error(command, raw_args, str(e), e.code)
        sys.exit(_EXIT_CODE_RUNTIME)
    except requests.exceptions.Timeout:
        _print_error(command, raw_args, "Request timed out. Please try again later.")
        sys.exit(_EXIT_CODE_RUNTIME)
    except requests.exceptions.ConnectionError:
        _print_error(command, raw_args, "Unable to connect to Tuya API. Please check your network.")
        sys.exit(_EXIT_CODE_RUNTIME)
    except requests.exceptions.HTTPError as e:
        _print_error(command, raw_args, f"HTTP error from Tuya API: {e}")
        sys.exit(_EXIT_CODE_RUNTIME)
    except requests.exceptions.RequestException as e:
        _print_error(command, raw_args, f"Request failed: {e}")
        sys.exit(_EXIT_CODE_RUNTIME)
    except json.JSONDecodeError:
        _print_error(command, raw_args, "Received non-JSON response from Tuya API.")
        sys.exit(_EXIT_CODE_RUNTIME)


if __name__ == "__main__":
    main()
