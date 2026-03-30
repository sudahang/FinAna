# Web Search Skill for FinAna

用于搜索公司股票信息的网络搜索技能。

## 功能

- 搜索股票代码和公司名称
- 查找公司所属国家和市场
- 识别公司所属行业/板块
- 支持 A 股、港股、美股

## 使用示例

```python
from skills.web_search.web_search import (
    search_company_info,
    get_web_searcher,
    WebSearcher
)

# 简单搜索
result = search_company_info('腾讯')
print(result)
# 输出：
# {
#     'symbol': 'HK00700',
#     'name': '腾讯',
#     'country': 'hk',
#     'sector': '科技',
#     'confidence': 0.9
# }

# 使用 WebSearcher 类
searcher = get_web_searcher()
result = searcher.search_stock_info('特斯拉')

# 使用 Yahoo Finance 搜索
result = searcher.search_with_engine('Apple', engine='yahoo')
```

## 支持的市场

| 市场 | 代码格式 | 示例 |
|------|----------|------|
| A 股 - 上交所 | sh + 6 位 | sh600519 |
| A 股 - 深交所 | sz + 6 位 | sz000001 |
| 港股 | HK + 5 位 | HK00700 |
| 美股 | Ticker | TSLA |

## 测试

```bash
python skills/web_search/web_search.py
```
