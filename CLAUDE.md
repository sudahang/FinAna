# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinAna 是一个基于多智能体协作和真实 AI 大模型的自动化投资研究分析系统。用户输入自然语言查询（如"分析特斯拉股票的未来走势"），系统通过四个 AI 智能体协作生成专业投研报告。

## 快速启动

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置 PYTHONPATH
export PYTHONPATH=/home/sudahang/Documents/github/FinAna

# 运行测试
pytest -v

# 启动 Web UI
python -m web_ui.app
# 访问 http://localhost:7860

# 启动 API 服务
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs

# 测试 AI Agent
python test_ai_agent.py
```

## 技术栈

- **LLM**: DashScope Qwen3.5-plus (`https://coding.dashscope.aliyuncs.com/v1`)
- **后端**: FastAPI + Pydantic
- **前端**: Gradio (v6.0, 现代化 UI 设计)
- **数据源**: 新浪财经 (行情/新闻)、东方财富 (行业/财务数据)

## 项目结构

```
FinAna/
├── agents/                     # AI 智能体
│   ├── macro_analyst_ai.py     # 宏观经济分析师 (AI)
│   ├── industry_analyst_ai.py  # 行业分析师 (AI)
│   ├── equity_analyst_ai.py    # 个股分析师 (AI)
│   └── report_synthesizer_ai.py # 报告合成器 (AI)
├── workflows/                  # 工作流编排
│   └── ai_research_workflow.py # AI 投研工作流
├── data/                       # 数据层
│   ├── schemas.py              # Pydantic 数据模型
│   └── finance_data.py         # 真实财经数据获取
├── llm/                        # 大模型模块
│   └── client.py               # DashScope API 客户端
├── api/                        # API 服务
│   ├── main.py                 # FastAPI 应用
│   └── routers/analysis.py     # 分析端点
├── web_ui/                     # Web 界面
│   └── app.py                  # Gradio 应用 (现代设计)
├── skills/                     # 技能模块
│   └── stock_info/             # 上市公司信息查询 skill
│       ├── stock_info.py       # 核心实现 (A 股/港股/美股)
│       ├── skill.yml           # Skill 配置
│       └── test_stock_info.py  # 测试脚本
├── tests/                      # 单元测试
├── test_ai_agent.py            # AI Agent 集成测试
└── requirements.txt            # 依赖
```

## AI 智能体协作流程

```
用户查询 → MacroAnalystAgent → IndustryAnalystAgent → EquityAnalystAgent → ReportSynthesizerAgent → Markdown 报告
```

1. **MacroAnalystAgent**: 分析 GDP、CPI、利率等宏观指标
2. **IndustryAnalystAgent**: 分析行业趋势、竞争格局
3. **EquityAnalystAgent**: 分析公司基本面、技术指标
4. **ReportSynthesizerAgent**: 整合所有分析生成完整报告

## 关键配置

### LLM 配置 (`llm/client.py`)
```python
class DashScopeConfig(BaseModel):
    api_key: str
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model: str = "qwen3.5-plus"
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30  # 超时设置
```

### 环境变量 (`.env`)
```bash
DASHSCOPE_API_KEY=sk-your-api-key
DASHSCOPE_MODEL=qwen3.5-plus
```

### 支持的股票
- **美股**: TSLA, NVDA, AAPL, MSFT, GOOGL, AMZN, META
- 通过 `company_mapping` 自动识别中英文公司名称

## 测试

```bash
# 运行所有测试
pytest -v

# AI Agent 集成测试 (6 项测试)
python test_ai_agent.py
# - LLM 客户端连接
# - 财经数据获取
# - 宏观分析师 AI
# - 行业分析师 AI
# - 个股分析师 AI
# - 完整工作流

# Stock Info Skill 测试
python skills/stock_info/test_stock_info.py
```

## Stock Info Skill

查询上市公司信息的技能，支持 A 股、港股、美股。

### 数据源
- **新浪财经**: 实时行情、新闻
- **东方财富**: 行情、财务数据、新闻
- **巨潮资讯网**: 法定信息披露 (A 股/港股)

### 使用示例

```python
from skills.stock_info.stock_info import (
    search_stock_info,      # 搜索股票
    get_stock_quote,        # 获取实时行情
    get_company_info,       # 获取公司信息
    get_stock_history,      # 获取历史 K 线
    get_stock_news          # 获取股票新闻
)

# 搜索股票
results = search_stock_info("贵州茅台")

# 获取行情 (A 股需要市场前缀)
quote = get_stock_quote("sh600519")  # 贵州茅台
quote = get_stock_quote("HK00700")   # 腾讯控股
quote = get_stock_quote("TSLA")      # 特斯拉

# 获取公司信息
info = get_company_info("sh600519")

# 获取历史 K 线
klines = get_stock_history("sh600519", period="d")

# 获取新闻
news_list = get_stock_news("sh600519", limit=10)
```

### 支持的股票市场
| 市场 | 代码格式 | 示例 |
|------|----------|------|
| 上交所 | sh + 6 位 | sh600519 |
| 深交所 | sz + 6 位 | sz000001 |
| 港股 | HK + 5 位 | HK00700 |
| 美股 | Ticker | TSLA |
```

## 开发注意事项

- **超时处理**: API timeout 设为 30 秒，fallback 机制处理超时
- **队列支持**: Gradio 使用 `demo.queue(max_size=10)` 处理长任务
- **进度显示**: `show_progress="full"` 显示加载指示器
- **错误处理**: 区分超时错误和其他 API 错误，显示友好提示
