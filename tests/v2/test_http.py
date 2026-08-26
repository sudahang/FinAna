from __future__ import annotations

import json

import pytest

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


def test_fetch_json_falls_back_to_cffi_and_reraises(monkeypatch):
    import requests

    class _FailSession:
        def get(self, *args, **kwargs):
            raise requests.exceptions.ConnectionError("boom")

        def mount(self, *args, **kwargs):
            return None

    monkeypatch.setattr(http, "_SESSION", _FailSession())
    # curl_cffi 未安装 -> ImportError -> 还原原始 ConnectionError
    with pytest.raises(requests.exceptions.ConnectionError):
        http.fetch_json("https://example.com/api")
