#!/usr/bin/env python3
"""
离线部署验证脚本
检查所有静态资源是否本地化，无外部依赖
"""

import os
import re
from pathlib import Path

def check_static_files():
    """检查必需的静态文件是否存在"""
    print("=" * 70)
    print("1. 检查静态资源文件")
    print("=" * 70)
    
    required_files = [
        'static/css/bootstrap.min.css',
        'static/css/bootstrap-icons.min.css',
        'static/css/style.css',
        'static/js/bootstrap.bundle.min.js',
        'static/js/chart.umd.min.js',
        'static/js/ajax-utils.js',
        'static/js/chart-optimizer.js',
        'static/js/performance-monitor.js',
        'static/fonts/bootstrap-icons.woff',
        'static/fonts/bootstrap-icons.woff2',
        'static/css/fonts/bootstrap-icons.woff',
        'static/css/fonts/bootstrap-icons.woff2',
    ]
    
    all_exist = True
    for file in required_files:
        exists = os.path.exists(file)
        status = '✓' if exists else '✗'
        if exists:
            size = os.path.getsize(file)
            print(f"{status} {file:55} {size:>10,} bytes")
        else:
            print(f"{status} {file:55} {'缺失':>10}")
            all_exist = False
    
    return all_exist


def check_cdn_references():
    """检查模板文件中的CDN引用"""
    print("\n" + "=" * 70)
    print("2. 检查模板文件中的CDN引用")
    print("=" * 70)
    
    cdn_patterns = [
        r'https?://cdn\.jsdelivr\.net',
        r'https?://.*googleapis\.com',
        r'https?://.*cloudflare\.com',
        r'https?://unpkg\.com',
        r'https?://cdnjs\.cloudflare\.com',
    ]
    
    templates_dir = Path('templates')
    found_cdn = False
    
    for template_file in templates_dir.glob('*.html'):
        content = template_file.read_text(encoding='utf-8')
        
        for pattern in cdn_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                found_cdn = True
                print(f"✗ {template_file.name}: 发现CDN引用")
                for match in matches:
                    print(f"  └─ {match}")
    
    if not found_cdn:
        print("✓ 未发现任何CDN引用")
    
    return not found_cdn


def check_url_for_usage():
    """检查模板文件是否正确使用url_for加载静态资源"""
    print("\n" + "=" * 70)
    print("3. 检查静态资源引用方式")
    print("=" * 70)
    
    templates_dir = Path('templates')
    correct_usage = True
    
    # 检查是否使用了硬编码的静态路径
    bad_patterns = [
        (r'<link[^>]+href=["\'](?!{{)(?!/static/)[^"\']*\.css', '硬编码CSS路径'),
        (r'<script[^>]+src=["\'](?!{{)(?!/static/)[^"\']*\.js', '硬编码JS路径'),
    ]
    
    for template_file in templates_dir.glob('*.html'):
        content = template_file.read_text(encoding='utf-8')
        
        for pattern, desc in bad_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            # 过滤掉http://127.0.0.1这类本地测试URL
            matches = [m for m in matches if 'http://127.0.0.1' not in m and 'localhost' not in m]
            if matches:
                correct_usage = False
                print(f"⚠ {template_file.name}: 发现{desc}")
                for match in matches[:3]:  # 只显示前3个
                    print(f"  └─ {match[:80]}...")
    
    if correct_usage:
        print("✓ 所有静态资源都使用url_for()或相对路径")
    
    return correct_usage


def check_font_paths():
    """检查字体文件路径配置"""
    print("\n" + "=" * 70)
    print("4. 检查字体文件路径")
    print("=" * 70)
    
    css_file = Path('static/css/bootstrap-icons.min.css')
    if not css_file.exists():
        print("✗ bootstrap-icons.min.css 不存在")
        return False
    
    content = css_file.read_text(encoding='utf-8')
    
    # 检查字体路径
    if 'url("fonts/bootstrap-icons.woff2' in content or "url('fonts/bootstrap-icons.woff2" in content:
        print("✓ CSS中字体路径为相对路径: fonts/bootstrap-icons.woff2")
        
        # 检查对应的字体文件是否存在
        font_dir = Path('static/css/fonts')
        if font_dir.exists():
            woff2 = font_dir / 'bootstrap-icons.woff2'
            woff = font_dir / 'bootstrap-icons.woff'
            
            if woff2.exists() and woff.exists():
                print(f"✓ 字体文件存在: {font_dir}/")
                print(f"  ├─ bootstrap-icons.woff2 ({woff2.stat().st_size:,} bytes)")
                print(f"  └─ bootstrap-icons.woff ({woff.stat().st_size:,} bytes)")
                return True
            else:
                print(f"✗ 字体文件缺失在 {font_dir}/")
                return False
        else:
            print(f"✗ 字体目录不存在: {font_dir}")
            return False
    else:
        print("⚠ CSS中未找到预期的字体路径")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("离线部署验证脚本")
    print("=" * 70)
    print()
    
    results = {
        '静态文件完整性': check_static_files(),
        'CDN引用检查': check_cdn_references(),
        '资源引用方式': check_url_for_usage(),
        '字体路径配置': check_font_paths(),
    }
    
    print("\n" + "=" * 70)
    print("验证结果汇总")
    print("=" * 70)
    
    all_passed = True
    for check_name, passed in results.items():
        status = '✅ 通过' if passed else '❌ 失败'
        print(f"{status} - {check_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n🎉 所有检查通过！项目已完全本地化，可以在离线环境部署。")
        return 0
    else:
        print("\n⚠️  部分检查未通过，请根据上述提示修复问题。")
        return 1


if __name__ == "__main__":
    exit(main())
