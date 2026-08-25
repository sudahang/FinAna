"""统一 HTTP 封装（UA、超时、JSON/文本抓取），供所有 provider 复用。"""

import requests

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def fetch_json(url, params=None, headers=None, timeout: int = 10) -> dict:
    """GET 请求并返回 JSON，统一 UA 与超时。"""
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    resp = requests.get(url, params=params, headers=h, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_text(url, params=None, headers=None, timeout: int = 10) -> str:
    """GET 请求并返回自动探测编码后的文本。"""
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    resp = requests.get(url, params=params, headers=h, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "gbk"
    return resp.text
