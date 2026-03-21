# FinAna - 智能投研助手

FinAna 是一个基于多智能体协作和真实 AI 大模型的自动化投资研究分析系统，为个人投资者提供专业级的投研服务。

## ✨ 核心特性

### 🤖 AI 驱动
- **Qwen 大模型**: 集成阿里云 DashScope Qwen-plus 大语言模型
- **真实数据**: 从新浪财经、东方财富获取实时财经数据
- **智能分析**: 四个 AI 智能体分工协作，生成专业投研报告

### 📊 数据来源
- **股票行情**: 实时股价、K 线、成交量等（新浪财经 API）
- **财经新闻**: 实时新闻推送（新浪财经、东方财富）
- **宏观数据**: GDP、CPI、利率等（东方财富、金十数据）
- **行业数据**: 行业增长率、竞争格局等

### 🏗️ 多智能体架构
1. **宏观分析师** - 分析经济环境和市场情绪
2. **行业分析师** - 评估行业趋势和竞争格局
3. **个股分析师** - 深度分析公司基本面和技术面
4. **报告合成器** - 整合所有分析生成完整报告

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的 DashScope API Key
# 获取 API Key: https://dashscope.console.aliyun.com/
```

**.env 文件内容**:
```bash
DASHSCOPE_API_KEY=sk-your-api-key-here
DASHSCOPE_MODEL=qwen-plus
```

### 3. 运行测试

```bash
# 运行全部测试
pytest

# 运行特定测试模块
pytest tests/test_agents.py -v
```

### 4. 启动服务

#### 启动 Web 界面（推荐）

```bash
python -m web_ui.app
```

访问 http://localhost:7860

#### 启动 API 服务

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

## 项目结构

```
FinAna/
├── agents/                     # AI 智能体模块
│   ├── macro_analyst_ai.py     # 宏观经济分析师（AI）
│   ├── industry_analyst_ai.py  # 行业分析师（AI）
│   ├── equity_analyst_ai.py    # 个股分析师（AI）
│   └── report_synthesizer_ai.py # 报告合成器（AI）
│   ├── macro_analyst.py        # 宏观经济分析师（模拟）
│   ├── industry_analyst.py     # 行业分析师（模拟）
│   ├── equity_analyst.py       # 个股分析师（模拟）
│   └── report_synthesizer.py   # 报告合成器（模拟）
├── workflows/                  # 工作流模块
│   ├── ai_research_workflow.py # AI 投研工作流
│   └── research_workflow.py    # 模拟工作流
├── data/                       # 数据模块
│   ├── schemas.py              # Pydantic 数据模型
│   ├── mock_data.py            # 模拟数据（备用）
│   └── finance_data.py         # 真实财经数据获取
├── llm/                        # 大模型模块
│   ├── client.py               # DashScope API 客户端
│   └── __init__.py
├── api/                        # API 服务模块
│   ├── main.py                 # FastAPI 应用
│   └── routers/analysis.py     # 分析端点
├── web_ui/                     # Web 界面模块
│   └── app.py                  # Gradio 应用
├── tests/                      # 测试模块
├── requirements.txt            # Python 依赖
├── .env.example                # 环境配置模板
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
│              AI Research Workflow                           │
│         协调四个 AI 智能体按顺序执行分析任务                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│  Macro Agent  │ → │ Industry Agent  │ → │ Equity Agent  │
│   宏观分析师   │   │    行业分析师    │   │   个股分析师   │
│               │   │                 │   │               │
│ + Qwen LLM    │   │ + Qwen LLM      │   │ + Qwen LLM    │
│ + 真实宏观数据 │   │ + 真实行业数据   │   │ + 真实股票数据  │
└───────────────┘   └─────────────────┘   └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         Report Synthesizer (AI 报告合成器)                   │
│              整合所有分析，生成 Markdown 报告                   │
└─────────────────────────────────────────────────────────────┘
```

## 数据源说明

### 境内数据源
| 数据源 | 用途 | 可靠性 |
|--------|------|--------|
| 新浪财经 | 股票行情、财经新闻 | ⭐⭐⭐⭐⭐ |
| 东方财富 | 行业数据、财务数据 | ⭐⭐⭐⭐⭐ |
| 金十数据 | 宏观经济数据 | ⭐⭐⭐⭐ |

### 支持的股票
- **美股**: TSLA, NVDA, AAPL, MSFT, GOOGL, AMZN, META 等
- **A 股**: 沪深 300 成分股（需配置对应市场数据源）
- **港股**: 恒生指数成分股（需配置对应市场数据源）

## API 使用示例

### 使用 curl

```bash
# 提交分析请求
curl -X POST "http://localhost:8000/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query": "分析特斯拉股票的投资价值"}'

# 获取分析结果
curl "http://localhost:8000/analysis/result/{task_id}"
```

### 使用 Python

```python
from workflows.ai_research_workflow import AIResearchWorkflow

workflow = AIResearchWorkflow()
report = workflow.execute("分析特斯拉股票的未来走势")

print(report.full_report)
print(f"投资建议：{report.recommendation}")
print(f"目标价格：${report.target_price}")
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DASHSCOPE_API_KEY` | DashScope API 密钥 | 必填 |
| `DASHSCOPE_MODEL` | 使用的模型 | `qwen-plus` |
| `DASHSCOPE_MAX_TOKENS` | 最大输出 token 数 | 4096 |
| `DASHSCOPE_TEMPERATURE` | 生成温度 | 0.7 |

### 模型选择

DashScope 提供多个 Qwen 模型：

| 模型 | 适用场景 | 价格 |
|------|----------|------|
| qwen-turbo | 快速响应，简单任务 | 最便宜 |
| qwen-plus | 复杂分析任务（推荐） | 中等 |
| qwen-max | 最高质量分析 | 最贵 |

## 测试

```bash
# 运行所有测试
pytest

# 详细输出
pytest -v

# 运行特定测试
pytest tests/test_agents.py::TestMacroAnalystAI -v
pytest tests/test_api.py -v
```

## 示例输出

输入：`"分析特斯拉股票的未来走势"`

输出报告包含：
```markdown
# 投资研究报告

**查询**: 分析特斯拉股票的未来走势

## 执行摘要
**投资建议**: 买入
**目标价格**: $213.33
**时间 horizon**: 3-6 个月

## 宏观经济分析
- GDP 增长：5.2%
- 通胀率：0.2%
- 利率：3.45%
- 市场情绪：bullish

## 行业分析：汽车
- 行业增长：8.3%
- 主要趋势：电动化、智能化、网联化

## 公司分析：Tesla (TSLA)
- 当前股价：$185.50
- 财务健康：稳健
- 技术信号：buy

## 投资结论
...
```

## 常见问题

### Q: 如何获取 DashScope API Key?
A: 访问 [DashScope 控制台](https://dashscope.console.aliyun.com/) 注册账号并创建 API Key。

### Q: 分析失败怎么办？
A: 检查以下几点：
1. API Key 是否正确配置
2. 网络连接是否正常
3. API 账户是否有足够额度
4. 查看错误日志获取详细信息

### Q: 可以分析 A 股/港股吗？
A: 当前主要支持美股，A 股和港股数据源正在集成中。

### Q: 费用如何？
A: DashScope API 按 token 计费，具体价格参考 [官方定价](https://help.aliyun.com/zh/dashscope/)。

## 开发计划

### 已完成
- [x] DashScope Qwen 大模型集成
- [x] 财经数据获取（新闻、行情、宏观）
- [x] AI 智能体实现
- [x] 现代化 Web 界面
- [x] 单元测试

### 进行中
- [ ] A 股数据源集成
- [ ] 更多技术指标分析
- [ ] 图表可视化

### 计划中
- [ ] 实时推送通知
- [ ] 投资组合管理
- [ ] 历史报告回测

## 免责声明

- 本项目仅供学习和演示用途
- 生成的报告不构成投资建议
- 投资有风险，决策需谨慎
- 请咨询持牌金融顾问获取专业建议

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
