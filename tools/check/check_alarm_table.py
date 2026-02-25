#!/usr/bin/env python3
"""查询告警表结构"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from db.mysql import MySQLClient

def check_alarm_table_structure():
    """检查告警表结构"""
    try:
        # 初始化配置和MySQL客户端
        cfg = Config()
        mysql_client = MySQLClient(cfg.mysql_config)
        
        # 查询cur_alarm表结构
        print("=== cur_alarm表结构 ===")
        structure = mysql_client.fetch_all("DESCRIBE cur_alarm")
        if structure:
            for row in structure[:10]:  # 只显示前10个字段
                print(row)
        else:
            print("未找到cur_alarm表")
        
        print()
        
        # 查询cur_alarm_nokia表结构
        print("=== cur_alarm_nokia表结构 ===")
        structure_nokia = mysql_client.fetch_all("DESCRIBE cur_alarm_nokia")
        if structure_nokia:
            for row in structure_nokia[:10]:  # 只显示前10个字段
                print(row)
        else:
            print("未找到cur_alarm_nokia表")
            
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == "__main__":
    check_alarm_table_structure()
