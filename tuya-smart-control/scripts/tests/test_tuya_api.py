import json
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

from scripts.tuya_api import (
    TuyaAPI,
    TuyaAPIError,
    _parse_flags,
    _parse_json_arg,
    _redact_args,
    _resolve_base_url,
    _validate_lat_lon,
    _validate_stats_time_window,
    _validate_time_yyyyMMddHH,
)


class ResolveBaseUrlTest(unittest.TestCase):
    def test_known_prefixes(self):
        self.assertEqual(_resolve_base_url("sk-AYabc"), "https://openapi.tuyacn.com")
        self.assertEqual(_resolve_base_url("AZabc"), "https://openapi.tuyaus.com")
        self.assertEqual(_resolve_base_url("sk-EUxyz"), "https://openapi.tuyaeu.com")
        self.assertEqual(_resolve_base_url("sk-INabc"), "https://openapi.tuyain.com")

    def test_unknown_prefix_raises(self):
        with self.assertRaises(ValueError):
            _resolve_base_url("sk-ZZabc")


class ParseFlagsTest(unittest.TestCase):
    def test_single_flag(self):
        flags, positional, err = _parse_flags(["--home", "123", "extra"])
        self.assertIsNone(err)
        self.assertEqual(flags, {"home": "123"})
        self.assertEqual(positional, ["extra"])

    def test_missing_value(self):
        flags, positional, err = _parse_flags(["--home"])
        self.assertEqual(flags, {})
        self.assertEqual(positional, [])
        self.assertIn("requires a value", err)

    def test_empty_flag_name(self):
        _, _, err = _parse_flags(["--"])
        self.assertIn("Invalid flag", err)

    def test_no_flags(self):
        flags, positional, err = _parse_flags(["arg1", "arg2"])
        self.assertIsNone(err)
        self.assertEqual(flags, {})
        self.assertEqual(positional, ["arg1", "arg2"])

    def test_flag_followed_by_flag(self):
        _, _, err = _parse_flags(["--home", "--room"])
        self.assertIn("requires a value", err)


class ParseJsonArgTest(unittest.TestCase):
    def test_valid_object(self):
        obj = _parse_json_arg('{"switch_led": true}', "properties_json")
        self.assertIsInstance(obj, dict)
        self.assertTrue(obj["switch_led"])

    def test_valid_array(self):
        arr = _parse_json_arg('["w.temp"]', "codes_json")
        self.assertIsInstance(arr, list)

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            _parse_json_arg("{invalid", "properties_json")


class ValidateCoordinatesTest(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(_validate_lat_lon("39.90", "116.40"))
        self.assertTrue(_validate_lat_lon("0", "0"))
        self.assertTrue(_validate_lat_lon("-90", "-180"))
        self.assertTrue(_validate_lat_lon("90", "180"))

    def test_out_of_range(self):
        self.assertFalse(_validate_lat_lon("91", "100"))
        self.assertFalse(_validate_lat_lon("30", "181"))

    def test_non_numeric(self):
        self.assertFalse(_validate_lat_lon("abc", "100"))


class ValidateTimeTest(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(_validate_time_yyyyMMddHH("2024010123"))

    def test_invalid_format(self):
        self.assertFalse(_validate_time_yyyyMMddHH("2024-01-01 23"))
        self.assertFalse(_validate_time_yyyyMMddHH(""))

    def test_window_within_24h(self):
        self.assertTrue(_validate_stats_time_window("2024010100", "2024010123"))

    def test_window_exceeds_24h(self):
        self.assertFalse(_validate_stats_time_window("2024010100", "2024010201"))

    def test_window_end_before_start(self):
        self.assertFalse(_validate_stats_time_window("2024010201", "2024010100"))


class RedactArgsTest(unittest.TestCase):
    def test_non_sensitive_command_unchanged(self):
        args = ["device123", '{"switch_led": true}']
        self.assertEqual(_redact_args("control", args), args)

    def test_sms_long_message_truncated(self):
        long_msg = "A" * 200
        result = _redact_args("sms", [long_msg])
        self.assertIn("...<truncated>", result[0])
        self.assertTrue(len(result[0]) < len(long_msg))

    def test_short_message_unchanged(self):
        result = _redact_args("sms", ["Hello"])
        self.assertEqual(result, ["Hello"])

    def test_mail_truncated(self):
        result = _redact_args("mail", ["subject", "B" * 200])
        self.assertEqual(result[0], "subject")
        self.assertIn("...<truncated>", result[1])


# ─── TuyaAPI class tests (mocked HTTP) ───

def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


class TuyaAPIInitTest(unittest.TestCase):
    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                TuyaAPI()

    @patch.dict("os.environ", {"TUYA_API_KEY": "sk-AYtest123"})
    def test_auto_detect_base_url(self):
        api = TuyaAPI()
        self.assertEqual(api.base_url, "https://openapi.tuyacn.com")

    @patch.dict("os.environ", {"TUYA_API_KEY": "sk-AYtest123",
                                "TUYA_BASE_URL": "https://custom.example.com/"})
    def test_explicit_base_url_override(self):
        api = TuyaAPI()
        self.assertEqual(api.base_url, "https://custom.example.com")


class TuyaAPIGetTest(unittest.TestCase):
    @patch.dict("os.environ", {"TUYA_API_KEY": "sk-AYtest123"})
    def setUp(self):
        self.api = TuyaAPI()

    @patch("requests.Session.get")
    def test_get_homes_returns_result(self, mock_get):
        mock_get.return_value = _mock_response({
            "success": True, "t": 123, "result": {"homes": []}
        })
        result = self.api.get_homes()
        self.assertEqual(result, {"homes": []})

    @patch("requests.Session.get")
    def test_get_returns_none_for_null_result(self, mock_get):
        mock_get.return_value = _mock_response({
            "success": True, "t": 0, "result": None
        })
        result = self.api.get_device_detail("nonexistent")
        self.assertIsNone(result)

    @patch("requests.Session.get")
    def test_get_raises_on_api_error(self, mock_get):
        mock_get.return_value = _mock_response({
            "success": False, "code": 1010, "msg": "token invalid"
        })
        with self.assertRaises(TuyaAPIError) as ctx:
            self.api.get_homes()
        self.assertEqual(ctx.exception.code, 1010)
        self.assertEqual(ctx.exception.msg, "token invalid")


class TuyaAPIPostTest(unittest.TestCase):
    @patch.dict("os.environ", {"TUYA_API_KEY": "sk-AYtest123"})
    def setUp(self):
        self.api = TuyaAPI()

    @patch("requests.Session.post")
    def test_issue_properties_returns_result(self, mock_post):
        mock_post.return_value = _mock_response({
            "success": True, "t": 123, "result": {}
        })
        result = self.api.issue_properties("dev123abc456def789", {"switch_led": True})
        self.assertEqual(result, {})
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertIn("properties", body)
        self.assertEqual(json.loads(body["properties"]), {"switch_led": True})

    @patch("requests.Session.post")
    def test_post_raises_on_api_error(self, mock_post):
        mock_post.return_value = _mock_response({
            "success": False, "code": 40000901, "msg": "The device does not exist"
        })
        with self.assertRaises(TuyaAPIError):
            self.api.rename_device("dev123abc456def789", "New Name")

    @patch("requests.Session.post")
    def test_send_sms_returns_result(self, mock_post):
        mock_post.return_value = _mock_response({
            "success": True, "t": 123, "result": True
        })
        result = self.api.send_sms("test message")
        self.assertTrue(result)


class TuyaAPIErrorTest(unittest.TestCase):
    def test_error_attributes(self):
        err = TuyaAPIError(1010, "token invalid")
        self.assertEqual(err.code, 1010)
        self.assertEqual(err.msg, "token invalid")
        self.assertIn("1010", str(err))
        self.assertIn("token invalid", str(err))


# ─── CLI integration tests (subprocess) ───

class CLITest(unittest.TestCase):
    """Test CLI by invoking as a subprocess."""

    _SCRIPT = "scripts/tuya_api.py"

    def _run(self, *args, env_override=None):
        import os
        env = os.environ.copy()
        env.pop("TUYA_API_KEY", None)
        env.pop("TUYA_BASE_URL", None)
        if env_override:
            env.update(env_override)
        result = subprocess.run(
            [sys.executable, self._SCRIPT] + list(args),
            capture_output=True, text=True, env=env,
            cwd=".",
        )
        return result

    def test_help_exits_0(self):
        result = self._run("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)

    def test_no_args_exits_2(self):
        result = self._run()
        self.assertEqual(result.returncode, 2)

    def test_unknown_command_exits_2(self):
        result = self._run("foobar", env_override={"TUYA_API_KEY": "sk-AYtest123"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown command", result.stderr)

    def test_missing_api_key_exits_2(self):
        result = self._run("homes")
        self.assertEqual(result.returncode, 2)
        self.assertIn("API key", result.stderr)

    def test_control_missing_args_exits_2(self):
        result = self._run("control", "0620068884f3eb414579",
                           env_override={"TUYA_API_KEY": "sk-AYtest123"})
        self.assertEqual(result.returncode, 2)

    def test_weather_invalid_coords_exits_2(self):
        result = self._run("weather", "999", "999",
                           env_override={"TUYA_API_KEY": "sk-AYtest123"})
        self.assertEqual(result.returncode, 2)

    def test_stats_data_bad_time_exits_2(self):
        result = self._run("stats_data", "0620068884f3eb414579",
                           "ele_usage", "SUM", "badtime", "badtime",
                           env_override={"TUYA_API_KEY": "sk-AYtest123"})
        self.assertEqual(result.returncode, 2)

    def test_devices_both_flags_exits_2(self):
        result = self._run("devices", "--home", "1", "--room", "2",
                           env_override={"TUYA_API_KEY": "sk-AYtest123"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("--home or --room", result.stderr)


if __name__ == "__main__":
    unittest.main()
