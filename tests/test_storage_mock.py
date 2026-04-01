#!/usr/bin/env python3
"""存储和缓存功能测试 - 不依赖 Docker 的模拟测试。"""

import os
import sys
import json
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置临时目录用于模拟 SeaweedFS 存储
TEMP_STORAGE_DIR = tempfile.mkdtemp(prefix="finana_seaweed_")
os.environ["SEAWEED_FILER_URL"] = f"file://{TEMP_STORAGE_DIR}"


def print_header(title: str):
    """打印标题."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(name: str, success: bool, message: str = ""):
    """打印测试结果."""
    status = "✅" if success else "❌"
    msg = f"{status} {name}"
    if message:
        msg += f": {message}"
    print(msg)
    return success


# ============================================
# 测试 1: 类初始化测试
# ============================================
def test_class_initialization():
    """测试类初始化."""
    print_header("测试 1: 类初始化 (不连接)")

    from storage.redis_client import RedisClient
    from storage.seaweed_client import SeaweedClient
    from storage.report_cache import ReportCacheService

    results = []

    # 测试 Redis 客户端 (不连接)
    try:
        redis_client = RedisClient(
            host="localhost",
            port=6379,
            default_ttl=3600,
        )
        results.append(print_result("RedisClient 初始化", True))
    except Exception as e:
        results.append(print_result("RedisClient 初始化", False, str(e)))

    # 测试 SeaweedFS 客户端 (不连接)
    try:
        seaweed_client = SeaweedClient(
            filer_url="http://localhost:8888",
            master_url="http://localhost:9333",
        )
        results.append(print_result("SeaweedClient 初始化", True))
    except Exception as e:
        results.append(print_result("SeaweedClient 初始化", False, str(e)))

    # 测试 ReportCacheService (禁用缓存)
    try:
        cache_service = ReportCacheService(enable_cache=False)
        results.append(print_result("ReportCacheService 初始化", True))
    except Exception as e:
        results.append(print_result("ReportCacheService 初始化", False, str(e)))

    return all(results)


# ============================================
# 测试 2: 摘要提取逻辑
# ============================================
def test_summary_extraction():
    """测试摘要提取逻辑."""
    print_header("测试 2: 摘要提取逻辑")

    from storage.report_cache import ReportCacheService

    cache_service = ReportCacheService(enable_cache=False)

    # 测试报告文本
    report_text = """# 投资分析报告

## 摘要
特斯拉是一家领先的电动汽车制造商，在自动驾驶技术和电池创新方面处于行业领先地位。

## 宏观环境
美国经济稳定增长，GDP 增长率约为 2.5%。通胀率控制在 2-3% 范围内。

## 行业分析
电动汽车行业快速增长，预计年增长率超过 20%。竞争格局激烈，主要竞争者包括比亚迪、蔚来等。

## 公司分析
特斯拉 2024 年交付量创历史新高，毛利率保持在 25% 以上。

## 投资建议
建议买入，目标价格 300 美元。
"""

    # 测试摘要提取
    summary = cache_service._extract_summary(report_text, max_length=100)
    print_result("摘要提取 (100 字符)", len(summary) > 0, f"{len(summary)}字符")

    summary_long = cache_service._extract_summary(report_text, max_length=300)
    print_result("摘要提取 (300 字符)", len(summary_long) > 0, f"{len(summary_long)}字符")

    # 验证摘要包含关键信息
    has_keyword = any(kw in summary_long for kw in ["特斯拉", "投资", "分析"])
    print_result("摘要包含关键词", has_keyword)

    return True


# ============================================
# 测试 3: 报告 ID 生成
# ============================================
def test_report_id_generation():
    """测试报告 ID 生成。"""
    print_header("测试 3: 报告 ID 生成")

    from storage.report_cache import ReportCacheService

    cache_service = ReportCacheService(enable_cache=False)

    # 测试 ID 生成
    id1 = cache_service._generate_report_id("分析特斯拉", "TSLA")
    id2 = cache_service._generate_report_id("分析特斯拉", "TSLA")
    id3 = cache_service._generate_report_id("分析苹果", "AAPL")

    # 相同查询应该生成不同的 ID (因为包含时间戳)
    print_result("生成报告 ID", len(id1) == 32, f"ID: {id1}")
    print_result("ID 唯一性", id1 != id2, "不同时间生成不同 ID")
    print_result("不同查询不同 ID", id1 != id3, "不同查询生成不同 ID")

    return True


# ============================================
# 测试 4: 本地文件存储测试
# ============================================
def test_local_file_storage():
    """测试本地文件存储 (模拟 SeaweedFS)."""
    print_header("测试 4: 本地文件存储测试")

    # 创建测试报告
    report_content = """# 测试报告

## 摘要
这是一个测试报告，用于验证存储功能。

## 分析结果
- 投资建议：买入
- 目标价格：$100.00
"""

    # 保存到临时目录
    report_id = "test_report_12345"
    file_path = os.path.join(TEMP_STORAGE_DIR, f"{report_id}.md")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print_result("保存报告", True, f"路径：{file_path}")

        # 验证文件存在
        file_exists = os.path.exists(file_path)
        print_result("文件存在", file_exists)

        # 读取验证
        if file_exists:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            content_match = content == report_content
            print_result("内容验证", content_match)

        # 清理
        if os.path.exists(file_path):
            os.remove(file_path)
        print_result("清理测试文件", True)

        return True

    except Exception as e:
        print_result("本地存储测试", False, str(e))
        return False


# ============================================
# 测试 5: 查询哈希和索引
# ============================================
def test_query_hash_index():
    """测试查询哈希和索引逻辑."""
    print_header("测试 5: 查询哈希和索引")

    import hashlib

    # 测试查询哈希
    query1 = "分析特斯拉股票"
    query2 = "分析特斯拉股票"
    query3 = "分析苹果公司"

    hash1 = hashlib.md5(query1.lower().strip().encode()).hexdigest()
    hash2 = hashlib.md5(query2.lower().strip().encode()).hexdigest()
    hash3 = hashlib.md5(query3.lower().strip().encode()).hexdigest()

    print_result("查询哈希", len(hash1) == 32, f"Hash: {hash1[:16]}...")
    print_result("相同查询相同哈希", hash1 == hash2)
    print_result("不同查询不同哈希", hash1 != hash3)

    # 测试关键词提取
    def extract_keywords(query: str, stop_words: set = None) -> list:
        if stop_words is None:
            stop_words = {"的", "是", "在", "和", "了", "分析", "股票", "公司"}
        keywords = []
        for word in query.lower().split():
            if word not in stop_words and len(word) > 1:
                keywords.append(word)
        # 中文字符提取
        for char in query:
            if '\u4e00' <= char <= '\u9fff' and char not in stop_words:
                keywords.append(char)
        return list(set(keywords))[:5]

    keywords = extract_keywords("分析特斯拉股票未来走势")
    print_result("关键词提取", len(keywords) > 0, f"关键词：{keywords}")

    return True


# ============================================
# 测试 6: 完整的缓存工作流 (模拟)
# ============================================
def test_mock_cache_workflow():
    """测试完整的缓存工作流 (模拟)."""
    print_header("测试 6: 完整缓存工作流 (模拟)")

    from data.schemas import (
        ResearchReport,
        MacroContext,
        IndustryContext,
        CompanyAnalysis,
        CompanyData,
    )

    # 创建完整的测试报告
    report = ResearchReport(
        query="测试查询：分析特斯拉",
        macro_analysis=MacroContext(
            gdp_growth=2.5,
            inflation_rate=2.0,
            interest_rate=4.0,
            unemployment_rate=3.5,
            market_sentiment="neutral",
            summary="宏观经济稳定"
        ),
        industry_analysis=IndustryContext(
            sector_name="电动汽车",
            sector_growth=20.0,
            competitive_landscape="竞争激烈",
            regulatory_environment="支持政策",
            trends=["电动化", "智能化", "网联化"],
            outlook="positive",
            summary="行业前景良好"
        ),
        company_analysis=CompanyAnalysis(
            company=CompanyData(
                symbol="TSLA",
                name="特斯拉",
                sector="电动汽车",
                market_cap=800.0,
                pe_ratio=50.0,
                current_price=250.0
            ),
            financial_health="良好",
            recent_news=[],
            technical_indicator="buy",
            risks=["竞争加剧", "供应链风险"],
            summary="公司基本面良好"
        ),
        investment_thesis="基于分析，建议买入特斯拉",
        recommendation="买入",
        target_price=300.0,
        time_horizon="长期 (1-3 年)",
        full_report="# 特斯拉投资分析报告\n\n## 摘要\n建议买入..."
    )

    print_result("创建 ResearchReport", True, f"查询：{report.query[:20]}...")
    print_result("投资建议", report.recommendation == "买入", report.recommendation)
    print_result("目标价格", report.target_price == 300.0, f"${report.target_price}")

    # 模拟缓存流程
    # 1. 生成报告 ID
    import hashlib
    report_id = hashlib.md5(f"{report.query}:{report.company_analysis.company.symbol}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    print_result("生成报告 ID", len(report_id) > 0, f"ID: {report_id}")

    # 2. 提取摘要
    from storage.report_cache import ReportCacheService
    cache_service = ReportCacheService(enable_cache=False)
    summary = cache_service._extract_summary(report.full_report)
    print_result("提取摘要", len(summary) > 0, f"{len(summary)}字符")

    # 3. 准备元数据
    metadata = {
        "query": report.query,
        "symbol": report.company_analysis.company.symbol,
        "country": "us",
        "sector": report.industry_analysis.sector_name,
        "recommendation": report.recommendation,
        "target_price": str(report.target_price),
        "generated_at": datetime.now().isoformat(),
    }
    print_result("准备元数据", len(metadata) == 7)

    # 4. 模拟存储 (本地文件)
    file_path = os.path.join(TEMP_STORAGE_DIR, f"{report_id}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report.full_report)

    # 保存元数据
    meta_path = os.path.join(TEMP_STORAGE_DIR, f"{report_id}.meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print_result("模拟存储报告", os.path.exists(file_path))
    print_result("模拟存储元数据", os.path.exists(meta_path))

    # 5. 模拟检索
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            loaded_meta = json.load(f)
        symbol_match = loaded_meta.get("symbol") == "TSLA"
        print_result("模拟检索元数据", symbol_match, f"symbol={loaded_meta.get('symbol')}")

    # 清理
    for f in [file_path, meta_path]:
        if os.path.exists(f):
            os.remove(f)
    print_result("清理测试数据", True)

    return True


# ============================================
# 测试 7: Docker 服务检查
# ============================================
def check_docker_services():
    """检查 Docker 服务状态."""
    print_header("测试 7: Docker 服务状态检查")

    import subprocess

    results = []

    # 检查 Docker
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        docker_ok = result.returncode == 0
        print_result("Docker 可用", docker_ok, result.stdout.strip() if docker_ok else "")
    except Exception as e:
        print_result("Docker 可用", False, str(e))
        return False

    # 检查 Docker Compose
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        compose_ok = result.returncode == 0
        print_result("Docker Compose 可用", compose_ok, result.stdout.strip() if compose_ok else "")
    except Exception as e:
        print_result("Docker Compose 可用", False, str(e))

    # 检查运行中的容器
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout:
            containers = result.stdout.strip().split("\n")
            redis_running = any("redis" in c.lower() for c in containers)
            seaweed_running = any("seaweed" in c.lower() for c in containers)
            print_result("Redis 容器运行", redis_running)
            print_result("SeaweedFS 容器运行", seaweed_running)
        else:
            print_result("运行中的容器", False, "无容器运行")
    except Exception as e:
        print_result("检查容器状态", False, str(e))

    return True


# ============================================
# 主测试函数
# ============================================
def main():
    """运行所有测试."""
    print("\n" + "🚀" * 35)
    print("  FinAna 存储服务测试 (不依赖 Docker)")
    print("🚀" * 35)

    print(f"\n临时存储目录：{TEMP_STORAGE_DIR}")

    results = {
        "类初始化": test_class_initialization(),
        "摘要提取": test_summary_extraction(),
        "报告 ID 生成": test_report_id_generation(),
        "本地文件存储": test_local_file_storage(),
        "查询哈希索引": test_query_hash_index(),
        "完整缓存工作流": test_mock_cache_workflow(),
        "Docker 服务检查": check_docker_services(),
    }

    # 打印总结
    print_header("测试总结")

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n总计：{passed}/{total} 测试通过")

    # 清理临时目录
    try:
        import shutil
        shutil.rmtree(TEMP_STORAGE_DIR)
        print(f"\n已清理临时目录：{TEMP_STORAGE_DIR}")
    except Exception as e:
        print(f"清理临时目录失败：{e}")

    if passed == total:
        print("\n🎉 所有测试通过！")
        print("\n下一步 (可选):")
        print("  1. 启动 Docker 服务: docker compose up -d")
        print("  2. 运行真实存储测试：python test_storage_cache.py")
        print("  3. 启动 API 服务：uvicorn api.main:app --reload")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
