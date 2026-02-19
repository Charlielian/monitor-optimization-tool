#!/usr/bin/env python3
"""
离线图表完整修复脚本
解决离线环境下图表库无法加载的问题
"""

import os
import sys
import subprocess

def check_file(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        size_kb = size / 1024
        print(f"  ✅ {description}: {filepath} ({size_kb:.1f}KB)")
        return True
    else:
        print(f"  ❌ {description}: {filepath} 不存在")
        return False

def main():
    print("=" * 60)
    print("离线图表完整修复")
    print("=" * 60)
    print()
    
    # 检查必要的文件
    print("1. 检查静态资源文件...")
    files_ok = True
    
    # Chart.js
    files_ok &= check_file("static/js/chart.umd.min.js", "Chart.js")
    
    # Bootstrap
    files_ok &= check_file("static/css/bootstrap.min.css", "Bootstrap CSS")
    files_ok &= check_file("static/js/bootstrap.bundle.min.js", "Bootstrap JS")
    
    # Bootstrap Icons
    files_ok &= check_file("static/css/bootstrap-icons.min.css", "Bootstrap Icons CSS")
    files_ok &= check_file("static/fonts/bootstrap-icons.woff", "Bootstrap Icons 字体 (WOFF)")
    files_ok &= check_file("static/fonts/bootstrap-icons.woff2", "Bootstrap Icons 字体 (WOFF2)")
    
    print()
    
    if not files_ok:
        print("❌ 部分文件缺失！")
        print()
        print("修复步骤:")
        print("  1. 下载 Bootstrap Icons:")
        print("     python download_bootstrap_icons.py")
        print()
        print("  2. 确保 Chart.js 和 Bootstrap 文件存在")
        print("     如果缺失，请从 CDN 下载或从备份恢复")
        print()
        return False
    
    # 检查 base.html 配置
    print("2. 检查 base.html 配置...")
    
    with open("templates/base.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = [
        ("Bootstrap Icons 本地优先", "url_for('static', filename='css/bootstrap-icons.min.css')"),
        ("Chart.js 本地加载", "url_for('static', filename='js/chart.umd.min.js')"),
        ("Bootstrap JS 本地加载", "url_for('static', filename='js/bootstrap.bundle.min.js')"),
    ]
    
    config_ok = True
    for desc, pattern in checks:
        if pattern in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc} - 未找到")
            config_ok = False
    
    print()
    
    if not config_ok:
        print("❌ base.html 配置不正确！")
        print()
        print("请检查 templates/base.html 文件")
        return False
    
    # 检查 Chart.js 加载顺序
    print("3. 检查 Chart.js 加载顺序...")
    
    # Chart.js 应该在 </body> 前加载，不应该有 defer
    chart_in_head = '<head>' in content and 'chart.umd.min.js' in content.split('</head>')[0]
    chart_has_defer = 'chart.umd.min.js" defer' in content
    
    if chart_in_head:
        print("  ⚠️  Chart.js 在 <head> 中加载（可能阻塞渲染）")
        print("     建议：移到 </body> 前")
    else:
        print("  ✅ Chart.js 在 <body> 底部加载")
    
    if chart_has_defer:
        print("  ⚠️  Chart.js 使用了 defer 属性（可能导致图表代码执行时库未加载）")
        print("     建议：移除 defer 属性")
    else:
        print("  ✅ Chart.js 同步加载（确保图表代码执行前已加载）")
    
    print()
    
    # 总结
    print("=" * 60)
    if files_ok and config_ok and not chart_in_head and not chart_has_defer:
        print("✅ 所有检查通过！离线图表应该可以正常显示。")
        print()
        print("测试步骤:")
        print("  1. 重启应用: python app.py")
        print("  2. 访问应用: http://localhost:5000")
        print("  3. 断开网络连接（模拟离线环境）")
        print("  4. 刷新页面，检查图表是否正常显示")
        print()
        return True
    else:
        print("⚠️  部分检查未通过，可能影响离线图表显示。")
        print()
        print("建议:")
        print("  1. 确保所有静态资源文件都已下载")
        print("  2. 检查 base.html 配置")
        print("  3. 确保 Chart.js 在正确的位置加载")
        print()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
