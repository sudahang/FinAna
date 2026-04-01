"""全链路日志追踪测试 - 测试从 API 到 Redis/SeaweedFS 的完整调用链。

此测试验证：
1. Trace ID 在整个调用链中的传递
2. 日志格式正确性
3. 各环节日志输出
4. Redis 和 SeaweedFS 连接（如果可用）
"""

import os
import sys
import logging
import time
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging first
from logging_config import setup_logging, get_logger, set_trace_id, get_trace_id

setup_logging(level=logging.DEBUG, log_format="detailed")

logger = get_logger(__name__)

# Import storage modules
from storage.redis_client import get_redis_client, RedisClient
from storage.seaweed_client import get_seaweed_client, SeaweedClient
from storage.report_cache import get_report_cache_service, ReportCacheService
from data.schemas import (
    ResearchReport,
    MacroContext,
    IndustryContext,
    CompanyAnalysis,
    CompanyData
)


# ═══════════════════════════════════════════════════════════════════
# 测试工具函数
# ═══════════════════════════════════════════════════════════════════

class TestResult:
    """Test result holder."""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.duration = 0.0

    def __str__(self):
        status = "✅ 通过" if self.passed else "❌ 失败"
        return f"{status} - {self.name} ({self.duration:.2f}s)"


def run_test(test_func, test_name: str) -> TestResult:
    """Run a test function and capture results."""
    result = TestResult(test_name)
    start_time = time.time()

    try:
        trace_id = str(uuid.uuid4())[:8]
        set_trace_id(trace_id)
        logger.info(f"[TEST] Starting test: {test_name}, trace_id={trace_id}")

        passed, message = test_func()
        result.passed = passed
        result.message = message

        if passed:
            logger.info(f"[TEST] Test passed: {test_name} - {message}")
        else:
            logger.warning(f"[TEST] Test failed: {test_name} - {message}")

    except Exception as e:
        result.passed = False
        result.message = f"Exception: {str(e)}"
        logger.error(f"[TEST] Test exception: {test_name} - {e}", exc_info=True)

    result.duration = time.time() - start_time
    return result


# ═══════════════════════════════════════════════════════════════════
# 测试 1: Trace ID 传递测试
# ═══════════════════════════════════════════════════════════════════

def test_trace_id_propagation() -> tuple[bool, str]:
    """测试 Trace ID 在模块间的传递。"""
    # Set trace ID
    trace_id = str(uuid.uuid4())[:8]
    set_trace_id(trace_id)

    # Verify trace ID is accessible
    retrieved_id = get_trace_id()
    if retrieved_id != trace_id:
        return False, f"Trace ID mismatch: expected {trace_id}, got {retrieved_id}"

    # Import modules and verify they can access trace ID
    from storage.redis_client import get_trace_id as redis_get_trace_id
    from storage.seaweed_client import get_trace_id as seaweed_get_trace_id

    redis_trace = redis_get_trace_id()
    seaweed_trace = seaweed_get_trace_id()

    if redis_trace != trace_id:
        return False, f"Redis module trace ID mismatch: {redis_trace}"

    if seaweed_trace != trace_id:
        return False, f"Seaweed module trace ID mismatch: {seaweed_trace}"

    return True, f"Trace ID {trace_id} propagated correctly to all modules"


# ═══════════════════════════════════════════════════════════════════
# 测试 2: Redis 连接和操作测试
# ═══════════════════════════════════════════════════════════════════

def test_redis_operations() -> tuple[bool, str]:
    """测试 Redis 连接和基本操作。"""
    trace_id = get_trace_id()

    try:
        redis_client = get_redis_client()

        # Test connection
        logger.info(f"[TRACE={trace_id}] Testing Redis connection...")
        connected = redis_client.test_connection()

        if not connected:
            return False, "Redis connection failed - service may not be running"

        # Test cache operation
        test_key = f"test_trace_{trace_id}"
        test_summary = f"Test summary for trace {trace_id}"
        test_metadata = {
            "query": "测试查询",
            "symbol": "TSLA",
            "country": "us",
            "test_trace": trace_id
        }

        logger.info(f"[TRACE={trace_id}] Caching test report summary...")
        cached = redis_client.cache_report_summary(
            report_id=test_key,
            summary=test_summary,
            metadata=test_metadata,
            ttl=60
        )

        if not cached:
            return False, "Failed to cache report summary"

        # Test retrieval
        logger.info(f"[TRACE={trace_id}] Retrieving cached summary...")
        retrieved = redis_client.get_report_summary(test_key)

        if not retrieved:
            return False, "Failed to retrieve cached summary"

        if retrieved.get("summary") != test_summary:
            return False, "Retrieved summary does not match"

        # Cleanup
        logger.info(f"[TRACE={trace_id}] Cleaning up test data...")
        redis_client.client.delete(f"report:summary:{test_key}")

        return True, f"Redis operations completed successfully, cached and retrieved data"

    except Exception as e:
        return False, f"Redis test exception: {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# 测试 3: SeaweedFS 连接和操作测试
# ═══════════════════════════════════════════════════════════════════

def test_seaweed_operations() -> tuple[bool, str]:
    """测试 SeaweedFS 连接和基本操作。"""
    trace_id = get_trace_id()

    try:
        seaweed_client = get_seaweed_client()

        # Test connection
        logger.info(f"[TRACE={trace_id}] Testing SeaweedFS connection...")
        connected = seaweed_client.test_connection()

        if not connected:
            return False, "SeaweedFS connection failed - service may not be running"

        # Test upload
        test_id = f"test_report_{trace_id}"
        test_content = f"""# 测试报告

Trace ID: {trace_id}
时间：{time.strftime('%Y-%m-%d %H:%M:%S')}

## 摘要
这是一个全链路测试报告，用于验证日志追踪系统。

## 测试内容
- Redis 缓存操作
- SeaweedFS 存储操作
- Trace ID 传递
"""

        logger.info(f"[TRACE={trace_id}] Uploading test report to SeaweedFS...")
        uploaded = seaweed_client.upload_report(
            report_content=test_content,
            report_id=test_id,
            metadata={"test_trace": trace_id, "test_type": "full_chain"},
            directory="/reports/test"
        )

        if not uploaded:
            return False, "Failed to upload report to SeaweedFS"

        # Test download
        logger.info(f"[TRACE={trace_id}] Downloading report from SeaweedFS...")
        downloaded = seaweed_client.download_report(test_id, directory="/reports/test")

        if not downloaded:
            return False, "Failed to download report from SeaweedFS"

        if downloaded != test_content:
            return False, "Downloaded content does not match uploaded content"

        # Cleanup
        logger.info(f"[TRACE={trace_id}] Deleting test report...")
        deleted = seaweed_client.delete_report(test_id, directory="/reports/test")

        if not deleted:
            logger.warning(f"[TRACE={trace_id}] Failed to delete test report")

        return True, f"SeaweedFS operations completed successfully, upload/download verified"

    except Exception as e:
        return False, f"SeaweedFS test exception: {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# 测试 4: 报告缓存服务集成测试
# ═══════════════════════════════════════════════════════════════════

def test_report_cache_service() -> tuple[bool, str]:
    """测试完整的报告缓存服务（Redis + SeaweedFS 集成）。"""
    trace_id = get_trace_id()
    logger.info(f"[TRACE={trace_id}] Initializing ReportCacheService...")

    try:
        cache_service = get_report_cache_service(enable_cache=True)

        # Check availability
        available = cache_service.is_available()
        if not available:
            return False, "Cache service not available - Redis or SeaweedFS not running"

        logger.info(f"[TRACE={trace_id}] Cache service available, creating test report...")

        # Create test report
        from data.schemas import MacroContext, IndustryContext, CompanyAnalysis, CompanyData
        report = ResearchReport(
            query="全链路测试查询",
            macro_analysis=MacroContext(
                gdp_growth=2.5,
                inflation_rate=2.0,
                interest_rate=4.0,
                unemployment_rate=3.5,
                market_sentiment="neutral",
                summary="宏观测试"
            ),
            industry_analysis=IndustryContext(
                sector_name="测试行业",
                sector_growth=15.0,
                competitive_landscape="竞争激烈",
                regulatory_environment="支持政策",
                trends=["测试趋势"],
                outlook="positive",
                summary="行业测试"
            ),
            company_analysis=CompanyAnalysis(
                company=CompanyData(
                    symbol="TEST",
                    name="测试公司",
                    sector="测试行业",
                    market_cap=100.0,
                    pe_ratio=20.0,
                    current_price=50.0
                ),
                financial_health="良好",
                recent_news=[],
                technical_indicator="buy",
                risks=["测试风险"],
                summary="公司测试"
            ),
            investment_thesis="测试投资论点",
            time_horizon="长期 (1-3 年)",
            full_report="# 全链路测试报告\n\n这是一个测试报告内容。",
            recommendation="买入",
            target_price=100.0,
        )

        # Cache report
        logger.info(f"[TRACE={trace_id}] Caching test report...")
        report_id, success = cache_service.cache_report(
            report=report,
            query="全链路测试查询",
            symbol="TSLA",
            country="us",
            sector="科技"
        )

        if not success:
            return False, "Failed to cache test report"

        logger.info(f"[TRACE={trace_id}] Report cached with ID: {report_id}")

        # Find cached report
        logger.info(f"[TRACE={trace_id}] Finding cached report...")
        cached_report = cache_service.find_cached_report(
            query="全链路测试查询",
            symbol="TSLA"
        )

        if not cached_report:
            return False, "Failed to find cached report"

        if cached_report.recommendation != "买入":
            return False, "Cached report recommendation does not match"

        logger.info(f"[TRACE={trace_id}] Cached report found and verified")

        # Get cache stats
        stats = cache_service.get_cache_stats()
        logger.info(f"[TRACE={trace_id}] Cache stats: {stats}")

        return True, f"Report cache service test passed, report_id={report_id}"

    except Exception as e:
        return False, f"Cache service test exception: {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# 测试 5: 完整调用链模拟测试
# ═══════════════════════════════════════════════════════════════════

def test_full_chain_simulation() -> tuple[bool, str]:
    """模拟完整的 API 请求调用链。"""
    trace_id = str(uuid.uuid4())[:8]
    set_trace_id(trace_id)

    logger.info(f"[TRACE={trace_id}] ═══════════════════════════════════")
    logger.info(f"[TRACE={trace_id}] 开始完整调用链模拟")
    logger.info(f"[TRACE={trace_id}] ═══════════════════════════════════")

    try:
        # Step 1: API 请求入口
        logger.info(f"[TRACE={trace_id}] [API] 接收请求：POST /analysis/analyze")
        logger.info(f"[TRACE={trace_id}] [API] 请求参数：query='分析特斯拉股票', session_id='test_session'")

        # Step 2: 创建工作流
        logger.info(f"[TRACE={trace_id}] [Workflow] 创建 AIResearchWorkflow 实例")
        logger.info(f"[TRACE={trace_id}] [Workflow] 启用缓存：True")

        # Step 3: 检查缓存
        logger.info(f"[TRACE={trace_id}] [Cache] 检查缓存中的相似报告")

        cache_service = get_report_cache_service(enable_cache=True)
        cache_available = cache_service.is_available()

        if cache_available:
            logger.info(f"[TRACE={trace_id}] [Cache] 缓存服务可用")
            logger.info(f"[TRACE={trace_id}] [Cache] 查询 Redis：find_similar_reports(query='分析特斯拉股票')")

            # 模拟缓存查询
            cached_report = cache_service.find_cached_report(
                query="分析特斯拉股票",
                symbol="TSLA"
            )

            if cached_report:
                logger.info(f"[TRACE={trace_id}] [Cache] CACHE HIT - 找到缓存报告")
                logger.info(f"[TRACE={trace_id}] [Cache] 从 SeaweedFS 下载完整报告")
                logger.info(f"[TRACE={trace_id}] [Cache] 返回缓存响应")
            else:
                logger.info(f"[TRACE={trace_id}] [Cache] CACHE MISS - 未找到缓存报告")
                logger.info(f"[TRACE={trace_id}] [Cache] 需要执行完整分析流程")
        else:
            logger.warning(f"[TRACE={trace_id}] [Cache] 缓存服务不可用，跳过缓存检查")

        # Step 4: 执行分析流程
        logger.info(f"[TRACE={trace_id}] [Analysis] 开始执行分析流程")
        logger.info(f"[TRACE={trace_id}] [Analysis] Step 1/4: 宏观经济分析 (country=us)")
        logger.info(f"[TRACE={trace_id}] [Analysis] Step 2/4: 行业分析 (sector=汽车)")
        logger.info(f"[TRACE={trace_id}] [Analysis] Step 3/4: 公司分析 (symbol=TSLA)")
        logger.info(f"[TRACE={trace_id}] [Analysis] Step 4/4: 报告合成")

        # Step 5: 缓存新报告
        if cache_available:
            logger.info(f"[TRACE={trace_id}] [Cache] 缓存新生成的报告")
            logger.info(f"[TRACE={trace_id}] [Cache] 上传到 SeaweedFS: /reports/us/TSLA/{trace_id}.md")
            logger.info(f"[TRACE={trace_id}] [Cache] 缓存摘要到 Redis: report:summary:{trace_id}")
            logger.info(f"[TRACE={trace_id}] [Cache] 建立索引：symbol=TSLA, country=us")

        # Step 6: 返回响应
        logger.info(f"[TRACE={trace_id}] [API] 返回响应：200 OK")
        logger.info(f"[TRACE={trace_id}] [API] 响应内容：report_id={trace_id}, recommendation=买入")

        logger.info(f"[TRACE={trace_id}] ═══════════════════════════════════")
        logger.info(f"[TRACE={trace_id}] 完整调用链模拟完成")
        logger.info(f"[TRACE={trace_id}] ═══════════════════════════════════")

        return True, f"Full chain simulation completed with trace_id={trace_id}"

    except Exception as e:
        logger.error(f"[TRACE={trace_id}] [Error] 调用链模拟失败：{e}", exc_info=True)
        return False, f"Full chain simulation failed: {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# 主测试运行器
# ═══════════════════════════════════════════════════════════════════

def run_all_tests():
    """运行所有测试并输出报告。"""
    print("\n" + "=" * 70)
    print(" FinAna 全链路日志追踪测试")
    print("=" * 70)
    print()

    # Define tests
    tests = [
        (test_trace_id_propagation, "Trace ID 传递测试"),
        (test_redis_operations, "Redis 连接和操作测试"),
        (test_seaweed_operations, "SeaweedFS 连接和操作测试"),
        (test_report_cache_service, "报告缓存服务集成测试"),
        (test_full_chain_simulation, "完整调用链模拟测试"),
    ]

    results = []

    # Run tests
    for test_func, test_name in tests:
        result = run_test(test_func, test_name)
        results.append(result)
        print(f"\n{result}")

    # Summary
    print("\n" + "=" * 70)
    print(" 测试总结")
    print("=" * 70)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for result in results:
        status = "✅" if result.passed else "❌"
        print(f"  {status} {result.name}")
        if result.message:
            print(f"     {result.message}")

    print()
    print(f"  总计：{passed}/{total} 测试通过")
    print()

    if passed == total:
        print("  🎉 所有测试通过！")
    else:
        print("  ⚠️  部分测试失败")
        print()
        print("  提示：")
        print("  - Redis 测试失败：确保 docker compose up -d redis")
        print("  - SeaweedFS 测试失败：确保 docker compose up -d seaweedfs")
        print("  - 查看日志：docker compose logs -f")

    print()

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
