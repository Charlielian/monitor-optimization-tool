# -*- coding: utf-8 -*-
"""
干扰小区提取功能测试脚本
用于测试登录和数据提取功能是否正常
"""
import os
import sys

# 添加项目路径
project_path = os.path.join(os.getcwd(), 'WNCOP-20250303-debug')
sys.path.insert(0, project_path)


def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试1: 模块导入")
    print("=" * 60)
    
    try:
        from feature.login import Login
        print("✓ Login 模块导入成功")
    except Exception as e:
        print(f"✗ Login 模块导入失败: {e}")
        return False
    
    try:
        from feature.get_data.JXCX import entry
        print("✓ JXCX entry 模块导入成功")
    except Exception as e:
        print(f"✗ JXCX entry 模块导入失败: {e}")
        return False
    
    try:
        from feature.get_data.JXCX.payload import ganrao_NR, ganrao_LTE, set_where
        print("✓ Payload 模块导入成功")
    except Exception as e:
        print(f"✗ Payload 模块导入失败: {e}")
        return False
    
    print("\n✓ 所有模块导入成功\n")
    return True


def test_payload_structure():
    """测试payload数据结构"""
    print("=" * 60)
    print("测试2: Payload数据结构")
    print("=" * 60)
    
    try:
        from feature.get_data.JXCX.payload import ganrao_NR, ganrao_LTE
        
        # 测试5G payload
        payload_5g = ganrao_NR.data_d
        print(f"\n5G Payload 结构:")
        print(f"  - 表名: {payload_5g['result']['result'][0]['table']}")
        print(f"  - 字段数: {len(payload_5g['result']['result'])}")
        print(f"  - 查询条件数: {len(payload_5g['where'])}")
        
        # 显示字段列表
        print(f"\n  字段列表:")
        for field in payload_5g['result']['result']:
            print(f"    - {field['feildName']}: {field['feild']}")
        
        # 测试4G payload
        payload_4g = ganrao_LTE.data_d
        print(f"\n4G Payload 结构:")
        print(f"  - 表名: {payload_4g['result']['result'][0]['table']}")
        print(f"  - 字段数: {len(payload_4g['result']['result'])}")
        print(f"  - 查询条件数: {len(payload_4g['where'])}")
        
        print(f"\n  字段列表:")
        for field in payload_4g['result']['result']:
            print(f"    - {field['feildName']}: {field['feild']}")
        
        print("\n✓ Payload结构验证成功\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Payload结构验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_set_where():
    """测试查询条件设置"""
    print("=" * 60)
    print("测试3: 查询条件设置")
    print("=" * 60)
    
    try:
        from feature.get_data.JXCX.payload import ganrao_NR, set_where
        
        payload = ganrao_NR.data_d.copy()
        print(f"\n原始查询条件:")
        for condition in payload['where']:
            print(f"  {condition['feild']} {condition['symbol']} {condition['val']}")
        
        # 设置新的时间范围
        start_time = '2025-01-13 00:00:00'
        end_time = '2025-01-19 23:59:59'
        payload = set_where.set_where(payload, start_time, end_time)
        
        print(f"\n修改后查询条件:")
        for condition in payload['where']:
            print(f"  {condition['feild']} {condition['symbol']} {condition['val']}")
        
        # 验证时间是否正确设置
        time_conditions = [c for c in payload['where'] if c['feild'] == 'starttime']
        if len(time_conditions) == 2:
            print(f"\n✓ 时间条件设置成功")
            return True
        else:
            print(f"\n✗ 时间条件设置失败")
            return False
            
    except Exception as e:
        print(f"\n✗ 查询条件设置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_structure():
    """测试目录结构"""
    print("=" * 60)
    print("测试4: 目录结构")
    print("=" * 60)
    
    required_dirs = [
        'WNCOP-20250303-debug',
        'WNCOP-20250303-debug/feature',
        'WNCOP-20250303-debug/feature/login',
        'WNCOP-20250303-debug/feature/get_data',
        'WNCOP-20250303-debug/feature/get_data/JXCX',
        'WNCOP-20250303-debug/feature/get_data/JXCX/payload',
        'WNCOP-20250303-debug/data',
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} (不存在)")
            all_exist = False
    
    # 创建必要的输出目录
    output_dirs = [
        'WNCOP-20250303-debug/data/out',
        'WNCOP-20250303-debug/data/cookies',
        'WNCOP-20250303-debug/data/验证码',
    ]
    
    print(f"\n创建输出目录:")
    for dir_path in output_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ {dir_path}")
    
    if all_exist:
        print("\n✓ 目录结构验证成功\n")
        return True
    else:
        print("\n✗ 部分目录不存在\n")
        return False


def test_login_module():
    """测试登录模块（不实际登录）"""
    print("=" * 60)
    print("测试5: 登录模块初始化")
    print("=" * 60)
    
    try:
        from feature.login import Login
        
        # 创建登录对象（不执行登录）
        login_obj = Login.Login()
        
        print(f"\n登录配置:")
        print(f"  - 用户名: {login_obj.username}")
        print(f"  - 登录URL: {login_obj.login_url}")
        print(f"  - 验证码URL: {login_obj.captcha_url}")
        print(f"  - 验证码目录: {login_obj.captcha_dir}")
        
        print("\n✓ 登录模块初始化成功")
        print("⚠ 注意: 未执行实际登录操作\n")
        return True
        
    except Exception as e:
        print(f"\n✗ 登录模块初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_extractor_class():
    """测试提取器类"""
    print("=" * 60)
    print("测试6: 提取器类初始化")
    print("=" * 60)
    
    try:
        from get_interference_cells import InterferenceCellExtractor
        
        extractor = InterferenceCellExtractor()
        
        print(f"\n提取器属性:")
        print(f"  - username: {extractor.username}")
        print(f"  - password: {'*' * len(extractor.password) if extractor.password else None}")
        print(f"  - login_obj: {extractor.login_obj}")
        print(f"  - jxcx: {extractor.jxcx}")
        
        print("\n✓ 提取器类初始化成功\n")
        return True
        
    except Exception as e:
        print(f"\n✗ 提取器类初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("干扰小区提取功能测试套件")
    print("=" * 60 + "\n")
    
    tests = [
        ("模块导入", test_imports),
        ("Payload数据结构", test_payload_structure),
        ("查询条件设置", test_set_where),
        ("目录结构", test_directory_structure),
        ("登录模块初始化", test_login_module),
        ("提取器类初始化", test_extractor_class),
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
        print("\n🎉 所有测试通过！可以开始使用干扰小区提取功能。")
        print("\n下一步:")
        print("  1. 运行 python quick_extract_interference.py 快速提取数据")
        print("  2. 或运行 python get_interference_cells.py 使用完整功能")
    else:
        print("\n⚠️ 部分测试失败，请检查环境配置。")
    
    print("=" * 60 + "\n")


if __name__ == '__main__':
    run_all_tests()
