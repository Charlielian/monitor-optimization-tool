"""
分页工具模块
提供通用的分页功能
"""
from typing import List, Any, Dict, TypeVar
from math import ceil
from constants import DEFAULT_PAGE_SIZE

T = TypeVar('T')


def paginate(
    data: List[T],
    page: int,
    page_size: int = DEFAULT_PAGE_SIZE
) -> Dict[str, Any]:
    """
    通用分页函数
    
    Args:
        data: 数据列表
        page: 当前页码 (从1开始)
        page_size: 每页大小（默认使用 DEFAULT_PAGE_SIZE）
    
    Returns:
        {
            "data": [...],      # 当前页数据
            "page": int,        # 当前页码（已校正到有效范围）
            "pages": int,       # 总页数
            "total": int,       # 总记录数
            "page_size": int,   # 每页大小
            "has_prev": bool,   # 是否有上一页
            "has_next": bool    # 是否有下一页
        }
    
    Examples:
        >>> paginate([1, 2, 3, 4, 5], page=1, page_size=2)
        {'data': [1, 2], 'page': 1, 'pages': 3, 'total': 5, 'page_size': 2, 'has_prev': False, 'has_next': True}
        
        >>> paginate([], page=1, page_size=10)
        {'data': [], 'page': 1, 'pages': 0, 'total': 0, 'page_size': 10, 'has_prev': False, 'has_next': False}
    """
    # 处理边界条件
    if not data:
        return {
            "data": [],
            "page": 1,
            "pages": 0,
            "total": 0,
            "page_size": page_size,
            "has_prev": False,
            "has_next": False
        }
    
    # 确保 page_size 至少为 1
    page_size = max(1, page_size)
    
    total = len(data)
    pages = ceil(total / page_size)
    
    # 校正页码到有效范围
    page = max(1, min(page, pages))
    
    # 计算切片索引
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    return {
        "data": data[start_idx:end_idx],
        "page": page,
        "pages": pages,
        "total": total,
        "page_size": page_size,
        "has_prev": page > 1,
        "has_next": page < pages
    }


def get_page_range(
    current_page: int,
    total_pages: int,
    window_size: int = 5
) -> List[int]:
    """
    获取分页导航的页码范围
    
    Args:
        current_page: 当前页码
        total_pages: 总页数
        window_size: 显示的页码数量（默认5）
    
    Returns:
        页码列表，如 [1, 2, 3, 4, 5] 或 [3, 4, 5, 6, 7]
    
    Examples:
        >>> get_page_range(1, 10, 5)
        [1, 2, 3, 4, 5]
        
        >>> get_page_range(5, 10, 5)
        [3, 4, 5, 6, 7]
        
        >>> get_page_range(9, 10, 5)
        [6, 7, 8, 9, 10]
    """
    if total_pages <= window_size:
        return list(range(1, total_pages + 1))
    
    half_window = window_size // 2
    
    if current_page <= half_window:
        # 靠近开头
        return list(range(1, window_size + 1))
    elif current_page >= total_pages - half_window:
        # 靠近结尾
        return list(range(total_pages - window_size + 1, total_pages + 1))
    else:
        # 在中间
        return list(range(current_page - half_window, current_page + half_window + 1))
