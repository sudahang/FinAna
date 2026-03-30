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

## 多轮对话功能

系统支持多轮对话，保留对话历史和上下文，允许用户进行连续追问。

### 对话记忆架构

```
memory/
├── __init__.py                  # 模块导出
└── conversation_memory.py       # 对话记忆管理
```

### 核心组件

1. **ConversationMemory**: 会话管理器
   - 基于 session_id 管理对话
   - 自动清理过期会话 (TTL: 1 小时)
   - LRU 淘汰机制 (默认最多 1000 个会话)

2. **ConversationSession**: 单个会话
   - 存储消息历史
   - 存储上下文数据 (股票、国家、行业等)

3. **Message**: 单条消息
   - 角色 (user/assistant)
   - 内容、时间戳、元数据

### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/analysis/chat` | POST | 聊天端点，支持 session_id 和 history |
| `/analysis/session/{id}` | GET | 获取会话信息 |
| `/analysis/session/{id}/history` | GET | 获取会话历史 |
| `/analysis/session/{id}` | DELETE | 清除会话 |

### 使用示例

```python
from memory.conversation_memory import get_conversation_memory
from workflows.langgraph_workflow import AIResearchWorkflow

# 获取对话记忆
memory = get_conversation_memory()

# 创建会话
session_id = memory.create_session()

# 第一轮对话
workflow = AIResearchWorkflow()
report1 = workflow.execute("分析特斯拉", session_id=session_id)

# 第二轮对话 (带历史)
history = memory.get_history(session_id)
report2 = workflow.execute(
    "它的估值合理吗？",
    session_id=session_id,
    conversation_history=history
)

# 获取存储的上下文
context = memory.get_context(session_id)
# {'symbol': 'TSLA', 'country': 'us', 'sector': '汽车', ...}
```

### Web UI

启动 Web UI 后，访问 **💬 多轮对话** 标签页体验对话功能：

```bash
python -m web_ui.app
```

支持的操作：
- 连续追问，系统自动保留上下文
- 清除对话，开始新话题
- 撤回上一条消息

### 测试

```bash
# 测试多轮对话功能
python test_multi_turn_chat.py
```

## 报告存储和缓存

系统使用 Redis 和 SeaweedFS 实现报告缓存和持久化存储，提高相似查询的响应速度。

### 架构

```
storage/
├── __init__.py              # 模块导出
├── redis_client.py          # Redis 客户端 (缓存摘要)
├── seaweed_client.py        # SeaweedFS 客户端 (存储完整报告)
└── report_cache.py          # 报告缓存服务
```

### 工作流程

```
用户查询 → 检查 Redis 缓存 → (未命中) → 执行 AI 分析 → 存储到 SeaweedFS → 缓存摘要到 Redis
         ↓
    (命中) → 返回缓存报告
```

### 启动存储服

```bash
# 启动 Redis 和 SeaweedFS
docker-compose up -d

# 验证服务
docker-compose ps

# 查看日志
docker-compose logs -f redis
docker-compose logs -f seaweedfs
```

### 服务端口

| 服务 | 端口 | 用途 |
|------|------|------|
| Redis | 6379 | 缓存摘要和索引 |
| SeaweedFS Master | 9333 | 集群管理 |
| SeaweedFS Filer | 8888 | 文件访问 |
| SeaweedFS Volume | 8080 | 数据卷 |

### 使用示例

```python
from storage.report_cache import get_report_cache_service

# 获取缓存服务
cache_service = get_report_cache_service()

# 检查缓存
cached_report = cache_service.find_cached_report("分析特斯拉")
if cached_report:
    print(f"找到缓存报告：{cached_report.recommendation}")

# 缓存新报告
report_id, success = cache_service.cache_report(
    report=report,
    query="分析特斯拉",
    symbol="TSLA",
    country="us"
)
```

### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/analysis/cache/search?query=xxx` | GET | 搜索相似缓存报告 |
| `/analysis/cache/report/{id}` | GET | 获取指定缓存报告 |
| `/analysis/cache/stats` | GET | 获取缓存统计 |
| `/analysis/cache/clear` | POST | 清除缓存 |
| `/analysis/cache/health` | GET | 检查缓存健康状态 |

### 配置

```bash
# 环境变量
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 可选

SEAWEED_FILER_URL=http://localhost:8888
SEAWEED_MASTER_URL=http://localhost:9333

ENABLE_REPORT_CACHE=true
REPORT_CACHE_TTL=604800  # 7 天
```

### 测试

```bash
# 测试存储和缓存功能
python test_storage_cache.py
```

### 缓存策略

- **相似性匹配**: 基于查询哈希和关键词匹配
- **符号索引**: 按股票代码索引报告
- **自动过期**: 默认 7 天 TTL
- **容量限制**: 最多缓存 1000 份报告/符号

## 测试

```bash
# 运行所有测试 (不依赖外部服务)
python test_full_workflow.py    # 7/7 测试通过
python test_storage_mock.py     # 7/7 测试通过
python test_multi_turn_chat.py  # 多轮对话测试

# 运行真实存储测试 (需要 Docker)
python test_storage_cache.py

# AI Agent 集成测试 (需要 API Key)
python test_ai_agent.py
```

### 测试状态

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 模块导入 | ✅ | 所有 Python 模块正常导入 |
| 对话记忆 | ✅ | 多轮对话记忆功能正常 |
| 输入路由 | ✅ | 用户查询识别正常 |
| 工作流初始化 | ✅ | LangGraph 工作流正常 |
| 存储服务类 | ✅ | Redis/SeaweedFS 客户端正常 |
| 缓存逻辑 | ✅ | 报告缓存逻辑正常 |
| API 模型 | ✅ | FastAPI 请求/响应模型正常 |

**注意**: 输入路由测试需要有效的 DashScope API Key，如果没有配置会显示 API 错误，但核心功能正常。
