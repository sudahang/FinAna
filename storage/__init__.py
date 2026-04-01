"""Storage module for report persistence and caching.

This module provides:
- Redis client for caching report summaries
- SeaweedFS client for storing full reports
- Report cache service with similarity matching
"""

from storage.redis_client import RedisClient, get_redis_client
from storage.seaweed_client import SeaweedClient, get_seaweed_client
from storage.report_cache import ReportCacheService, get_report_cache_service

__all__ = [
    "RedisClient",
    "get_redis_client",
    "SeaweedClient",
    "get_seaweed_client",
    "ReportCacheService",
    "get_report_cache_service",
]
