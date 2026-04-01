# FinAna Docker 服务测试指南

## 当前状态

### ✅ 已完成测试 (7/7 通过)

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 类初始化 | ✅ | RedisClient、SeaweedClient、ReportCacheService 正常 |
| 摘要提取 | ✅ | 从报告提取摘要功能正常 |
| 报告 ID 生成 | ✅ | 唯一 ID 生成正常 |
| 本地文件存储 | ✅ | 文件保存和读取正常 |
| 查询哈希索引 | ✅ | 哈希生成和关键词提取正常 |
| 完整缓存工作流 | ✅ | 模拟缓存流程正常 |
| Docker 服务检查 | ✅ | Docker 和 Docker Compose 已安装 |

### ⚠️ 待完成测试

| 测试项 | 状态 | 原因 |
|--------|------|------|
| Redis 真实连接 | ⏸️ | Docker 镜像拉取失败 (网络问题) |
| SeaweedFS 真实连接 | ⏸️ | Docker 镜像拉取失败 (网络问题) |
| 完整存储测试 | ⏸️ | 等待 Docker 服务启动 |

---

## 启动 Docker 服务的方法

### 方法 1: 使用国内镜像 (推荐)

修改 `docker-compose.yml` 使用国内镜像源：

```yaml
services:
  redis:
    image: registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine
  seaweedfs:
    image: registry.cn-shanghai.aliyuncs.com/seaweedfs/seaweedfs:latest
```

### 方法 2: 手动拉取镜像

```bash
# 拉取 Redis
docker pull registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine

# 拉取 SeaweedFS
docker pull registry.cn-shanghai.aliyuncs.com/seaweedfs/seaweedfs:latest

# 启动服务
docker compose up -d
```

### 方法 3: 直接运行容器

```bash
# 运行 Redis
docker run -d --name finana-redis \
  -p 6379:6379 \
  --restart unless-stopped \
  registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine

# 运行 SeaweedFS
docker run -d --name finana-seaweedfs \
  -p 9333:9333 -p 8080:8080 -p 8888:8888 \
  --restart unless-stopped \
  registry.cn-shanghai.aliyuncs.com/seaweedfs/seaweedfs:latest \
  weed master -ip=0.0.0.0 -port=9333 & \
  weed volume -master=127.0.0.1:9333 -ip=0.0.0.0 -port=8080 -dir=/data/volume & \
  weed filer -master=127.0.0.1:9333 -ip=0.0.0.0 -port=8888
```

---

## 验证服务

### 检查容器状态

```bash
docker compose ps
# 或
docker ps | grep finana
```

### 测试 Redis 连接

```bash
docker exec -it finana-redis redis-cli ping
# 应返回：PONG
```

### 测试 SeaweedFS 连接

```bash
curl http://localhost:8888/
# 应返回 SeaweedFS 信息
```

### 测试 API 健康检查

```bash
curl http://localhost:8000/analysis/cache/health
```

---

## 运行完整测试

### 1. 启动服务后运行

```bash
# 启动 Docker 服务
docker compose up -d

# 等待服务就绪
sleep 5

# 运行存储测试
python test_storage_cache.py

# 运行完整工作流测试
python test_full_workflow.py
```

### 2. 查看测试报告

```bash
cat TEST_REPORT.md
```

---

## 当前网络问题解决方案

由于 Docker Hub 拉取超时，建议：

1. **配置 Docker 镜像加速器**
   ```bash
   # 编辑 /etc/docker/daemon.json
   {
     "registry-mirrors": [
       "https://docker.mirrors.ustc.edu.cn",
       "https://registry.cn-hangzhou.aliyuncs.com"
     ]
   }

   # 重启 Docker
   sudo systemctl restart docker
   ```

2. **离线下载镜像**
   - 在有网络的机器上下载镜像
   - 导出：`docker save -o redis.tar redis:7-alpine`
   - 导入：`docker load -i redis.tar`

3. **使用本地 Redis**
   ```bash
   # 安装 Redis
   sudo apt-get install redis-server

   # 启动 Redis
   sudo systemctl start redis-server

   # 验证
   redis-cli ping
   ```

---

## 测试结果摘要

### 通过的测试功能

✅ **核心功能正常**
- 所有 Python 模块导入正常
- 对话记忆功能正常
- 输入路由功能正常
- 工作流初始化正常
- 存储服务类初始化正常
- 缓存逻辑正常
- API 模型正常

✅ **模拟测试通过**
- 摘要提取逻辑正确
- 报告 ID 生成唯一
- 本地文件存储正常
- 查询哈希索引正确
- 完整缓存工作流正常

### 等待 Docker 服务

⏸️ **需要 Docker 服务验证的功能**
- Redis 真实连接测试
- SeaweedFS 真实连接测试
- 报告上传/下载测试
- 缓存命中率测试

---

## 下一步

1. **解决网络问题** 配置 Docker 镜像加速
2. **启动 Docker 服务** `docker compose up -d`
3. **运行完整测试** `python test_storage_cache.py`
4. **启动 API 服务** `uvicorn api.main:app --reload`

---

**文档生成时间**: 2026-03-30
**测试版本**: v0.2.0
**网络状态**: Docker Hub 连接超时
