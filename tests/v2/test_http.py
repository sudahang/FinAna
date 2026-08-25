import pytest

import finana.datacore.http as http_mod


class FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _reject(*a, **k):
    raise http_mod.requests.exceptions.ConnectionError("RemoteDisconnected")


def test_fetch_json_falls_back_on_connection_error(monkeypatch):
    monkeypatch.setattr(http_mod.requests, "get", _reject)
    monkeypatch.setattr(http_mod, "_via_cffi", lambda *a, **k: FakeResp({"ok": 1}))
    assert http_mod.fetch_json("https://example.com/x") == {"ok": 1}


def test_fetch_json_falls_back_on_junk_json(monkeypatch):
    junk = http_mod.requests.exceptions.JSONDecodeError("Expecting value", "<jsonp>(", 0)

    monkeypatch.setattr(http_mod.requests, "get", lambda *a, **k: FakeResp(junk))
    monkeypatch.setattr(http_mod, "_via_cffi", lambda *a, **k: FakeResp({"ok": 2}))
    assert http_mod.fetch_json("https://example.com/x") == {"ok": 2}


def test_fetch_json_reraises_without_cffi(monkeypatch):
    monkeypatch.setattr(http_mod.requests, "get", _reject)

    def no_cffi(*a, **k):
        raise ImportError("curl_cffi 未安装")

    monkeypatch.setattr(http_mod, "_via_cffi", no_cffi)
    with pytest.raises(http_mod.requests.exceptions.ConnectionError):
        http_mod.fetch_json("https://example.com/x")


def test_http_error_not_retried(monkeypatch):
    class ErrResp(FakeResp):
        def raise_for_status(self):
            err = http_mod.requests.exceptions.HTTPError("500")
            err.response = None
            raise err

    calls = []

    def record_get(*a, **k):
        calls.append(1)
        return ErrResp({})

    monkeypatch.setattr(http_mod.requests, "get", record_get)
    with pytest.raises(http_mod.requests.exceptions.HTTPError):
        http_mod.fetch_json("https://example.com/x")
    assert len(calls) == 1
