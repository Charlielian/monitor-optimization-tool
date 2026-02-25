"""
统一配置管理
整合所有配置项，支持环境变量和多层级配置
"""
import json
import os
from typing import Any, Dict, Optional
from constants import (
    TIME_RANGE_6H,
    NETWORK_4G,
    NETWORK_5G,
    CACHE_TTL_1MIN,
    CACHE_TTL_5MIN,
)


class ConfigManager:
    """
    统一配置管理器
    配置优先级：环境变量 > 项目配置文件 > 上级配置文件 > 默认值
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        