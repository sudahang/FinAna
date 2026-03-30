"""Test script for Redis and SeaweedFS storage with report caching."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.schemas import ResearchReport
from storage.redis_client import get_redis_client
from storage.seaweed_client import get_seaweed_client
from storage.report_cache import get_report_cache_service


def test_redis_connection():
    """Test Redis connection."""
    print("=" * 60)
    print("测试 1: Redis 连接测试")
    print("=" * 60)

    try:
        redis_client = get_redis_client()
        connected = redis_client.test_connection()

        if connected:
            print("✅ Redis 连接成功")
            stats = redis_client.get_stats()
            print(f"   内存使用：{stats.get('memory_used', 'N/A')}")
            print(f"   连接客户端数：{stats.get('connected_clients', 'N/A')}")
            return True
        else:
            print("❌ Redis 连接失败")
            print("   请确保 Redis 正在运行：docker-compose up -d redis")
            return False

    except Exception as e:
        print(f"❌ Redis 测试失败：{e}")
        return False


def test_seaweed_connection():
    """Test SeaweedFS connection."""
    print("\n" + "=" * 60)
    print("测试 2: SeaweedFS 连接测试")
    print("=" * 60)

    try:
        seaweed_client = get_seaweed_client()
        connected = seaweed_client.test_connection()

        if connected:
            print("✅ SeaweedFS 连接成功")
            stats = seaweed_client.get_stats()
            print(f"   状态：{stats}")
            return True
        else:
            print("❌ SeaweedFS 连接失败")
            print("   请确保 SeaweedFS 正在运行：docker-compose up -d seaweedfs")
            return False

    except Exception as e:
        print(f"❌ SeaweedFS 测试失败：{e}")
        return False


def test_report_upload_download():
    """Test report upload and download with SeaweedFS."""
    print("\n" + "=" * 60)
    print("测试 3: 报告上传/下载测试")
    print("=" * 60)

    try:
        seaweed_client = get_seaweed_client()

        if not seaweed_client.test_connection():
            print("⚠️  跳过：SeaweedFS 未连接")
            return False

        # Create test report
        report_id = "test_report_" + os.urandom(4).hex()
        report_content = """# 测试报告

## 摘要
这是一个测试报告，用于验证 SeaweedFS 存储功能。

## 分析结果
- 投资建议：买入
- 目标价格：$100.00
- 当前价格：$80.00

## 详细分析
这是一个示例报告内容，用于测试存储和检索功能。
"""

        # Upload report
        print(f"上传报告：{report_id}")
        result = seaweed_client.upload_report(
            report_content=report_content,
            report_id=report_id,
            metadata={"test": "true", "type": "test_report"},
        )

        if result:
            print("✅ 报告上传成功")

            # Download report
            print(f"下载报告：{report_id}")
            downloaded = seaweed_client.download_report(report_id)

            if downloaded:
                print("✅ 报告下载成功")
                print(f"   报告长度：{len(downloaded)} 字符")

                # Verify content
                if downloaded == report_content:
                    print("✅ 内容验证通过")
                else:
                    print("⚠️  内容不匹配")

                # Clean up
                seaweed_client.delete_report(report_id)
                print("✅ 测试报告已删除")

                return True
            else:
                print("❌ 报告下载失败")
                return False
        else:
            print("❌ 报告上传失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False


def test_redis_cache_operations():
    """Test Redis cache operations."""
    print("\n" + "=" * 60)
    print("测试 4: Redis 缓存操作测试")
    print("=" * 60)

    try:
        redis_client = get_redis_client()

        if not redis_client.test_connection():
            print("⚠️  跳过：Redis 未连接")
            return False

        # Test caching
        report_id = "cache_test_" + os.urandom(4).hex()
        summary = "这是一个测试报告摘要"
        metadata = {
            "query": "测试查询",
            "symbol": "TSLA",
            "country": "us",
            "sector": "汽车",
            "recommendation": "买入",
        }

        print(f"缓存报告摘要：{report_id}")
        success = redis_client.cache_report_summary(
            report_id=report_id,
            summary=summary,
            metadata=metadata,
            ttl=3600,  # 1 hour
        )

        if success:
            print("✅ 报告摘要缓存成功")

            # Retrieve cached summary
            print(f"获取缓存的摘要：{report_id}")
            cached = redis_client.get_report_summary(report_id)

            if cached:
                print("✅ 缓存摘要检索成功")
                print(f"   摘要：{cached.get('summary', '')}")
                print(f"   元数据：{cached.get('metadata', {})}")
            else:
                print("❌ 缓存摘要检索失败")

            # Find similar reports
            print("\n查找相似报告...")
            similar = redis_client.find_similar_reports(
                query="测试查询",
                symbol="TSLA",
                limit=5,
            )
            print(f"✅ 找到 {len(similar)} 个相似报告")

            # Clean up
            redis_client.delete_session(report_id) if hasattr(redis_client, 'delete_session') else None

            return True
        else:
            print("❌ 报告摘要缓存失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_cache_service():
    """Test integrated report cache service."""
    print("\n" + "=" * 60)
    print("测试 5: 报告缓存服务集成测试")
    print("=" * 60)

    try:
        cache_service = get_report_cache_service(enable_cache=True)

        if not cache_service:
            print("❌ 无法创建缓存服务")
            return False

        # Check availability
        available = cache_service.is_available()
        print(f"缓存服务可用性：{available}")

        if not available:
            print("⚠️  缓存服务不可用，请确保 Redis 和 SeaweedFS 正在运行")
            return False

        # Get stats
        stats = cache_service.get_cache_stats()
        print(f"缓存统计：{stats}")

        # Create test report
        report = ResearchReport(
            full_report="# 测试报告\n\n这是一个测试报告内容。",
            recommendation="买入",
            target_price=100.0,
        )

        # Cache report
        print("\n缓存测试报告...")
        report_id, success = cache_service.cache_report(
            report=report,
            query="测试查询",
            symbol="TEST",
            country="us",
            sector="测试",
        )

        if success:
            print(f"✅ 报告缓存成功，ID: {report_id}")

            # Find cached report
            print("\n查找缓存的报告...")
            cached_report = cache_service.find_cached_report(
                query="测试查询",
                symbol="TEST",
            )

            if cached_report:
                print("✅ 找到缓存的报告")
                print(f"   投资建议：{cached_report.recommendation}")
                print(f"   目标价格：{cached_report.target_price}")
            else:
                print("⚠️  未找到缓存的报告")

            return True
        else:
            print("❌ 报告缓存失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("FinAna 存储和缓存功能测试")
    print("=" * 60)

    # Check environment
    print("\n环境检查:")
    print(f"  REDIS_HOST: {os.getenv('REDIS_HOST', 'localhost')}")
    print(f"  REDIS_PORT: {os.getenv('REDIS_PORT', '6379')}")
    print(f"  SEAWEED_FILER_URL: {os.getenv('SEAWEED_FILER_URL', 'http://localhost:8888')}")

    # Run tests
    results = {
        "redis": test_redis_connection(),
        "seaweed": test_seaweed_connection(),
        "upload_download": test_report_upload_download(),
        "redis_cache": test_redis_cache_operations(),
        "cache_service": test_report_cache_service(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")

    print(f"\n总计：{passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查 Redis 和 SeaweedFS 配置")
        print("\n启动服务:")
        print("  docker-compose up -d")
        print("\n查看日志:")
        print("  docker-compose logs redis")
        print("  docker-compose logs seaweedfs")


if __name__ == "__main__":
    main()
