#!/usr/bin/env python3
"""
下载静态资源脚本
在有网络的环境下运行此脚本，将资源下载到本地
"""
import os
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STATIC_DIR = SCRIPT_DIR / "static"

# 创建必要的目录
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

RESOURCES = [
    {
        "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
        "path": STATIC_DIR / "css" / "bootstrap.min.css",
        "name": "Bootstrap CSS"
    },
    {
        "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
        "path": STATIC_DIR / "js" / "bootstrap.bundle.min.js",
        "name": "Bootstrap JS"
    },
    {
        "url": "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js",
        "path": STATIC_DIR / "js" / "chart.umd.min.js",
        "name": "Chart.js"
    }
]

def download_file(url, path, name):
    """下载文件"""
    print(f"下载 {name}...")
    try:
        urllib.request.urlretrieve(url, path)
        print(f"✅ {name} 下载完成: {path}")
        return True
    except Exception as e:
        print(f"❌ {name} 下载失败: {e}")
        return False

if __name__ == "__main__":
    print("开始下载静态资源...\n")
    
    success_count = 0
    for resource in RESOURCES:
        if download_file(resource["url"], resource["path"], resource["name"]):
            success_count += 1
        print()
    
    print(f"完成！成功下载 {success_count}/{len(RESOURCES)} 个文件")
    if success_count == len(RESOURCES):
        print("\n所有资源已下载到 static 目录，现在可以在无网络环境下使用。")
    else:
        print("\n部分资源下载失败，请检查网络连接后重试。")

