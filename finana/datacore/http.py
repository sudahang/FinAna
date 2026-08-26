"""统一 HTTP 封装（UA、超时、重试退避、JSON/文本抓取、curl_cffi 反爬兜底），供所有 provider 复用。"""

import time

import certifi
import requests

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
# Task 11 实测：东财 push2/search-api 会按 TLS 指纹拒绝 python-requests
# （连接直接断开或返回降级响应），curl_cffi 的 libcurl TLS 栈不受影响。
_RETRY_EXC = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.JSONDecodeError,
)

# 连接级重置（RemoteDisconnected 属于 ConnectionError）多为东财临时限流，
# 退避重试可显著改善取数稳定性；verify 固定指向 certifi，避免 macOS 框架 Python
# 缺系统 CA 证书时整体 TLS 失败。
_VERIFY = certifi.where()


def _build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": _UA})
    retry = requests.adapters.Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


_SESSION = _build_session()


def _headers(headers: dict | None) -> dict:
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    return h


def _via_cffi(url, params, headers, timeout: int):
    """curl_cffi 兜底请求；未安装时抛 ImportError 由上层还原原始错误。"""
    from curl_cffi import requests as cffi_requests

    return cffi_requests.get(url, params=params, headers=headers, timeout=timeout, verify=_VERIFY)


def _get(url, params=None, headers=None, timeout: int = 10):
    """requests 主取（含退避重试）；被拒连时切换 curl_cffi 重试一次。"""
    h = _headers(headers)
    try:
        return _SESSION.get(url, params=params, headers=h, timeout=timeout, verify=_VERIFY)
    except _RETRY_EXC as first_err:
        try:
            return _via_cffi(url, params, h, timeout)
        except ImportError:
            raise first_err


def fetch_json(url, params=None, headers=None, timeout: int = 10) -> dict:
    """GET 请求并返回 JSON，统一 UA 与超时，含退避重试与 curl_cffi 兜底。

    兜底同时覆盖两类反爬：requests 被直接断连（ConnectionError），
    以及返回 200 但内容为 JSONP 包裹的降级响应（JSONDecodeError）。
    """
    h = _headers(headers)
    try:
        resp = _SESSION.get(url, params=params, headers=h, timeout=timeout, verify=_VERIFY)
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
    """GET 请求并返回自动探测编码后的文本，含退避重试与 curl_cffi 兜底。"""
    resp = _get(url, params, headers, timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "gbk"
    return resp.text
