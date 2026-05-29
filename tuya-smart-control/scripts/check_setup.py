#!/usr/bin/env python3
"""Tuya Smart Home Setup Checker

Validates that the environment is correctly configured for Tuya API access.
Checks Python version, required packages, environment variables, and API
connectivity — without printing any secrets.

Usage:
    python check_setup.py
"""

import os
import sys
import json

# ── Helpers ──────────────────────────────────────────────────

OK = "✅"
WARN = "⚠️"
FAIL = "❌"

_issues = []


def _mask(value: str, show: int = 4) -> str:
    """Return a masked version of a secret, showing only the first `show` chars."""
    if not value:
        return "(empty)"
    if len(value) <= show:
        return value[0] + "***"
    return value[:show] + "***" + value[-2:]


def _check(label: str, condition: bool, detail: str = "", warn_only: bool = False):
    symbol = OK if condition else (WARN if warn_only else FAIL)
    msg = f"  {symbol} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not condition and not warn_only:
        _issues.append(label)
    return condition


# ── 1. Python version ────────────────────────────────────────

print("\n🐍 Python Environment")
_check(
    "Python version ≥ 3.7",
    sys.version_info >= (3, 7),
    f"running {sys.version.split()[0]}",
)

# ── 2. Required packages ─────────────────────────────────────

print("\n📦 Required Packages")

try:
    import requests
    _check("requests", True, f"v{requests.__version__}")
except ImportError:
    _check("requests", False, "not installed — run: pip install requests")

try:
    import websockets
    _check("websockets", True, f"v{websockets.__version__}", warn_only=True)
except ImportError:
    _check("websockets", False, "not installed (optional, needed for real-time events) — run: pip install websockets", warn_only=True)

# ── 3. Environment variables ─────────────────────────────────

print("\n🔑 Environment Variables")

# Load .env if present (simple key=value parser, no dotenv dependency)
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if not os.path.isfile(_env_file):
    _env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(_env_file):
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k and not os.environ.get(k):
                    os.environ[k] = v
    print(f"  ℹ️  Loaded .env from {_env_file}")

access_id = os.environ.get("TUYA_ACCESS_ID", "")
access_secret = os.environ.get("TUYA_ACCESS_SECRET", "")
endpoint = os.environ.get("TUYA_ENDPOINT", "")
uid = os.environ.get("TUYA_UID", "")
api_key = os.environ.get("TUYA_API_KEY", "")

# Cloud OpenAPI route
has_cloud = bool(access_id and access_secret and endpoint)
has_legacy = bool(api_key)

# If legacy key is present, Cloud vars are optional (warn only)
cloud_warn_only = has_legacy
_check(
    "TUYA_ACCESS_ID",
    bool(access_id),
    _mask(access_id) if access_id else "not set" + (" (optional if using TUYA_API_KEY)" if has_legacy else ""),
    warn_only=cloud_warn_only,
)
_check(
    "TUYA_ACCESS_SECRET",
    bool(access_secret),
    _mask(access_secret) if access_secret else "not set" + (" (optional if using TUYA_API_KEY)" if has_legacy else ""),
    warn_only=cloud_warn_only,
)
_check(
    "TUYA_ENDPOINT",
    bool(endpoint),
    endpoint if endpoint else "not set" + (" (optional if using TUYA_API_KEY)" if has_legacy else ""),
    warn_only=cloud_warn_only,
)
_check("TUYA_UID", bool(uid), uid if uid else "not set (optional)", warn_only=True)

# Legacy Bearer route — warn only if Cloud is configured
_check(
    "TUYA_API_KEY (legacy)",
    bool(api_key),
    _mask(api_key) if api_key else "not set (optional if using Access ID/Secret)",
    warn_only=True,
)

if not has_cloud and not has_legacy:
    print(f"\n  {FAIL} No credentials configured at all!")
    print("     Set TUYA_ACCESS_ID + TUYA_ACCESS_SECRET + TUYA_ENDPOINT (recommended)")
    print("     or TUYA_API_KEY (legacy) in your .env file.")
    _issues.append("No credentials")

# ── 4. API connectivity ──────────────────────────────────────

print("\n🌐 API Connectivity")

if has_cloud and "requests" in sys.modules:
    try:
        # Attempt to get a token via Cloud OpenAPI
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tuya_api import TuyaCloudAPI
        cloud = TuyaCloudAPI(
            access_id=access_id,
            access_secret=access_secret,
            base_url=endpoint,
        )
        token = cloud.get_access_token()
        _check("Cloud OpenAPI token", True, f"got token {_mask(token, 8)}")
    except Exception as e:
        _check("Cloud OpenAPI token", False, str(e)[:120])

if api_key and "requests" in sys.modules:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tuya_api import TuyaAPI
        api = TuyaAPI(api_key=api_key)
        homes = api.get_homes()
        count = len(homes) if isinstance(homes, list) else "?"
        _check("Bearer API (homes)", True, f"found {count} home(s)")
    except Exception as e:
        _check("Bearer API (homes)", False, str(e)[:120])

# ── Summary ──────────────────────────────────────────────────

print()
if _issues:
    print(f"⛔ {len(_issues)} issue(s) found: {', '.join(_issues)}")
    print("   Fix the issues above and re-run this script.")
    sys.exit(1)
else:
    print("🎉 All checks passed! You're ready to use Tuya Smart Home.")
    sys.exit(0)
