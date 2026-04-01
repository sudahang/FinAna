# 日志系统使用指南

FinAna 项目现在配备了完整的日志追踪系统，可以追踪从 API 请求到 Redis/SeaweedFS 存储的完整调用链。

## 日志架构

```
API 请求 (/analysis/analyze)
    │
    ├─→ [TRACE=abc123] 生成 Trace ID
    │
    ├─→ AIResearchWorkflow.execute()
    │     │
    │     ├─→ 检查缓存 (ReportCacheService)
    │     │     │
    │     │     ├─→ Redis: find_similar_reports()
    │     │     └─→ SeaweedFS: download_report()
    │     │
    │     ├─→ 宏观分析 (MacroAnalystAgent)
    │     ├─→ 行业分析 (IndustryAnalystAgent)
    │     ├─→ 公司分析 (EquityAnalystAgent)
    │     └─→ 报告合成 (ReportSynthesizerAgent)
    │
    ├─→ 缓存新报告 (ReportCacheService.cache_report())
    │     │
    │     ├─→ SeaweedFS: upload_report()
    │     └─→ Redis: cache_report_summary()
    │
    └─→ 返回响应
```

## 日志格式

```
时间戳 [级别] [模块名] [TRACE=trace_id] [文件名：行号] - 消息
```

示例：
```
2026-04-01 08:00:00 [INFO] [api.routers.analysis] [TRACE=abc12345] [analysis.py:50] - Starting analysis: task_id=xxx, query='分析特斯拉...'
2026-04-01 08:00:01 [INFO] [workflows.langgraph_workflow] [TRACE=abc12345] [langgraph_workflow.py:360] - Starting AI research workflow
2026-04-01 08:00:01 [INFO] [storage.report_cache] [TRACE=abc12345] [report_cache.py:150] - Looking for cached report
2026-04-01 08:00:01 [INFO] [storage.redis_client] [TRACE=abc12345] [redis_client.py:200] - Finding similar reports
2026-04-01 08:00:02 [INFO] [storage.seaweed_client] [TRACE=abc12345] [seaweed_client.py:200] - Downloading report from SeaweedFS
```

## 配置日志

### 基本使用

```python
from logging_config import setup_logging, get_logger

# 设置日志
setup_logging(level=logging.INFO)

# 获取 logger
logger = get_logger(__name__)

# 记录日志
logger.info("应用启动")
logger.debug("调试信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### Trace ID 追踪

```python
from logging_config import set_trace_id, get_trace_id

# 设置 Trace ID
set_trace_id('abc12345')

# 在日志中自动包含 Trace ID
logger.info('这条日志会包含 TRACE=abc12345')

# 获取当前 Trace ID
current_trace = get_trace_id()
```

### 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| DEBUG | 调试信息 | 详细的函数调用、参数传递 |
| INFO | 一般信息 | 关键步骤完成、状态变更 |
| WARNING | 警告 | 非致命错误、降级处理 |
| ERROR | 错误 | 操作失败、异常捕获 |

### 日志输出配置

```python
from logging_config import setup_logging
import logging

# 输出到控制台（INFO 级别）
setup_logging(level=logging.INFO)

# 输出到文件（DEBUG 级别）
setup_logging(
    level=logging.DEBUG,
    log_to_file=True,
    log_file='finana.log'
)

# 简单格式（不包含 Trace ID）
setup_logging(log_format='simple')
```

## 查看日志

### 开发环境

启动 API 服务后，日志会输出到标准输出：

```bash
# 启动 API 服务
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 日志直接显示在终端
```

### 生产环境

配置日志文件：

```python
# 在 main.py 中
setup_logging(
    level=logging.INFO,
    log_to_file=True,
    log_file='/var/log/finana/api.log'
)
```

查看日志文件：

```bash
# 实时查看日志
tail -f /var/log/finana/api.log

# 搜索特定 Trace ID
grep "TRACE=abc12345" /var/log/finana/api.log

# 查看错误日志
grep "ERROR" /var/log/finana/api.log
```

### Docker 环境

```bash
# 查看服务日志
docker-compose logs -f api

# 查看 Redis 操作日志
docker-compose logs -f api | grep Redis

# 查看特定 Trace ID 的调用链
docker-compose logs -f api | grep "TRACE=abc12345"
```

## 日志追踪示例

### 完整调用链追踪

当用户请求"分析特斯拉股票"时：

```
# 1. API 层接收请求
[INFO] [api.routers.analysis] [TRACE=xyz789] Starting analysis: query='分析特斯拉股票'

# 2. 工作流启动
[INFO] [workflows.langgraph_workflow] [TRACE=xyz789] Starting AI research workflow

# 3. 检查缓存
[INFO] [storage.report_cache] [TRACE=xyz789] Looking for cached report: query='分析特斯拉股票'
[INFO] [storage.redis_client] [TRACE=xyz789] Finding similar reports
[DEBUG] [storage.redis_client] [TRACE=xyz789] Exact query match found

# 4. 缓存未命中，执行分析
[INFO] [workflows.langgraph_workflow] [TRACE=xyz789] CACHE MISS: No similar report found
[INFO] [workflows.langgraph_workflow] [TRACE=xyz789] Running macro analysis for country: us
[INFO] [workflows.langgraph_workflow] [TRACE=xyz789] Running industry analysis for sector: 汽车
[INFO] [workflows.langgraph_workflow] [TRACE=xyz789] Running equity analysis for symbol: TSLA

# 5. 缓存新报告
[INFO] [storage.report_cache] [TRACE=xyz789] Caching newly generated report: symbol=TSLA
[INFO] [storage.seaweed_client] [TRACE=xyz789] Uploading report to SeaweedFS: report_id=abc123
[INFO] [storage.seaweed_client] [TRACE=xyz789] Report uploaded successfully
[INFO] [storage.redis_client] [TRACE=xyz789] Caching report summary: report_id=abc123
[INFO] [storage.redis_client] [TRACE=xyz789] Report summary cached successfully

# 6. 完成
[INFO] [workflows.langgraph_workflow] [TRACE=xyz789] Workflow execution completed successfully
```

### 错误追踪

```
# 错误发生时的日志
[ERROR] [storage.seaweed_client] [TRACE=xyz789] Failed to upload report: Connection refused
[ERROR] [storage.report_cache] [TRACE=xyz789] Failed to cache report: SeaweedFS upload failed
[WARNING] [workflows.langgraph_workflow] [TRACE=xyz789] Failed to cache report
[INFO] [workflows.langgraph_workflow] [TRACE=xyz789] Workflow completed (cache disabled)
```

## 最佳实践

1. **统一使用 Trace ID**: 在请求入口处生成 Trace ID，并在整个调用链中传递

2. **记录关键节点**:
   - 请求入口和出口
   - 缓存命中/未命中
   - 外部服务调用（Redis、SeaweedFS、LLM）
   - 错误和异常

3. **避免过度日志**:
   - 循环内使用 DEBUG 级别
   - 不要记录敏感信息（API Key、密码等）

4. **使用结构化日志**:
   ```python
   # 好的做法
   logger.info(f"Report cached: report_id={report_id}, symbol={symbol}")

   # 避免
   logger.info(f"缓存报告 {report_id} 成功，股票代码 {symbol}，时间 {datetime.now()}")
   ```

5. **错误处理**:
   ```python
   try:
       # 操作
   except Exception as e:
       logger.error(f"[TRACE={get_trace_id()}] Operation failed: {e}", exc_info=True)
   ```

## 故障排查

### 日志不显示

检查日志级别设置：
```python
# 确保级别正确
setup_logging(level=logging.INFO)  # 或 DEBUG 获取更详细信息
```

### Trace ID 丢失

确保在调用链开始设置 Trace ID：
```python
set_trace_id(str(uuid.uuid4())[:8])
```

### 日志文件过大

配置日志轮转：
```python
import logging
from logging.handlers import RotatingFileHandler

# 在 setup_logging 中添加
file_handler = RotatingFileHandler(
    'finana.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```
