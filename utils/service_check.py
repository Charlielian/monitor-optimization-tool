"""
服务可用性检查工具
提供统一的服务检查功能和装饰器
"""
from typing import Any, Optional, Tuple, Callable, List
from functools import wraps
from flask import flash, redirect, url_for, render_template
import logging


def check_service_availability(
    service: Any,
    service_name: str,
    error_template: str = "error.html"
) -> Optional[Any]:
    """
    检查服务可用性，返回错误响应或None
    
    Args:
        service: 服务对象
        service_name: 服务名称（用于错误消息）
        error_template: 错误页面模板名称
    
    Returns:
        如果服务不可用，返回错误响应；否则返回 None
    
    Example:
        error_response = check_service_availability(service, "数据库服务")
        if error_response:
            return error_response
        # 继续正常处理...
    """
    if not service:
        message = f"{service_name}未连接，请检查配置或联系管理员"
        flash(message, "danger")
        return render_template(error_template, message=f"{service_name}未连接")
    return None


def check_services(*services_with_names: Tuple[Any, str]) -> Tuple[bool, str]:
    """
    检查多个服务是否可用
    
    Args:
        *services_with_names: (服务对象, 服务名称) 元组列表
    
    Returns:
        (all_available, error_message)
        - all_available: 所有服务是否都可用
        - error_message: 如果有服务不可用，返回错误消息；否则为空字符串
    
    Example:
        available, error = check_services(
            (service, "数据库服务"),
            (alarm_service, "告警服务")
        )
        if not available:
            flash(error, "danger")
            return redirect(url_for("dashboard"))
    """
    unavailable = []
    for service, name in services_with_names:
        if not service:
            unavailable.append(name)
    
    if unavailable:
        return False, f"以下服务未连接: {', '.join(unavailable)}"
    return True, ""


def require_service(
    service_getter: Callable[[], Any],
    service_name: str,
    redirect_url: str = "dashboard",
    use_template: bool = False,
    error_template: str = "error.html"
):
    """
    装饰器：检查服务是否可用
    
    Args:
        service_getter: 获取服务对象的函数（无参数）
        service_name: 服务名称（用于错误消息）
        redirect_url: 服务不可用时的重定向URL（endpoint名称）
        use_template: 是否使用错误模板而不是重定向
        error_template: 错误页面模板名称
    
    Example:
        @require_service(lambda: alarm_service, "告警服务", "dashboard")
        def alarm():
            # 此时 alarm_service 一定可用
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            service = service_getter()
            if not service:
                message = f"{service_name}未初始化，请检查配置"
                flash(message, "danger")
                if use_template:
                    return render_template(error_template, message=f"{service_name}未连接")
                return redirect(url_for(redirect_url))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_services(*service_configs):
    """
    装饰器：检查多个服务是否可用
    
    Args:
        *service_configs: 服务配置元组列表，每个元组包含：
            (service_getter, service_name)
            - service_getter: 获取服务对象的函数
            - service_name: 服务名称
    
    Keyword Args (通过最后一个字典参数传递):
        redirect_url: 服务不可用时的重定向URL（默认 "dashboard"）
        use_template: 是否使用错误模板（默认 False）
        error_template: 错误页面模板名称（默认 "error.html"）
    
    Example:
        @require_services(
            (lambda: service, "数据库服务"),
            (lambda: scenario_service, "场景服务"),
            redirect_url="dashboard"
        )
        def monitor():
            ...
    """
    # 分离服务配置和选项
    configs = []
    options = {
        "redirect_url": "dashboard",
        "use_template": False,
        "error_template": "error.html"
    }
    
    for item in service_configs:
        if isinstance(item, dict):
            options.update(item)
        else:
            configs.append(item)
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            unavailable = []
            for service_getter, service_name in configs:
                service = service_getter()
                if not service:
                    unavailable.append(service_name)
            
            if unavailable:
                message = f"以下服务未连接: {', '.join(unavailable)}"
                flash(message, "danger")
                if options["use_template"]:
                    return render_template(
                        options["error_template"],
                        message=message
                    )
                return redirect(url_for(options["redirect_url"]))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


class ServiceChecker:
    """
    服务检查器类，用于在路由中进行服务检查
    
    Example:
        checker = ServiceChecker()
        checker.add(service, "数据库服务")
        checker.add(alarm_service, "告警服务")
        
        error_response = checker.check()
        if error_response:
            return error_response
    """
    
    def __init__(
        self,
        redirect_url: str = "dashboard",
        use_template: bool = False,
        error_template: str = "error.html"
    ):
        self.services: List[Tuple[Any, str]] = []
        self.redirect_url = redirect_url
        self.use_template = use_template
        self.error_template = error_template
    
    def add(self, service: Any, service_name: str) -> 'ServiceChecker':
        """添加要检查的服务"""
        self.services.append((service, service_name))
        return self
    
    def check(self) -> Optional[Any]:
        """
        执行服务检查
        
        Returns:
            如果有服务不可用，返回错误响应；否则返回 None
        """
        unavailable = []
        for service, name in self.services:
            if not service:
                unavailable.append(name)
        
        if unavailable:
            message = f"以下服务未连接: {', '.join(unavailable)}"
            flash(message, "danger")
            if self.use_template:
                return render_template(self.error_template, message=message)
            return redirect(url_for(self.redirect_url))
        
        return None
