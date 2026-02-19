# -*- coding: utf-8 -*-
"""
独立脚本功能测试
测试 standalone_interference_extractor.py 的各个模块是否正常工作
"""
import sys


def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试1: 模块导入")
    print("=" * 60)
    
    try:
        import standalone_interference_extractor as sie
        print("✓ 主模块导入成功")
        
        # 测试类和函数是否存在
        assert hasattr(sie, 'LoginManager'), "LoginManager 类不存在"
        assert hasattr(sie, 'JXCXQuery'), "JXCXQuery 类不存在"
        assert hasattr(sie, 'InterferenceCellExtractor'), "InterferenceCellExtractor 类不存在"
        assert hasattr(sie, 'quick_extract'), "quick_extract 函数不存在"
        assert hasattr(sie, 'get_5g_interference_payload'), "get_5g_interference_payload 函数不存在"
        assert hasattr(sie, 'get_4g_interference_payload'), "get_4g_interference_payload 函数不存在"
        
        print("✓ 所有必需的类和函数都存在")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_payload_structure():
    """测试payload结构"""
    print("\n" + "=" * 60)
    print("测试2: Payload结构")
    print("=" * 60)
    
    try:
        import standalone_interference_extractor as sie
        
        # 测试5G payload
        payload_5g = sie.get_5g_interference_payload()
        print(f"\n5G Payload:")
        print(f"  表名: {payload_5g['result']['result'][0]['table']}")
        print(f"  字段数: {len(payload_5g['result']['result'])}")
        print(f"  查询条件数: {len(payload_5g['where'])}")
        
        assert 'result' in payload_5g, "5G payload缺少result字段"
        assert 'where' in payload_5g, "5G payload缺少where字段"
        assert len(payload_5g['result']['result']) == 10, "5G payload字段数不正确"
        
        # 测试4G payload
        payload_4g = sie.get_4g_interference_payload()
        print(f"\n4G Payload:")
        print(f"  表名: {payload_4g['result']['result'][0]['table']}")
        print(f"  字段数: {len(payload_4g['result']['result'])}")
        print(f"  查询条件数: {len(payload_4g['where'])}")
        
        assert 'result' in payload_4g, "4G payload缺少result字段"
        assert 'where' in payload_4g, "4G payload缺少where字段"
        assert len(payload_4g['result']['result']) == 9, "4G payload字段数不正确"
        
        print("\n✓ Payload结构验证成功")
        return True
    except Exception as e:
        print(f"\n✗ Payload结构验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_payload_modification():
    """测试payload修改功能"""
    print("\n" + "=" * 60)
    print("测试3: Payload修改功能")
    print("=" * 60)
    
    try:
        import standalone_interference_extractor as sie
        
        payload = sie.get_5g_interference_payload()
        
        # 测试时间设置
        start_time = '2025-01-01 00:00:00'
        end_time = '2025-01-31 23:59:59'
        payload = sie.set_payload_time(payload, start_time, end_time)
        
        time_conditions = [c for c in payload['where'] if c['feild'] == 'starttime']
        assert len(time_conditions) == 2, "时间条件数量不正确"
        
        start_cond = [c for c in time_conditions if c['symbol'] == '>='][0]
        end_cond = [c for c in time_conditions if c['symbol'] == '<'][0]
        
        assert start_cond['val'] == start_time, "开始时间设置不正确"
        assert end_cond['val'] == end_time, "结束时间设置不正确"
        
        print(f"✓ 时间设置正确:")
        print(f"  开始时间: {start_cond['val']}")
        print(f"  结束时间: {end_cond['val']}")
        
        # 测试城市设置
        city = '广州'
        payload = sie.set_payload_city(payload, city)
        
        city_condition = [c for c in payload['where'] if c['feild'] == 'city'][0]
        assert city_condition['val'] == city, "城市设置不正确"
        
        print(f"✓ 城市设置正确: {city_condition['val']}")
        
        print("\n✓ Payload修改功能验证成功")
        return True
    except Exception as e:
        print(f"\n✗ Payload修改功能验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_creation():
    """测试目录创建功能"""
    print("\n" + "=" * 60)
    print("测试4: 目录创建功能")
    print("=" * 60)
    
    try:
        import standalone_interference_extractor as sie
        import os
        
        sie.ensure_dirs()
        
        dirs = [sie.OUTPUT_DIR, sie.COOKIE_DIR, sie.CAPTCHA_DIR]
        
        for dir_path in dirs:
            if os.path.exists(dir_path):
                print(f"✓ {dir_path} 已创建")
            else:
                print(f"✗ {dir_path} 创建失败")
                return False
        
        print("\n✓ 目录创建功能验证成功")
        return True
    except Exception as e:
        print(f"\n✗ 目录创建功能验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_initialization():
    """测试类初始化"""
    print("\n" + "=" * 60)
    print("测试5: 类初始化")
    print("=" * 60)
    
    try:
        import standalone_interference_extractor as sie
        
        # 测试LoginManager
        login_mgr = sie.LoginManager()
        print(f"✓ LoginManager 初始化成功")
        print(f"  用户名: {login_mgr.username}")
        
        # 测试InterferenceCellExtractor
        extractor = sie.InterferenceCellExtractor()
        print(f"✓ InterferenceCellExtractor 初始化成功")
        
        # 测试自定义账号
        extractor_custom = sie.InterferenceCellExtractor(
            username='test_user',
            password='test_pass'
        )
        print(f"✓ 自定义账号初始化成功")
        print(f"  用户名: {extractor_custom.username}")
        
        print("\n✓ 类初始化验证成功")
        return True
    except Exception as e:
        print(f"\n✗ 类初始化验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """测试配置"""
    print("\n" + "=" * 60)
    print("测试6: 配置检查")
    print("=" * 60)
    
    try:
        import standalone_interference_extractor as sie
        
        print(f"配置信息:")
        print(f"  默认用户名: {sie.DEFAULT_USERNAME}")
        print(f"  基础URL: {sie.BASE_URL}")
        print(f"  输出目录: {sie.OUTPUT_DIR}")
        print(f"  Cookie目录: {sie.COOKIE_DIR}")
        print(f"  验证码目录: {sie.CAPTCHA_DIR}")
        
        # 检查URL配置
        assert sie.BASE_URL.startswith('https://'), "BASE_URL应该使用HTTPS"
        assert 'nqi.gmcc.net' in sie.BASE_URL, "BASE_URL域名不正确"
        
        print("\n✓ 配置检查通过")
        return True
    except Exception as e:
        print(f"\n✗ 配置检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("独立脚本功能测试套件")
    print("=" * 60 + "\n")
    
    tests = [
        ("模块导入", test_imports),
        ("Payload结构", test_payload_structure),
        ("Payload修改功能", test_payload_modification),
        ("目录创建功能", test_directory_creation),
        ("类初始化", test_class_initialization),
        ("配置检查", test_configuration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{test_name}' 执行异常: {e}")
            results.append((test_name, False))
    
    # 显示测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！脚本可以正常使用。")
        print("\n下一步:")
        print("  运行: python standalone_interference_extractor.py")
        print("  或在代码中调用: from standalone_interference_extractor import quick_extract")
    else:
        print("\n⚠️ 部分测试失败，请检查脚本。")
    
    print("=" * 60 + "\n")


if __name__ == '__main__':
    run_all_tests()
