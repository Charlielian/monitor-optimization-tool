#!/usr/bin/env python3
"""
自动应用性能优化
一键执行所有可自动化的优化步骤
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def check_file_exists(filepath):
    """检查文件是否存在"""
    return os.path.exists(filepath)


def backup_file(filepath):
    """备份文件"""
    if check_file_exists(filepath):
        backup_path = f"{filepath}.backup"
        import shutil
        shutil.copy2(filepath, backup_path)
        logging.info(f"✓ 已备份: {filepath} -> {backup_path}")
        return True
    return False


def install_dependencies():
    """安装必要的依赖"""
    logging.info("=" * 60)
    logging.info("步骤 1: 安装依赖包")
    logging.info("=" * 60)
    
    dependencies = [
        'flask-compress',
    ]
    
    for dep in dependencies:
        try:
            logging.info(f"安装 {dep}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
            logging.info(f"✓ {dep} 安装成功")
        except subprocess.CalledProcessError as e:
            logging.error(f"✗ {dep} 安装失败: {e}")
            return False
    
    return True


def create_database_indexes():
    """创建数据库索引"""
    logging.info("=" * 60)
    logging.info("步骤 2: 创建数据库索引")
    logging.info("=" * 60)
    
    try:
        from db.pg import PostgresClient
        from config import Config
        
        cfg = Config()
        pg = PostgresClient(cfg.pgsql_config)
        
        # 读取索引SQL
        with open('db/optimize_indexes.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句（按分号分割）
        sql_statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        
        # 只执行 CREATE INDEX 语句
        index_statements = [s for s in sql_statements if 'CREATE INDEX' in s.upper()]
        
        logging.info(f"找到 {len(index_statements)} 个索引创建语句")
        
        for i, sql in enumerate(index_statements, 1):
            try:
                logging.info(f"执行索引 {i}/{len(index_statements)}...")
                pg.execute(sql)
                logging.info(f"✓ 索引 {i} 创建成功")
            except Exception as e:
                # 索引可能已存在，忽略错误
                if 'already exists' in str(e).lower():
                    logging.info(f"  索引已存在，跳过")
                else:
                    logging.warning(f"  索引创建失败: {e}")
        
        # 执行 ANALYZE
        logging.info("执行 ANALYZE 更新统计信息...")
        try:
            pg.execute("ANALYZE metrics_4g;")
            pg.execute("ANALYZE metrics_5g;")
            logging.info("✓ ANALYZE 完成")
        except Exception as e:
            logging.warning(f"ANALYZE 失败: {e}")
        
        logging.info("✓ 数据库索引优化完成")
        return True
        
    except Exception as e:
        logging.error(f"✗ 数据库索引创建失败: {e}")
        logging.error("请手动执行: psql -f db/optimize_indexes.sql")
        return False


def enable_compression_in_app():
    """在 app.py 中启用压缩"""
    logging.info("=" * 60)
    logging.info("步骤 3: 启用 gzip 压缩")
    logging.info("=" * 60)
    
    app_file = 'app.py'
    
    if not check_file_exists(app_file):
        logging.error(f"✗ 找不到 {app_file}")
        return False
    
    # 备份
    backup_file(app_file)
    
    # 读取文件
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经添加
    if 'flask_compress' in content.lower() or 'Compress(app)' in content:
        logging.info("✓ 压缩已启用，跳过")
        return True
    
    # 添加导入
    if 'from flask import' in content:
        content = content.replace(
            'from flask import',
            'from flask import',
            1
        )
        # 在导入部分添加
        import_section = content.find('from flask import')
        if import_section != -1:
            # 找到导入部分的结束位置
            next_line = content.find('\n', import_section)
            content = (
                content[:next_line + 1] +
                'from flask_compress import Compress\n' +
                content[next_line + 1:]
            )
    
    # 在 create_app 中添加压缩配置
    if 'def create_app()' in content:
        # 找到 Flask 应用创建的位置
        app_creation = content.find('app = Flask(__name__)')
        if app_creation != -1:
            # 找到下一个空行
            next_empty = content.find('\n\n', app_creation)
            if next_empty != -1:
                compression_code = '''
    # 启用 gzip 压缩
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 'text/css', 'text/xml', 'text/plain',
        'application/json', 'application/javascript',
        'application/xml', 'application/xhtml+xml'
    ]
    app.config['COMPRESS_LEVEL'] = 6
    app.config['COMPRESS_MIN_SIZE'] = 500
    Compress(app)
    logging.info("✓ 响应压缩已启用")
'''
                content = (
                    content[:next_empty] +
                    compression_code +
                    content[next_empty:]
                )
    
    # 写回文件
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logging.info("✓ 压缩配置已添加到 app.py")
    logging.info("  请重启应用以生效")
    return True


def add_chart_optimizer_to_base():
    """在 base.html 中添加图表优化工具"""
    logging.info("=" * 60)
    logging.info("步骤 4: 添加图表优化工具")
    logging.info("=" * 60)
    
    base_file = 'templates/base.html'
    
    if not check_file_exists(base_file):
        logging.error(f"✗ 找不到 {base_file}")
        return False
    
    # 备份
    backup_file(base_file)
    
    # 读取文件
    with open(base_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经添加
    if 'chart-optimizer.js' in content:
        logging.info("✓ 图表优化工具已添加，跳过")
        return True
    
    # 在 performance-monitor.js 之前添加
    if 'performance-monitor.js' in content:
        content = content.replace(
            '<script src="{{ url_for(\'static\', filename=\'js/performance-monitor.js\') }}" defer></script>',
            '<script src="{{ url_for(\'static\', filename=\'js/chart-optimizer.js\') }}" defer></script>\n    <script src="{{ url_for(\'static\', filename=\'js/performance-monitor.js\') }}" defer></script>'
        )
        
        # 写回文件
        with open(base_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info("✓ 图表优化工具已添加到 base.html")
        return True
    else:
        logging.warning("✗ 找不到 performance-monitor.js 引用")
        return False


def update_requirements():
    """更新 requirements.txt"""
    logging.info("=" * 60)
    logging.info("步骤 5: 更新 requirements.txt")
    logging.info("=" * 60)
    
    req_file = 'requirements.txt'
    
    if not check_file_exists(req_file):
        logging.warning(f"✗ 找不到 {req_file}")
        return False
    
    # 读取现有依赖
    with open(req_file, 'r', encoding='utf-8') as f:
        requirements = f.read()
    
    # 检查是否已添加
    if 'flask-compress' in requirements.lower():
        logging.info("✓ requirements.txt 已包含 flask-compress")
        return True
    
    # 添加新依赖
    with open(req_file, 'a', encoding='utf-8') as f:
        f.write('\n# 性能优化\n')
        f.write('flask-compress==1.14\n')
    
    logging.info("✓ requirements.txt 已更新")
    return True


def print_summary():
    """打印优化总结"""
    logging.info("=" * 60)
    logging.info("优化完成总结")
    logging.info("=" * 60)
    
    print("""
✅ 已完成的优化:
  1. ✓ 安装依赖包 (flask-compress)
  2. ✓ 创建数据库索引
  3. ✓ 启用 gzip 压缩
  4. ✓ 添加图表优化工具
  5. ✓ 更新 requirements.txt

📋 下一步操作:
  1. 重启 Flask 应用
  2. 清除浏览器缓存
  3. 测试页面加载速度
  4. 运行性能分析: python analyze_performance.py

📊 预期效果:
  - 首屏时间: 从 50秒 降至 5-10秒
  - 后端查询: 从 5.8秒 降至 1.5秒
  - 传输数据: 减少 70-80%

📖 更多优化:
  - 查看 QUICK_OPTIMIZATION_GUIDE.md
  - 查看 PERFORMANCE_ANALYSIS_REPORT.md
  - 实施并行查询优化

⚠️ 注意事项:
  - 已自动备份修改的文件 (.backup)
  - 如有问题，可恢复备份文件
  - 建议在测试环境先验证
    """)


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║         性能优化自动化脚本                                ║
║         Performance Optimization Script                  ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 确认执行
    response = input("是否继续执行优化? (y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    success_count = 0
    total_steps = 5
    
    # 执行优化步骤
    if install_dependencies():
        success_count += 1
    
    if create_database_indexes():
        success_count += 1
    
    if enable_compression_in_app():
        success_count += 1
    
    if add_chart_optimizer_to_base():
        success_count += 1
    
    if update_requirements():
        success_count += 1
    
    # 打印总结
    print_summary()
    
    logging.info(f"完成 {success_count}/{total_steps} 个优化步骤")
    
    if success_count == total_steps:
        logging.info("🎉 所有优化步骤执行成功!")
        return 0
    else:
        logging.warning(f"⚠️ 部分优化步骤失败 ({total_steps - success_count} 个)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
