# FinAna 存储和缓存配置指南

本文档介绍如何配置和使用 Redis + SeaweedFS 存储系统，用于加速相似查询的响应速度。

## 架构概述

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  用户查询   │ ──→ │  Redis 缓存  │ ──→ │  命中缓存    │
└─────────────┘     └──────────────┘     └──────────────┘
                           ↓                    │
                      未命中缓存                │
                           ↓                    │
                    ┌──────────────┐            │
                    │  AI 分析工作流 │            │
                    └──────────────┘            │
                           │                    │
                           ↓                    │
                    ┌──────────────┐            │
                    │ SeaweedFS    │ ←──────────┘
                    │ (完整报告)   │
                    └──────────────┘
                           │
                           ↓
                    ┌──────────────┐
                    │ Redis 缓存   │
                    │ (摘要/索引)  │
                    └──────────────┘
```

## 快速启动

### 1. 启动存储服务

```bash
# 启动 Redis 和 SeaweedFS
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f redis
docker-compose logs -f seaweedfs
```

### 2. 验证连接

```bash
# 测试 Redis
docker exec -it finana-redis redis-cli ping
# 应返回：PONG

# 测试 SeaweedFS
curl http://localhost:8888/
# 应返回 SeaweedFS Filer 信息
```

### 3. 测试存储功能

```bash
# 运行测试脚本
python test_storage_cache.py
```

## 服务配置

### Redis (缓存层)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 端口 | 6379 | Redis 服务端口 |
| 最大内存 | 256MB | 缓存使用上限 |
| 淘汰策略 | allkeys-lru | LRU 自动淘汰 |
| TTL | 7 天 | 缓存过期时间 |

### SeaweedFS (存储层)

| 组件 | 端口 | 说明 |
|------|------|------|
| Master | 9333 | 集群管理 |
| Volume | 8080 | 数据卷服务 |
| Filer | 8888 | 文件访问接口 |

## 环境变量

在 `.env` 文件中配置：

```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 可选

# SeaweedFS 配置
SEAWEED_FILER_URL=http://localhost:8888
SEAWEED_MASTER_URL=http://localhost:9333

# 缓存策略
ENABLE_REPORT_CACHE=true
REPORT_CACHE_TTL=604800  # 7 天（秒）
```

## API 使用示例

### 1. 搜索相似缓存报告

```bash
curl "http://localhost:8000/analysis/cache/search?query=分析特斯拉&symbol=TSLA&limit=5"
```

### 2. 获取缓存统计

```bash
curl "http://localhost:8000/analysis/cache/stats"
```

### 3. 检查缓存健康状态

```bash
curl "http://localhost:8000/analysis/cache/health"
```

### 4. 清除缓存

```bash
curl -X POST "http://localhost:8000/analysis/cache/clear"
```

## Python 使用示例

```python
from storage.report_cache import get_report_cache_service
from data.schemas import ResearchReport

# 获取缓存服务
cache_service = get_report_cache_service()

# 检查服务可用性
if cache_service.is_available():
    print("缓存服务可用")

    # 查找缓存的报告
    cached = cache_service.find_cached_report("分析特斯拉")
    if cached:
        print(f"找到缓存报告：{cached.recommendation}")
    else:
        # 生成新报告
        report = ResearchReport(
            full_report="# 分析报告\n...",
            recommendation="买入",
            target_price=100.0
        )

        # 缓存报告
        report_id, success = cache_service.cache_report(
            report=report,
            query="分析特斯拉",
            symbol="TSLA",
            country="us"
        )
        print(f"报告已缓存：{report_id}")

# 获取缓存统计
stats = cache_service.get_cache_stats()
print(f"Redis: {stats['redis']}")
print(f"SeaweedFS: {stats['seaweed']}")
```

## 缓存策略

### 相似性匹配

系统使用以下方式查找相似报告：

1. **精确匹配**: 查询哈希完全匹配
2. **股票代码匹配**: 按相同股票索引
3. **关键词匹配**: 提取查询关键词搜索

### 索引结构

```
report:index:symbol:TSLA    # 按股票代码索引
report:index:country:us     # 按国家索引
report:index:sector:科技    # 按行业索引
report:query:{hash}         # 按查询哈希索引
report:summary:{id}         # 报告摘要
```

### 容量管理

- **最大缓存数**: 每个股票最多 1000 份报告
- **自动过期**: 7 天后自动删除
- **LRU 淘汰**: 内存不足时淘汰最久未访问

## 故障排查

### Redis 连接失败

```bash
# 检查 Redis 是否运行
docker ps | grep redis

# 查看 Redis 日志
docker-compose logs redis

# 重启 Redis
docker-compose restart redis
```

### SeaweedFS 连接失败

```bash
# 检查 SeaweedFS 是否运行
docker ps | grep seaweed

# 查看 SeaweedFS 日志
docker-compose logs seaweedfs

# 重启 SeaweedFS
docker-compose restart seaweedfs
```

### 缓存未命中

如果缓存命中率低：

1. 增加 `REPORT_CACHE_TTL`
2. 检查查询语句相似性
3. 查看缓存统计：`/analysis/cache/stats`

## 数据持久化

### Redis 持久化

Redis 配置了 AOF 持久化，数据保存在 `redis-data` 卷中：

```bash
# 查看 Redis 数据
docker exec -it finana-redis redis-cli INFO persistence
```

### SeaweedFS 持久化

SeaweedFS 数据保存在 `seaweedfs-data` 卷中：

```bash
# 查看存储的数据
docker volume inspect finana-seaweedfs-data
```

## 备份和恢复

### 备份 Redis 数据

```bash
# 保存 RDB 快照
docker exec -it finana-redis redis-cli BGSAVE

# 复制数据文件
docker cp finana-redis:/data/dump.rdb ./backup-redis-dump.rdb
```

### 备份 SeaweedFS 数据

```bash
# 复制数据卷
docker run --rm -v finana-seaweedfs-data:/data -v $(pwd):/backup \
  busybox tar czf /backup/seaweedfs-backup.tar.gz /data
```

## 性能优化

### Redis 优化

```bash
# 增加最大内存
docker-compose.yml:
  redis:
    command: redis-server --maxmemory 512mb
```

### SeaweedFS 优化

```bash
# 增加卷大小限制
weed master -volumeSizeLimit=2048
```

## 生产部署建议

1. **Redis 集群**: 使用 Redis Sentinel 或 Cluster
2. **SeaweedFS 多节点**: 部署多个 Volume Server
3. **SSL/TLS**: 启用加密连接
4. **认证**: 配置 Redis 密码和 SeaweedFS 访问控制
5. **监控**: 集成 Prometheus + Grafana 监控

## 相关文档

- [Redis 官方文档](https://redis.io/docs/)
- [SeaweedFS 官方文档](https://github.com/chrislusf/seaweedfs/wiki)
- [Docker Compose 配置](../docker-compose.yml)
