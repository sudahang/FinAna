# FinAna - 智能投研助手

FinAna 是一个基于多智能体协作的自动化投资研究分析系统，为个人投资者提供接近专业水平的投研服务。

## 功能特点

- **多智能体协作**：四个专业智能体分工合作（宏观分析师、行业分析师、个股分析师、报告合成器）
- **结构化报告**：生成包含宏观经济、行业分析、公司分析和投资建议的完整 Markdown 报告
- **模拟数据集成**：内置模拟的股票、新闻、经济数据，演示稳定可靠
- **RESTful API**：完整的 FastAPI 后端服务
- **交互式 Web 界面**：基于 Gradio 的简洁前端

## 技术栈

| 组件 | 技术 |
|------|------|
| 智能体框架 | LangGraph / CrewAI |
| 后端服务 | FastAPI |
| 前端界面 | Gradio |
| 数据模型 | Pydantic |
| 测试框架 | pytest |

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行测试

```bash
# 运行全部测试
pytest

# 运行特定测试模块
pytest tests/test_agents.py -v
pytest tests/test_api.py -v

# 查看测试覆盖率
pytest --cov=.
```

### 3. 启动服务

#### 方式一：启动 API 服务

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看交互式 API 文档

#### 方式二：启动 Web 界面

```bash
python -m web_ui.app
```

访问 http://localhost:7860 使用 Web 界面

## 项目结构

```
FinAna/
├── agents/                     # 智能体模块
│   ├── __init__.py
│   ├── macro_analyst.py        # 宏观经济分析师
│   ├── industry_analyst.py     # 行业分析师
│   ├── equity_analyst.py       # 个股分析师
│   └── report_synthesizer.py   # 报告合成器
├── workflows/                  # 工作流模块
│   ├── __init__.py
│   └── research_workflow.py    # 投研工作流编排
├── data/                       # 数据模块
│   ├── __init__.py
│   ├── schemas.py              # Pydantic 数据模型
│   └── mock_data.py            # 模拟数据生成
├── api/                        # API 服务模块
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── models.py               # API 数据模型
│   └── routers/
│       ├── __init__.py
│       └── analysis.py         # 分析相关端点
├── web_ui/                     # Web 界面模块
│   ├── __init__.py
│   └── app.py                  # Gradio 应用
├── tests/                      # 测试模块
│   ├── __init__.py
│   ├── test_schemas.py         # 数据模型测试
│   ├── test_mock_data.py       # 模拟数据测试
│   ├── test_agents.py          # 智能体测试
│   ├── test_workflow.py        # 工作流测试
│   └── test_api.py             # API 测试
├── requirements.txt            # Python 依赖
├── pytest.ini                  # pytest 配置
├── Design.md                   # 设计文档
├── CLAUDE.md                   # 开发指南
└── README.md                   # 项目说明
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web UI (Gradio)                        │
│                   用户输入查询，查看报告                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                     │
│           POST /analysis/analyze - 提交分析请求              │
│           GET  /analysis/status/{id} - 查询任务状态          │
│           GET  /analysis/result/{id} - 获取分析结果          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Workflow Orchestrator                       │
│              协调智能体按顺序执行分析任务                      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│  Macro Agent  │ → │ Industry Agent  │ → │ Equity Agent  │
│   宏观分析师   │   │    行业分析师    │   │   个股分析师   │
│               │   │                 │   │               │
│ - GDP 增长     │   │ - 行业增长率     │   │ - 财务健康     │
│ - 通胀率       │   │ - 竞争格局       │   │ - 技术分析     │
│ - 利率         │   │ - 监管环境       │   │ - 风险因素     │
│ - 市场情绪     │   │ - 行业趋势       │   │ - 新闻摘要     │
└───────────────┘   └─────────────────┘   └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Report Synthesizer (报告合成器)                 │
│           整合所有分析，生成结构化 Markdown 报告                │
└─────────────────────────────────────────────────────────────┘
```

## 核心模块说明

### 智能体模块 (agents/)

#### MacroAnalystAgent - 宏观经济分析师
分析整体经济环境，提供投资背景：
- GDP 增长率
- 通胀率
- 利率
- 失业率
- 市场情绪

#### IndustryAnalystAgent - 行业分析师
分析特定行业/板块：
- 行业增长率
- 竞争格局
- 监管环境
- 关键趋势
- 行业前景

#### EquityAnalystAgent - 个股分析师
分析具体公司/股票：
- 公司基本面
- 财务健康
- 近期新闻
- 技术指标
- 风险因素

#### ReportSynthesizerAgent - 报告合成器
整合所有分析结果：
- 生成投资论点
- 给出投资建议 (买入/持有/卖出)
- 计算目标价格
- 生成完整 Markdown 报告

### 数据模型 (data/schemas.py)

```python
# 宏观经济分析上下文
MacroContext

# 行业分析上下文
IndustryContext

# 公司基本信息
CompanyData

# 新闻条目
NewsItem

# 公司分析结果
CompanyAnalysis

# 最终研究报告
ResearchReport
```

### API 端点 (api/routers/analysis.py)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/analysis/analyze` | POST | 提交分析请求，返回任务 ID |
| `/analysis/status/{task_id}` | GET | 查询任务状态 |
| `/analysis/result/{task_id}` | GET | 获取完整分析结果 |

### 示例请求

```bash
# 提交分析请求
curl -X POST "http://localhost:8000/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query": "分析特斯拉股票"}'

# 查询任务状态
curl "http://localhost:8000/analysis/status/{task_id}"

# 获取分析结果
curl "http://localhost:8000/analysis/result/{task_id}"
```

## 支持的投资标的

当前 Demo 内置模拟数据支持以下股票：

| 代码 | 名称 | 行业 |
|------|------|------|
| TSLA | Tesla, Inc. | 汽车 |
| NVDA | NVIDIA Corporation | 科技 |
| AAPL | Apple Inc. | 科技 |
| MSFT | Microsoft Corporation | 科技 |
| GOOGL | Alphabet Inc. | 科技 |

其他股票将返回默认模拟数据。

## 测试说明

### 运行测试

```bash
# 运行所有测试
pytest

# 详细输出
pytest -v

# 运行特定测试文件
pytest tests/test_agents.py -v
pytest tests/test_api.py -v

# 运行特定测试类
pytest tests/test_agents.py::TestMacroAnalystAgent -v

# 运行特定测试函数
pytest tests/test_agents.py::TestMacroAnalystAgent::test_create_agent -v
```

### 测试覆盖

- `test_schemas.py` - 数据模型验证测试
- `test_mock_data.py` - 模拟数据生成测试
- `test_agents.py` - 各智能体单元测试
- `test_workflow.py` - 工作流集成测试
- `test_api.py` - API 端点测试

## 配置说明

### 依赖要求

- Python 3.10+
- 主要依赖见 `requirements.txt`

### 环境变量（可选）

当前 Demo 使用模拟数据，无需配置 API 密钥。未来接入真实 LLM 时可配置：

```bash
export OPENAI_API_KEY="your-api-key"
export LANGCHAIN_API_KEY="your-api-key"
```

## 示例输出

输入查询：`"分析特斯拉股票的未来走势"`

系统将生成包含以下章节的报告：

```markdown
# Investment Research Report

**Query:** 分析特斯拉股票的未来走势

---

## Executive Summary
**Recommendation:** BUY
**Target Price:** $213.33
**Time Horizon:** 3-6 months

---

## Macroeconomic Analysis
| Indicator | Value |
|-----------|-------|
| GDP Growth | 2.5% |
| Inflation Rate | 3.2% |
...

## Industry Analysis: Automotive
...

## Company Analysis: Tesla, Inc. (TSLA)
...

## Investment Conclusion
...
```

## 开发计划

### 当前阶段
- [x] 多智能体架构设计
- [x] 模拟数据集成
- [x] 基础工作流实现
- [x] API 服务
- [x] Web 界面
- [x] 单元测试

### 未来增强
- [ ] 接入真实 LLM（OpenAI/Anthropic）
- [ ] 集成真实金融数据 API（Yahoo Finance/Alpha Vantage）
- [ ] 支持更多投资标的
- [ ] 添加图表可视化
- [ ] 实现异步任务队列（Celery）
- [ ] 添加用户认证
- [ ] 支持历史分析查询
- [ ] 多语言支持

## 注意事项

- 本项目为演示用途，使用模拟数据
- 生成的报告不构成真实投资建议
- 实际投资请咨询持牌金融顾问

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
