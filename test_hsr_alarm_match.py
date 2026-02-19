#!/usr/bin/env python3
"""
测试高铁小区告警匹配脚本

此脚本用于测试高铁小区告警匹配逻辑，特别是针对RRU断链告警的匹配
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.hsr_health_check import HSRHealthCheckService
from db.mysql import MySQLClient


def test_hsr_alarm_match():
    """
    测试高铁小区告警匹配
    """
    print("开始测试高铁小区告警匹配...")
    
    # 初始化MySQL客户端
    mysql_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "password",
        "database": "monitor_db"
    }
    
    try:
        mysql_client = MySQLClient(mysql_config)
        print("MySQL客户端初始化成功")
    except Exception as e:
        print(f"MySQL客户端初始化失败: {e}")
        return
    
    # 初始化HSRHealthCheckService
    hsr_service = HSRHealthCheckService(mysql_client)
    print("HSRHealthCheckService初始化成功")
    
    # 获取所有高铁小区
    print("获取所有高铁小区...")
    cells_sql = """
        SELECT 
            id,
            line_name,
            Transmitting_Point_Name as site_name,
            area,
            site_type,
            bbu_name,
            celname,
            CGI,
            lng,
            lat,
            high,
            ant_dir,
            zhishi as network_type,
            cpId,
            cpId_key,
            rru_id_key,
            rru_id,
            rru_type
        FROM hsr_info
        ORDER BY line_name, site_name, celname
    """
    
    try:
        cells = mysql_client.fetch_all(cells_sql)
        print(f"获取到 {len(cells)} 个高铁小区")
        
        # 打印前10个小区的信息
        print("前10个小区信息:")
        for i, cell in enumerate(cells[:10]):
            print(f"{i+1}. CGI: {cell.get('CGI')}, 小区名称: {cell.get('celname')}, CPID: {cell.get('cpId')}, RRU ID: {cell.get('rru_id')}")
        
    except Exception as e:
        print(f"获取小区数据失败: {e}")
        return
    
    # 模拟告警数据
    print("\n模拟告警数据...")
    mock_alarms = [
        {
            "alarm_code_name": "RRU断链",
            "alarm_title": "RRU断链",
            "alarm_level": "紧急",
            "occur_time": datetime.now(),
            "alarm_reason": "物理小区ID: 1，逻辑小区ID: 460-00-12672955-1，CPID: 4，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672955。Location：rack=1,shelf=1,board=1。",
            "ne_id": "12672955",
            "alarm_object_name": "RRU1",
            "additional_info": "物理小区ID: 1，逻辑小区ID: 460-00-12672955-1，CPID: 4，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672955。Location：rack=1,shelf=1,board=1。"
        },
        {
            "alarm_code_name": "RRU断链",
            "alarm_title": "RRU断链",
            "alarm_level": "紧急",
            "occur_time": datetime.now(),
            "alarm_reason": "物理小区ID: 1，逻辑小区ID: 460-00-12672934-1，CPID: 3，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672934。Location：rack=1,shelf=1,board=1。",
            "ne_id": "12672934",
            "alarm_object_name": "RRU1",
            "additional_info": "物理小区ID: 1，逻辑小区ID: 460-00-12672934-1，CPID: 3，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672934。Location：rack=1,shelf=1,board=1。"
        }
    ]
    
    print(f"模拟了 {len(mock_alarms)} 个告警")
    for i, alarm in enumerate(mock_alarms):
        print(f"{i+1}. 告警: {alarm['alarm_code_name']}, 逻辑小区ID: {alarm['alarm_reason'].split('逻辑小区ID: ')[1].split('，')[0]}, CPID: {alarm['alarm_reason'].split('CPID: ')[1].split('，')[0]}, gNBId: {alarm['alarm_reason'].split('NR gNBId:')[1].split('。')[0]}")
    
    # 调用get_alarm_data方法（注意：这里需要修改方法为public或者创建一个测试方法）
    print("\n调用告警匹配逻辑...")
    try:
        # 直接调用_get_alarm_data方法
        alarm_data = hsr_service._get_alarm_data(cells)
        print(f"告警匹配完成，匹配到 {len(alarm_data)} 个小区")
        
        # 打印匹配结果
        print("\n告警匹配结果:")
        for cgi, alarms in alarm_data.items():
            print(f"小区 CGI: {cgi}, 匹配到 {len(alarms)} 个告警")
            for alarm in alarms:
                print(f"  - 告警: {alarm.get('alarm_name')}, 级别: {alarm.get('alarm_level')}")
        
    except Exception as e:
        print(f"告警匹配失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试特定小区的匹配
    print("\n测试特定小区的匹配...")
    test_cgis = ["460-00-12672955-1", "460-00-12672934-1"]
    
    for cgi in test_cgis:
        if cgi in alarm_data:
            print(f"小区 {cgi} 匹配到 {len(alarm_data[cgi])} 个告警")
        else:
            print(f"小区 {cgi} 未匹配到任何告警")
    
    print("\n测试完成！")


if __name__ == "__main__":
    test_hsr_alarm_match()
