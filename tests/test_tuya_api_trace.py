#!/usr/bin/env python3
"""Minimal tests for TuyaAPI trace field support."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tuya-smart-control', 'scripts'))

from tuya_api import TuyaAPI, TuyaAPIError

def test_extract_trace_present():
    body = {"success": True, "result": {"a": 1}, "t": 1234567890, "tid": "abc-123"}
    trace = TuyaAPI._extract_trace(body)
    assert trace == {"t": 1234567890, "tid": "abc-123"}, trace

def test_extract_trace_partial():
    body = {"success": False, "code": 1108, "msg": "err", "t": 1234567890}
    trace = TuyaAPI._extract_trace(body)
    assert trace == {"t": 1234567890}, trace

def test_extract_trace_empty():
    body = {"success": True, "result": {}}
    trace = TuyaAPI._extract_trace(body)
    assert trace == {}, trace

def test_tuya_api_error_trace():
    err = TuyaAPIError(1108, "bad", {"t": 1, "tid": "x"})
    assert err.code == 1108
    assert err.msg == "bad"
    assert err.trace == {"t": 1, "tid": "x"}

def test_tuya_api_error_trace_defaults():
    err = TuyaAPIError(1108, "bad")
    assert err.trace == {}

if __name__ == "__main__":
    test_extract_trace_present()
    test_extract_trace_partial()
    test_extract_trace_empty()
    test_tuya_api_error_trace()
    test_tuya_api_error_trace_defaults()
    print("OK")
