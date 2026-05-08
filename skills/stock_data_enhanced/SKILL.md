---
name: "stock-data-enhanced"
description: "获取股票实时行情和公司信息，使用 AKShare（A股/港股）和 yfinance（美股）作为稳定数据源。Invoke when user needs reliable stock data for A-shares, HK stocks, or US stocks."
---

# Stock Data Enhanced Skill

这个 skill 使用两个稳定的开源数据源来获取股票数据：
- **AKShare**: 用于 A 股和港股数据
- **yfinance**: 用于美股数据

## 数据源对比

| 市场 | 数据源 | 优点 |
|------|--------|------|
| A 股 | AKShare | 免费、开源、数据全面、持续维护 |
| 港股 | AKShare | 支持港股通数据 |
| 美股 | yfinance | Yahoo Finance 数据、稳定、社区活跃 |

## 安装依赖

```bash
pip install akshare yfinance
```

## 使用方法

### 1. 获取 A 股行情

```python
from skills.stock_data_enhanced.stock_data import get_stock_quote

# 获取 A 股行情（支持多种代码格式）
quote = get_stock_quote("600519")  # 贵州茅台
quote = get_stock_quote("sh600519")
quote = get_stock_quote("000001")  # 平安银行
```

### 2. 获取港股行情

```python
# 获取港股行情
quote = get_stock_quote("HK00700")  # 腾讯控股
quote = get_stock_quote("00700")
```

### 3. 获取美股行情

```python
# 获取美股行情
quote = get_stock_quote("AAPL")  # 苹果
quote = get_stock_quote("TSLA")  # 特斯拉
quote = get_stock_quote("NVDA")  # 英伟达
```

### 4. 获取公司基本信息

```python
from skills.stock_data_enhanced.stock_data import get_company_info

# 获取公司信息
info = get_company_info("600519")  # A 股
info = get_company_info("AAPL")    # 美股
```

### 5. 获取历史 K 线数据

```python
from skills.stock_data_enhanced.stock_data import get_history

# 获取日 K 线数据
history = get_history("600519", period="d")  # A 股日线
history = get_history("AAPL", period="d")    # 美股日线
history = get_history("600519", period="w")  # A 股周线
```

## 返回数据格式

### 实时行情

```python
{
    "symbol": "600519",
    "name": "贵州茅台",
    "current_price": 1688.88,
    "open": 1680.00,
    "high": 1695.00,
    "low": 1675.00,
    "prev_close": 1685.00,
    "change": 3.88,
    "change_pct": 0.23,
    "volume": 12345678,
    "amount": 20800000000.0,
    "market_cap": 2120000000000.0,
    "pe_ratio": 35.2,
    "pb_ratio": 9.8,
    "turnover_rate": 0.98,
    "market": "sh",  # sh/sz/hk/us
    "timestamp": datetime(2024, 1, 1, 15, 0, 0)
}
```

### 公司信息

```python
{
    "symbol": "600519",
    "name": "贵州茅台",
    "industry": "白酒",
    "area": "贵州",
    "listing_date": "2001-08-27",
    "pe_ratio": 35.2,
    "pb_ratio": 9.8,
    "total_revenue": 150000000000.0,
    "net_profit": 75000000000.0,
    "gross_margin": 91.5,
    "roe": 28.5,
    "market_cap": 2120000000000.0,
    "timestamp": datetime(2024, 1, 1, 15, 0, 0)
}
```

### 历史 K 线

```python
[
    {
        "date": "2024-01-01",
        "open": 1680.00,
        "high": 1695.00,
        "low": 1675.00,
        "close": 1688.88,
        "volume": 12345678,
        "amount": 20800000000.0
    },
    ...
]
```

## 错误处理

- 如果数据获取失败，返回 `None`
- 自动重试 3 次
- 超时时间设置为 15 秒
- 详细的日志记录

## 注意事项

1. **数据延迟**: 免费数据源可能存在 10-15 分钟延迟
2. **交易时间**: 非交易时间获取的数据为最近收盘价
3. **港股代码**: AKShare 使用 `HK` 前缀 + 5 位数字（如 `HK00700`）
4. **美股代码**: yfinance 使用标准美股代码（如 `AAPL`, `TSLA`）
5. **A 股代码**: 支持 6 位数字或带市场前缀（`sh600519`, `sz000001`）

## 测试

```bash
cd /Users/tom/github/FinAna
python skills/stock_data_enhanced/test_stock_data.py
```

## 与现有代码集成

这个 skill 可以替代或补充现有的 `skills/stock_info/stock_info.py`，提供更稳定的数据源。

建议在 `data/finance_data.py` 中优先使用这个 skill 的数据源，如果失败再 fallback 到原有的新浪/东方财富数据源。
