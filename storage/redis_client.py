"""Redis client for caching report summaries."""

import json
import hashlib
from typing import Optional
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError
import logging

logger = logging.getLogger(__name__)

# Import trace ID utilities from logging_config
from logging_config import get_trace_id


class RedisClient:
    """
    Redis client for caching report summaries and metadata.

    Features:
    - Cache report summaries with TTL
    - Index reports by symbol, country, sector
    - Similarity search for cached reports
    - Automatic expiration
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str = None,
        default_ttl: int = 3600 * 24 * 7,  # 7 days default
        max_cached_reports: int = 1000,
    ):
        """
        Initialize Redis client.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            default_ttl: Default TTL for cached items in seconds
            max_cached_reports: Maximum number of cached reports
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.max_cached_reports = max_cached_reports

        # Connection pool
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            max_connections=50
        )

        self.client = redis.Redis(connection_pool=self.pool)

    def test_connection(self) -> bool:
        """Test Redis connection."""
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Redis connection test started")
        try:
            self.client.ping()
            logger.info(f"[TRACE={trace_id}] Redis connection test successful")
            return True
        except RedisError as e:
            logger.error(f"[TRACE={trace_id}] Redis connection failed: {e}")
            return False

    def cache_report_summary(
        self,
        report_id: str,
        summary: str,
        metadata: dict,
        ttl: int = None
    ) -> bool:
        """
        Cache a report summary.

        Args:
            report_id: Unique report identifier (SeaweedFS fid)
            summary: Report summary text
            metadata: Report metadata (symbol, country, sector, etc.)
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        trace_id = get_trace_id()
        ttl = ttl or self.default_ttl

        logger.info(f"[TRACE={trace_id}] Caching report summary: report_id={report_id}, ttl={ttl}s")

        try:
            # Store summary
            key = f"report:summary:{report_id}"
            data = {
                "summary": summary,
                "metadata": json.dumps(metadata),
                "created_at": datetime.now().isoformat(),
            }
            self.client.hset(key, mapping=data)
            self.client.expire(key, ttl)
            logger.debug(f"[TRACE={trace_id}] Report summary stored: key={key}")

            # Index by symbol
            symbol = metadata.get("symbol", "").upper()
            if symbol:
                index_key = f"report:index:symbol:{symbol}"
                self.client.zadd(index_key, {report_id: datetime.now().timestamp()})
                self.client.expire(index_key, ttl)
                # Keep only recent reports
                self.client.zremrangebyrank(index_key, 0, -self.max_cached_reports)
                logger.debug(f"[TRACE={trace_id}] Indexed by symbol: {symbol}")

            # Index by country
            country = metadata.get("country", "")
            if country:
                country_key = f"report:index:country:{country}"
                self.client.zadd(country_key, {report_id: datetime.now().timestamp()})
                self.client.expire(country_key, ttl)
                logger.debug(f"[TRACE={trace_id}] Indexed by country: {country}")

            # Index by sector
            sector = metadata.get("sector", "")
            if sector:
                sector_key = f"report:index:sector:{sector}"
                self.client.zadd(sector_key, {report_id: datetime.now().timestamp()})
                self.client.expire(sector_key, ttl)
                logger.debug(f"[TRACE={trace_id}] Indexed by sector: {sector}")

            # Store query hash for similarity search
            query = metadata.get("query", "")
            if query:
                query_hash = self._hash_query(query)
                query_key = f"report:query:{query_hash}"
                self.client.hset(query_key, mapping={
                    "report_id": report_id,
                    "query": query,
                    "summary": summary,
                    "created_at": datetime.now().isoformat(),
                })
                self.client.expire(query_key, ttl)
                logger.debug(f"[TRACE={trace_id}] Query hash stored: {query_hash[:8]}...")

            logger.info(f"[TRACE={trace_id}] Report summary cached successfully: report_id={report_id}")
            return True

        except RedisError as e:
            logger.error(f"[TRACE={trace_id}] Failed to cache report summary: {e}")
            return False

    def get_report_summary(self, report_id: str) -> Optional[dict]:
        """
        Get cached report summary.

        Args:
            report_id: Report identifier

        Returns:
            Report summary data or None if not found
        """
        trace_id = get_trace_id()
        try:
            key = f"report:summary:{report_id}"
            data = self.client.hgetall(key)

            if not data:
                logger.debug(f"[TRACE={trace_id}] Report summary not found: key={key}")
                return None

            logger.debug(f"[TRACE={trace_id}] Report summary retrieved: key={key}")
            return {
                "summary": data.get("summary", ""),
                "metadata": json.loads(data.get("metadata", "{}")),
                "created_at": data.get("created_at", ""),
            }

        except RedisError as e:
            logger.error(f"[TRACE={trace_id}] Failed to get report summary: {e}")
            return None

    def find_similar_reports(
        self,
        query: str,
        symbol: str = None,
        limit: int = 5
    ) -> list[dict]:
        """
        Find similar cached reports based on query and symbol.

        Args:
            query: User query to find similar reports for
            symbol: Optional stock symbol to filter
            limit: Maximum number of results

        Returns:
            List of similar report summaries
        """
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Finding similar reports: query='{query[:50]}...', symbol={symbol}, limit={limit}")

        results = []

        try:
            # Generate query hash for exact match
            query_hash = self._hash_query(query)
            query_key = f"report:query:{query_hash}"

            # Check for exact query match
            if self.client.exists(query_key):
                data = self.client.hgetall(query_key)
                if data:
                    logger.info(f"[TRACE={trace_id}] Exact query match found: query_hash={query_hash[:8]}...")
                    # Get full metadata from report:summary key
                    report_id = data.get("report_id", "")
                    summary_data = self.get_report_summary(report_id)
                    metadata = summary_data.get("metadata", {}) if summary_data else {}

                    results.append({
                        "report_id": report_id,
                        "query": data.get("query", ""),
                        "summary": data.get("summary", ""),
                        "created_at": data.get("created_at", ""),
                        "match_type": "exact",
                        "similarity": 1.0,
                        "metadata": metadata,
                    })
                    if limit == 1:
                        return results

            # Find by symbol
            if symbol:
                symbol = symbol.upper()
                index_key = f"report:index:symbol:{symbol}"
                logger.debug(f"[TRACE={trace_id}] Checking symbol index: {index_key}")
                index_exists = self.client.exists(index_key)
                logger.debug(f"[TRACE={trace_id}] Symbol index exists: {index_exists}")
                report_ids = self.client.zrevrange(index_key, 0, limit - 1)

                if report_ids:
                    logger.debug(f"[TRACE={trace_id}] Found {len(report_ids)} reports by symbol: {symbol}, report_ids: {report_ids}")

                for report_id in report_ids:
                    summary_data = self.get_report_summary(report_id)
                    if summary_data:
                        results.append({
                            "report_id": report_id,
                            "query": summary_data["metadata"].get("query", ""),
                            "summary": summary_data["summary"],
                            "created_at": summary_data["created_at"],
                            "match_type": "symbol",
                            "similarity": 0.8,
                            "metadata": summary_data["metadata"],
                        })

            # Find by keywords (simple keyword matching)
            keywords = self._extract_keywords(query)
            if keywords:
                logger.debug(f"[TRACE={trace_id}] Searching by keywords: {keywords}")
                keyword_results = self._search_by_keywords(keywords, limit)
                for result in keyword_results:
                    # Avoid duplicates
                    if not any(r["report_id"] == result["report_id"] for r in results):
                        results.append(result)

            # Sort by similarity and created_at
            results.sort(
                key=lambda x: (x["similarity"], x.get("created_at", "")),
                reverse=True
            )

            logger.info(f"[TRACE={trace_id}] Found {len(results)} similar reports")
            return results[:limit]

        except RedisError as e:
            logger.error(f"[TRACE={trace_id}] Failed to find similar reports: {e}")
            return []

    def _hash_query(self, query: str) -> str:
        """Generate hash for a query."""
        # Normalize query
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract keywords from query for search."""
        # Remove common words
        stop_words = {"的", "是", "在", "和", "了", "与", "及", "等", "分析", "股票", "公司"}
        keywords = []
        for word in query.lower().split():
            if word not in stop_words and len(word) > 1:
                keywords.append(word)

        # Also extract Chinese keywords
        for char in query:
            if '\u4e00' <= char <= '\u9fff' and char not in stop_words:
                keywords.append(char)

        return list(set(keywords))[:5]  # Limit to 5 keywords

    def _search_by_keywords(self, keywords: list[str], limit: int) -> list[dict]:
        """Search reports by keywords."""
        results = []

        # Scan all report summaries
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match="report:summary:*", count=100)

            for key in keys:
                data = self.client.hgetall(key)
                summary = data.get("summary", "").lower()
                query = data.get("query", "").lower()

                # Count keyword matches
                matches = sum(1 for kw in keywords if kw in summary or kw in query)

                if matches > 0:
                    report_id = key.replace("report:summary:", "")
                    results.append({
                        "report_id": report_id,
                        "query": query,
                        "summary": summary,
                        "created_at": data.get("created_at", ""),
                        "match_type": "keyword",
                        "similarity": matches / len(keywords),
                    })

                    if len(results) >= limit * 2:  # Get more for sorting
                        break

            if cursor == 0 or len(results) >= limit * 2:
                break

        return results

    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            # Count indexed reports
            symbol_keys = self.client.keys("report:index:symbol:*")
            total_reports = 0

            for key in symbol_keys:
                count = self.client.zcard(key)
                total_reports += count

            # Get memory info
            info = self.client.info("memory")

            return {
                "total_cached_reports": total_reports,
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except RedisError as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def clear_cache(self) -> bool:
        """Clear all cached reports."""
        try:
            # Delete all report keys
            keys_to_delete = []

            for key in self.client.scan_iter(match="report:*"):
                keys_to_delete.append(key)

            if keys_to_delete:
                self.client.delete(*keys_to_delete)

            return True
        except RedisError as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    def close(self):
        """Close Redis connection."""
        self.pool.disconnect()


_redis_client: Optional[RedisClient] = None


def get_redis_client(
    host: str = None,
    port: int = None,
    password: str = None
) -> RedisClient:
    """
    Get or create Redis client singleton.

    Args:
        host: Override Redis host
        port: Override Redis port
        password: Override Redis password

    Returns:
        RedisClient instance
    """
    global _redis_client

    if _redis_client is None:
        import os

        host = host or os.getenv("REDIS_HOST", "localhost")
        port = port or int(os.getenv("REDIS_PORT", "6379"))
        password = password or os.getenv("REDIS_PASSWORD")

        _redis_client = RedisClient(
            host=host,
            port=port,
            password=password,
        )

    return _redis_client
