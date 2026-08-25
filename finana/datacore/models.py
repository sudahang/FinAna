"""datacore 核心数据模型（K 线、行情、资金流）。"""

from dataclasses import dataclass, field


@dataclass
class Bar:
    """单根 K 线。

    A 股 volume 单位约定：Quote.volume=股、Bar.volume=手（K线各渠道原始口径）。
    """

    date: str
    open_: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0


@dataclass
class KLine:
    """一组 K 线序列。"""

    symbol: str
    period: str
    bars: list[Bar] = field(default_factory=list)
    source: str = ""


@dataclass
class Quote:
    """实时行情快照。"""

    symbol: str
    name: str
    price: float
    change_pct: float
    open_: float
    high: float
    low: float
    prev_close: float
    volume: float
    amount: float
    timestamp: float
    source: str = ""


@dataclass
class MoneyFlowDay:
    """单日资金流。"""

    date: str
    main_net: float
    source: str = ""
