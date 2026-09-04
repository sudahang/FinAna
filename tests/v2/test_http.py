from __future__ import annotations

import json

import pytest
import requests

import finana.datacore.http as http


class _OKResp:
    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


class _OKSession:
    def get(self, *args, **kwargs):
        return _OKResp()

    def mount(self, *args, **kwargs):
        return None


def test_session_has_retry_adapter():
    adapter = http._SESSION.get_adapter("https://example.com")
    assert adapter.max_retries.total == 3
    assert adapter.max_retries.backoff_factor > 0


def test_fetch_json_returns_parsed_payload(monkeypatch):
    monkeypatch.setattr(http, "_SESSION", _OKSession())
    assert http.fetch_json("https://example.com/api") == {"ok": True}


class _FailSession:
    def get(self, *args, **kwargs):
        raise requests.exceptions.ConnectionError("boom")

    def mount(self, *args, **kwargs):
        return None


def test_fetch_json_falls_back_to_cffi(monkeypatch):
    """requests 被拒连时切换到 curl_cffi 并成功取数。"""
    monkeypatch.setattr(http, "_SESSION", _FailSession())
    monkeypatch.setattr(http, "_via_cffi", lambda *a, **k: _OKResp())
    assert http.fetch_json("https://example.com/api") == {"ok": True}


def test_fetch_json_reraises_original_error_when_cffi_unavailable(monkeypatch):
    """curl_cffi 不可用时还原原始 ConnectionError。

    兜底路径用 monkeypatch 隔离：既不发起真实网络请求，
    也不受 curl_cffi 是否真的安装影响。
    """

    def _without_cffi(*args, **kwargs):
        raise ImportError("curl_cffi not installed")

    monkeypatch.setattr(http, "_SESSION", _FailSession())
    monkeypatch.setattr(http, "_via_cffi", _without_cffi)
    with pytest.raises(requests.exceptions.ConnectionError):
        http.fetch_json("https://example.com/api")
