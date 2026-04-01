# FinAna - 智能投研助手

<div align="center">

**基于多智能体协作和 AI 大模型的自动化投资研究分析系统**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Gradio](https://img.shields.io/badge/Gradio-4.0+-orange.svg)](https://gradio.app)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [架构设计](#-架构设计) • [文档](docs/)

</div>

---

## 📖 项目简介

FinAna 是一个基于多智能体协作和真实 AI 大模型的自动化投资研究分析系统。用户输入自然语言查询（如"分析特斯拉股票的未来走势"），系统通过四个 AI 智能体协作，结合真实财经数据，生成专业级的投研报告。

### 核心优势

- 🤖 **AI 驱动**: 集成阿里云 DashScope Qwen3.5-plus 大语言模型
- 📊 **真实数据**: 从新浪财经、东方财富获取实时财经数据
- 💬 **多轮对话**: 支持连续追问，保留对话历史和上下文
- 💾 **智能缓存**: Redis + SeaweedFS 存储，相似查询秒级响应
- 🌐 **全球市场**: 支持美股、A 股、港股分析

---

## ✨ 功能特性

### 1. 多智能体协作

| 智能体 | 职责 | 分析内容 |
|--------|------|----------|
| 🏛️ 宏观分析师 | 经济环境分析 | GDP、CPI、利率、市场情绪 |
| 🏭 行业分析师 | 行业趋势分析 | 行业增长、竞争格局、政策法规 |
| 🏢 个股分析师 | 公司基本面分析 | 财务健康、技术指标、新闻资讯 |
| 📝 报告合成器 | 整合所有分析 | 生成完整投资建议和报告 |

### 2. 多轮对话支持

- 💬 **连续追问**: 基于之前的分析结果深入提问
- 🧠 **上下文记忆**: 自动保留对话历史和关键信息
- ⚡ **快速响应**: 相似问题直接返回缓存结果

**示例对话**:
```
用户：分析特斯拉股票
助手：[生成完整分析报告]

用户：它的估值合理吗？
助手：[基于之前的分析，详细解答估值问题]

用户：和比亚迪比哪个更值得投资？
助手：[对比分析两只股票]
```

### 3. 报告缓存与存储

- 📌 **Redis 缓存**: 存储报告摘要和索引，支持相似性搜索
- 🗄️ **SeaweedFS 存储**: 持久化存储完整报告内容
- ⚡ **快速检索**: 相似查询响应时间从 30 秒降至 0.5 秒
- 🔄 **自动过期**: 默认 7 天 TTL，智能管理缓存容量

### 4. 全链路日志追踪

- 🔍 **Trace ID 追踪**: 每个请求生成唯一 Trace ID，贯穿整个调用链
- 📝 **详细日志**: API → Workflow → Cache → Storage 全环节日志覆盖
- 🐛 **故障排查**: 通过 Trace ID 快速定位问题环节
- 📊 **性能分析**: 清晰展示各环节耗时和状态

**日志示例**:
```
[TRACE=abc12345] [API] 接收请求：POST /analysis/analyze
[TRACE=abc12345] [Workflow] 创建 AIResearchWorkflow 实例
[TRACE=abc12345] [Cache] 检查缓存中的相似报告
[TRACE=abc12345] [Redis] Finding similar reports: query='分析特斯拉...'
[TRACE=abc12345] [Cache] CACHE MISS - 未找到缓存报告
[TRACE=abc12345] [Analysis] Step 1/4: 宏观经济分析
[TRACE=abc12345] [Analysis] Step 2/4: 行业分析
[TRACE=abc12345] [Analysis] Step 3/4: 公司分析
[TRACE=abc12345] [SeaweedFS] Uploading report to /reports/us/TSLA/abc12345.md
[TRACE=abc12345] [Redis] Caching report summary
[TRACE=abc12345] [API] 返回响应：200 OK
```

### 5. 支持的市场

| 市场 | 代码格式 | 示例 | 状态 |
|------|----------|------|------|
| 美股 | Ticker | TSLA, AAPL, NVDA | ✅ 已支持 |
| A 股 | sh/sz + 6 位 | sh600519, sz000858 | ✅ 已支持 |
| 港股 | HK + 5 位 | HK00700, HK09988 | ✅ 已支持 |
| 中概股 | Ticker | BABA, PDD, JD | ✅ 已支持 |

---

## 🏗️ 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户交互层                               │
│  ┌─────────────────┐  ┌─────────────────────────────────────┐  │
│  │   Web UI        │  │   REST API                          │  │
│  │   (Gradio)      │  │   (FastAPI)                         │  │
│  └─────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         智能体编排层                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LangGraph Workflow                                     │   │
│  │  - 输入路由 (查询分析 + 参数识别)                        │   │
│  │  - 多轮对话记忆管理                                      │   │
│  │  - 报告缓存检查                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
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
┌─────────────────────────────────────────────────────────────────┐
│                       报告合成器                                 │
│            整合所有分析，生成 Markdown 格式报告                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         存储层                                   │
│  ┌─────────────────┐  ┌─────────────────────────────────────┐  │
│  │   Redis         │  │   SeaweedFS                         │  │
│  │   (缓存摘要)    │  │   (完整报告)                        │  │
│  └─────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 工作流程

```
1. 用户查询
   │
   ▼
2. 输入路由分析 (识别股票、国家、行业)
   │
   ▼
3. 检查缓存 (相似查询？)
   ├─ 命中 → 直接返回缓存报告
   └─ 未命中 → 执行 AI 分析
       │
       ├── 宏观经济分析
       ├── 行业分析
       ├── 公司分析
       └── 报告合成
           │
           ▼
4. 存储报告 (SeaweedFS) + 缓存摘要 (Redis)
   │
   ▼
5. 返回给用户
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/yourusername/finana.git
cd finana

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的 DashScope API Key
```

**.env 文件内容**:
```bash
# LLM 配置
DASHSCOPE_API_KEY=sk-your-api-key-here
DASHSCOPE_MODEL=qwen3.5-plus
DASHSCOPE_MAX_TOKENS=4096
DASHSCOPE_TEMPERATURE=0.7

# Redis 配置 (可选，用于报告缓存)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# SeaweedFS 配置 (可选，用于报告存储)
SEAWEED_FILER_URL=http://localhost:8888
SEAWEED_MASTER_URL=http://localhost:9333

# 缓存策略
ENABLE_REPORT_CACHE=true
REPORT_CACHE_TTL=604800  # 7 天（秒）
```

### 3. 启动存储服务 (可选)

```bash
# 启动 Redis 和 SeaweedFS
docker compose up -d

# 验证服务
docker compose ps

# 查看日志
docker compose logs -f redis
docker compose logs -f seaweedfs
```

### 4. 运行测试

```bash
# 运行所有测试
python test_full_workflow.py

# 存储功能测试
python test_storage_mock.py

# 多轮对话测试
python test_multi_turn_chat.py
```

### 5. 启动服务

#### 方式一：Web UI (推荐)

```bash
python -m web_ui.app
```

访问 http://localhost:7860

#### 方式二：API 服务

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

#### 方式三：命令行工具

```bash
./cli.sh "分析特斯拉股票"
```

---

## 📡 API 使用示例

### REST API

```bash
# 提交分析请求
curl -X POST "http://localhost:8000/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query": "分析特斯拉股票的投资价值"}'

# 使用缓存搜索
curl "http://localhost:8000/analysis/cache/search?query=分析特斯拉&symbol=TSLA&limit=5"

# 查看缓存统计
curl "http://localhost:8000/analysis/cache/stats"

# 检查缓存健康状态
curl "http://localhost:8000/analysis/cache/health"
```

### Python SDK

```python
from workflows.langgraph_workflow import AIResearchWorkflow
from memory.conversation_memory import get_conversation_memory

# 初始化工作流
workflow = AIResearchWorkflow()

# 单次分析
report = workflow.execute("分析特斯拉股票的未来走势")
print(report.full_report)
print(f"投资建议：{report.recommendation}")
print(f"目标价格：${report.target_price}")

# 多轮对话
memory = get_conversation_memory()
session_id = memory.create_session()

# 第一轮
report1 = workflow.execute("分析特斯拉", session_id=session_id)

# 第二轮 (带历史)
history = memory.get_history(session_id)
report2 = workflow.execute(
    "它的估值合理吗？",
    session_id=session_id,
    conversation_history=history
)
```

---

## 📁 项目结构

```
FinAna/
├── agents/                     # AI 智能体模块
│   ├── input_router_ai.py      # 输入路由器 (查询分析)
│   ├── macro_analyst_ai.py     # 宏观经济分析师
│   ├── industry_analyst_ai.py  # 行业分析师
│   ├── equity_analyst_ai.py    # 个股分析师
│   └── report_synthesizer_ai.py # 报告合成器
├── workflows/                  # 工作流模块
│   ├── langgraph_workflow.py   # LangGraph 工作流
│   └── ai_research_workflow.py # AI 投研工作流
├── memory/                     # 对话记忆模块
│   ├── __init__.py
│   └── conversation_memory.py  # 对话记忆管理
├── storage/                    # 存储模块
│   ├── __init__.py
│   ├── redis_client.py         # Redis 客户端
│   ├── seaweed_client.py       # SeaweedFS 客户端
│   └── report_cache.py         # 报告缓存服务
├── data/                       # 数据模块
│   ├── schemas.py              # Pydantic 数据模型
│   └── finance_data.py         # 财经数据获取
├── llm/                        # 大模型模块
│   └── client.py               # DashScope API 客户端
├── api/                        # API 服务模块
│   ├── main.py                 # FastAPI 应用
│   ├── models.py               # 请求/响应模型
│   └── routers/
│       └── analysis.py         # 分析端点
├── web_ui/                     # Web 界面模块
│   └── app.py                  # Gradio 应用
├── skills/                     # 技能模块
│   └── stock_info/             # 股票信息查询
├── tests/                      # 单元测试模块
├── test_*.py                   # 各种测试脚本
├── docs/                       # 文档目录
├── docker-compose.yml          # Docker 配置
├── requirements.txt            # Python 依赖
└── .env                        # 环境变量配置
```

---

## 🧪 测试

### 测试脚本

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `test_full_workflow.py` | 完整工作流测试 | 无 |
| `test_storage_mock.py` | 存储功能模拟测试 | 无 |
| `test_storage_cache.py` | 存储功能真实测试 | Redis + SeaweedFS |
| `test_full_chain_logging.py` | 全链路日志追踪测试 | Redis + SeaweedFS |
| `test_multi_turn_chat.py` | 多轮对话测试 | 无 |
| `test_ai_agent.py` | AI Agent 集成测试 | API Key |

### 运行测试

```bash
# 运行所有测试
python test_full_workflow.py

# 全链路日志测试（推荐）
python test_full_chain_logging.py

# 运行特定测试
python test_storage_mock.py -v

# 查看测试报告
cat TEST_REPORT.md
```

### 全链路日志测试

全链路日志测试验证从 API 到 Redis/SeaweedFS 的完整调用链：

```bash
# 启动存储服务
docker compose up -d

# 运行全链路测试
python test_full_chain_logging.py
```

**测试项目**:
| 测试 | 说明 | 依赖 |
|------|------|------|
| Trace ID 传递测试 | 验证 Trace ID 在模块间正确传递 | 无 |
| Redis 连接和操作测试 | 测试 Redis 连接和缓存操作 | Redis |
| SeaweedFS 连接和操作测试 | 测试 SeaweedFS 上传下载 | SeaweedFS |
| 报告缓存服务集成测试 | 测试完整的缓存服务 | Redis + SeaweedFS |
| 完整调用链模拟测试 | 模拟完整 API 请求流程 | 无 |

详见：[日志系统使用指南](docs/LOGGING.md) | [全链路测试指南](docs/FULL_CHAIN_TEST.md)

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `DASHSCOPE_API_KEY` | DashScope API 密钥 | - | ✅ |
| `DASHSCOPE_MODEL` | 使用的模型 | `qwen3.5-plus` | ❌ |
| `DASHSCOPE_MAX_TOKENS` | 最大输出 token 数 | `4096` | ❌ |
| `DASHSCOPE_TEMPERATURE` | 生成温度 | `0.7` | ❌ |
| `REDIS_HOST` | Redis 主机 | `localhost` | ❌ |
| `REDIS_PORT` | Redis 端口 | `6379` | ❌ |
| `SEAWEED_FILER_URL` | SeaweedFS Filer 地址 | `http://localhost:8888` | ❌ |
| `ENABLE_REPORT_CACHE` | 启用报告缓存 | `true` | ❌ |
| `REPORT_CACHE_TTL` | 缓存过期时间 (秒) | `604800` | ❌ |

### 模型选择

DashScope 提供多个 Qwen 模型：

| 模型 | 适用场景 | 价格 | 推荐 |
|------|----------|------|------|
| qwen-turbo | 快速响应，简单任务 | 最低 | ⭐⭐ |
| qwen-plus | 复杂分析任务 | 中等 | ⭐⭐⭐⭐ |
| qwen3.5-plus | 最高质量分析 | 较高 | ⭐⭐⭐⭐⭐ |

---

## 🔍 常见问题

### Q: 如何获取 DashScope API Key?

A: 访问 [DashScope 控制台](https://dashscope.console.aliyun.com/) 注册账号并创建 API Key。

### Q: 分析失败怎么办？

A: 检查以下几点：
1. API Key 是否正确配置
2. 网络连接是否正常
3. API 账户是否有足够额度
4. 查看错误日志获取详细信息

### Q: 缓存服务如何工作？

A: 系统使用 Redis 存储报告摘要和索引，SeaweedFS 存储完整报告。当用户查询时，系统先检查缓存，如果找到相似报告则直接返回，否则执行 AI 分析并缓存结果。

### Q: 如何清除缓存？

A: 调用 API 端点：
```bash
curl -X POST "http://localhost:8000/analysis/cache/clear"
```

### Q: 支持哪些股票市场？

A: 目前支持美股、A 股、港股和中概股。详见 [支持的股票市场](#5-支持的市场)。

---

## 📚 相关文档

- [存储配置指南](docs/storage_setup.md) - Redis 和 SeaweedFS 详细配置
- [Docker 测试指南](DOCKER_TEST_GUIDE.md) - Docker 服务启动和测试
- [测试报告](TEST_REPORT.md) - 完整测试结果
- [日志系统使用指南](docs/LOGGING.md) - 日志配置和 Trace ID 追踪
- [全链路测试指南](docs/FULL_CHAIN_TEST.md) - 全链路日志追踪测试

---

## 📅 开发计划

### 已完成
- [x] DashScope Qwen 大模型集成
- [x] 财经数据获取（新闻、行情、宏观）
- [x] AI 智能体实现
- [x] 现代化 Web 界面
- [x] 多轮对话支持
- [x] 报告缓存和存储
- [x] 全链路日志追踪系统
- [x] 单元测试和集成测试

### 进行中
- [ ] A 股数据源深度集成
- [ ] 更多技术指标分析
- [ ] 图表可视化

### 计划中
- [ ] 实时推送通知
- [ ] 投资组合管理
- [ ] 历史报告回测
- [ ] 移动端应用

---

## ⚠️ 免责声明

- 本项目仅供学习和演示用途
- 生成的报告不构成投资建议
- 投资有风险，决策需谨慎
- 请咨询持牌金融顾问获取专业建议

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📞 联系方式

- 📧 Email: your.email@example.com
- 💬 Issues: [GitHub Issues](https://github.com/yourusername/finana/issues)
- 📖 Wiki: [项目 Wiki](https://github.com/yourusername/finana/wiki)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star 支持！⭐**

[🏠 返回顶部](#finana---智能投研助手)

</div>
