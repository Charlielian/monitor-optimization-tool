import json
import logging
import logging.config
import time
from datetime import datetime, timedelta
from typing import List

# 尝试导入 yaml 模块，如果失败则设置为 None
try:
    import yaml
except ImportError:
    yaml = None

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
    session,
    jsonify,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

from config import Config
from db.pg import PostgresClient
from db.mysql import MySQLClient
from services.metrics_service import MetricsService
from services.scenario_service import ScenarioService
from services.engineering_params_service import EngineeringParamsService
from services.scheduler_service import SchedulerService
from services.alarm_service import AlarmService, NokiaAlarmService
from services.grid_service import GridService
from services.cache import cache_1m, cache_5m
from auth import AuthManager, login_required, admin_required, page_permission_required, create_page_decorator, DEFAULT_USERS
from utils.validators import sanitize_html, validate_username, sanitize_search_query, validate_string_length
import csv
import io
import argparse
import os
from openpyxl import Workbook


class RequestIDFilter(logging.Filter):
    """将请求ID添加到日志记录中"""
    def filter(self, record):
        record.request_id = getattr(request, 'request_id', 'N/A') if request else 'N/A'
        return True


def save_config(cfg: Config, users_config: dict):
    """
    保存配置到 config.json 文件
    
    Args:
        cfg: Config 对象
        users_config: 用户配置字典
    """
    # 查找配置文件路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(project_root, "config.json")
    
    # 读取现有配置
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        logging.error(f"读取配置文件失败: {e}")
        config_data = {}
    
    # 更新用户配置
    if "auth_config" not in config_data:
        config_data["auth_config"] = {}
    config_data["auth_config"]["users"] = users_config
    
    # 保存到文件
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        logging.info(f"配置已保存到: {config_path}")
    except Exception as e:
        logging.error(f"保存配置文件失败: {e}")
        raise


def create_app() -> Flask:
    import time
    app_start_time = time.time()
    
    cfg = Config()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 确保日志目录存在
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # 加载日志配置
    logging_config_path = os.path.join(base_dir, "logging.yaml")
    if yaml and os.path.exists(logging_config_path):
        with open(logging_config_path, 'r', encoding='utf-8') as f:
            log_config = yaml.safe_load(f)
            # 更新日志文件路径
            if 'handlers' in log_config and 'file' in log_config['handlers']:
                log_config['handlers']['file']['filename'] = cfg.log_config.get("file_path", os.path.join(logs_dir, "monitoring_app.log"))
            # 更新日志级别
            if 'root' in log_config:
                log_config['root']['level'] = cfg.log_config.get("level", "INFO").upper()
            # 移除filter引用（将在配置后手动添加）
            if 'handlers' in log_config:
                for handler_config in log_config['handlers'].values():
                    if 'filters' in handler_config:
                        del handler_config['filters']
            if 'filters' in log_config:
                del log_config['filters']
            logging.config.dictConfig(log_config)
    else:
        # 回退到基本配置
        logging.basicConfig(
            level=getattr(logging, cfg.log_config["level"].upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=cfg.log_config.get("file_path"),
            encoding="utf-8",
        )

    # 为所有日志处理器添加请求ID过滤器
    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIDFilter())

    logging.info("=" * 60)
    logging.info("🚀 Flask 应用启动中...")
    logging.info("=" * 60)

    # PostgreSQL 客户端初始化（允许失败）
    db_start = time.time()
    pg_client = None
    try:
        pg_client = PostgresClient(cfg.pgsql_config)
        if pg_client.test_connection():
            logging.info(f"✓ PostgreSQL 客户端初始化完成 ({(time.time() - db_start) * 1000:.2f}ms)")
        else:
            logging.warning(f"⚠️ PostgreSQL 连接测试失败，应用将以降级模式运行")
            pg_client = None
    except Exception as e:
        logging.warning(f"⚠️ PostgreSQL 客户端初始化失败: {e}，应用将以降级模式运行")
        pg_client = None

    # 初始化认证管理器
    auth_start = time.time()
    auth_enabled = cfg.auth_config.get("enable_auth", True)
    users_config = cfg.auth_config.get("users", DEFAULT_USERS)
    admin_access_config = cfg.auth_config.get("admin_access", cfg.auth_config.get("admin_access_control", {}))
    auth_manager = AuthManager(users_config, admin_access_config) if auth_enabled else None
    logging.info(f"✓ 认证管理器初始化完成 ({(time.time() - auth_start) * 1000:.2f}ms)")

    # 初始化 MySQL 客户端和工参服务
    mysql_start = time.time()
    mysql_client = None
    engineering_params_service = None
    alarm_service = None
    alarm_service_zte = None
    alarm_service_nokia = None
    grid_service = None
    try:
        mysql_client = MySQLClient(cfg.mysql_config)
        engineering_params_service = EngineeringParamsService(mysql_client)
        
        # 创建中兴设备告警服务实例
        alarm_service_zte = AlarmService(
            mysql_client,
            current_table='cur_alarm',
            history_table='his_alarm',
            vendor_name='中兴'
        )
        
        # 创建诺基亚设备告警服务实例（使用专门的NokiaAlarmService类）
        alarm_service_nokia = NokiaAlarmService(
            mysql_client,
            current_table='cur_alarm_nokia',
            history_table='his_alarm_nokia',
            vendor_name='诺基亚'
        )
        
        # 保持向后兼容，alarm_service 指向中兴服务实例
        alarm_service = alarm_service_zte
        
        # 初始化网格服务（MySQL必需，PostgreSQL可选）
        grid_service = GridService(mysql_client, pg_client)
        if pg_client:
            logging.info(f"✓ 工参服务、告警服务（中兴/诺基亚）和网格服务初始化成功 ({(time.time() - mysql_start) * 1000:.2f}ms)")
        else:
            logging.info(f"✓ 工参服务、告警服务（中兴/诺基亚）和网格服务初始化成功（PostgreSQL未连接，功能受限） ({(time.time() - mysql_start) * 1000:.2f}ms)")
    except Exception as e:
        logging.warning(f"⚠️ 工参服务和告警服务初始化失败: {e}")

    # 创建业务服务对象（允许数据库连接失败）
    service_start = time.time()
    service = None
    scenario_service = None
    try:
        if pg_client:
            service = MetricsService(pg_client, engineering_params_service)
            scenario_service = ScenarioService(pg_client, mysql_client)
            logging.info(f"✓ 业务服务初始化完成 ({(time.time() - service_start) * 1000:.2f}ms)")
        else:
            logging.warning(f"⚠️ PostgreSQL 未连接，业务服务未初始化")
    except Exception as e:
        logging.warning(f"⚠️ 业务服务初始化失败: {e}")
    
    # 初始化计划任务调度服务
    scheduler_service = None
    try:
        scheduler_start = time.time()
        scheduler_service = SchedulerService()
        logging.info(f"✓ 计划任务调度服务初始化完成 ({(time.time() - scheduler_start) * 1000:.2f}ms)")
    except Exception as e:
        logging.warning(f"⚠️ 计划任务调度服务初始化失败: {e}")
    
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )
    # 使用配置/环境变量提供的 secret_key，而不是硬编码，便于上线时替换
    app.secret_key = cfg.secret_key  # for flash messages

    # 启用CSRF保护
    csrf = CSRFProtect(app)
    
    # 豁免某些API接口的CSRF保护（用于AJAX调用）
    csrf.exempt("routes.main.api_log_performance")
    csrf.exempt("routes.main.api_add_cell")

    # 速率限制功能暂时禁用，因为缺少 flask_limiter 模块

    # 配置 Session
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=cfg.auth_config.get("session_lifetime_hours", 24))

    # 配置模板自动重载（开发环境）
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True

    # 配置安全的Session Cookie（从配置文件读取）
    app.config['SESSION_COOKIE_SECURE'] = cfg.security_config.get("session_cookie_secure", False)
    app.config['SESSION_COOKIE_HTTPONLY'] = cfg.security_config.get("session_cookie_httponly", True)
    app.config['SESSION_COOKIE_SAMESITE'] = cfg.security_config.get("session_cookie_samesite", "Lax")
    
    # 将数据库客户端和服务存储到 app.config 中，方便后续访问和重连
    app.config['pg_client'] = pg_client
    app.config['mysql_client'] = mysql_client
    app.config['service'] = service
    app.config['scenario_service'] = scenario_service
    app.config['alarm_service'] = alarm_service
    app.config['alarm_service_zte'] = alarm_service_zte
    app.config['alarm_service_nokia'] = alarm_service_nokia
    app.config['scheduler_service'] = scheduler_service
    
    # 注册模板过滤器
    @app.template_filter('schedule_desc')
    def get_schedule_desc(job):
        """获取调度描述"""
        schedule_type = job.get('schedule_type', '')
        config = job.get('schedule_config', {})
        
        if schedule_type == 'cron':
            parts = []
            if config.get('day_of_week'):
                parts.append(f"每周{config['day_of_week']}")
            if config.get('day'):
                parts.append(f"每月{config['day']}日")
            if config.get('hour'):
                parts.append(f"{config['hour']}时")
            if config.get('minute'):
                parts.append(f"{config['minute']}分")
            return ' '.join(parts) if parts else 'Cron'
        elif schedule_type == 'interval':
            parts = []
            if config.get('days'): parts.append(f"{config['days']}天")
            if config.get('hours'): parts.append(f"{config['hours']}小时")
            if config.get('minutes'): parts.append(f"{config['minutes']}分钟")
            if config.get('seconds'): parts.append(f"{config['seconds']}秒")
            return '每' + ''.join(parts) if parts else '间隔'
        elif schedule_type == 'date':
            return f"一次性: {config.get('run_date', '')}"
        return schedule_type
    app.config['grid_service'] = grid_service
    app.config['engineering_params_service'] = engineering_params_service
    app.config['pgsql_config'] = cfg.pgsql_config
    app.config['mysql_config'] = cfg.mysql_config
    app.config['auth_manager'] = auth_manager  # 添加认证管理器到配置
    app.config['auth_enabled'] = auth_enabled  # 添加认证启用状态到配置
    app.config['app_config'] = cfg  # 添加应用配置到config
    app.config['app_start_time'] = app_start_time  # 添加应用启动时间到配置

    # ==================== 注册API蓝图 ====================
    from api_v1 import api_v1
    app.register_blueprint(api_v1)
    
    # ==================== 注册路由蓝图 ====================
    # Register all route blueprints using the centralized registration function
    from routes import register_blueprints
    register_blueprints(app)

    # ==================== 性能监控中间件 ====================

    @app.before_request
    def before_request():
        """请求开始前记录时间和请求信息"""
        request.start_time = time.time()
        request.request_id = f"{int(time.time() * 1000)}-{id(request)}"
        
        # 会话超时检查（仅对已登录用户）
        if auth_enabled and session.get("logged_in"):
            # 检查会话是否超时
            last_activity = session.get("last_activity")
            if last_activity:
                # 计算距离上次活动的时间（秒）
                inactive_seconds = time.time() - last_activity
                # 获取超时时间（小时转秒）
                timeout_seconds = cfg.auth_config.get("session_timeout_hours", 24) * 3600
                
                if inactive_seconds > timeout_seconds:
                    # 会话超时，清除session
                    username = session.get("username", "未知用户")
                    logging.info(f"会话超时: {username}, 不活动时间: {inactive_seconds/3600:.2f}小时")
                    session.clear()
                    flash("会话已超时，请重新登录", "warning")
                    return redirect(url_for("login", next=request.url))
            
            # 更新最后活动时间
            session["last_activity"] = time.time()

        # 记录请求信息
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # 记录详细的请求信息
        user_agent = request.headers.get('User-Agent', 'Unknown')[:100]  # 限制长度
        referer = request.headers.get('Referer', '-')
        
        # 构建查询参数字符串（限制长度）
        query_string = request.query_string.decode('utf-8')[:200] if request.query_string else ''
        query_info = f"?{query_string}" if query_string else ""
        
        # 记录请求开始
        logging.info(
            f"📥 {request.method} {request.path}{query_info} | "
            f"IP: {client_ip} | User: {session.get('username', 'anonymous')}"
        )
        
        # 对于POST请求，记录表单大小（不记录内容，保护隐私）
        if request.method == 'POST' and request.content_length:
            logging.debug(f"  └─ POST数据大小: {request.content_length} bytes")
    
    @app.after_request
    def after_request(response):
        """请求结束后记录耗时和响应信息"""
        if hasattr(request, 'start_time'):
            from constants import PERF_THRESHOLD_ERROR, PERF_THRESHOLD_WARNING, PERF_THRESHOLD_INFO
            elapsed = (time.time() - request.start_time) * 1000

            # 获取响应大小
            response_size = response.content_length or len(response.get_data()) if response.get_data else 0
            size_kb = response_size / 1024 if response_size else 0

            # 根据耗时设置日志级别和emoji
            if elapsed > PERF_THRESHOLD_ERROR:
                level = "ERROR"
                emoji = "🔴"
            elif elapsed > PERF_THRESHOLD_WARNING:
                level = "WARNING"
                emoji = "🟡"
            elif elapsed > PERF_THRESHOLD_INFO:
                level = "INFO"
                emoji = "🟢"
            else:
                level = "DEBUG"
                emoji = "⚡"

            # 构建日志消息
            log_msg = (
                f"{emoji} {request.method} {request.path} | "
                f"状态: {response.status_code} | "
                f"耗时: {elapsed:.2f}ms | "
                f"大小: {size_kb:.2f}KB"
            )
            
            # 对于慢请求，添加额外的警告信息
            if elapsed > PERF_THRESHOLD_WARNING:
                log_msg += f" | ⚠️ 慢请求警告"

            # 根据级别记录日志
            if level == "ERROR":
                logging.error(log_msg)
            elif level == "WARNING":
                logging.warning(log_msg)
            elif level == "INFO":
                logging.info(log_msg)
            else:
                logging.debug(log_msg)
            
            # 对于非常慢的请求，记录详细的性能分析
            if elapsed > PERF_THRESHOLD_ERROR:
                logging.error(
                    f"  └─ 性能分析: 请求ID={request.request_id} | "
                    f"路径={request.path} | "
                    f"方法={request.method} | "
                    f"用户={session.get('username', 'anonymous')} | "
                    f"IP={request.headers.get('X-Forwarded-For', request.remote_addr)}"
                )

        return response

    # 全局错误处理器
    @app.errorhandler(404)
    def not_found_error(error):
        """处理404错误"""
        logging.warning(f"404错误: {request.url}")
        return render_template("error.html", message="页面未找到"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """处理500错误"""
        logging.error(f"500错误: {error}", exc_info=True)
        return render_template("error.html", message="服务器内部错误，请稍后重试"), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """处理所有未捕获的异常"""
        logging.error(f"未捕获的异常: {error}", exc_info=True)
        # 如果是HTTP异常，返回相应的状态码
        if hasattr(error, 'code'):
            return render_template("error.html", message=str(error)), error.code
        # 其他异常返回500
        return render_template("error.html", message="发生错误，请稍后重试"), 500

    @app.template_filter("jsonify")
    def _jsonify(obj):
        return json.dumps(obj, default=str, ensure_ascii=False)

    @app.template_filter("smart_traffic")
    def smart_traffic(value):
        """
        智能转换流量单位
        - 小于 1000 GB：显示为 GB
        - 大于等于 1000 GB：显示为 TB
        
        Args:
            value: 流量值（GB）
        
        Returns:
            格式化后的字符串，如 "1.02 TB" 或 "999.5 GB"
        """
        try:
            value = float(value)
            if value >= 1000:
                # 转换为 TB
                tb_value = value / 1000.0
                return f"{tb_value:.2f} TB"
            else:
                # 保持 GB
                return f"{value:.2f} GB"
        except (ValueError, TypeError):
            return "0.00 GB"

    @app.context_processor
    def inject_nav():
        ctx_start = time.time()
        
        # 从 app.config 获取客户端和服务
        pg_client = app.config.get('pg_client')
        mysql_client = app.config.get('mysql_client')
        scenario_service = app.config.get('scenario_service')
        alarm_service = app.config.get('alarm_service')
        service = app.config.get('service')
        engineering_params_service = app.config.get('engineering_params_service')
        auth_manager = app.config.get('auth_manager')
        
        # 检查 PostgreSQL 连接状态，如果失败则尝试重连
        health_pg = False
        if pg_client:
            health_pg = cache_1m.get("health_pg", pg_client.test_connection)
            # 如果连接失败，尝试重连（但不要太频繁）
            if not health_pg:
                # 使用时间戳避免频繁重连（5分钟尝试一次）
                last_reconnect_key = "pg_last_reconnect_timestamp"
                last_attempt = cache_5m.get(last_reconnect_key, lambda: 0)
                current_time = time.time()
                # 如果距离上次尝试超过5分钟（300秒），则尝试重连
                if current_time - last_attempt > 300:
                    logging.info("🔄 检测到 PostgreSQL 连接失败，尝试重连...")
                    cache_5m.set(last_reconnect_key, current_time)
                    if pg_client.reconnect():
                        health_pg = True
                        cache_1m.invalidate("health_pg")
                        # 重连成功后，重新初始化业务服务
                        if not service or not scenario_service:
                            try:
                                service = MetricsService(pg_client, engineering_params_service)
                                scenario_service = ScenarioService(pg_client)
                                # 更新 app.config
                                app.config['service'] = service
                                app.config['scenario_service'] = scenario_service
                                logging.info("✓ 业务服务重新初始化成功")
                            except Exception as e:
                                logging.warning(f"⚠️ 业务服务重新初始化失败: {e}")
        
        # 检查 MySQL 连接状态，如果失败则尝试重连
        health_mysql = False
        if mysql_client:
            try:
                # 简单的连接测试
                test_result = mysql_client.fetch_one("SELECT 1 as test")
                health_mysql = test_result is not None
            except Exception as e:
                logging.debug(f"MySQL 连接测试失败: {e}")
                health_mysql = False

                # 如果连接失败，尝试重连（但不要太频繁）
                last_reconnect_key = "mysql_last_reconnect_timestamp"
                last_attempt = cache_5m.get(last_reconnect_key, lambda: 0)
                current_time = time.time()
                # 如果距离上次尝试超过5分钟（300秒），则尝试重连
                if current_time - last_attempt > 300:
                    logging.info("🔄 检测到 MySQL 连接失败，尝试重连...")
                    cache_5m.set(last_reconnect_key, current_time)
                    
                    # 重新读取配置文件，以支持配置热更新
                    try:
                        from config import Config
                        fresh_cfg = Config()
                        new_mysql_config = fresh_cfg.mysql_config
                        logging.info(f"重新加载配置: {new_mysql_config.get('host')}:{new_mysql_config.get('port')}/{new_mysql_config.get('database')}")
                        
                        # 使用新配置重连
                        if mysql_client.reconnect(new_mysql_config):
                            health_mysql = True
                            # 重连成功后，重新初始化告警服务（中兴和诺基亚）
                            alarm_service = app.config.get('alarm_service')
                            alarm_service_zte = app.config.get('alarm_service_zte')
                            alarm_service_nokia = app.config.get('alarm_service_nokia')
                            if not alarm_service or not alarm_service_zte or not alarm_service_nokia:
                                try:
                                    # 创建中兴设备告警服务实例
                                    alarm_service_zte = AlarmService(
                                        mysql_client,
                                        current_table='cur_alarm',
                                        history_table='his_alarm',
                                        vendor_name='中兴'
                                    )
                                    # 创建诺基亚设备告警服务实例（使用专门的NokiaAlarmService类）
                                    alarm_service_nokia = NokiaAlarmService(
                                        mysql_client,
                                        current_table='cur_alarm_nokia',
                                        history_table='his_alarm_nokia',
                                        vendor_name='诺基亚'
                                    )
                                    # 保持向后兼容
                                    alarm_service = alarm_service_zte
                                    # 更新 app.config
                                    app.config['alarm_service'] = alarm_service
                                    app.config['alarm_service_zte'] = alarm_service_zte
                                    app.config['alarm_service_nokia'] = alarm_service_nokia
                                    logging.info("✓ 告警服务已恢复")
                                except Exception as e:
                                    logging.error(f"重新初始化告警服务失败: {e}")
                    except Exception as e:
                        logging.error(f"重新加载配置失败: {e}")
                        # 如果重新加载配置失败，尝试使用旧配置重连
                        if mysql_client.reconnect():
                            health_mysql = True
        
        latest = scenario_service.latest_time() if scenario_service else {"4g": None, "5g": None}
        latest_ts_ok = bool(latest.get("4g") or latest.get("5g"))
        
        # 所有可用的页面（key, 显示名称, URL）
        all_pages = [
            ("dashboard", "全网监控", url_for("main.dashboard")),
            ("monitor", "保障监控", url_for("main.monitor")),
            ("cell", "指标查询", url_for("main.cell")),

            ("scenarios", "场景管理", url_for("main.scenarios")),
            ("grid", "网格监控", url_for("grid.grid")),
            ("alarm", "告警监控（中兴设备）", url_for("alarm.alarm")),
            ("alarm_nokia", "告警监控（诺基亚设备）", url_for("alarm.alarm_nokia")),
        ]
        
        # 根据用户权限过滤导航项
        nav_items = []
        username = session.get("username")
        user_role = session.get("role")
        
        if username and auth_manager:
            # 获取用户信息
            user_info = auth_manager.get_user_info(username)
            allowed_pages = user_info.get("allowed_pages")
            
            # 管理员可以访问所有页面
            if user_role == "admin":
                nav_items = all_pages.copy()
                nav_items.append(("admin", "管理员", url_for("admin.admin")))
            else:
                # 普通用户根据权限过滤
                if allowed_pages is not None:
                    # 如果配置了allowed_pages（包括空列表），只显示允许的页面
                    for page_key, page_name, page_url in all_pages:
                        if page_key in allowed_pages:
                            nav_items.append((page_key, page_name, page_url))
                else:
                    # 如果没有配置allowed_pages（None），默认显示所有页面（向后兼容）
                    nav_items = all_pages.copy()
        else:
            # 未登录或未启用认证，显示所有页面
            nav_items = all_pages.copy()
        
        ctx_elapsed = (time.time() - ctx_start) * 1000
        if ctx_elapsed > 100:
            logging.warning(f"⚠️ inject_nav 上下文处理器耗时: {ctx_elapsed:.2f}ms")
        
        return dict(
            nav_items=nav_items,
            latest_ts=latest,
            health_pg=health_pg,
            health_mysql=health_mysql,
            latest_ts_ok=latest_ts_ok,
            auth_enabled=auth_enabled,
            current_user=session.get("username"),
            user_role=user_role,
            user_name=session.get("name"),
        )
    
    logging.info(f"✓ Flask 应用初始化完成，总耗时: {(time.time() - app_start_time) * 1000:.2f}ms")
    logging.info("=" * 60)

    # ==================== 认证路由 ====================
    
    @app.route("/login", methods=["GET", "POST"])
    def login():
        """登录页面"""
        if not auth_enabled:
            # 如果未启用认证，直接跳转到首页
            return redirect(url_for("main.dashboard"))
        
        if request.method == "POST":
            username = validate_username(request.form.get("username", "").strip())
            password = request.form.get("password", "")
            
            # 获取客户端IP
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            # 调试日志：记录登录尝试
            logging.info(f"🔐 登录尝试 - 用户: {username}, IP: {client_ip}")

            if auth_manager:
                # 验证用户（包括管理员IP白名单检查）
                verified, error_msg = auth_manager.verify_user(username, password, client_ip)
                logging.info(f"🔐 验证结果 - 用户: {username}, IP: {client_ip}, 结果: {verified}, 错误: {error_msg}")
                
                if verified:
                    # 获取用户信息
                    user_info = auth_manager.get_user_info(username)
                    user_role = user_info.get("role", "user")
                    
                    # 如果是管理员，检查IP限制（单IP登录限制）
                    if user_role == "admin":
                        if not auth_manager.check_admin_ip(username, client_ip):
                            # IP不匹配，踢出旧session并允许新登录
                            auth_manager.clear_admin_login(username)
                            logging.warning(f"管理员 {username} 从新IP登录，已踢出旧session: {client_ip}")
                    
                    # 登录成功
                    session.clear()
                    session["logged_in"] = True
                    session["username"] = username
                    session["login_ip"] = client_ip
                    session["login_time"] = time.time()  # 记录登录时间
                    session["last_activity"] = time.time()  # 记录最后活动时间
                    session.permanent = request.form.get("remember") == "on"
                    session["role"] = user_role
                    session["name"] = user_info.get("name", username)
                    
                    # 记录管理员登录IP
                    if user_role == "admin":
                        auth_manager.record_admin_login(username, client_ip)

                    # 记录用户登录时间
                    auth_manager.record_login_time(username)

                    flash(f"欢迎回来，{user_info.get('name', username)}！", "success")
                    
                    # 重定向到原页面或首页
                    next_page = request.args.get("next")
                    if next_page:
                        return redirect(next_page)
                    return redirect(url_for("main.dashboard"))
                else:
                    flash(error_msg or "用户名或密码错误", "danger")
            else:
                flash("认证服务未初始化", "danger")
        
        return render_template("login.html")
    
    @app.route("/logout")
    def logout():
        """登出"""
        username = session.get("username", "未知用户")
        user_role = session.get("role", "user")
        
        # 如果是管理员，清除IP记录
        if user_role == "admin" and auth_manager:
            auth_manager.clear_admin_login(username)
        
        session.clear()
        flash(f"{username} 已安全退出", "info")
        return redirect(url_for("login"))
    
    @app.route("/session_info")
    @login_required
    def session_info():
        """会话信息页面"""
        # 获取会话超时配置
        session_timeout_hours = cfg.auth_config.get("session_timeout_hours", 8)
        session_lifetime_hours = cfg.auth_config.get("session_lifetime_hours", 24)
        
        return render_template(
            "session_info.html",
            session_timeout_hours=session_timeout_hours,
            session_lifetime_hours=session_lifetime_hours,
            title="会话信息"
        )
    
    # ==================== 管理员路由 ====================
    # Note: Admin routes have been moved to routes/admin.py
    # The admin_bp blueprint is registered above
    # Routes: /admin, /admin/add_user, /admin/delete_user, /admin/change_password,
    #         /admin/get_user_permissions, /admin/update_user_permissions, /admin/reset_user_permissions

    # ==================== 业务路由（添加认证保护）====================
    # Note: Main business routes have been moved to routes/main.py
    # The main_bp blueprint is registered above
    # Routes: /, /cell, /monitor, /scenarios, /api/performance/log, /api/scenarios/cells

    # ==================== 数据导出路由 ====================
    # Note: Export routes have been moved to routes/export.py
    # The export_bp blueprint is registered above
    # Routes: /export/traffic.csv, /export/top.csv, /export/monitor.csv, /export/monitor.xlsx,
    #         /export/monitor_xlsx_full, /export/latest_metrics.xlsx, /export/cell_data.xlsx,
    #         /export/top_utilization.xlsx, /scenarios/download_template, /scenarios/export_cells

    # ==================== 告警监控路由 ====================
    # Note: Alarm routes have been moved to routes/alarm.py
    # The alarm_bp blueprint is registered above
    # Routes: /alarm, /alarm_nokia, /export/current_alarms.xlsx, 
    #         /export/historical_alarms.xlsx, /export/current_alarms_nokia.xlsx,
    #         /export/historical_alarms_nokia.xlsx

    # ==================== 网格监控路由 ====================
    # Note: Grid monitoring routes have been moved to routes/grid.py
    # The grid_bp blueprint is registered above
    # Routes: /grid, /grid/<grid_id>, /api/grid/autocomplete,
    #         /grid/export/traffic_degraded, /grid/export/no_traffic_increased

    # ==================== 系统路由 ====================

    @app.route("/health")
    def health():
        """综合健康检查端点"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        # 检查PostgreSQL
        try:
            pg_healthy = pg_client.test_connection() if pg_client else False
            health_status["checks"]["postgresql"] = {
                "status": "up" if pg_healthy else "down",
                "healthy": pg_healthy
            }
            if not pg_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["postgresql"] = {
                "status": "down",
                "healthy": False,
                "error": str(e)
            }
            health_status["status"] = "degraded"

        # 检查MySQL
        try:
            if mysql_client:
                mysql_result = mysql_client.fetch_one("SELECT 1 as test")
                mysql_healthy = mysql_result is not None
            else:
                mysql_healthy = False
            health_status["checks"]["mysql"] = {
                "status": "up" if mysql_healthy else "down",
                "healthy": mysql_healthy
            }
            if not mysql_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["mysql"] = {
                "status": "down",
                "healthy": False,
                "error": str(e)
            }
            health_status["status"] = "degraded"

        # 检查服务可用性
        health_status["checks"]["services"] = {
            "metrics_service": service is not None,
            "scenario_service": scenario_service is not None,
            "alarm_service": alarm_service is not None
        }

        # 检查最新数据时间
        if scenario_service:
            try:
                latest = scenario_service.latest_time()
                health_status["checks"]["data_freshness"] = {
                    "4g": latest.get("4g"),
                    "5g": latest.get("5g")
                }
            except Exception as e:
                health_status["checks"]["data_freshness"] = {"error": str(e)}

        # 设置HTTP状态码
        status_code = 200 if health_status["status"] == "healthy" else 503

        return jsonify(health_status), status_code

    # ==================== 诊断路由 ====================
    
    @app.route("/test_navigation")
    def test_navigation():
        """导航栏测试页面 - 用于诊断导航栏不显示的问题"""
        return render_template("test_navigation.html")
        
        # 检查服务是否可用
        if not service or not scenario_service:
            flash("数据库服务未连接，请检查配置或联系管理员", "danger")
            return render_template("error.html", message="数据库服务未连接")
        
        from constants import (
            DEFAULT_PAGE_SIZE,
            TOP_CELLS_DEFAULT_LIMIT,
            GRANULARITY_15MIN,
            DEFAULT_AUTO_REFRESH_INTERVAL,
            PERF_THRESHOLD_ERROR,
            PERF_THRESHOLD_WARNING,
            PERF_THRESHOLD_INFO,
        )
        from utils.validators import validate_time_range, validate_granularity
        
        # 参数验证
        param_start = time.time()
        range_key = validate_time_range(request.args.get("range", ""))
        networks: List[str] = request.args.getlist("networks") or cfg.ui_config["default_networks"]
        auto = request.args.get("auto", "0") == "1"
        auto_interval = int(request.args.get("auto_interval", DEFAULT_AUTO_REFRESH_INTERVAL))
        granularity = validate_granularity(request.args.get("granularity", ""))
        logging.debug(f"  ├─ 参数解析: {(time.time() - param_start) * 1000:.2f}ms")
        
        # 处理日期参数（用于显示日流量和话务量）
        date_str = request.args.get("date", "")
        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception as e:
                logging.warning(f"解析日期参数失败: {date_str}, 错误: {e}")

        # 获取最新时间
        latest_start = time.time()
        latest = scenario_service.latest_time()
        latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
        latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
        logging.debug(f"  ├─ 获取最新时间: {(time.time() - latest_start) * 1000:.2f}ms")

        # 解析时间范围
        range_start = time.time()
        start, end = service.resolve_range(range_key, reference_time=latest_ts)
        logging.debug(f"  ├─ 解析时间范围: {(time.time() - range_start) * 1000:.2f}ms")

        # 创建稳定的缓存键（使用排序后的字符串）
        networks_key = ','.join(sorted(networks))

        # 查询流量数据
        traffic_start = time.time()
        traffic = cache_5m.get(
            f"traffic:{range_key}:{networks_key}:{granularity}:{end}",
            lambda: service.traffic_series(networks, start, end, granularity),
        )
        logging.debug(f"  ├─ 查询流量数据: {(time.time() - traffic_start) * 1000:.2f}ms")

        # 查询接通率数据
        connect_start = time.time()
        connect_series = cache_5m.get(
            f"connect:{range_key}:{networks_key}:{granularity}:{end}",
            lambda: service.connectivity_series(networks, start, end, granularity),
        )
        logging.debug(f"  ├─ 查询接通率数据: {(time.time() - connect_start) * 1000:.2f}ms")
        
        # 查询RRC数据
        rrc_start = time.time()
        rrc_series = cache_5m.get(
            f"rrc:{range_key}:{networks_key}:{granularity}:{end}",
            lambda: service.rrc_series(networks, start, end, granularity),
        )
        logging.debug(f"  ├─ 查询RRC数据: {(time.time() - rrc_start) * 1000:.2f}ms")
        
        # Top 利用率（按最新时段）
        top_start = time.time()
        top4_raw = service.top_utilization("4G", limit=TOP_CELLS_DEFAULT_LIMIT, granularity=granularity)
        top5_raw = service.top_utilization("5G", limit=TOP_CELLS_DEFAULT_LIMIT, granularity=granularity)
        logging.debug(f"  ├─ 查询Top利用率: {(time.time() - top_start) * 1000:.2f}ms")
        
        page4 = int(request.args.get("page4", 1))
        page5 = int(request.args.get("page5", 1))

        def paginate(data: List[dict], page: int) -> dict:
            total = len(data)
            pages = (total + DEFAULT_PAGE_SIZE - 1) // DEFAULT_PAGE_SIZE if total else 0
            start_idx = (page - 1) * DEFAULT_PAGE_SIZE
            end_idx = start_idx + DEFAULT_PAGE_SIZE
            return {
                "data": data[start_idx:end_idx],
                "page": page,
                "pages": pages,
                "total": total,
            }

        top4 = paginate(top4_raw, page4)
        top5 = paginate(top5_raw, page5)
        
        # 查询日流量和话务量
        daily_start = time.time()
        daily_stats = service.daily_traffic_and_voice(target_date)
        daily_stats_by_region = service.daily_traffic_and_voice_by_region(target_date)
        logging.debug(f"  ├─ 查询日统计数据: {(time.time() - daily_start) * 1000:.2f}ms")
        
        logging.info(f"  └─ dashboard 数据查询总耗时: {(time.time() - route_start) * 1000:.2f}ms")

        return render_template(
            "dashboard.html",
            range_key=range_key,
            networks=networks,
            traffic=traffic,
            top4=top4,
            top5=top5,
            page4=page4,
            page5=page5,
            connect_series=connect_series,
            rrc_series=rrc_series,
            end_time=end,
            auto=auto,
            auto_interval=auto_interval,
            latest_ts=latest,
            granularity=granularity,
            daily_stats=daily_stats,
            daily_stats_by_region=daily_stats_by_region,
            selected_date=date_str or daily_stats["date"],
        )

    # ==================== 告警监控路由 ====================
    # Note: Alarm routes have been moved to routes/alarm.py
    # The alarm_bp blueprint is registered above
    # Routes: /alarm, /alarm_nokia, /export/current_alarms.xlsx, 
    #         /export/historical_alarms.xlsx, /export/current_alarms_nokia.xlsx,
    #         /export/historical_alarms_nokia.xlsx

    # ==================== 网格监控路由 ====================
    # Note: Grid monitoring routes have been moved to routes/grid.py
    # The grid_bp blueprint is registered above
    # Routes: /grid, /grid/<grid_id>, /api/grid/autocomplete,
    #         /grid/export/traffic_degraded, /grid/export/no_traffic_increased
    
    # ==================== 诊断路由 ====================
    
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="保障指标监控（Flask）")
    parser.add_argument("--host", default=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("FLASK_RUN_PORT", 5001)),
        help="HTTP 端口（默认 5000，可用 5001 等规避占用）",
    )
    # 默认关闭 debug，线上如需开启请显式传参或设置环境变量
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="启用调试模式（默认关闭，适用于开发环境）",
    )
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
