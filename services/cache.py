import time
import logging
from typing import Any, Callable, Dict, Tuple, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class SimpleTTLCache:
    """
    改进的TTL缓存，支持缓存统计和线程安全
    """

    def __init__(self, ttl_seconds: int = 300, name: str = "cache") -> None:
        self.ttl = ttl_seconds
        self.name = name
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = Lock()
        
        # 缓存统计
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
        }

    def get(self, key: str, loader: Callable[[], Any]) -> Any:
        """
        获取缓存值，如果不存在或过期则调用loader加载
        
        Args:
            key: 缓存键
            loader: 加载函数
        
        Returns:
            缓存值
        """
        now = time.time()
        
        with self._lock:
            if key in self._store:
                ts, val = self._store[key]
                if now - ts < self.ttl:
                    self._stats["hits"] += 1
                    return val
            
            self._stats["misses"] += 1
        
        # 在锁外执行loader，避免阻塞其他请求
        try:
            val = loader()
        except Exception as e:
            logger.error(f"缓存加载失败 [{self.name}:{key}]: {e}")
            raise
        
        with self._lock:
            self._store[key] = (now, val)
            self._stats["sets"] += 1
        
        return val

    def set(self, key: str, value: Any) -> None:
        """
        直接设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            self._store[key] = (time.time(), value)
            self._stats["sets"] += 1

    def invalidate(self, key: str) -> None:
        """
        使指定缓存失效
        
        Args:
            key: 缓存键
        """
        with self._lock:
            if self._store.pop(key, None) is not None:
                self._stats["invalidations"] += 1

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self._stats["invalidations"] += count

    def cleanup_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        now = time.time()
        expired_keys = []
        
        with self._lock:
            for key, (ts, _) in self._store.items():
                if now - ts >= self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._store.pop(key, None)
            
            self._stats["invalidations"] += len(expired_keys)
        
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "name": self.name,
                "ttl_seconds": self.ttl,
                "size": len(self._store),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "invalidations": self._stats["invalidations"],
                "hit_rate": f"{hit_rate:.2f}%",
            }

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "invalidations": 0,
            }


# 全局缓存实例
cache_5m = SimpleTTLCache(300, name="5min")
cache_1m = SimpleTTLCache(60, name="1min")
cache_30m = SimpleTTLCache(1800, name="30min")  # 30分钟缓存


def get_all_cache_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有缓存的统计信息"""
    return {
        "cache_5m": cache_5m.get_stats(),
        "cache_1m": cache_1m.get_stats(),
        "cache_30m": cache_30m.get_stats(),
    }


__all__ = ["SimpleTTLCache", "cache_5m", "cache_1m", "cache_30m", "get_all_cache_stats"]

