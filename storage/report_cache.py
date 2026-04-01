"""Report cache service combining Redis and SeaweedFS."""

import uuid
import hashlib
from typing import Optional, Tuple
from datetime import datetime
import logging
from data.schemas import ResearchReport

from storage.redis_client import RedisClient, get_redis_client
from storage.seaweed_client import SeaweedClient, get_seaweed_client
from logging_config import set_trace_id, get_trace_id

logger = logging.getLogger(__name__)


class ReportCacheService:
    """
    Report cache service for fast retrieval of similar reports.

    Architecture:
    1. Redis: Stores report summaries, metadata, and indexes
    2. SeaweedFS: Stores full report content

    Features:
    - Cache report with summary extraction
    - Find similar cached reports
    - Fast retrieval of cached reports
    - Automatic expiration and cleanup
    """

    def __init__(
        self,
        redis_client: RedisClient = None,
        seaweed_client: SeaweedClient = None,
        cache_ttl: int = 604800,  # 7 days
        enable_cache: bool = True,
    ):
        """
        Initialize report cache service.

        Args:
            redis_client: Redis client instance
            seaweed_client: SeaweedFS client instance
            cache_ttl: Cache TTL in seconds
            enable_cache: Enable/disable caching
        """
        self.redis = redis_client or get_redis_client()
        self.seaweed = seaweed_client or get_seaweed_client()
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache

        # Directory structure for reports
        self.base_directory = "/reports"

    def cache_report(
        self,
        report: ResearchReport,
        query: str,
        symbol: str = None,
        country: str = None,
        sector: str = None,
        ttl: int = None,
    ) -> Tuple[str, bool]:
        """
        Cache a generated report.

        Args:
            report: ResearchReport object
            query: Original user query
            symbol: Stock symbol
            country: Country/market
            sector: Industry sector
            ttl: Optional TTL override

        Returns:
            Tuple of (report_id, success)
        """
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Starting to cache report: query='{query[:50]}...', symbol={symbol}")

        if not self.enable_cache:
            logger.debug(f"[TRACE={trace_id}] Cache is disabled, skipping")
            return str(uuid.uuid4()), False

        try:
            # Generate unique report ID
            report_id = self._generate_report_id(query, symbol)
            logger.debug(f"[TRACE={trace_id}] Generated report_id: {report_id}")

            # Extract summary from report
            summary = self._extract_summary(report.full_report)
            logger.debug(f"[TRACE={trace_id}] Extracted summary: {len(summary)} chars")

            # Prepare metadata with all required fields for ResearchReport reconstruction
            metadata = {
                "query": query,
                "symbol": symbol or "",
                "country": country or "",
                "sector": sector or "",
                "recommendation": report.recommendation,
                "target_price": str(report.target_price) if report.target_price else "",
                "investment_thesis": report.investment_thesis,
                "time_horizon": report.time_horizon,
                # Store nested context summaries for reconstruction
                "macro_summary": report.macro_analysis.summary if report.macro_analysis else "",
                "industry_summary": report.industry_analysis.summary if report.industry_analysis else "",
                "company_summary": report.company_analysis.summary if report.company_analysis else "",
                "generated_at": datetime.now().isoformat(),
            }

            # Store full report in SeaweedFS
            directory = f"{self.base_directory}/{country or 'unknown'}/{symbol or 'general'}"
            logger.info(f"[TRACE={trace_id}] Uploading report to SeaweedFS: directory={directory}")
            upload_success = self.seaweed.upload_report(
                report_content=report.full_report,
                report_id=report_id,
                metadata=metadata,
                directory=directory,
            )

            if not upload_success:
                logger.error(f"[TRACE={trace_id}] Failed to upload report to SeaweedFS")
                return report_id, False

            # Cache summary and metadata in Redis
            logger.info(f"[TRACE={trace_id}] Caching report summary in Redis")
            cache_success = self.redis.cache_report_summary(
                report_id=report_id,
                summary=summary,
                metadata=metadata,
                ttl=ttl or self.cache_ttl,
            )

            if not cache_success:
                logger.error(f"[TRACE={trace_id}] Failed to cache report summary in Redis")
                return report_id, False

            logger.info(f"[TRACE={trace_id}] Report cached successfully: report_id={report_id}")
            return report_id, True

        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Failed to cache report: {e}")
            return str(uuid.uuid4()), False

    def find_cached_report(
        self,
        query: str,
        symbol: str = None,
        similarity_threshold: float = 0.7,
    ) -> Optional[ResearchReport]:
        """
        Find a similar cached report.

        Args:
            query: User query
            symbol: Stock symbol to filter
            similarity_threshold: Minimum similarity score

        Returns:
            ResearchReport if found, None otherwise
        """
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Looking for cached report: query='{query[:50]}...', symbol={symbol}")

        if not self.enable_cache:
            logger.debug(f"[TRACE={trace_id}] Cache is disabled, skipping lookup")
            return None

        try:
            # Find similar reports
            similar_reports = self.redis.find_similar_reports(
                query=query,
                symbol=symbol,
                limit=5,
            )

            if not similar_reports:
                logger.info(f"[TRACE={trace_id}] No similar reports found in cache")
                return None

            # Get the best match
            best_match = similar_reports[0]
            similarity = best_match.get("similarity", 0)
            logger.info(f"[TRACE={trace_id}] Found similar report: similarity={similarity:.2f}, threshold={similarity_threshold}")

            if similarity < similarity_threshold:
                logger.info(f"[TRACE={trace_id}] Similarity {similarity:.2f} below threshold {similarity_threshold}, skipping")
                return None

            # Download full report from SeaweedFS
            report_id = best_match["report_id"]
            logger.info(f"[TRACE={trace_id}] Downloading cached report from SeaweedFS: report_id={report_id}")
            report_content = self._download_cached_report(report_id)

            if not report_content:
                logger.warning(f"[TRACE={trace_id}] Failed to download cached report content")
                return None

            # Reconstruct ResearchReport with all required fields
            metadata = best_match.get("metadata", {})

            # Build minimal context objects from stored summaries
            from data.schemas import MacroContext, IndustryContext, CompanyAnalysis, CompanyData

            macro_analysis = MacroContext(
                gdp_growth=0.0,
                inflation_rate=0.0,
                interest_rate=0.0,
                unemployment_rate=0.0,
                market_sentiment="neutral",
                summary=metadata.get("macro_summary", "Cached report"),
            )

            industry_analysis = IndustryContext(
                sector_name=metadata.get("sector", "Unknown"),
                sector_growth=0.0,
                competitive_landscape="See full report",
                regulatory_environment="See full report",
                trends=[],
                outlook="neutral",
                summary=metadata.get("industry_summary", "Cached report"),
            )

            company_analysis = CompanyAnalysis(
                company=CompanyData(
                    symbol=metadata.get("symbol", ""),
                    name=metadata.get("symbol", "Unknown"),
                    sector=metadata.get("sector", ""),
                    market_cap=0.0,
                    pe_ratio=0.0,
                    current_price=0.0,
                ),
                financial_health="See full report",
                recent_news=[],
                technical_indicator="hold",
                risks=[],
                summary=metadata.get("company_summary", "Cached report"),
            )

            logger.info(f"[TRACE={trace_id}] Cached report found and loaded: report_id={report_id}")
            return ResearchReport(
                query=metadata.get("query", query),
                macro_analysis=macro_analysis,
                industry_analysis=industry_analysis,
                company_analysis=company_analysis,
                investment_thesis=metadata.get("investment_thesis", "See full report"),
                recommendation=metadata.get("recommendation", "hold"),
                target_price=float(metadata.get("target_price", 0)) if metadata.get("target_price") else None,
                time_horizon=metadata.get("time_horizon", "Medium-term"),
                full_report=report_content,
            )

        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Failed to find cached report: {e}")
            return None

    def get_cached_report_by_id(self, report_id: str) -> Optional[ResearchReport]:
        """
        Get a cached report by ID.

        Args:
            report_id: Report identifier

        Returns:
            ResearchReport if found, None otherwise
        """
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Getting cached report by ID: {report_id}")

        try:
            # Download from SeaweedFS
            logger.debug(f"[TRACE={trace_id}] Downloading report from SeaweedFS")
            report_content = self._download_cached_report(report_id)

            if not report_content:
                logger.warning(f"[TRACE={trace_id}] Report content not found in SeaweedFS")
                return None

            # Get metadata from Redis
            logger.debug(f"[TRACE={trace_id}] Getting metadata from Redis")
            summary_data = self.redis.get_report_summary(report_id)

            if not summary_data:
                logger.warning(f"[TRACE={trace_id}] Report metadata not found in Redis")
                return None

            metadata = summary_data.get("metadata", {})
            logger.info(f"[TRACE={trace_id}] Cached report loaded successfully")

            return ResearchReport(
                full_report=report_content,
                recommendation=metadata.get("recommendation", "hold"),
                target_price=float(metadata.get("target_price", 0)) if metadata.get("target_price") else None,
            )

        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Failed to get cached report: {e}")
            return None

    def _download_cached_report(self, report_id: str) -> Optional[str]:
        """Download cached report from SeaweedFS."""
        trace_id = get_trace_id()

        # First, try to get metadata from Redis to know the correct directory
        summary_data = self.redis.get_report_summary(report_id)
        if summary_data:
            metadata = summary_data.get("metadata", {})
            country = metadata.get("country", "unknown")
            symbol = metadata.get("symbol", "")

            # Try country/symbol pattern first (most specific)
            if country and symbol:
                directory = f"{self.base_directory}/{country}/{symbol}"
                logger.debug(f"[TRACE={trace_id}] Trying to download from directory: {directory}")
                content = self.seaweed.download_report(report_id, directory)
                if content:
                    logger.debug(f"[TRACE={trace_id}] Successfully downloaded from {directory}")
                    return content

            # Try country pattern
            if country:
                directory = f"{self.base_directory}/{country}"
                logger.debug(f"[TRACE={trace_id}] Trying to download from directory: {directory}")
                content = self.seaweed.download_report(report_id, directory)
                if content:
                    logger.debug(f"[TRACE={trace_id}] Successfully downloaded from {directory}")
                    return content

        # Try different country patterns
        directories = [
            f"{self.base_directory}/china",
            f"{self.base_directory}/us",
            f"{self.base_directory}/hk",
            f"{self.base_directory}/unknown",
        ]

        for directory in directories:
            logger.debug(f"[TRACE={trace_id}] Trying to download from directory: {directory}")
            content = self.seaweed.download_report(report_id, directory)
            if content:
                logger.debug(f"[TRACE={trace_id}] Successfully downloaded from {directory}")
                return content

        # Try base directory
        logger.debug(f"[TRACE={trace_id}] Trying base directory: {self.base_directory}")
        return self.seaweed.download_report(report_id, self.base_directory)

    def _generate_report_id(self, query: str, symbol: str = None) -> str:
        """
        Generate a unique report ID.

        Args:
            query: User query
            symbol: Stock symbol

        Returns:
            Unique report ID
        """
        # Use timestamp + hash for uniqueness
        timestamp = datetime.now().isoformat()
        content = f"{query}:{symbol}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _extract_summary(self, full_report: str, max_length: int = 500) -> str:
        """
        Extract a summary from the full report.

        Args:
            full_report: Full report text
            max_length: Maximum summary length

        Returns:
            Extracted summary
        """
        # Take first few paragraphs
        lines = full_report.split("\n")
        summary_lines = []
        current_length = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip headers
            if line.startswith("#"):
                continue

            summary_lines.append(line)
            current_length += len(line)

            if current_length >= max_length:
                break

        summary = " ".join(summary_lines)

        # Truncate if needed
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        return summary

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Getting cache statistics")

        redis_stats = self.redis.get_stats()
        seaweed_stats = self.seaweed.get_stats()

        stats = {
            "redis": redis_stats,
            "seaweed": seaweed_stats,
            "cache_enabled": self.enable_cache,
            "cache_ttl": self.cache_ttl,
        }
        logger.info(f"[TRACE={trace_id}] Cache stats: redis={redis_stats.get('total_cached_reports', 0)} reports, seaweed connected={seaweed_stats.get('connected', False)}")
        return stats

    def clear_cache(self) -> bool:
        """Clear all cached reports."""
        redis_success = self.redis.clear_cache()

        # Note: We don't delete from SeaweedFS to preserve data

        return redis_success

    def is_available(self) -> bool:
        """Check if cache service is available."""
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Checking cache service availability")

        redis_ok = self.redis.test_connection()
        seaweed_ok = self.seaweed.test_connection()

        if not redis_ok:
            logger.warning(f"[TRACE={trace_id}] Redis connection failed")
        if not seaweed_ok:
            logger.warning(f"[TRACE={trace_id}] SeaweedFS connection failed")

        available = redis_ok and seaweed_ok
        logger.info(f"[TRACE={trace_id}] Cache service availability: {available}")
        return available


# Global singleton instance
_report_cache_service: Optional[ReportCacheService] = None


def get_report_cache_service(
    enable_cache: bool = True,
    cache_ttl: int = None,
) -> ReportCacheService:
    """
    Get or create ReportCacheService singleton.

    Args:
        enable_cache: Enable/disable caching
        cache_ttl: Cache TTL in seconds

    Returns:
        ReportCacheService instance
    """
    global _report_cache_service

    if _report_cache_service is None:
        import os

        ttl = cache_ttl or int(os.getenv("REPORT_CACHE_TTL", "604800"))  # 7 days
        enable = enable_cache and os.getenv("ENABLE_REPORT_CACHE", "true").lower() != "false"

        _report_cache_service = ReportCacheService(
            enable_cache=enable,
            cache_ttl=ttl,
        )

    return _report_cache_service
