"""
用户认证模块
提供登录、登出、权限验证等功能
"""
from functools import wraps
from flask import session, redirect, url_for, request, flash
from werkzeug.security import check_password_hash, generate_password_hash
import logging
from datetime import datetime, time as dt_time
from collections import deque


class AuthManager:
    """认证管理器"""

    def __init__(self, users_config: dict, admin_access_config: dict = None):
        """
        初始化认证管理器

        Args:
            users_config: 用户配置字典，格式：
                {
                    "admin": {
                        "password_hash": "...",
                        "role": "admin",
                        "name": "管理员",
                        "allowed_ips": ["192.168.1.1", "10.0.0.0/24"]  # 可选，IP白名单
                    }
                }
            admin_access_config: 管理员访问控制配置，格式：
                {
                    "enable_time_restriction": True,
                    "allowed_time_start": "08:00",
                    "allowed_time_end": "18:00",
                    "enable_access_log": True,
                    "enable_ip_whitelist": True,  # 是否启用IP白名单
                    "global_admin_ips": ["192.168.1.0/24"]  # 全局管理员IP白名单
                }
        """
        self.users = users_config
        self.admin_access_config = admin_access_config or {}
        self.logger = logging.getLogger(__name__)
        # 管理员登录IP记录：{username: ip_address}
        self.admin_login_ips = {}
        # 用户最后登录时间记录：{username: datetime}
        self.last_login_times = {}
        # 管理员访问日志（使用deque自动限制大小，避免内存泄漏）
        self.admin_access_logs = deque(maxlen=1000)
    
    def verify_user(self, username: str, password: str, ip_address: str = None) -> tuple[bool, str]:
        """
        验证用户名和密码，同时检查管理员IP白名单
        
        Args:
            username: 用户名
            password: 密码（明文）
            ip_address: 登录IP地址（可选，用于管理员IP白名单验证）
            
        Returns:
            (验证成功返回 True, 错误信息)
        """
        if username not in self.users:
            self.logger.warning(f"登录失败：用户不存在 - {username}")
            return False, "用户名或密码错误"
        
        user = self.users[username]
        password_hash = user.get("password_hash", "")
        
        # 验证密码
        if not check_password_hash(password_hash, password):
            self.logger.warning(f"登录失败：密码错误 - {username}")
            return False, "用户名或密码错误"
        
        # 检查管理员IP白名单
        if user.get("role") == "admin" and ip_address:
            ip_allowed, ip_reason = self._check_admin_ip_whitelist(username, ip_address)
            if not ip_allowed:
                self.logger.warning(f"登录失败：IP不在白名单 - {username} - {ip_address}")
                return False, ip_reason
        
        self.logger.info(f"用户登录成功：{username}")
        return True, ""
    
    def _check_admin_ip_whitelist(self, username: str, ip_address: str) -> tuple[bool, str]:
        """
        检查管理员IP是否在白名单中
        
        Args:
            username: 用户名
            ip_address: IP地址
            
        Returns:
            (是否允许, 拒绝原因)
        """
        # 检查是否启用IP白名单
        if not self.admin_access_config.get("enable_ip_whitelist", False):
            return True, ""
        
        user = self.users.get(username, {})
        
        # 获取用户级别的IP白名单
        user_allowed_ips = user.get("allowed_ips", [])
        
        # 获取全局管理员IP白名单
        global_admin_ips = self.admin_access_config.get("global_admin_ips", [])
        
        # 合并白名单
        all_allowed_ips = list(set(user_allowed_ips + global_admin_ips))
        
        # 如果没有配置任何白名单，默认允许
        if not all_allowed_ips:
            return True, ""
        
        # 检查IP是否在白名单中
        if self._ip_in_whitelist(ip_address, all_allowed_ips):
            return True, ""
        
        return False, f"您的IP地址 {ip_address} 不在允许登录的范围内"
    
    def _ip_in_whitelist(self, ip_address: str, whitelist: list) -> bool:
        """
        检查IP是否在白名单中（支持CIDR格式）
        
        Args:
            ip_address: 要检查的IP地址
            whitelist: IP白名单列表（支持单个IP或CIDR格式如 192.168.1.0/24）
            
        Returns:
            是否在白名单中
        """
        import ipaddress
        
        try:
            check_ip = ipaddress.ip_address(ip_address)
            
            for allowed in whitelist:
                try:
                    if '/' in allowed:
                        # CIDR格式
                        network = ipaddress.ip_network(allowed, strict=False)
                        if check_ip in network:
                            return True
                    else:
                        # 单个IP
                        if check_ip == ipaddress.ip_address(allowed):
                            return True
                except ValueError:
                    # 无效的IP格式，跳过
                    continue
            
            return False
        except ValueError:
            # 无效的IP地址
            self.logger.error(f"无效的IP地址: {ip_address}")
            return False
    
    def get_user_info(self, username: str) -> dict:
        """
        获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            用户信息字典
        """
        if username not in self.users:
            return {}
        
        user = self.users[username]
        return {
            "username": username,
            "role": user.get("role", "user"),
            "name": user.get("name", username),
            "allowed_pages": user.get("allowed_pages", []),  # 允许访问的页面列表
        }
    
    def check_page_permission(self, username: str, page_key: str) -> bool:
        """
        检查用户是否有权限访问指定页面
        
        Args:
            username: 用户名
            page_key: 页面标识（如 'dashboard', 'monitor' 等）
            
        Returns:
            是否有权限访问
        """
        if username not in self.users:
            return False
        
        user = self.users[username]
        
        # 管理员可以访问所有页面
        if user.get("role") == "admin":
            return True
        
        # 获取用户允许访问的页面列表
        allowed_pages = user.get("allowed_pages")
        
        # 如果没有配置allowed_pages（None），默认允许访问所有页面（向后兼容）
        # 如果配置了空列表（[]），则不允许访问任何页面
        if allowed_pages is None:
            return True
        
        # 检查页面是否在允许列表中
        return page_key in allowed_pages
    
    def check_admin_ip(self, username: str, current_ip: str) -> bool:
        """
        检查管理员IP是否匹配（用于单IP登录限制）
        
        Args:
            username: 用户名
            current_ip: 当前请求的IP地址
            
        Returns:
            如果是管理员且IP不匹配返回False，否则返回True
        """
        user = self.users.get(username, {})
        if user.get("role") != "admin":
            return True  # 非管理员不限制
        
        # 检查是否已有登录IP
        if username in self.admin_login_ips:
            stored_ip = self.admin_login_ips[username]
            if stored_ip != current_ip:
                self.logger.warning(f"管理员 {username} 尝试从新IP登录: {current_ip}，旧IP: {stored_ip}")
                return False
        
        return True
    
    def check_admin_access(self, username: str, ip_address: str) -> tuple[bool, str]:
        """
        检查管理员访问权限（时间限制等）
        
        Args:
            username: 用户名
            ip_address: IP地址
            
        Returns:
            (是否允许访问, 拒绝原因)
        """
        user = self.users.get(username, {})
        if user.get("role") != "admin":
            return True, ""  # 非管理员不限制
        
        # 检查访问时间限制
        if self.admin_access_config.get("enable_time_restriction", False):
            if not self._check_time_restriction():
                start_time = self.admin_access_config.get("allowed_time_start", "00:00")
                end_time = self.admin_access_config.get("allowed_time_end", "23:59")
                reason = f"当前时间不在允许访问时间段内（{start_time} - {end_time}）"
                self.logger.warning(f"管理员 {username} 访问被拒绝: {reason}")
                return False, reason
        
        return True, ""
    
    def _check_time_restriction(self) -> bool:
        """
        检查当前时间是否在允许访问的时间段内
        
        Returns:
            是否在允许的时间段内
        """
        try:
            now = datetime.now().time()
            start_str = self.admin_access_config.get("allowed_time_start", "00:00")
            end_str = self.admin_access_config.get("allowed_time_end", "23:59")
            
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            
            # 处理跨天的情况
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                return now >= start_time or now <= end_time
        except Exception as e:
            self.logger.error(f"检查时间限制失败: {e}")
            return True  # 出错时默认允许访问
    
    def log_admin_access(self, username: str, ip_address: str, action: str, success: bool, reason: str = ""):
        """
        记录管理员访问日志
        
        Args:
            username: 用户名
            ip_address: IP地址
            action: 操作类型
            success: 是否成功
            reason: 失败原因
        """
        if not self.admin_access_config.get("enable_access_log", True):
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username,
            "ip_address": ip_address,
            "action": action,
            "success": success,
            "reason": reason
        }

        # deque会自动维护maxlen限制，无需手动切片
        self.admin_access_logs.append(log_entry)

        # 记录到日志文件
        if success:
            self.logger.info(f"管理员访问: {username} - {action} - IP: {ip_address}")
        else:
            self.logger.warning(f"管理员访问被拒绝: {username} - {action} - IP: {ip_address} - 原因: {reason}")
    
    def get_admin_access_logs(self, limit: int = 100) -> list:
        """
        获取管理员访问日志
        
        Args:
            limit: 返回的日志条数
            
        Returns:
            日志列表
        """
        # deque不支持负数切片，需要转换为list
        logs = list(self.admin_access_logs)
        return logs[-limit:] if logs else []
    
    def record_admin_login(self, username: str, ip_address: str):
        """
        记录管理员登录IP
        
        Args:
            username: 用户名
            ip_address: IP地址
        """
        user = self.users.get(username, {})
        if user.get("role") == "admin":
            self.admin_login_ips[username] = ip_address
            self.logger.info(f"管理员 {username} 登录IP已记录: {ip_address}")
            # 记录访问日志
            self.log_admin_access(username, ip_address, "login", True)
    
    def clear_admin_login(self, username: str):
        """
        清除管理员登录IP记录

        Args:
            username: 用户名
        """
        if username in self.admin_login_ips:
            del self.admin_login_ips[username]
            self.logger.info(f"管理员 {username} 登录IP已清除")

    def record_login_time(self, username: str):
        """
        记录用户登录时间

        Args:
            username: 用户名
        """
        self.last_login_times[username] = datetime.now()
        self.logger.info(f"用户 {username} 登录时间已记录")

    def get_last_login_time(self, username: str):
        """
        获取用户最后登录时间

        Args:
            username: 用户名

        Returns:
            最后登录时间（datetime对象），如果没有记录则返回None
        """
        return self.last_login_times.get(username)

    @staticmethod
    def hash_password(password: str) -> str:
        """
        生成密码哈希（用于初始化用户）
        
        Args:
            password: 明文密码
            
        Returns:
            密码哈希
        """
        return generate_password_hash(password)


def login_required(f):
    """
    登录验证装饰器
    用于保护需要登录才能访问的路由
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("请先登录", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """
    API登录验证装饰器
    用于保护需要登录才能访问的API端点
    返回JSON格式的错误信息而不是重定向
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            from flask import jsonify
            return jsonify({"success": False, "error": "未登录，请先登录", "code": 401}), 401
        return f(*args, **kwargs)
    return decorated_function


def page_permission_required(page_key: str):
    """
    页面权限验证装饰器
    用于保护需要特定权限才能访问的页面
    
    Args:
        page_key: 页面标识（如 'dashboard', 'monitor' 等）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("logged_in"):
                flash("请先登录", "warning")
                return redirect(url_for("login", next=request.url))
            
            # 从 Flask app 获取 auth_manager
            from flask import current_app
            auth_manager = current_app.config.get('auth_manager')
            
            if auth_manager:
                username = session.get("username")
                if not auth_manager.check_page_permission(username, page_key):
                    flash(f"您没有权限访问该页面", "danger")
                    # 跳转到第一个有权限的页面
                    user_info = auth_manager.get_user_info(username)
                    allowed_pages = user_info.get("allowed_pages", [])
                    if allowed_pages:
                        # 页面优先级顺序
                        page_priority = ["dashboard", "monitor", "cell", "scenarios", "grid", "alarm"]
                        for page in page_priority:
                            if page in allowed_pages:
                                return redirect(url_for(page))
                    # 如果没有任何允许的页面，跳转到登录页
                    return redirect(url_for("login"))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    管理员权限验证装饰器
    用于保护需要管理员权限的路由
    同时检查管理员IP是否匹配（单IP登录限制）和访问控制（IP白名单、时间限制等）
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("请先登录", "warning")
            return redirect(url_for("login", next=request.url))
        
        if session.get("role") != "admin":
            flash("需要管理员权限", "danger")
            return redirect(url_for("dashboard"))
        
        # 获取当前IP
        username = session.get("username")
        login_ip = session.get("login_ip")
        current_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in current_ip:
            current_ip = current_ip.split(',')[0].strip()
        
        # 检查管理员IP是否匹配（单IP登录限制）
        if login_ip and login_ip != current_ip:
            logging.warning(f"管理员 {username} IP不匹配，已踢出: 登录IP={login_ip}, 当前IP={current_ip}")
            session.clear()
            flash("检测到异地登录，已退出当前会话", "warning")
            return redirect(url_for("login"))
        
        # 检查管理员访问控制（IP白名单、时间限制等）
        # 从 Flask app 获取 auth_manager
        from flask import current_app
        auth_manager = current_app.config.get('auth_manager')
        if auth_manager:
            allowed, reason = auth_manager.check_admin_access(username, current_ip)
            if not allowed:
                # 记录访问日志
                auth_manager.log_admin_access(username, current_ip, request.endpoint or "unknown", False, reason)
                session.clear()
                flash(f"访问被拒绝: {reason}", "danger")
                return redirect(url_for("login"))
            
            # 记录访问日志
            auth_manager.log_admin_access(username, current_ip, request.endpoint or "unknown", True)
        
        return f(*args, **kwargs)
    return decorated_function


# 默认用户配置（用于初始化）
DEFAULT_USERS = {
    "admin": {
        "password_hash": generate_password_hash("admin123"),  # 默认密码：admin123
        "role": "admin",
        "name": "管理员"
    },
    "user": {
        "password_hash": generate_password_hash("user123"),  # 默认密码：user123
        "role": "user",
        "name": "普通用户"
    }
}

# 默认管理员访问控制配置
DEFAULT_ADMIN_ACCESS_CONFIG = {
    "enable_time_restriction": False,  # 是否启用时间限制
    "allowed_time_start": "08:00",  # 允许访问开始时间
    "allowed_time_end": "18:00",  # 允许访问结束时间
    "enable_access_log": True,  # 是否启用访问日志
    "enable_ip_whitelist": False,  # 是否启用管理员IP白名单
    "global_admin_ips": [],  # 全局管理员IP白名单（支持CIDR格式如 192.168.1.0/24）
}


def create_page_decorator(page_key: str, auth_enabled: bool = True):
    """
    创建页面装饰器（组合登录验证和页面权限验证）
    
    Args:
        page_key: 页面标识
        auth_enabled: 是否启用认证
        
    Returns:
        装饰器函数
    """
    if auth_enabled:
        def decorator(f):
            # 先应用登录验证，再应用页面权限验证
            f = login_required(f)
            f = page_permission_required(page_key)(f)
            return f
        return decorator
    else:
        # 如果未启用认证，返回空装饰器
        return lambda f: f
