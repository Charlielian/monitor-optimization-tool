"""
数据格式化工具
统一处理数据转换和格式化逻辑
"""
from typing import Tuple
from constants import GB_TO_TB


def format_traffic_with_unit(traffic_gb: float) -> Tuple[float, str]:
    """
    根据流量大小自适应返回值和单位
    
    Args:
        traffic_gb: 流量值（GB）
    
    Returns:
        (值, 单位) 元组
        如果流量 >= 1024 GB，返回 TB 单位，否则返回 GB 单位
    """
    if traffic_gb >= GB_TO_TB:
        return (round(traffic_gb / GB_TO_TB, 2), "TB")
    return (round(traffic_gb, 2), "GB")


def bytes_to_gb(bytes_value: float) -> float:
    """
    字节转GB
    
    Args:
        bytes_value: 字节数
    
    Returns:
        GB值
    """
    from constants import BYTES_TO_MB
    return bytes_value / BYTES_TO_MB


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    格式化百分比值
    
    Args:
        value: 数值
        decimals: 小数位数
    
    Returns:
        格式化后的字符串
    """
    return f"{float(value or 0):.{decimals}f}"
