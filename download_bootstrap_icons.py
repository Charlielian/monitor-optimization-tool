#!/usr/bin/env python3
"""
下载 Bootstrap Icons 到本地，支持离线环境
Python 版本（跨平台）
"""

import os
import urllib.request
import re

def download_file(url, filepath):
    """下载文件"""
    try:
        print(f"正在下载: {url}")
        urllib.request.urlretrieve(url, filepath)
        print(f"✓ 下载成功: {filepath}")
        return True
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        return False

def main():
    print("=" * 60)
    print("下载 Bootstrap Icons 到本地")
    print("=" * 60)
    
    # 创建目录
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/fonts", exist_ok=True)
    
    # 下载 CSS
    css_url = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
    css_path = "static/css/bootstrap-icons.min.css"
    
    if not download_file(css_url, css_path):
        return False
    
    # 下载字体文件
    fonts = [
        ("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2",
         "static/fonts/bootstrap-icons.woff2"),
        ("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff",
         "static/fonts/bootstrap-icons.woff"),
    ]
    
    for url, path in fonts:
        if not download_file(url, path):
            print(f"警告: {path} 下载失败，但可以继续")
    
    # 修改 CSS 文件中的字体路径
    print("\n正在修改字体路径...")
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换字体路径
        content = content.replace('../fonts/bootstrap-icons.woff2', '/static/fonts/bootstrap-icons.woff2')
        content = content.replace('../fonts/bootstrap-icons.woff', '/static/fonts/bootstrap-icons.woff')
        
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ 字体路径修改成功")
    except Exception as e:
        print(f"✗ 字体路径修改失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ Bootstrap Icons 下载完成！")
    print("=" * 60)
    print("文件位置:")
    print("  - CSS: static/css/bootstrap-icons.min.css")
    print("  - 字体: static/fonts/bootstrap-icons.woff2")
    print("  - 字体: static/fonts/bootstrap-icons.woff")
    print("\n现在可以在离线环境使用 Bootstrap Icons 了！")
    
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
