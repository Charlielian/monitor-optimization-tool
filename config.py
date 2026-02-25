import json
import os
from typing import Any, Dict
from constants import TIME_RANGE_6H, NETWORK_4G, NETWORK_5G


class Config:
    """
    轻量级配置加载器
    
    配置文件查找优先级：
    1. 环境变量 MONITOR_CONFIG 指定的路径
    2. 当前项目目录下的 config.json
    3. 上一级目录下的 config.json（兼容旧项目）
    """

    def __init__(self) -> None:
        project_root = os.path.dirname(os.path.abspath(__file__))
        legacy_root = os.path.dirname(project_root)

        # 配置文件查找
        candidates = []
        env_path = os.environ.get("MONITOR_CONFIG")
        if env_path:
            candidates.append(env_path)
        candidates.append(os.path.join(project_root, "config.json"))
        candidates.append(os.path.join(legacy_root, "config.json"))

        config_json = None
        for path in candidates:
            if path and os.path.exists(path):
                config_json = path
                break

        data: Dict[str, Any] = {}
        if config_json:
            try:
                with open(config_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                print(f"警告: 读取 {config_json} 失败，使用默认配置。原因: {exc}")

        # PostgreSQL配置
        pg_defaults = {
            "host": "localhost",
            "port": 5432,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres",
            "pool_min": 1,
            "pool_max": 10,
            "connect_timeout": 10,
            "application_name": "monitoring_app",
        }
        self.pgsql_config: Dict[str, Any] = {**pg_defaults, **data.get("pgsql_config", {})}

        # MySQL配置
        mysql_defaults = {
            "host": "192.168.31.175",
            "port": 3306,
            "database": "optimization_toolbox",
            "user": "root",
            "password": "103001"
        }
        self.mysql_config: Dict[str, Any] = {**mysql_defaults, **data.get("mysql_config", {})}

        # 日志配置
        logs_dir = os.path.join(project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        self.log_config = {
            "level": str(data.get("log_level", "INFO")).upper(),
            "file_path": data.get("log_file", os.path.join(logs_dir, "monitoring_app.log")),
        }

        # 应用安全配置
        # 优先级：config.json > 环境变量 > 默认开发密钥
        self.secret_key: str = str(
            data.get("secret_key")
            or os.environ.get("FLASK_SECRET_KEY")
            or "dev-monitoring-app"
        )

        # 安全配置
        security_config_data = data.get("security_config", {})
        self.security_config = {
            "session_cookie_secure": security_config_data.get("session_cookie_secure", False),  # 默认False便于开发
            "session_cookie_httponly": security_config_data.get("session_cookie_httponly", True),
            "session_cookie_samesite": security_config_data.get("session_cookie_samesite", "Lax"),
        }

        # UI默认配置
        ui_config_data = data.get("ui_config", {})
        self.ui_config = {
            "default_range": ui_config_data.get("default_range", TIME_RANGE_6H),
            "default_networks": ui_config_data.get("default_networks", [NETWORK_4G, NETWORK_5G]),
            "auto_refresh_interval": ui_config_data.get("auto_refresh_interval", 300),
            "max_cell_query": ui_config_data.get("max_cell_query", 200),
        }

        # 认证配置
        auth_config_data = data.get("auth_config", {})
        self.auth_config = {
            "enable_auth": auth_config_data.get("enable_auth", True),
            "session_lifetime_hours": auth_config_data.get("session_lifetime_hours", 24),
            "session_timeout_hours": auth_config_data.get("session_timeout_hours", 1),
            "users": auth_config_data.get("users", {}),
            "admin_access": auth_config_data.get("admin_access", {}),
        }

        # SSL配置
        ssl_config_data = data.get("ssl_config", {})
        self.ssl_config = {
            "enabled": ssl_config_data.get("enabled", False),
            "cert_file": ssl_config_data.get("cert_file", ""),
            "key_file": ssl_config_data.get("key_file", ""),
            "ciphers": ssl_config_data.get("ciphers", "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA256"),
            "protocol": ssl_config_data.get("protocol", "TLSv1.2+"),
        }


__all__ = ["Config"]


