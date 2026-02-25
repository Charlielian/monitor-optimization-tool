"""
Admin Routes Blueprint

This module contains all admin-related routes:
- Admin dashboard: 管理员控制台
- User management: 添加、删除、修改密码
- Permission management: 权限配置

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import json
import logging
import os
import time
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash

from auth import admin_required
from utils.validators import sanitize_html, validate_username, validate_string_length


# Create the admin blueprint with no URL prefix to maintain existing URL patterns
admin_bp = Blueprint('admin', __name__)


def save_config(cfg, users_config: dict):
    """
    保存配置到 config.json 文件
    
    Args:
        cfg: Config 对象
        users_config: 用户配置字典
    """
    # 查找配置文件路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def get_admin_context():
    """
    Get admin-related context from app config.
    
    Returns:
        tuple: (cfg, users_config, auth_manager, scenario_service, 
                engineering_params_service, pg_client, mysql_client, app_start_time)
    """
    cfg = current_app.config.get('app_config')
    auth_manager = current_app.config.get('auth_manager')
    scenario_service = current_app.config.get('scenario_service')
    engineering_params_service = current_app.config.get('engineering_params_service')
    pg_client = current_app.config.get('pg_client')
    mysql_client = current_app.config.get('mysql_client')
    
    # Get users_config from auth_manager or config
    users_config = auth_manager.users if auth_manager else {}
    
    return (cfg, users_config, auth_manager, scenario_service, 
            engineering_params_service, pg_client, mysql_client)


# All available pages (key, display name)
ALL_PAGES = [
    {"key": "dashboard", "name": "全网监控"},
    {"key": "monitor", "name": "保障监控"},
    {"key": "cell", "name": "指标查询"},
    {"key": "scenarios", "name": "场景管理"},
    {"key": "grid", "name": "网格监控"},
    {"key": "alarm", "name": "告警监控（中兴设备）"},
    {"key": "alarm_nokia", "name": "告警监控（诺基亚设备）"},
]

VALID_PAGE_KEYS = [p["key"] for p in ALL_PAGES]


@admin_bp.route("/admin")
@admin_required
def admin():
    """管理员控制台"""
    (cfg, users_config, auth_manager, scenario_service, 
     engineering_params_service, pg_client, mysql_client) = get_admin_context()
    
    # Get app start time from config (set during app creation)
    app_start_time = current_app.config.get('app_start_time', time.time())
    
    # 系统统计
    scenarios = scenario_service.list_scenarios() if scenario_service else []
    total_cells = 0
    for s in scenarios:
        cells = scenario_service.list_cells(s["id"]) if scenario_service else []
        total_cells += len(cells)

    # 计算运行时间
    uptime_seconds = int(time.time() - app_start_time)
    uptime_hours = uptime_seconds // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60
    uptime_str = f"{uptime_hours}小时{uptime_minutes}分钟"

    stats = {
        "total_scenarios": len(scenarios),
        "total_cells": total_cells,
        "total_users": len(users_config),
        "uptime": uptime_str,
    }
    
    # 用户列表
    users = []
    for username, user_data in users_config.items():
        last_login = auth_manager.get_last_login_time(username) if auth_manager else None
        users.append({
            "username": username,
            "name": user_data.get("name", username),
            "role": user_data.get("role", "user"),
            "role_name": "管理员" if user_data.get("role") == "admin" else "普通用户",
            "last_login": last_login.strftime("%Y-%m-%d %H:%M:%S") if last_login else "从未登录",
        })
    
    # 管理员访问日志（最近50条）
    admin_access_logs = []
    if auth_manager:
        admin_access_logs = auth_manager.get_admin_access_logs(limit=50)
    
    # 系统日志（最近50条）
    logs = []
    try:
        log_file = cfg.log_config.get("file_path") if cfg else None
        if log_file and os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-50:]
                for line in lines:
                    # 简单解析日志
                    parts = line.strip().split(" - ", 2)
                    if len(parts) >= 3:
                        logs.append({
                            "timestamp": parts[0],
                            "level": parts[1],
                            "message": parts[2],
                            "username": None,
                        })
    except Exception as e:
        logging.error(f"读取日志文件失败: {e}")
    
    # 数据库状态
    latest = scenario_service.latest_time() if scenario_service else {"4g": None, "5g": None}
    db_status = {
        "pg_connected": pg_client.test_connection() if pg_client else False,
        "latest_4g": latest.get("4g"),
        "latest_5g": latest.get("5g"),
        "mysql_connected": mysql_client is not None if mysql_client else False,
        "engineering_params_count": len(engineering_params_service._region_cache) if engineering_params_service else 0,
        "cache_status": "正常",
    }
    
    # 管理员访问控制配置
    admin_access_config = auth_manager.admin_access_config if auth_manager else {}
    
    return render_template(
        "admin.html",
        stats=stats,
        users=users,
        logs=logs,
        admin_access_logs=admin_access_logs,
        db_status=db_status,
        admin_access_config=admin_access_config,
    )


@admin_bp.route("/admin/add_user", methods=["POST"])
@admin_required
def admin_add_user():
    """添加用户"""
    (cfg, users_config, auth_manager, _, _, _, _) = get_admin_context()
    
    try:
        username = validate_username(request.form.get("username", "").strip())
        name = validate_string_length(sanitize_html(request.form.get("name", "").strip()), 100)
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        
        # 验证输入
        if not username or not name or not password:
            flash("用户名、姓名和密码不能为空", "danger")
            return redirect(url_for("admin.admin"))
        
        if username in users_config:
            flash(f"用户名 {username} 已存在", "danger")
            return redirect(url_for("admin.admin"))
        
        if role not in ["user", "admin"]:
            role = "user"
        
        # 生成密码哈希
        password_hash = generate_password_hash(password)
        
        # 添加用户到配置
        users_config[username] = {
            "password_hash": password_hash,
            "role": role,
            "name": name
        }
        
        # 保存到配置文件
        save_config(cfg, users_config)
        
        # 更新认证管理器
        if auth_manager:
            auth_manager.users = users_config
        
        flash(f"用户 {username} 添加成功", "success")
        logging.info(f"管理员 {session.get('username')} 添加了新用户: {username}")
        
    except (ValueError, KeyError) as e:
        flash(f"添加用户失败: 输入数据无效", "danger")
        logging.error(f"添加用户失败: {e}", exc_info=True)
    except IOError as e:
        flash(f"添加用户失败: 配置文件写入失败", "danger")
        logging.error(f"配置文件写入失败: {e}", exc_info=True)
    except Exception as e:
        flash(f"添加用户失败: {str(e)}", "danger")
        logging.error(f"添加用户失败: {e}", exc_info=True)

    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/delete_user", methods=["POST"])
@admin_required
def admin_delete_user():
    """删除用户"""
    (cfg, users_config, auth_manager, _, _, _, _) = get_admin_context()
    
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        
        if not username:
            return jsonify({"success": False, "message": "用户名不能为空"})
        
        if username == session.get("username"):
            return jsonify({"success": False, "message": "不能删除当前登录的用户"})
        
        if username not in users_config:
            return jsonify({"success": False, "message": f"用户 {username} 不存在"})
        
        # 删除用户
        del users_config[username]
        
        # 保存到配置文件
        save_config(cfg, users_config)
        
        # 更新认证管理器
        if auth_manager:
            auth_manager.users = users_config
        
        logging.info(f"管理员 {session.get('username')} 删除了用户: {username}")
        return jsonify({"success": True, "message": f"用户 {username} 已删除"})
        
    except Exception as e:
        logging.error(f"删除用户失败: {e}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"})


@admin_bp.route("/admin/change_password", methods=["POST"])
@admin_required
def admin_change_password():
    """修改用户密码"""
    (cfg, users_config, auth_manager, _, _, _, _) = get_admin_context()
    
    try:
        username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "")
        
        if not username or not new_password:
            flash("用户名和新密码不能为空", "danger")
            return redirect(url_for("admin.admin"))
        
        if username not in users_config:
            flash(f"用户 {username} 不存在", "danger")
            return redirect(url_for("admin.admin"))
        
        # 生成新密码哈希
        password_hash = generate_password_hash(new_password)
        
        # 更新密码
        users_config[username]["password_hash"] = password_hash
        
        # 保存到配置文件
        save_config(cfg, users_config)
        
        # 更新认证管理器
        if auth_manager:
            auth_manager.users = users_config
        
        flash(f"用户 {username} 的密码已修改", "success")
        logging.info(f"管理员 {session.get('username')} 修改了用户 {username} 的密码")
        
    except Exception as e:
        flash(f"修改密码失败: {str(e)}", "danger")
        logging.error(f"修改密码失败: {e}")
    
    return redirect(url_for("admin.admin"))


@admin_bp.route("/admin/get_user_permissions", methods=["POST"])
@admin_required
def admin_get_user_permissions():
    """获取用户权限配置"""
    (_, users_config, _, _, _, _, _) = get_admin_context()
    
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        
        if not username:
            return jsonify({"success": False, "message": "用户名不能为空"})
        
        if username not in users_config:
            return jsonify({"success": False, "message": f"用户 {username} 不存在"})
        
        user = users_config[username]
        allowed_pages = user.get("allowed_pages")
        
        return jsonify({
            "success": True,
            "username": username,
            "name": user.get("name", username),
            "role": user.get("role", "user"),
            "allowed_pages": allowed_pages,
            "all_pages": ALL_PAGES
        })
        
    except Exception as e:
        logging.error(f"获取用户权限失败: {e}")
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"})


@admin_bp.route("/admin/update_user_permissions", methods=["POST"])
@admin_required
def admin_update_user_permissions():
    """更新用户权限配置"""
    (cfg, users_config, auth_manager, _, _, _, _) = get_admin_context()
    
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        allowed_pages = data.get("allowed_pages", [])
        
        if not username:
            return jsonify({"success": False, "message": "用户名不能为空"})
        
        if username not in users_config:
            return jsonify({"success": False, "message": f"用户 {username} 不存在"})
        
        # 验证页面标识
        for page in allowed_pages:
            if page not in VALID_PAGE_KEYS:
                return jsonify({"success": False, "message": f"无效的页面标识: {page}"})
        
        # 更新用户权限
        if allowed_pages:
            users_config[username]["allowed_pages"] = allowed_pages
        else:
            # 如果传入空数组，设置为空数组（不允许访问任何页面）
            users_config[username]["allowed_pages"] = []
        
        # 保存到配置文件
        save_config(cfg, users_config)
        
        # 更新认证管理器
        if auth_manager:
            auth_manager.users = users_config
        
        logging.info(f"管理员 {session.get('username')} 更新了用户 {username} 的权限: {allowed_pages}")
        return jsonify({
            "success": True,
            "message": f"用户 {username} 的权限已更新"
        })
        
    except Exception as e:
        logging.error(f"更新用户权限失败: {e}")
        return jsonify({"success": False, "message": f"更新失败: {str(e)}"})


@admin_bp.route("/admin/reset_user_permissions", methods=["POST"])
@admin_required
def admin_reset_user_permissions():
    """重置用户权限为默认（允许访问所有页面）"""
    (cfg, users_config, auth_manager, _, _, _, _) = get_admin_context()
    
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        
        if not username:
            return jsonify({"success": False, "message": "用户名不能为空"})
        
        if username not in users_config:
            return jsonify({"success": False, "message": f"用户 {username} 不存在"})
        
        # 移除 allowed_pages 配置（恢复默认行为）
        if "allowed_pages" in users_config[username]:
            del users_config[username]["allowed_pages"]
        
        # 保存到配置文件
        save_config(cfg, users_config)
        
        # 更新认证管理器
        if auth_manager:
            auth_manager.users = users_config
        
        logging.info(f"管理员 {session.get('username')} 重置了用户 {username} 的权限为默认")
        return jsonify({
            "success": True,
            "message": f"用户 {username} 的权限已重置为默认（允许访问所有页面）"
        })
        
    except Exception as e:
        logging.error(f"重置用户权限失败: {e}")
        return jsonify({"success": False, "message": f"重置失败: {str(e)}"})
