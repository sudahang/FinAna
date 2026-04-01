# Stock Info Skill - 上市公司信息查询

基于多个免费数据源的上市公司信息查询工具，支持 A 股、港股、美股。

## 数据源

| 数据源 | 类型 | 覆盖市场 | 可靠性 |
|--------|------|----------|--------|
| 腾讯财经 | 实时行情 | A 股 | 高 |
| 新浪财经 | 实时行情、新闻 | A 股、港股 | 中 |
| 东方财富 | 行情、财务数据、新闻 | A 股、港股、美股 | 中 |
| 巨潮资讯网 | 法定信息披露 | A 股、港股 | 官方 |
| 上交所/深交所官网 | 官方公告 | A 股 | 官方 |

## 安装

无需额外依赖，使用项目现有 `requests` 库即可。

## 使用方法

### 导入模块

```python
from skills.stock_info.stock_info import (
    search_stock_info,      # 搜索股票
    get_stock_quote,        # 获取实时行情
    get_company_info,       # 获取公司信息
    get_stock_history,      # 获取历史 K 线
    get_stock_news          # 获取股票新闻
)
```

### 搜索股票

```python
# 支持公司名称、代码、拼音搜索
results = search_stock_info("贵州茅台")
# [{'code': '600519', 'name': '贵州茅台', 'market': 'sh', ...}]

results = search_stock_info("腾讯")
# [{'code': '00700', 'name': '腾讯控股', 'market': 'hk', ...}]

results = search_stock_info("特斯拉")
```

### 获取实时行情

```python
# A 股 (需要市场前缀)
quote = get_stock_quote("sh600519")  # 贵州茅台
quote = get_stock_quote("sz000001")  # 平安银行

# 港股
quote = get_stock_quote("HK00700")   # 腾讯控股
quote = get_stock_quote("HK09988")   # 阿里巴巴

# 美股
quote = get_stock_quote("TSLA")      # 特斯拉
quote = get_stock_quote("AAPL")      # 苹果

# 返回数据
{
    "symbol": "sh600519",
    "name": "贵州茅台",
    "current_price": 1680.50,
    "open": 1675.00,
    "high": 1690.00,
    "low": 1670.00,
    "prev_close": 1678.00,
    "change": 2.50,
    "change_pct": 0.15,
    "volume": 1234567,
    "amount": 2075000000.00,
    "market_cap": 2100000000000,
    "pe_ratio": 28.5,
    "pb_ratio": 8.2,
    "timestamp": "2025-03-22 15:00:00"
}
```

### 获取公司信息

```python
info = get_company_info("sh600519")

# 返回数据
{
    "symbol": "600519",
    "name": "贵州茅台",
    "industry": "酒类制造",
    "area": "贵州遵义",
    "listing_date": "2001-08-27",
    "pe_ratio": 28.5,
    "pb_ratio": 8.2,
    "total_revenue": 120000000000,
    "net_profit": 50000000000,
    "gross_margin": 92.5,
    "roe": 30.2,
    "debt_ratio": 15.3,
    "market_cap": 2100000000000
}
```

### 获取历史 K 线

```python
# 日 K 线
klines = get_stock_history("sh600519", period="d")

# 指定日期范围
klines = get_stock_history(
    "sh600519",
    start_date="20250101",
    end_date="20250322",
    period="d"
)

# 周 K/月 K
klines = get_stock_history("sh600519", period="w")  # 周线
klines = get_stock_history("sh600519", period="m")  # 月线

# 返回数据
[
    {
        "date": "2025-03-22",
        "open": 1675.00,
        "close": 1680.50,
        "high": 1690.00,
        "low": 1670.00,
        "volume": 1234567,
        "amount": 2075000000.00,
        "change_pct": 0.15
    },
    ...
]
```

### 获取股票新闻

```python
news_list = get_stock_news("sh600519", limit=10)

# 返回数据
[
    {
        "title": "贵州茅台发布 2024 年年报",
        "summary": "公司实现营收...",
        "source": "东方财富",
        "published_at": "2025-03-21 18:30:00",
        "url": "https://news.eastmoney.com/news/xxx.html"
    },
    ...
]
```

## 支持的股票市场

### A 股
| 市场 | 代码前缀 | 示例 |
|------|----------|------|
| 上交所主板 | 60xxxx | sh600519 |
| 科创板 | 68xxxx | sh688001 |
| 深交所主板 | 00xxxx | sz000001 |
| 创业板 | 30xxxx | sz300750 |
| 北交所 | 4xxxxx/8xxxxx | bj832800 |

### 港股
- 代码格式：`HK` + 5 位数字
- 示例：`HK00700` (腾讯)、`HK09988` (阿里巴巴)

### 美股
- 代码格式：股票 ticker
- 示例：`TSLA`、`AAPL`、`NVDA`

## 注意事项

1. **数据延迟**: 免费数据源可能存在 10-15 分钟延迟
2. **API 稳定性**: 网络请求可能失败，建议添加重试机制
3. **调用频率**: 避免高频调用，建议添加限流
4. **交易时间**: 非交易时间获取的数据为收盘价

## 测试

```bash
cd /home/sudahang/Documents/github/FinAna
source venv/bin/activate
export PYTHONPATH=/home/sudahang/Documents/github/FinAna
python skills/stock_info/test_stock_info.py
```

## 故障排除

### 连接超时
检查网络连接，API 可能被防火墙限制。可尝试：
- 使用代理
- 切换到其他数据源

### 数据为空
- 检查股票代码格式是否正确
- 确认是否在交易时间
- 尝试其他数据源

### 港股代码错误
港股代码需要去掉前导零，例如：
- `HK00700` -> `116.700` (东方财富内部格式)

## 扩展阅读

- [巨潮资讯网](http://www.cninfo.com.cn/) - 证监会指定信息披露平台
- [东方财富网](https://www.eastmoney.com/) - 综合财经数据
- [新浪财经](https://finance.sina.com.cn/) - 实时行情数据
