# Stock Info Skill 文档

## 概述

Stock Info Skill 是一个用于查询上市公司信息的工具，整合了多个免费数据源，提供实时行情、公司信息、历史 K 线和股票新闻等功能。

## 支持的市场

| 市场 | 代码格式 | 示例 | 数据源 |
|------|----------|------|--------|
| 上交所 A 股 | sh + 6 位数字 | sh600519 | 腾讯财经、新浪财经 |
| 深交所 A 股 | sz + 6 位数字 | sz000001 | 腾讯财经、新浪财经 |
| 港股 | HK + 5 位数字 | HK00700 | 新浪财经 |
| 美股 | 股票代码 | TSLA, AAPL | 东方财富 |

## 功能列表

### 1. 搜索股票 (search_stock_info)

搜索股票，支持公司名称、代码、拼音。

```python
from skills.stock_info.stock_info import search_stock_info

# 按名称搜索
results = search_stock_info("贵州茅台")
results = search_stock_info("腾讯")
results = search_stock_info("特斯拉")

# 返回结果
[
    {
        "code": "600519",
        "name": "贵州茅台",
        "market": "sh",
        "full_name": "贵州茅台酒股份有限公司",
        "pinyin": "GZMT"
    }
]
```

### 2. 获取实时行情 (get_stock_quote)

获取股票实时行情数据。

```python
from skills.stock_info.stock_info import get_stock_quote

# A 股
quote = get_stock_quote("sh600519")  # 贵州茅台
quote = get_stock_quote("sz000001")  # 平安银行

# 港股
quote = get_stock_quote("HK00700")   # 腾讯控股

# 返回数据
{
    "symbol": "sh600519",
    "name": "贵州茅台",
    "current_price": 1445.0,
    "open": 1452.96,
    "high": 1462.5,
    "low": 1439.0,
    "prev_close": 1452.87,
    "change": -7.87,
    "change_pct": -0.54,
    "volume": 26132,
    "amount": 3782820000,
    "market_cap": 1809530000000,
    "pe_ratio": 20.1,
    "timestamp": datetime.now()
}
```

### 3. 获取公司信息 (get_company_info)

获取公司基本信息和财务指标。

```python
from skills.stock_info.stock_info import get_company_info

info = get_company_info("sh600519")

# 返回数据
{
    "symbol": "600519",
    "name": "贵州茅台",
    "industry": "酒类制造",
    "area": "贵州遵义",
    "listing_date": "2001-08-27",
    "pe_ratio": 20.1,
    "pb_ratio": 8.2,
    "total_revenue": 120000000000,
    "net_profit": 50000000000,
    "gross_margin": 92.5,
    "roe": 30.2,
    "debt_ratio": 15.3,
    "market_cap": 1809530000000
}
```

### 4. 获取历史 K 线 (get_stock_history)

获取历史行情数据。

```python
from skills.stock_info.stock_info import get_stock_history

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
        "open": 1452.96,
        "close": 1445.0,
        "high": 1462.5,
        "low": 1439.0,
        "volume": 26132,
        "amount": 3782820000,
        "change_pct": -0.54
    }
]
```

### 5. 获取股票新闻 (get_stock_news)

获取股票相关新闻。

```python
from skills.stock_info.stock_info import get_stock_news

news_list = get_stock_news("sh600519", limit=10)

# 返回数据
[
    {
        "title": "贵州茅台发布 2024 年年报",
        "summary": "公司实现营收...",
        "source": "东方财富",
        "published_at": "2025-03-21 18:30:00",
        "url": "https://news.eastmoney.com/news/xxx.html"
    }
]
```

## 命令行使用

```bash
# 设置环境
source venv/bin/activate
export PYTHONPATH=/home/sudahang/Documents/github/FinAna

# 搜索股票
python skills/stock_info/run_stock_skill.py search 贵州茅台

# 获取行情
python skills/stock_info/run_stock_skill.py quote sh600519
python skills/stock_info/run_stock_skill.py quote HK00700
python skills/stock_info/run_stock_skill.py quote TSLA

# 获取公司信息
python skills/stock_info/run_stock_skill.py company sh600519

# 获取历史 K 线
python skills/stock_info/run_stock_skill.py history sh600519
python skills/stock_info/run_stock_skill.py history sh600519 period=w

# 获取新闻
python skills/stock_info/run_stock_skill.py news sh600519
python skills/stock_info/run_stock_skill.py news sh600519 limit=5
```

## 测试

```bash
# 运行测试脚本
python skills/stock_info/test_stock_info.py
```

## 注意事项

1. **数据延迟**: 免费数据源可能存在 10-15 分钟延迟
2. **API 稳定性**: 网络请求可能失败，建议添加重试机制
3. **调用频率**: 避免高频调用，建议添加限流
4. **交易时间**: 非交易时间获取的数据为收盘价
5. **港股支持**: 港股数据通过新浪财经获取，使用英文逗号分隔格式

## 故障排除

### 连接超时
检查网络连接，某些 API 可能被防火墙限制。

### 数据为空
- 检查股票代码格式是否正确
- 确认是否在交易时间
- 尝试其他数据源

### 常见问题

**Q: 为什么港股数据有时获取失败？**
A: 港股数据依赖新浪财经 API，该 API 有时会返回 403 错误。代码已添加专门的请求头处理。

**Q: 美股数据为什么获取不到？**
A: 美股数据通过东方财富获取，可能受网络连接影响。建议使用 LLM 作为 fallback。

## 扩展阅读

- [巨潮资讯网](http://www.cninfo.com.cn/) - 证监会指定信息披露平台
- [东方财富网](https://www.eastmoney.com/) - 综合财经数据
- [新浪财经](https://finance.sina.com.cn/) - 实时行情数据
- [腾讯财经](https://stockapp.finance.qq.com/) - A 股实时行情
