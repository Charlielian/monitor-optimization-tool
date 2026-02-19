#!/usr/bin/env python
"""验证告警监控功能配置"""
import json
import os
import sys

def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}不存在: {filepath}")
        return False

def check_config():
    """检查配置文件"""
    print("\n" + "=" * 60)
    print("1. 检查配置文件")
    print("=" * 60)
    
    if not check_file_exists('config.json', 'config.json'):
        return False
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if 'mysql_config' not in config:
            print("✗ config.json中缺少mysql_config配置")
            return False
        
        mysql_config = config['mysql_config']
        required_keys = ['host', 'port', 'database', 'user', 'password']
        
        for key in required_keys:
            if key not in mysql_config:
                print(f"✗ mysql_config中缺少{key}配置")
                return False
        
        print("✓ config.json配置完整")
        print(f"  - Host: {mysql_config['host']}")
        print(f"  - Port: {mysql_config['port']}")
        print(f"  - Database: {mysql_config['database']}")
        print(f"  - User: {mysql_config['user']}")
        
        return True
    except Exception as e:
        print(f"✗ 读取config.json失败: {e}")
        return False

def check_core_files():
    """检查核心文件"""
    print("\n" + "=" * 60)
    print("2. 检查核心文件")
    print("=" * 60)
    
    files = [
        ('services/alarm_service.py', '告警服务类'),
        ('templates/alarm.html', '告警页面模板'),
        ('app.py', '主应用文件'),
    ]
    
    all_exist = True
    for filepath, description in files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist

def check_test_files():
    """检查测试文件"""
    print("\n" + "=" * 60)
    print("3. 检查测试文件")
    print("=" * 60)
    
    files = [
        ('test_alarm_service.py', '服务测试脚本'),
        ('temp/scripts/insert_alarm_test_data.py', '数据插入脚本'),
        ('temp/scripts/create_alarm_test_data.sql', 'SQL测试脚本'),
    ]
    
    all_exist = True
    for filepath, description in files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist

def check_docs():
    """检查文档文件"""
    print("\n" + "=" * 60)
    print("4. 检查文档文件")
    print("=" * 60)
    
    files = [
        ('README_ALARM.md', '快速使用指南'),
        ('ALARM_CONFIG_UPDATE.md', '配置说明'),
        ('ALARM_UPDATE_SUMMARY.md', '更新总结'),
        ('temp/docs/ALARM_MONITORING_GUIDE.md', '完整功能说明'),
        ('temp/docs/ALARM_QUICKSTART.md', '快速启动指南'),
        ('temp/docs/ALARM_FEATURE_SUMMARY.md', '功能实现总结'),
    ]
    
    all_exist = True
    for filepath, description in files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist

def check_imports():
    """检查Python导入"""
    print("\n" + "=" * 60)
    print("5. 检查Python依赖")
    print("=" * 60)
    
    try:
        import json
        print("✓ json模块")
    except ImportError:
        print("✗ json模块")
        return False
    
    try:
        from db.mysql import MySQLClient
        print("✓ MySQLClient类")
    except ImportError as e:
        print(f"✗ MySQLClient类: {e}")
        return False
    
    try:
        from services.alarm_service import AlarmService
        print("✓ AlarmService类")
    except ImportError as e:
        print(f"✗ AlarmService类: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("告警监控功能配置验证")
    print("=" * 60)
    
    results = []
    
    # 检查配置
    results.append(("配置文件", check_config()))
    
    # 检查核心文件
    results.append(("核心文件", check_core_files()))
    
    # 检查测试文件
    results.append(("测试文件", check_test_files()))
    
    # 检查文档
    results.append(("文档文件", check_docs()))
    
    # 检查导入
    results.append(("Python依赖", check_imports()))
    
    # 总结
    print("\n" + "=" * 60)
    print("验证结果总结")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有检查通过！")
        print("=" * 60)
        print("\n下一步:")
        print("1. 运行测试: python test_alarm_service.py")
        print("2. 插入数据: python temp/scripts/insert_alarm_test_data.py")
        print("3. 启动应用: python app.py")
        print("4. 访问页面: http://127.0.0.1:5000/alarm")
        return 0
    else:
        print("✗ 部分检查失败，请修复后重试")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
