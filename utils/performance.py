"""
性能监控工具
用于记录和分析请求处理时间
"""
import time
import logging
from functools import wraps
from typing import Callable, Any


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def log_time(self, operation: str):
        """装饰器：记录函数执行时间"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
                    
                    # 根据耗时设置日志级别
                    if elapsed > 1000:  # 超过1秒
                        self.logger.warning(f"⚠️ {operation} 耗时: {elapsed:.2f}ms (较慢)")
                    elif elapsed > 500:  # 超过500ms
                        self.logger.info(f"⏱️ {operation} 耗时: {elapsed:.2f}ms")
                    else:
                        self.logger.debug(f"✓ {operation} 耗时: {elapsed:.2f}ms")
                    
                    return result
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    self.logger.error(f"❌ {operation} 失败 (耗时: {elapsed:.2f}ms): {str(e)}")
                    raise
            return wrapper
        return decorator
    
    def measure(self, operation: str):
        """上下文管理器：测量代码块执行时间"""
        return TimingContext(operation, self.logger)


class TimingContext:
    """计时上下文管理器"""
    
    def __init__(self, operation: str, logger):
        self.operation = operation
        self.logger = logger
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.time() - self.start_time) * 1000
        
        if exc_type is not None:
            self.logger.error(f"❌ {self.operation} 失败 (耗时: {elapsed:.2f}ms)")
        elif elapsed > 1000:
            self.logger.warning(f"⚠️ {self.operation} 耗时: {elapsed:.2f}ms (较慢)")
        elif elapsed > 500:
            self.logger.info(f"⏱️ {self.operation} 耗时: {elapsed:.2f}ms")
        else:
            self.logger.debug(f"✓ {self.operation} 耗时: {elapsed:.2f}ms")


# 全局性能监控器实例
perf_monitor = PerformanceMonitor()
