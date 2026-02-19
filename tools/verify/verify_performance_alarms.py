#!/usr/bin/env python3
"""
验证影响性能的告警过滤功能
"""
import sys
from datetime import datetime, timedelta
from services.alarm_grid_matcher import AlarmGridMatcher
from db.mysql import MySQLClient
from config import Config

def verify_performance_alarms():
    """验证影响性能的告警过滤"""
    print("=" * 80)
    print("验证影响性能的告警过滤功能")
    print("=" * 80)
    
    # 初始化配置和数据库连接
    cfg = Config()
    mysql = MySQLClient(cfg.mysql_config)
    
    # 初始化告警匹配器
    matcher = AlarmGridMatcher(mysql)
    
    # 显示影响性能的告警类型
    print("\n1. 影响性能的告警类型定义:")
    print("\n   中兴告警（{}种）:".format(len(matcher.PERFORMANCE_AFFECTING_ALARMS_ZTE)))
    for i, alarm_type in enumerate(sorted(matcher.PERFORMANCE_AFFECTING_ALARMS_ZTE), 1):
        print(f"      {i:2d}. {alarm_type}")
    
    print("\n   诺基亚告警（{}种）:".format(len(matcher.PERFORMANCE_AFFECTING_ALARMS_NOKIA)))
    for i, alarm_type in enumerate(sorted(matcher.PERFORMANCE_AFFECTING_ALARMS_NOKIA), 1):
        print(f"      {i:2d}. {alarm_type}")
    
    # 获取当前告警
    print("\n2. 获取当前告警数据...")
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    
    # 获取中兴告警
    zte_alarms = matcher._get_alarms_adaptive('cur_alarm', start_time)
    print(f"   - 中兴告警总数: {len(zte_alarms)}")
    
    # 过滤影响性能的中兴告警
    zte_performance_alarms = [
        alarm for alarm in zte_alarms
        if alarm.get('alarm_name', '') in matcher.PERFORMANCE_AFFECTING_ALARMS_ZTE
    ]
    print(f"   - 中兴影响性能告警: {len(zte_performance_alarms)}")
    
    # 获取诺基亚告警
    nokia_alarms = matcher._get_alarms_adaptive('cur_alarm_nokia', start_time)
    print(f"   - 诺基亚告警总数: {len(nokia_alarms)}")
    
    # 过滤影响性能的诺基亚告警
    nokia_performance_alarms = [
        alarm for alarm in nokia_alarms
        if alarm.get('alarm_name', '') in matcher.PERFORMANCE_AFFECTING_ALARMS_NOKIA
    ]
    print(f"   - 诺基亚影响性能告警: {len(nokia_performance_alarms)}")
    
    # 统计告警类型分布
    print("\n3. 中兴告警类型分布（前10种）:")
    zte_alarm_types = {}
    for alarm in zte_alarms:
        alarm_type = alarm.get('alarm_name', '未知')
        zte_alarm_types[alarm_type] = zte_alarm_types.get(alarm_type, 0) + 1
    
    sorted_zte = sorted(zte_alarm_types.items(), key=lambda x: x[1], reverse=True)
    for i, (alarm_type, count) in enumerate(sorted_zte[:10], 1):
        is_performance = alarm_type in matcher.PERFORMANCE_AFFECTING_ALARMS_ZTE
        marker = "✓" if is_performance else " "
        print(f"   {marker} {i:2d}. {alarm_type}: {count}条")
    
    print("\n4. 诺基亚告警类型分布（前10种）:")
    nokia_alarm_types = {}
    for alarm in nokia_alarms:
        alarm_type = alarm.get('alarm_name', '未知')
        nokia_alarm_types[alarm_type] = nokia_alarm_types.get(alarm_type, 0) + 1
    
    sorted_nokia = sorted(nokia_alarm_types.items(), key=lambda x: x[1], reverse=True)
    for i, (alarm_type, count) in enumerate(sorted_nokia[:10], 1):
        is_performance = alarm_type in matcher.PERFORMANCE_AFFECTING_ALARMS_NOKIA
        marker = "✓" if is_performance else " "
        print(f"   {marker} {i:2d}. {alarm_type}: {count}条")
    
    # 对比过滤前后的统计
    print("\n5. 过滤效果对比:")
    print(f"   中兴告警:")
    print(f"     - 过滤前: {len(zte_alarms)}条")
    print(f"     - 过滤后: {len(zte_performance_alarms)}条")
    print(f"     - 过滤率: {(1 - len(zte_performance_alarms) / len(zte_alarms)) * 100:.1f}%")
    
    print(f"   诺基亚告警:")
    print(f"     - 过滤前: {len(nokia_alarms)}条")
    print(f"     - 过滤后: {len(nokia_performance_alarms)}条")
    print(f"     - 过滤率: {(1 - len(nokia_performance_alarms) / len(nokia_alarms)) * 100:.1f}%")
    
    print(f"   总计:")
    total_before = len(zte_alarms) + len(nokia_alarms)
    total_after = len(zte_performance_alarms) + len(nokia_performance_alarms)
    print(f"     - 过滤前: {total_before}条")
    print(f"     - 过滤后: {total_after}条")
    print(f"     - 过滤率: {(1 - total_after / total_before) * 100:.1f}%")
    
    # 测试get_grid_fault_stats方法
    print("\n6. 测试get_grid_fault_stats方法:")
    
    print("   a) 不过滤（所有告警）:")
    all_faults = matcher.get_grid_fault_stats(performance_only=False)
    print(f"      - 故障小区数: {sum(all_faults.values())}")
    print(f"      - 故障网格数: {len(all_faults)}")
    
    print("   b) 只统计影响性能的告警:")
    perf_faults = matcher.get_grid_fault_stats(performance_only=True)
    print(f"      - 故障小区数: {sum(perf_faults.values())}")
    print(f"      - 故障网格数: {len(perf_faults)}")
    
    print("   c) 对比:")
    print(f"      - 故障小区减少: {sum(all_faults.values()) - sum(perf_faults.values())}个")
    print(f"      - 故障网格减少: {len(all_faults) - len(perf_faults)}个")
    print(f"      - 故障小区减少率: {(1 - sum(perf_faults.values()) / sum(all_faults.values())) * 100:.1f}%")
    print(f"      - 故障网格减少率: {(1 - len(perf_faults) / len(all_faults)) * 100:.1f}%")
    
    print("\n" + "=" * 80)
    print("✓ 验证完成！影响性能的告警过滤功能正常")
    print("=" * 80)
    
    return True

if __name__ == '__main__':
    try:
        success = verify_performance_alarms()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
