"""Report cache service combining Redis and SeaweedFS."""

import uuid
import hashlib
from typing import Optional, Tuple
from datetime import datetime
import logging
from data.schemas import ResearchReport

from storage.redis_client import RedisClient, get_redis_client
from storage.seaweed_client import SeaweedClient, get_seaweed_client

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
        if not self.enable_cache:
            return str(uuid.uuid4()), False

        try:
            # Generate unique report ID
            report_id = self._generate_report_id(query, symbol)

            # Extract summary from report
            summary = self._extract_summary(report.full_report)

            # Prepare metadata
            metadata = {
                "query": query,
                "symbol": symbol or "",
                "country": country or "",
                "sector": sector or "",
                "recommendation": report.recommendation,
                "target_price": str(report.target_price) if report.target_price else "",
                "generated_at": datetime.now().isoformat(),
            }

            # Store full report in SeaweedFS
            directory = f"{self.base_directory}/{country or 'unknown'}/{symbol or 'general'}"
            upload_success = self.seaweed.upload_report(
                report_content=report.full_report,
                report_id=report_id,
                metadata=metadata,
                directory=directory,
            )

            if not upload_success:
                logger.error("Failed to upload report to SeaweedFS")
                return report_id, False

            # Cache summary and metadata in Redis
            cache_success = self.redis.cache_report_summary(
                report_id=report_id,
                summary=summary,
                metadata=metadata,
                ttl=ttl or self.cache_ttl,
            )

            if not cache_success:
                logger.error("Failed to cache report summary in Redis")
                return report_id, False

            logger.info(f"Report cached: {report_id}")
            return report_id, True

        except Exception as e:
            logger.error(f"Failed to cache report: {e}")
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
        if not self.enable_cache:
            return None

        try:
            # Find similar reports
            similar_reports = self.redis.find_similar_reports(
                query=query,
                symbol=symbol,
                limit=5,
            )

            if not similar_reports:
                return None

            # Get the best match
            best_match = similar_reports[0]

            if best_match.get("similarity", 0) < similarity_threshold:
                return None

            # Download full report from SeaweedFS
            report_content = self._download_cached_report(best_match["report_id"])

            if not report_content:
                return None

            # Reconstruct ResearchReport
            metadata = best_match.get("metadata", {})

            return ResearchReport(
                full_report=report_content,
                recommendation=metadata.get("recommendation", "hold"),
                target_price=float(metadata.get("target_price", 0)) if metadata.get("target_price") else None,
            )

        except Exception as e:
            logger.error(f"Failed to find cached report: {e}")
            return None

    def get_cached_report_by_id(self, report_id: str) -> Optional[ResearchReport]:
        """
        Get a cached report by ID.

        Args:
            report_id: Report identifier

        Returns:
            ResearchReport if found, None otherwise
        """
        try:
            # Download from SeaweedFS
            report_content = self._download_cached_report(report_id)

            if not report_content:
                return None

            # Get metadata from Redis
            summary_data = self.redis.get_report_summary(report_id)

            if not summary_data:
                return None

            metadata = summary_data.get("metadata", {})

            return ResearchReport(
                full_report=report_content,
                recommendation=metadata.get("recommendation", "hold"),
                target_price=float(metadata.get("target_price", 0)) if metadata.get("target_price") else None,
            )

        except Exception as e:
            logger.error(f"Failed to get cached report: {e}")
            return None

    def _download_cached_report(self, report_id: str) -> Optional[str]:
        """Download cached report from SeaweedFS."""
        # Try different directory patterns
        directories = [
            f"{self.base_directory}/china",
            f"{self.base_directory}/us",
            f"{self.base_directory}/hk",
            f"{self.base_directory}/unknown",
        ]

        for directory in directories:
            content = self.seaweed.download_report(report_id, directory)
            if content:
                return content

        # Try base directory
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
        redis_stats = self.redis.get_stats()
        seaweed_stats = self.seaweed.get_stats()

        return {
            "redis": redis_stats,
            "seaweed": seaweed_stats,
            "cache_enabled": self.enable_cache,
            "cache_ttl": self.cache_ttl,
        }

    def clear_cache(self) -> bool:
        """Clear all cached reports."""
        redis_success = self.redis.clear_cache()

        # Note: We don't delete from SeaweedFS to preserve data

        return redis_success

    def is_available(self) -> bool:
        """Check if cache service is available."""
        redis_ok = self.redis.test_connection()
        seaweed_ok = self.seaweed.test_connection()

        if not redis_ok:
            logger.warning("Redis connection failed")
        if not seaweed_ok:
            logger.warning("SeaweedFS connection failed")

        return redis_ok and seaweed_ok


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
