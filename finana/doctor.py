"""finana-doctor：对各数据域发起真实请求并输出域级健康报告。"""

import argparse
import json
import time

from finana.datacore.base import DataUnavailable
from finana.observability import get_logger

log = get_logger("doctor")

PROBES = [
    ("quote", lambda c, s: c.get_quote(s)),
    ("kline", lambda c, s: c.get_kline(s, count=5)),
    ("moneyflow", lambda c, s: c.get_money_flow(s, days=5)),
    ("margin", lambda c, s: c.get_margin(s, days=5)),
    ("lhb", lambda c, s: c.get_lhb(s, days=5)),
    ("financials", lambda c, s: c.get_financials(s)),
    ("news", lambda c, s: c.get_news(s, limit=3)),
    ("sector", lambda c, s: c.get_sector_snapshot(limit=20)),
]


def probe(core, symbol: str) -> list[dict]:
    """对每个数据域发一次请求，返回含状态、耗时与错误明细的结果行。"""
    rows = []
    for domain, fn in PROBES:
        t0 = time.monotonic()
        status, detail = "ok", ""
        try:
            fn(core, symbol)
        except DataUnavailable as e:
            status, detail = "unavailable", ",".join(e.attempts)
        except Exception as e:
            status, detail = "error", f"{type(e).__name__}: {e}"
        rows.append({"domain": domain, "status": status,
                     "ms": round((time.monotonic() - t0) * 1000), "detail": detail})
    return rows


def main():
    """运行全域探测并输出结果表，无任何成功域时以退出码 1 结束。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="600519")
    args = parser.parse_args()
    from finana.config import get_settings
    from finana.datacore.core import get_datacore

    core = get_datacore()
    rows = probe(core, args.symbol)
    settings = get_settings()
    home = settings.finana_home.expanduser()
    out = home / "doctor_last.json"
    out.write_text(json.dumps({"ts": time.time(), "rows": rows,
                               "health": core.health()},
                              ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'domain':<12}{'status':<12}{'ms':>8}  detail")
    for r in rows:
        print(f"{r['domain']:<12}{r['status']:<12}{r['ms']:>8}  {r['detail']}")
    print("\n渠道熔断状态:")
    for h in core.health():
        print(f"{h['provider']:<16}{h['domain']:<12}{h['state']:<10} fails={h['failures']} {h['last_error']}")
    print(f"\n快照已写入 {out}")
    raise SystemExit(1 if all(r["status"] != "ok" for r in rows) else 0)


if __name__ == "__main__":
    main()
