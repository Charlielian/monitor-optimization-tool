"""
启用 Flask 响应压缩
减少传输数据量，提升加载速度
"""

from flask import Flask
from flask_compress import Compress


def enable_compression(app: Flask, config: dict = None):
    """
    为 Flask 应用启用 gzip 压缩
    
    Args:
        app: Flask 应用实例
        config: 压缩配置字典
    
    Returns:
        Compress 实例
    """
    # 默认配置
    default_config = {
        'COMPRESS_MIMETYPES': [
            'text/html',
            'text/css',
            'text/xml',
            'text/plain',
            'text/javascript',
            'application/json',
            'application/javascript',
            'application/xml',
            'application/xhtml+xml',
            'application/rss+xml',
            'application/atom+xml',
            'image/svg+xml',
        ],
        'COMPRESS_LEVEL': 6,  # 压缩级别 1-9，6是平衡点
        'COMPRESS_MIN_SIZE': 500,  # 最小压缩大小（字节）
        'COMPRESS_CACHE_KEY': None,
        'COMPRESS_CACHE_BACKEND': None,
        'COMPRESS_REGISTER': True,
        'COMPRESS_ALGORITHM': 'gzip',  # 或 'br' (Brotli)
    }
    
    # 合并用户配置
    if config:
        default_config.update(config)
    
    # 应用配置
    for key, value in default_config.items():
        app.config[key] = value
    
    # 初始化压缩
    compress = Compress(app)
    
    print("✓ Flask 响应压缩已启用")
    print(f"  - 压缩级别: {app.config['COMPRESS_LEVEL']}")
    print(f"  - 最小压缩大小: {app.config['COMPRESS_MIN_SIZE']} 字节")
    print(f"  - 压缩算法: {app.config['COMPRESS_ALGORITHM']}")
    
    return compress


def install_flask_compress():
    """
    安装 flask-compress 包的说明
    """
    print("""
    要启用压缩，需要安装 flask-compress:
    
    pip install flask-compress
    
    或添加到 requirements.txt:
    flask-compress==1.14
    """)


# 在 app.py 中使用示例
"""
from enable_compression import enable_compression

app = Flask(__name__)

# 启用压缩
enable_compression(app)

# 或使用自定义配置
enable_compression(app, {
    'COMPRESS_LEVEL': 9,  # 最高压缩率
    'COMPRESS_MIN_SIZE': 1000,
})
"""


# 性能对比示例
"""
未压缩：
- HTML: 50KB
- CSS: 200KB
- JavaScript: 500KB
- JSON: 100KB
总计: 850KB

启用 gzip 压缩后：
- HTML: 10KB (80% 压缩)
- CSS: 40KB (80% 压缩)
- JavaScript: 150KB (70% 压缩)
- JSON: 20KB (80% 压缩)
总计: 220KB

节省: 630KB (74%)
加载时间: 从 8.5秒 降至 2.2秒 (假设 100KB/s 网速)
"""


if __name__ == "__main__":
    install_flask_compress()
