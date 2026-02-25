"""
并行查询工具
使用线程池并行执行多个数据库查询，提升性能
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
from typing import List, Callable, Any, Dict


class ParallelQueryExecutor:
    """并行查询执行器"""
    
    def __init__(self, max_workers: int = 5):
        """
        初始化并行查询执行器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def execute_parallel(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        并行执行多个查询任务
        
        Args:
            tasks: 任务列表，每个任务是一个字典:
                {
                    'name': '任务名称',
                    'func': 可调用函数,
                    'args': 位置参数元组,
                    'kwargs': 关键字参数字典
                }
        
        Returns:
            结果字典，key为任务名称，value为执行结果
        """
        start_time = time.time()
        results = {}
        futures = {}
        
        # 提交所有任务
        for task in tasks:
            name = task['name']
            func = task['func']
            args = task.get('args', ())
            kwargs = task.get('kwargs', {})
            
            future = self.executor.submit(func, *args, **kwargs)
            futures[future] = name
        
        # 收集结果
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results[name] = result
                logging.debug(f"  ✓ 任务 '{name}' 完成")
            except Exception as e:
                logging.error(f"  ✗ 任务 '{name}' 失败: {e}")
                results[name] = None
        
        elapsed = (time.time() - start_time) * 1000
        logging.info(f"  并行查询完成，总耗时: {elapsed:.2f}ms")
        
        return results
    
    def execute_parallel_simple(self, funcs: List[Callable]) -> List[Any]:
        """
        简化版并行执行（不需要命名）
        
        Args:
            funcs: 可调用函数列表
        
        Returns:
            结果列表，顺序与输入函数列表一致
        """
        futures = [self.executor.submit(func) for func in funcs]
        results = []
        
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logging.error(f"并行查询失败: {e}")
                results.append(None)
        
        return results
    
    def shutdown(self):
        """关闭线程池"""
        self.executor.shutdown(wait=True)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()


# 全局执行器实例（可选）
_global_executor = None


def get_global_executor(max_workers: int = 5) -> ParallelQueryExecutor:
    """
    获取全局并行查询执行器
    
    Args:
        max_workers: 最大工作线程数
    
    Returns:
        ParallelQueryExecutor 实例
    """
    global _global_executor
    if _global_executor is None:
        _global_executor = ParallelQueryExecutor(max_workers=max_workers)
    return _global_executor


def parallel_query(tasks: List[Dict[str, Any]], max_workers: int = 5) -> Dict[str, Any]:
    """
    便捷函数：并行执行查询任务
    
    Args:
        tasks: 任务列表
        max_workers: 最大工作线程数
    
    Returns:
        结果字典
    """
    with ParallelQueryExecutor(max_workers=max_workers) as executor:
        return executor.execute_parallel(tasks)


# 使用示例
if __name__ == "__main__":
    import random
    
    def mock_query(name: str, delay: float):
        """模拟数据库查询"""
        time.sleep(delay)
        return f"{name} 查询结果"
    
    # 示例1：使用命名任务
    tasks = [
        {
            'name': 'traffic',
            'func': mock_query,
            'args': ('流量数据', 0.5)
        },
        {
            'name': 'connect',
            'func': mock_query,
            'args': ('接通率数据', 0.3)
        },
        {
            'name': 'rrc',
            'func': mock_query,
            'args': ('RRC数据', 0.4)
        },
        {
            'name': 'top4',
            'func': mock_query,
            'args': ('4G Top', 0.6)
        },
        {
            'name': 'top5',
            'func': mock_query,
            'args': ('5G Top', 0.5)
        }
    ]
    
    print("开始并行查询...")
    start = time.time()
    results = parallel_query(tasks)
    elapsed = time.time() - start
    
    print(f"\n查询结果:")
    for name, result in results.items():
        print(f"  {name}: {result}")
    
    print(f"\n总耗时: {elapsed:.2f}秒")
    print(f"如果串行执行需要: {sum([0.5, 0.3, 0.4, 0.6, 0.5]):.2f}秒")
    print(f"性能提升: {(sum([0.5, 0.3, 0.4, 0.6, 0.5]) / elapsed):.2f}倍")
