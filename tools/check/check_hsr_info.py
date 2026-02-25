#!/usr/bin/env python3
"""查询hsr_info表结构"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from db.mysql import MySQLClient

def check_hsr_info_structure():
    """检查hsr_info表结构"""
    try:
        # 初始化配置和MySQL客户端
        cfg = Config()
        mysql_client = MySQLClient(cfg.mysql_config)
        
        # 查询表结构
        print("=== hsr_info表结构 ===")
        structure = mysql_client.fetch_all("DESCRIBE hsr_info")
        if structure:
            for row in structure:
                print(row)
        else:
            print("未找到hsr_info表")
        
        # 查询前几行数据，了解字段内容
        print("\n=== hsr_info表前5行数据 ===")
        data = mysql_client.fetch_all("SELECT * FROM hsr_info LIMIT 5")
        if data:
            for row in data:
                print(row)
        else:
            print("hsr_info表为空")
            
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == "__main__":
    check_hsr_info_structure()
