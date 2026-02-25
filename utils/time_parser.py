"""
时间解析工具
统一处理时间参数的解析和验证
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from constants import DATETIME_FORMAT

logger = logging.getLogger(__name__)


def parse_datetime_param(
    time_str: str,
    default: Optional[datetime] = None,
    param_name: str = "时间"
) -> datetime:
    """
    解析时间参数，支持多种格式
    
    Args:
        time_str: 时间字符串
        default: 解析失败时的默认值
        param_name: 参数名称（用于日志）
    
    Returns:
        解析后的datetime对象
    """
    if not time_str:
        return default or datetime.now()
    
    try:
        # HTML datetime-local格式: YYYY-MM-DDTHH:MM
        if 'T' in time_str:
            return datetime.strptime(time_str, DATETIME_FORMAT)
        # ISO格式
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except Exception as e:
        logger.warning(f"解析{param_name}失败: {time_str}, 错误: {e}")
        return default or datetime.now()


def parse_time_range(
    start_time_str: str,
    end_time_str: str,
    latest_ts: Optional[datetime] = None,
    default_hours: int = 6,
    max_days: int = 30
) -> Tuple[datetime, datetime]:
    """
    解析时间范围参数，带验证和边界检查
    
    Args:
        start_time_str: 开始时间字符串
        end_time_str: 结束时间字符串
        latest_ts: 最新数据时间戳
        default_hours: 默认时间范围（小时）
        max_days: 最大查询天数
    
    Returns:
        (start, end) 时间范围元组
    """
    # 确定结束时间
    end = latest_ts or datetime.now()
    if end_time_str:
        end = parse_datetime_param(end_time_str, end, "结束时间")
    
    # 确定开始时间
    start = end - timedelta(hours=default_hours)
    if start_time_str:
        start = parse_datetime_param(start_time_str, start, "开始时间")
    
    # 验证：开始时间不能晚于结束时间
    start = min(start, end)
    
    # 验证：不允许查询超过max_days天的数据
    max_start_time = end - timedelta(days=max_days)
    start = max(start, max_start_time)
    
    return start, end


def format_datetime_for_input(dt: datetime) -> str:
    """
    格式化datetime为HTML input控件格式
    
    Args:
        dt: datetime对象
    
    Returns:
        格式化后的字符串
    """
    return dt.strftime(DATETIME_FORMAT)
