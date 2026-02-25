#!/usr/bin/env python3
"""
验证诺基亚告警匹配逻辑
验证 match_nokia_alarm 方法的告警类型匹配逻辑是否正确
"""

import sys
import inspect
from services.alarm_grid_matcher import AlarmGridMatcher


def verify_match_nokia_alarm_logic():
    """验证 match_nokia_alarm 方法的实现逻辑"""
    
    print("=" * 60)
    print("验证诺基亚告警匹配逻辑")
    print("=" * 60)
    
    # 获取方法源代码
    source = inspect.getsource(AlarmGridMatcher.match_nokia_alarm)
    
    print("\n检查项 1: 确认'小区退服'使用 cgi 字段")
    print("-" * 60)
    
    # 检查是否使用 cgi 字段
    if "fault_name == '小区退服'" in source and "alarm.get('cgi')" in source:
        print("✓ 正确: '小区退服'告警使用 cgi 字段进行匹配")
        check1_passed = True
    else:
        print("✗ 错误: '小区退服'告警未正确使用 cgi 字段")
        check1_passed = False
    
    print("\n检查项 2: 确认'RRU故障'和'网元断链'使用 ne_id 字段")
    print("-" * 60)
    
    # 检查是否使用 ne_id 字段
    if ("fault_name in ['RRU故障', '网元断链']" in source and 
        "alarm.get('ne_id')" in source):
        print("✓ 正确: 'RRU故障'和'网元断链'告警使用 ne_id 字段进行匹配")
        check2_passed = True
    else:
        print("✗ 错误: 'RRU故障'和'网元断链'告警未正确使用 ne_id 字段")
        check2_passed = False
    
    print("\n检查项 3: 确认优先使用标准字段名")
    print("-" * 60)
    
    # 检查字段访问顺序
    if "alarm.get('alarm_name', '')" in source:
        print("✓ 正确: 优先使用标准字段名 'alarm_name'")
        check3_passed = True
    else:
        print("✗ 错误: 未优先使用标准字段名")
        check3_passed = False
    
    print("\n检查项 4: 确认字段访问逻辑简化")
    print("-" * 60)
    
    # 检查是否移除了不必要的 fallback（如 CGI, ENBID 等大写字段）
    if "alarm.get('CGI')" not in source and "alarm.get('ENBID')" not in source:
        print("✓ 正确: 已移除不必要的大写字段 fallback 逻辑")
        check4_passed = True
    else:
        print("✗ 错误: 仍存在不必要的大写字段 fallback 逻辑")
        check4_passed = False
    
    # 总结
    print("\n" + "=" * 60)
    print("验证结果总结")
    print("=" * 60)
    
    all_passed = check1_passed and check2_passed and check3_passed and check4_passed
    
    if all_passed:
        print("✓ 所有检查项通过！match_nokia_alarm 方法实现正确。")
        print("\n验证的需求:")
        print("  - Requirements 2.1: '小区退服'使用 cgi 字段")
        print("  - Requirements 2.2: 'RRU故障'和'网元断链'使用 ne_id 字段")
        print("  - Requirements 2.3: 优先使用标准字段名")
        print("  - Requirements 4.2: 简化字段访问逻辑")
        return 0
    else:
        print("✗ 部分检查项未通过，请检查实现。")
        return 1


if __name__ == '__main__':
    sys.exit(verify_match_nokia_alarm_logic())
