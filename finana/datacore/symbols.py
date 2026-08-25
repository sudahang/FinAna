"""A 股代码规范化与多数据源代码格式转换。"""

_SH_PREFIXES = ("60", "68", "9")
_SZ_PREFIXES = ("00", "30", "20")
_BJ_PREFIXES = ("43", "83", "87", "88", "92")


def _suffix_for(code: str) -> str:
    if code.startswith(_SH_PREFIXES):
        return ".SH"
    if code.startswith(_BJ_PREFIXES):
        return ".BJ"
    return ".SZ"


def normalize_symbol(raw: str) -> str:
    """将任意常见写法规范化为 `600519.SH` 形式。"""
    s = raw.strip().upper().replace(".", "")
    for pfx in ("SH", "SZ", "BJ"):
        if s.startswith(pfx) and len(s) > len(pfx):
            return s[len(pfx):] + "." + pfx
    if s.endswith(("SH", "SZ", "BJ")) and s[:-2].isdigit():
        return s[:-2] + "." + s[-2:]
    if s.isdigit() and len(s) == 6:
        return s + _suffix_for(s)
    raise ValueError(f"无法识别的股票代码: {raw!r}")


def to_em_secid(sym: str) -> str:
    """转换为东方财富 secid 格式 (`600519.SH` -> `1.600519`)。"""
    code, _, mkt = sym.partition(".")
    return ("1." if mkt == "SH" else "0.") + code


def to_sina_code(sym: str) -> str:
    """转换为新浪/腾讯代码格式 (`600519.SH` -> `sh600519`)。"""
    code, _, mkt = sym.partition(".")
    return mkt.lower() + code


to_tencent_code = to_sina_code
