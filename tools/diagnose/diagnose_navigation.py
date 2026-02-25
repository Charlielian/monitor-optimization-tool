#!/usr/bin/env python3
"""
导航栏问题诊断脚本
用于快速检查导航栏不显示的可能原因
"""

import os
import sys
import json
from pathlib import Path


def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✅ {description}: 存在 ({size:,} 字节)")
        return True
    else:
        print(f"❌ {description}: 不存在")
        return False


def check_static_resources():
    """检查静态资源文件"""
    print("\n" + "=" * 60)
    print("检查静态资源文件")
    print("=" * 60)
    
    resources = [
        ("static/css/bootstrap.min.css", "Bootstrap CSS"),
        ("static/css/bootstrap-icons.min.css", "Bootstrap Icons CSS"),
        ("static/css/style.css", "自定义样式"),
        ("static/js/bootstrap.bundle.min.js", "Bootstrap JS"),
        ("static/js/chart.umd.min.js", "Chart.js"),
        ("static/fonts/bootstrap-icons.woff", "Bootstrap Icons 字体 (WOFF)"),
        ("static/fonts/bootstrap-icons.woff2", "Bootstrap Icons 字体 (WOFF2)"),
    ]
    
    all_exist = True
    for filepath, description in resources:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist


def check_templates():
    """检查模板文件"""
    print("\n" + "=" * 60)
    print("检查模板文件")
    print("=" * 60)
    
    templates = [
        ("templates/base.html", "基础模板"),
        ("templates/dashboard.html", "全网监控模板"),
        ("templates/monitor.html", "保障监控模板"),
        ("templates/cell.html", "小区查询模板"),
        ("templates/scenarios.html", "场景管理模板"),
        ("templates/grid.html", "网格监控模板"),
        ("templates/alarm.html", "告警监控模板"),
        ("templates/login.html", "登录页面模板"),
    ]
    
    all_exist = True
    for filepath, description in templates:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist


def check_base_template():
    """检查 base.html 模板中的导航栏代码"""
    print("\n" + "=" * 60)
    print("检查 base.html 模板")
    print("=" * 60)
    
    base_template = "templates/base.html"
    if not os.path.exists(base_template):
        print(f"❌ {base_template} 不存在")
        return False
    
    with open(base_template, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查关键元素
    checks = [
        ("<nav", "导航栏标签"),
        ("navbar", "导航栏类"),
        ("nav_items", "导航项变量"),
        ("url_for('static'", "静态资源引用"),
        ("bootstrap.min.css", "Bootstrap CSS 引用"),
        ("bootstrap.bundle.min.js", "Bootstrap JS 引用"),
    ]
    
    all_present = True
    for keyword, description in checks:
        if keyword in content:
            print(f"✅ {description}: 存在")
        else:
            print(f"❌ {description}: 缺失")
            all_present = False
    
    return all_present


def check_app_py():
    """检查 app.py 中的 inject_nav 函数"""
    print("\n" + "=" * 60)
    print("检查 app.py")
    print("=" * 60)
    
    app_file = "app.py"
    if not os.path.exists(app_file):
        print(f"❌ {app_file} 不存在")
        return False
    
    with open(app_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查关键函数
    checks = [
        ("def inject_nav", "inject_nav 上下文处理器"),
        ("@app.context_processor", "上下文处理器装饰器"),
        ("nav_items", "导航项变量"),
        ("return dict(", "返回字典"),
    ]
    
    all_present = True
    for keyword, description in checks:
        if keyword in content:
            print(f"✅ {description}: 存在")
        else:
            print(f"❌ {description}: 缺失")
            all_present = False
    
    return all_present


def check_config():
    """检查配置文件"""
    print("\n" + "=" * 60)
    print("检查配置文件")
    print("=" * 60)
    
    config_file = "config.json"
    if not os.path.exists(config_file):
        print(f"❌ {config_file} 不存在")
        return False
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        print(f"✅ 配置文件格式正确")
        
        # 检查认证配置
        if "auth_config" in config:
            auth_config = config["auth_config"]
            enable_auth = auth_config.get("enable_auth", True)
            print(f"   认证状态: {'启用' if enable_auth else '禁用'}")
            
            if "users" in auth_config:
                user_count = len(auth_config["users"])
                print(f"   用户数量: {user_count}")
            else:
                print(f"   ⚠️ 未配置用户")
        else:
            print(f"   ⚠️ 未配置认证")
        
        return True
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False


def check_flask_process():
    """检查 Flask 进程是否运行"""
    print("\n" + "=" * 60)
    print("检查 Flask 进程")
    print("=" * 60)
    
    try:
        import subprocess
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "app.py" in result.stdout:
            print("✅ Flask 应用正在运行")
            # 提取进程信息
            for line in result.stdout.split("\n"):
                if "app.py" in line and "grep" not in line:
                    print(f"   进程信息: {line.strip()}")
            return True
        else:
            print("❌ Flask 应用未运行")
            print("   请运行: python3 app.py")
            return False
    except Exception as e:
        print(f"⚠️ 无法检查进程状态: {e}")
        return None


def check_port():
    """检查端口是否被占用"""
    print("\n" + "=" * 60)
    print("检查端口占用")
    print("=" * 60)
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        
        if result == 0:
            print("✅ 端口 5000 已被占用（Flask 应用可能正在运行）")
            print("   访问地址: http://127.0.0.1:5000/")
            return True
        else:
            print("❌ 端口 5000 未被占用（Flask 应用未运行）")
            return False
    except Exception as e:
        print(f"⚠️ 无法检查端口状态: {e}")
        return None


def print_recommendations():
    """打印建议"""
    print("\n" + "=" * 60)
    print("建议操作")
    print("=" * 60)
    
    print("""
1. 确保 Flask 应用正在运行：
   python3 app.py

2. 在浏览器中访问正确的 URL：
   http://127.0.0.1:5000/
   或
   http://localhost:5000/

3. 不要直接打开 HTML 文件（file:// 协议）

4. 检查浏览器控制台（F12）是否有错误信息

5. 如果静态资源缺失，请从备份或在线环境复制

6. 查看应用日志：
   tail -f logs/monitoring_app.log

7. 如果问题仍未解决，请查看详细文档：
   cat NAVIGATION_FIX.md
""")


def main():
    """主函数"""
    print("=" * 60)
    print("导航栏问题诊断工具")
    print("=" * 60)
    
    # 检查当前目录
    if not os.path.exists("app.py"):
        print("❌ 错误：请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 执行各项检查
    results = {
        "静态资源": check_static_resources(),
        "模板文件": check_templates(),
        "base.html": check_base_template(),
        "app.py": check_app_py(),
        "配置文件": check_config(),
        "Flask 进程": check_flask_process(),
        "端口占用": check_port(),
    }
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("诊断结果汇总")
    print("=" * 60)
    
    for check_name, result in results.items():
        if result is True:
            status = "✅ 正常"
        elif result is False:
            status = "❌ 异常"
        else:
            status = "⚠️ 未知"
        print(f"{check_name}: {status}")
    
    # 判断整体状态
    failed_checks = [name for name, result in results.items() if result is False]
    
    if not failed_checks:
        print("\n✅ 所有检查通过！")
        print("如果导航栏仍然不显示，请：")
        print("1. 确认通过 http://127.0.0.1:5000/ 访问")
        print("2. 检查浏览器控制台（F12）是否有错误")
        print("3. 清除浏览器缓存后重试")
    else:
        print(f"\n❌ 发现 {len(failed_checks)} 个问题：")
        for name in failed_checks:
            print(f"   - {name}")
    
    # 打印建议
    print_recommendations()


if __name__ == "__main__":
    main()
