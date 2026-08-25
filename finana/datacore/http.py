"""统一 HTTP 封装（UA、超时、JSON/文本抓取、curl_cffi 反爬兜底），供所有 provider 复用。"""

import requests

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
# Task 11 实测：东财 push2/search-api 会按 TLS 指纹拒绝 python-requests
# （连接直接断开或返回降级响应），curl_cffi 的 libcurl TLS 栈不受影响。
_RETRY_EXC = (requests.exceptions.ConnectionError, requests.exceptions.JSONDecodeError)


def _headers(headers: dict | None) -> dict:
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    return h


def _via_cffi(url, params, headers, timeout: int):
    """curl_cffi 兜底请求；未安装时抛 ImportError 由上层还原原始错误。"""
    from curl_cffi import requests as cffi_requests

    return cffi_requests.get(url, params=params, headers=headers, timeout=timeout)


def _get(url, params=None, headers=None, timeout: int = 10):
    """requests 主取；被拒连时切换 curl_cffi 重试一次。"""
    h = _headers(headers)
    try:
        return requests.get(url, params=params, headers=h, timeout=timeout)
    except _RETRY_EXC as first_err:
        try:
            return _via_cffi(url, params, h, timeout)
        except ImportError:
            raise first_err


def fetch_json(url, params=None, headers=None, timeout: int = 10) -> dict:
    """GET 请求并返回 JSON，统一 UA 与超时，含 curl_cffi 兜底。

    兜底同时覆盖两类反爬：requests 被直接断连（ConnectionError），
    以及返回 200 但内容为 JSONP 包裹的降级响应（JSONDecodeError）。
    """
    h = _headers(headers)
    try:
        resp = requests.get(url, params=params, headers=h, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except _RETRY_EXC as first_err:
        try:
            resp = _via_cffi(url, params, h, timeout)
            resp.raise_for_status()
            return resp.json()
        except ImportError:
            raise first_err


def fetch_text(url, params=None, headers=None, timeout: int = 10) -> str:
    """GET 请求并返回自动探测编码后的文本，含 curl_cffi 兜底。"""
    resp = _get(url, params, headers, timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "gbk"
    return resp.text
