"""
输入验证工具
统一处理用户输入的验证逻辑
"""
import re
import html
from typing import List, Tuple
from constants import (
    MAX_CELL_QUERY_LIMIT,
    VALID_GRANULARITIES,
    VALID_NETWORKS,
    VALID_TIME_RANGES,
    GRANULARITY_15MIN
)


def validate_and_parse_cgis(cgi_input: str, max_limit: int = MAX_CELL_QUERY_LIMIT) -> Tuple[List[str], str]:
    """
    验证并解析CGI输入
    
    Args:
        cgi_input: CGI输入字符串（逗号分隔）
        max_limit: 最大数量限制
    
    Returns:
        (cgi列表, 警告消息) 元组
    """
    if not cgi_input:
        return [], ""
    
    # 解析CGI列表
    cgi_list = [c.strip() for c in cgi_input.split(',') if c.strip()]
    
    # 检查数量限制
    warning = ""
    if len(cgi_list) > max_limit:
        warning = f"最多只能查询{max_limit}个小区，当前输入了{len(cgi_list)}个，已自动截取前{max_limit}个"
        cgi_list = cgi_list[:max_limit]
    
    return cgi_list, warning


def validate_granularity(granularity: str) -> str:
    """
    验证时间粒度参数
    
    Args:
        granularity: 时间粒度
    
    Returns:
        验证后的时间粒度（无效时返回默认值）
    """
    if granularity in VALID_GRANULARITIES:
        return granularity
    return GRANULARITY_15MIN


def validate_network_type(network: str) -> str:
    """
    验证网络类型参数
    
    Args:
        network: 网络类型
    
    Returns:
        验证后的网络类型（无效时返回4G）
    """
    network = network.upper()
    if network in VALID_NETWORKS:
        return network
    return "4G"


def validate_time_range(range_key: str) -> str:
    """
    验证时间范围参数
    
    Args:
        range_key: 时间范围键
    
    Returns:
        验证后的时间范围（无效时返回6h）
    """
    if range_key in VALID_TIME_RANGES:
        return range_key
    return "6h"


def validate_threshold(threshold: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """
    验证阈值参数

    Args:
        threshold: 阈值
        min_val: 最小值
        max_val: 最大值

    Returns:
        验证后的阈值（超出范围时返回边界值）
    """
    return max(min_val, min(threshold, max_val))


def sanitize_html(text: str) -> str:
    """
    清理HTML内容，防止XSS攻击

    Args:
        text: 待清理的文本

    Returns:
        清理后的文本
    """
    if not text:
        return ""
    return html.escape(str(text))


def validate_username(username: str) -> str:
    """
    验证用户名，只允许字母、数字、下划线和连字符

    Args:
        username: 用户名

    Returns:
        验证后的用户名（移除非法字符）
    """
    if not username:
        return ""
    return re.sub(r'[^\w\-]', '', username)


def sanitize_search_query(query: str) -> str:
    """
    清理搜索查询，移除危险字符

    Args:
        query: 搜索查询

    Returns:
        清理后的查询
    """
    if not query:
        return ""
    # 移除SQL注入和XSS相关的危险字符
    dangerous_chars = ['<', '>', '"', "'", ';', '\\', '`']
    result = str(query)
    for char in dangerous_chars:
        result = result.replace(char, '')
    return result.strip()


def validate_string_length(text: str, max_length: int = 255) -> str:
    """
    验证字符串长度

    Args:
        text: 待验证的文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if not text:
        return ""
    return str(text)[:max_length]
