"""
Cache Monitoring and Optimization Service

This service provides comprehensive monitoring and optimization features for Redis caching:
- Performance analysis and recommendations
- Cache efficiency tracking across all cache services
- Memory usage optimization
- Automated cache health monitoring
- Cache pattern analysis and optimization suggestions
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from backend.core.redis import RedisClient
from backend.services.document_cache import get_document_cache
from backend.services.search_cache import get_search_cache
from backend.services.conversation_cache import get_conversation_cache

logger = logging.getLogger(__name__)


class CacheMonitor:
    """Comprehensive cache monitoring and optimization service"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        
        # Cache service instances
        self.document_cache = None
        self.search_cache = None  
        self.conversation_cache = None
        
        # Monitoring configuration
        self.monitoring_patterns = [
            "doc:*",          # Document cache patterns
            "search:*",       # Search cache patterns
            "conversation:*", # Conversation cache patterns
            "chunks:*",       # Document chunks cache
            "user:*"          # User-specific caches
        ]
        
        # Performance thresholds
        self.performance_thresholds = {
            "min_hit_rate": 0.7,        # 70% minimum hit rate
            "max_memory_per_key": 1024 * 1024,  # 1MB max per key
            "max_keys_without_ttl": 0.1,         # 10% max keys without TTL
            "max_memory_utilization": 0.8        # 80% max memory usage
        }
    
    def _init_cache_services(self):
        """Initialize cache service instances if not already done"""
        if self.document_cache is None:
            self.document_cache = get_document_cache()
        if self.search_cache is None:
            self.search_cache = get_search_cache()
        if self.conversation_cache is None:
            self.conversation_cache = get_conversation_cache()
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all cache services and Redis"""
        try:
            self._init_cache_services()
            
            # Get Redis server stats
            redis_stats = await self.redis.get_detailed_stats()
            
            # Get individual cache service stats
            cache_stats = {}
            
            try:
                cache_stats["document_cache"] = await self.document_cache.get_cache_stats()
            except Exception as e:
                cache_stats["document_cache"] = {"error": str(e)}
            
            try:
                cache_stats["search_cache"] = await self.search_cache.get_cache_stats()
            except Exception as e:
                cache_stats["search_cache"] = {"error": str(e)}
            
            try:
                cache_stats["conversation_cache"] = await self.conversation_cache.get_cache_stats()
            except Exception as e:
                cache_stats["conversation_cache"] = {"error": str(e)}
            
            # Calculate aggregated metrics
            total_cache_entries = 0
            for service_stats in cache_stats.values():
                if isinstance(service_stats, dict) and "error" not in service_stats:
                    for key, value in service_stats.items():
                        if isinstance(value, int) and "total" in key:
                            total_cache_entries += value
            
            # Combine all stats
            comprehensive_stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "redis_server": redis_stats,
                "cache_services": cache_stats,
                "aggregated": {
                    "total_cache_entries": total_cache_entries,
                    "services_healthy": len([s for s in cache_stats.values() if "error" not in s]),
                    "services_total": len(cache_stats)
                }
            }
            
            return comprehensive_stats
            
        except Exception as e:
            logger.error(f"Error getting comprehensive cache stats: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def analyze_performance(self) -> Dict[str, Any]:
        """Analyze cache performance and provide optimization recommendations"""
        try:
            # Get Redis efficiency analysis
            efficiency_analysis = await self.redis.analyze_cache_efficiency(self.monitoring_patterns)
            
            # Get overall Redis stats
            redis_stats = await self.redis.get_detailed_stats()
            
            performance_analysis = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_performance": {},
                "pattern_analysis": efficiency_analysis.get("patterns", {}),
                "recommendations": efficiency_analysis.get("recommendations", []),
                "health_score": 100,  # Start with perfect score
                "issues": []
            }
            
            if "error" in redis_stats:
                performance_analysis["overall_performance"] = {"error": redis_stats["error"]}
                performance_analysis["health_score"] = 0
                return performance_analysis
            
            # Analyze overall performance metrics
            performance = redis_stats.get("performance", {})
            memory = redis_stats.get("memory", {})
            
            hit_rate = performance.get("hit_rate", 0)
            memory_utilization = memory.get("utilization")
            
            performance_analysis["overall_performance"] = {
                "hit_rate": hit_rate,
                "miss_rate": performance.get("miss_rate", 0),
                "ops_per_second": performance.get("instantaneous_ops_per_sec", 0),
                "memory_utilization": memory_utilization,
                "total_keys": efficiency_analysis.get("total_keys", 0),
                "total_memory_bytes": efficiency_analysis.get("total_memory", 0)
            }
            
            # Check performance thresholds and calculate health score
            issues = []
            score_deductions = 0
            
            # Hit rate check
            if hit_rate < self.performance_thresholds["min_hit_rate"]:
                issues.append(f"Low hit rate: {hit_rate:.2%} (threshold: {self.performance_thresholds['min_hit_rate']:.2%})")
                score_deductions += 25
            
            # Memory utilization check
            if memory_utilization and memory_utilization > self.performance_thresholds["max_memory_utilization"]:
                issues.append(f"High memory utilization: {memory_utilization:.2%} (threshold: {self.performance_thresholds['max_memory_utilization']:.2%})")
                score_deductions += 20
            
            # TTL compliance check
            total_keys = efficiency_analysis.get("total_keys", 0)
            if total_keys > 0:
                keys_without_ttl = 0
                for pattern_stats in efficiency_analysis.get("patterns", {}).values():
                    keys_without_ttl += pattern_stats.get("keys_without_ttl", 0)
                
                ttl_compliance = 1 - (keys_without_ttl / total_keys)
                if ttl_compliance < (1 - self.performance_thresholds["max_keys_without_ttl"]):
                    issues.append(f"Many keys without TTL: {keys_without_ttl}/{total_keys} ({keys_without_ttl/total_keys:.2%})")
                    score_deductions += 15
            
            # Large key detection
            for pattern, stats in efficiency_analysis.get("patterns", {}).items():
                avg_memory = stats.get("avg_memory_per_key", 0)
                if avg_memory > self.performance_thresholds["max_memory_per_key"]:
                    issues.append(f"Large keys detected in pattern '{pattern}': avg {avg_memory/1024:.1f}KB per key")
                    score_deductions += 10
            
            performance_analysis["health_score"] = max(0, 100 - score_deductions)
            performance_analysis["issues"] = issues
            
            # Generate additional recommendations based on analysis
            additional_recommendations = []
            
            if hit_rate < 0.5:
                additional_recommendations.append("Consider reviewing cache TTL settings - very low hit rate suggests frequent cache misses")
            
            if memory_utilization and memory_utilization > 0.9:
                additional_recommendations.append("Memory utilization is critically high - consider increasing Redis memory or implementing cache eviction policies")
            
            if performance.get("evicted_keys", 0) > 0:
                additional_recommendations.append("Keys are being evicted - consider increasing memory or optimizing cache usage patterns")
            
            performance_analysis["recommendations"].extend(additional_recommendations)
            
            return performance_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing cache performance: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def optimize_cache_settings(self) -> Dict[str, Any]:
        """Provide optimization suggestions based on current usage patterns"""
        try:
            analysis = await self.analyze_performance()
            
            optimization_suggestions = {
                "timestamp": datetime.utcnow().isoformat(),
                "current_health_score": analysis.get("health_score", 0),
                "optimizations": [],
                "priority": "low"
            }
            
            performance = analysis.get("overall_performance", {})
            hit_rate = performance.get("hit_rate", 0)
            
            # TTL optimization suggestions
            if hit_rate < 0.6:
                optimization_suggestions["optimizations"].append({
                    "category": "TTL Configuration",
                    "suggestion": "Increase TTL for frequently accessed data",
                    "impact": "High",
                    "details": "Low hit rate suggests data is expiring too quickly. Consider increasing TTL for document metadata and search results."
                })
                optimization_suggestions["priority"] = "high"
            
            # Memory optimization
            if performance.get("memory_utilization", 0) > 0.7:
                optimization_suggestions["optimizations"].append({
                    "category": "Memory Management",
                    "suggestion": "Implement cache compression or reduce cache size",
                    "impact": "Medium",
                    "details": "High memory usage detected. Consider compressing large values or reducing cache retention periods."
                })
                if optimization_suggestions["priority"] == "low":
                    optimization_suggestions["priority"] = "medium"
            
            # Pattern-specific optimizations
            pattern_analysis = analysis.get("pattern_analysis", {})
            for pattern, stats in pattern_analysis.items():
                if stats.get("avg_memory_per_key", 0) > 512 * 1024:  # > 512KB
                    optimization_suggestions["optimizations"].append({
                        "category": "Data Structure",
                        "suggestion": f"Optimize large values in pattern '{pattern}'",
                        "impact": "Medium",
                        "details": f"Average key size is {stats['avg_memory_per_key']/1024:.1f}KB. Consider data compression or restructuring."
                    })
            
            # Performance optimization
            ops_per_sec = performance.get("ops_per_second", 0)
            if ops_per_sec > 1000:
                optimization_suggestions["optimizations"].append({
                    "category": "Performance Tuning",
                    "suggestion": "Consider Redis clustering or connection pooling",
                    "impact": "High",
                    "details": f"High operation rate ({ops_per_sec} ops/sec) detected. Consider scaling Redis infrastructure."
                })
                optimization_suggestions["priority"] = "high"
            
            # If no specific issues found, provide general recommendations
            if not optimization_suggestions["optimizations"]:
                optimization_suggestions["optimizations"].append({
                    "category": "Maintenance",
                    "suggestion": "Cache performance is optimal",
                    "impact": "Low",
                    "details": "Continue monitoring cache metrics and review TTL settings periodically."
                })
            
            return optimization_suggestions
            
        except Exception as e:
            logger.error(f"Error generating optimization suggestions: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check on all cache components"""
        try:
            health_status = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "healthy",
                "components": {},
                "summary": {}
            }
            
            # Check Redis server health
            redis_health = await self.redis.health_check()
            health_status["components"]["redis_server"] = redis_health
            
            # Check cache services
            self._init_cache_services()
            
            # Test each cache service
            cache_services = [
                ("document_cache", self.document_cache),
                ("search_cache", self.search_cache),
                ("conversation_cache", self.conversation_cache)
            ]
            
            healthy_services = 0
            total_services = len(cache_services)
            
            for service_name, cache_service in cache_services:
                try:
                    # Test basic functionality
                    test_key = f"health_check:{service_name}:{int(datetime.utcnow().timestamp())}"
                    test_value = {"test": True, "timestamp": datetime.utcnow().isoformat()}
                    
                    # Test set operation
                    set_success = await cache_service.redis.set_json(test_key, test_value, ttl=60)
                    
                    # Test get operation
                    retrieved_value = await cache_service.redis.get_json(test_key)
                    
                    # Clean up test key
                    await cache_service.redis.delete(test_key)
                    
                    if set_success and retrieved_value:
                        health_status["components"][service_name] = {
                            "status": "healthy",
                            "response_time_ms": None,  # Could add timing if needed
                            "test_operations": "passed"
                        }
                        healthy_services += 1
                    else:
                        health_status["components"][service_name] = {
                            "status": "degraded",
                            "error": "Cache operations failed",
                            "test_operations": "failed"
                        }
                        
                except Exception as e:
                    health_status["components"][service_name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "test_operations": "error"
                    }
            
            # Determine overall status
            if redis_health.get("status") != "healthy":
                health_status["overall_status"] = "unhealthy"
            elif healthy_services < total_services:
                health_status["overall_status"] = "degraded"
            
            # Add summary
            health_status["summary"] = {
                "healthy_services": healthy_services,
                "total_services": total_services,
                "redis_connected": redis_health.get("connected", False),
                "cache_availability": healthy_services / total_services if total_services > 0 else 0
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error running cache health check: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "error",
                "error": str(e)
            }


# Global cache monitor instance
cache_monitor: Optional[CacheMonitor] = None


def get_cache_monitor() -> CacheMonitor:
    """Get the global cache monitor instance"""
    global cache_monitor
    if cache_monitor is None:
        from backend.core.redis import get_redis_client
        redis_client = get_redis_client()
        cache_monitor = CacheMonitor(redis_client)
    return cache_monitor 