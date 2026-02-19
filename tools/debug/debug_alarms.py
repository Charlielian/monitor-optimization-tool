#!/usr/bin/env python3
"""
调试脚本：查看中兴影响性能的告警详情
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.mysql import MySQLClient

def debug_alarms():
    """查看中兴影响性能的告警详情"""
    print("=" * 120)
    print("调试脚本：查看中兴影响性能的告警详情")
    print("=" * 120)
    print()
    
    try:
        # 读取配置文件
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 获取MySQL配置
        mysql_config = config.get('mysql', {})
        
        # 创建MySQL客户端
        mysql_client = MySQLClient(mysql_config)
        
        # 定义影响性能的告警类型
        performance_alarm_types = [
            '小区退服', '小区不可用', '传输中断', '传输故障', '硬件故障',
            '板卡故障', '光模块故障', 'RRU故障', '天馈故障', '驻波比告警',
            '功率异常', '时钟失步', '同步失步', '超级小区CP退服', '超级小区CP退出服务',
            '网元断链', '网元离线', '基站退服', '基站离线', 'gnb断链'
        ]
        
        # 构建告警类型的SQL条件
        alarm_type_conditions = ' OR '.join([f"(alarm_code_name LIKE '%{t}%' OR alarm_title LIKE '%{t}%' OR alarm_reason LIKE '%{t}%')" for t in performance_alarm_types])
        
        # 查询告警数据
        sql = f"""
            SELECT * FROM cur_alarm 
            WHERE {alarm_type_conditions}
            ORDER BY occur_time DESC
        """
        
        print("正在查询告警数据...")
        alarms = mysql_client.fetch_all(sql)
        
        print(f"\n共查询到 {len(alarms)} 条中兴影响性能的告警")
        print("=" * 120)
        
        # 显示前20条告警的详细信息
        print("\n前20条告警详情：")
        print("=" * 120)
        
        for i, alarm in enumerate(alarms[:20], 1):
            print(f"\n{i}. 告警ID: {alarm.get('id', 'N/A')}")
            print(f"   告警名称: {alarm.get('alarm_code_name', '') or alarm.get('alarm_title', '')}")
            print(f"   告警级别: {alarm.get('alarm_level', 'N/A')}")
            print(f"   发生时间: {alarm.get('occur_time', 'N/A')}")
            print(f"   告警对象: {alarm.get('alarm_object_name', 'N/A')}")
            print(f"   网元ID: {alarm.get('ne_id', 'N/A')}")
            print(f"   告警原因: {alarm.get('alarm_reason', 'N/A')[:100]}..." if len(str(alarm.get('alarm_reason', ''))) > 100 else f"   告警原因: {alarm.get('alarm_reason', 'N/A')}")
            print("-" * 120)
        
        # 按告警类型统计
        print("\n告警类型统计：")
        print("=" * 120)
        
        alarm_types = {}
        for alarm in alarms:
            alarm_name = alarm.get('alarm_code_name', '') or alarm.get('alarm_title', '')
            if alarm_name:
                if alarm_name in alarm_types:
                    alarm_types[alarm_name] += 1
                else:
                    alarm_types[alarm_name] = 1
        
        # 按数量排序显示
        sorted_types = sorted(alarm_types.items(), key=lambda x: x[1], reverse=True)
        for alarm_type, count in sorted_types:
            print(f"{alarm_type}: {count} 条")
        
        print("\n" + "=" * 120)
        print("调试完成！")
        print("=" * 120)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_alarms()
