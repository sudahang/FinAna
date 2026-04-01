# 全链路日志追踪测试指南

## 运行测试

```bash
# 设置 PYTHONPATH
export PYTHONPATH=/home/sudahang/Documents/github/FinAna

# 运行测试
python3 test_full_chain_logging.py
```

## 测试项目

| 测试 | 说明 | 依赖 | 状态 |
|------|------|------|------|
| Trace ID 传递测试 | 验证 Trace ID 在模块间正确传递 | 无 | ✅ |
| Redis 连接和操作测试 | 测试 Redis 连接和缓存操作 | Redis | ✅ |
| SeaweedFS 连接和操作测试 | 测试 SeaweedFS 上传下载 | SeaweedFS | ⚠️ |
| 报告缓存服务集成测试 | 测试完整的缓存服务 | Redis + SeaweedFS | ⚠️ |
| 完整调用链模拟测试 | 模拟完整 API 请求流程 | 无 | ✅ |

**注意**: SeaweedFS 测试需要正确配置的 Docker 环境。如果 Filer 服务启动失败，请检查：
- Master、Volume、Filer 启动顺序
- 容器间网络连接
- 元数据存储配置（leveldb/redis）

## 启动依赖服务

```bash
# 启动 Redis 和 SeaweedFS
docker compose up -d

# 验证服务状态
docker compose ps

# 查看服务日志
docker compose logs -f redis
docker compose logs -f seaweedfs
```

## 日志输出示例

### Trace ID 传递

```
2026-04-01 08:16:57 [INFO] [__main__] [TRACE=07e84363] - Trace ID propagated correctly
```

### Redis 操作链路

```
[TRACE=f5383e80] Testing Redis connection...
[TRACE=f5383e80] Redis connection test started
[TRACE=f5383e80] Redis connection test successful
[TRACE=f5383e80] Caching test report summary...
[TRACE=f5383e80] Caching report summary: report_id=test_trace_f5383e80
[TRACE=f5383e80] Report summary stored: key=report:summary:test_trace_f5383e80
[TRACE=f5383e80] Indexed by symbol: TSLA
[TRACE=f5383e80] Indexed by country: us
[TRACE=f5383e80] Query hash stored: b6cbe6d3...
[TRACE=f5383e80] Report summary cached successfully
[TRACE=f5383e80] Retrieving cached summary...
[TRACE=f5383e80] Report summary retrieved: key=report:summary:test_trace_f5383e80
```

### 完整调用链模拟

```
[TRACE=ef1216db] ═══════════════════════════════════
[TRACE=ef1216db] 开始完整调用链模拟
[TRACE=ef1216db] ═══════════════════════════════════
[TRACE=ef1216db] [API] 接收请求：POST /analysis/analyze
[TRACE=ef1216db] [API] 请求参数：query='分析特斯拉股票'
[TRACE=ef1216db] [Workflow] 创建 AIResearchWorkflow 实例
[TRACE=ef1216db] [Cache] 检查缓存中的相似报告
[TRACE=ef1216db] [Cache] 查询 Redis: find_similar_reports
[TRACE=ef1216db] Redis connection test started
[TRACE=ef1216db] Redis connection test successful
[TRACE=ef1216db] SeaweedFS connection test started
[TRACE=ef1216db] [Cache] CACHE MISS - 未找到缓存报告
[TRACE=ef1216db] [Analysis] Step 1/4: 宏观经济分析
[TRACE=ef1216db] [Analysis] Step 2/4: 行业分析
[TRACE=ef1216db] [Analysis] Step 3/4: 公司分析
[TRACE=ef1216db] [Analysis] Step 4/4: 报告合成
[TRACE=ef1216db] [Cache] 缓存新生成的报告
[TRACE=ef1216db] [API] 返回响应：200 OK
[TRACE=ef1216db] ═══════════════════════════════════
[TRACE=ef1216db] 完整调用链模拟完成
```

## 故障排查

### 查看特定 Trace ID 的日志

```bash
# 从测试输出中复制 Trace ID
grep "TRACE=ef1216db" test_full_chain_logging.log

# 在生产环境中
grep "TRACE=ef1216db" /var/log/finana/api.log
```

### 追踪 Redis 操作

```bash
# 查看所有 Redis 相关日志
grep "Redis" test_full_chain_logging.log

# 查看特定 Trace ID 的 Redis 操作
grep "TRACE=xxx.*Redis" test_full_chain_logging.log
```

### 追踪 SeaweedFS 操作

```bash
# 查看所有 SeaweedFS 相关日志
grep "SeaweedFS" test_full_chain_logging.log

# 查看特定 Trace ID 的 SeaweedFS 操作
grep "TRACE=xxx.*SeaweedFS" test_full_chain_logging.log
```

## 日志级别说明

| 级别 | 说明 | 示例场景 |
|------|------|----------|
| DEBUG | 调试信息 | 数据存取详情、索引建立 |
| INFO | 一般信息 | 操作开始/完成、状态变更 |
| WARNING | 警告 | 服务降级、非致命错误 |
| ERROR | 错误 | 连接失败、操作异常 |

## 性能影响

日志系统对性能的影响：

- **Trace ID 传递**: 使用 contextvars，几乎无开销
- **日志输出**: 异步输出，对主流程影响小于 1ms
- **日志级别**: 生产环境建议使用 INFO 级别

## 最佳实践

1. **请求入口设置 Trace ID**: 在 API 层或工作流入口处生成 Trace ID

2. **统一日志格式**: 使用 `logging_config` 模块的 `get_logger` 函数

3. **结构化日志**:
   ```python
   logger.info(f"[TRACE={trace_id}] Operation completed: key={key}")
   ```

4. **错误日志包含异常堆栈**:
   ```python
   try:
       operation()
   except Exception as e:
       logger.error(f"Operation failed: {e}", exc_info=True)
   ```

5. **敏感信息脱敏**: 不要记录 API Key、密码等敏感信息
