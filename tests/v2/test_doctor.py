from finana.datacore.base import DataUnavailable


class RouterStub:
    def __init__(self, items=None):
        self.items = items or []

    def chain(self, _domain):
        return self.items

    def dispatch(self, domain, method, *args, **kwargs):
        if not self.items:
            raise DataUnavailable(domain, [f"{i}:skip" for i in []] or ["none"])
        return object()


def _stub_core():
    from finana.datacore.models import Quote

    class P:
        name = "p1"

        def get_quote(self, sym):
            return Quote(sym, "x", 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0.0, source="p1")

    class Core:
        def __init__(self):
            self._routers = {
                "quote": RouterStub([P()]), "kline": RouterStub(),
                "moneyflow": RouterStub(), "margin": RouterStub(),
                "lhb": RouterStub(), "financials": RouterStub(),
                "news": RouterStub(), "sector": RouterStub(),
            }

        def get_quote(self, s):
            return self._routers["quote"].dispatch("quote", "get_quote", s)

        def get_kline(self, s, period="d", count=5):
            return self._routers["kline"].dispatch("kline", "get_kline", s)

        def get_money_flow(self, s, days=5):
            return self._routers["moneyflow"].dispatch("moneyflow", "get_money_flow", s)

        def get_margin(self, s, days=5):
            return self._routers["margin"].dispatch("margin", "get_margin", s)

        def get_lhb(self, s, days=5):
            return self._routers["lhb"].dispatch("lhb", "get_lhb", s)

        def get_financials(self, s):
            return self._routers["financials"].dispatch("financials", "get_financials", s)

        def get_news(self, s, limit=3):
            return self._routers["news"].dispatch("news", "get_news", s)

        def get_sector_snapshot(self, limit=50):
            return self._routers["sector"].dispatch("sector", "get_sector_snapshot")

        def health(self):
            return [{"provider": "p1", "domain": "quote", "state": "closed",
                     "failures": 0, "last_error": ""}]

    return Core()


def test_probe_reports_ok_and_unavailable():
    from finana.doctor import probe

    rows = {r["domain"]: r for r in probe(_stub_core(), "600519.SH")}
    assert rows["quote"]["status"] == "ok"
    assert rows["kline"]["status"] == "unavailable"
    assert rows["quote"]["ms"] >= 0
