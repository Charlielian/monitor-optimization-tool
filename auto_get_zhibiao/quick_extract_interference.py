# -*- coding: utf-8 -*-
"""
快速提取干扰小区数据 - 简化版脚本
使用方法：直接运行此脚本，根据提示输入参数
"""
import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
project_path = os.path.join(os.getcwd(), 'WNCOP-20250303-debug')
sys.path.insert(0, project_path)

from feature.login import Login
from feature.get_data.JXCX import entry
from feature.get_data.JXCX.payload import ganrao_NR, ganrao_LTE, set_where


def quick_extract(network_type='5G', days=7, city='阳江'):
    """
    快速提取干扰小区数据
    :param network_type: '4G' 或 '5G'
    :param days: 查询最近几天的数据
    :param city: 城市名称
    """
    print(f"\n{'='*60}")
    print(f"快速提取 {network_type} 干扰小区数据")
    print(f"{'='*60}\n")
    
    # 1. 登录
    print("步骤 1/4: 登录中...")
    login_obj = Login.Login()
    login_obj.login()
    print("✓ 登录成功\n")
    
    # 2. 初始化即席查询
    print("步骤 2/4: 初始化即席查询...")
    jxcx = entry.Jxcx()
    jxcx.sess = login_obj.sess
    print("✓ 初始化成功\n")
    
    # 3. 准备查询参数
    print("步骤 3/4: 准备查询参数...")
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    start_time = start_date.strftime('%Y-%m-%d 00:00:00')
    end_time = end_date.strftime('%Y-%m-%d 23:59:59')
    
    print(f"  查询时间: {start_time} 至 {end_time}")
    print(f"  查询城市: {city}")
    
    # 选择payload
    if network_type == '5G':
        payload = ganrao_NR.data_d.copy()
        interfere_field = 'is_interfere_5g'
    else:
        payload = ganrao_LTE.data_d.copy()
        interfere_field = 'is_interfere'
    
    # 设置时间和城市
    payload = set_where.set_where(payload, start_time, end_time)
    for condition in payload['where']:
        if condition['feild'] == 'city':
            condition['val'] = city
    
    print("✓ 参数准备完成\n")
    
    # 4. 查询数据
    print("步骤 4/4: 查询数据...")
    count = jxcx.getTableCount(payload)
    print(f"  找到 {count} 条记录")
    
    if count == 0:
        print("⚠ 未查询到数据")
        return None
    
    payload['length'] = count
    df = jxcx.getTable(payload, to_df=True)
    
    # 过滤干扰小区
    if interfere_field in df.columns:
        df_interfered = df[df[interfere_field] == '是']
        print(f"  其中干扰小区: {len(df_interfered)} 个")
    else:
        df_interfered = df
    
    # 保存文件
    output_dir = os.path.join(project_path, 'data', 'out')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{network_type}_干扰小区_{timestamp}.xlsx'
    filepath = os.path.join(output_dir, filename)
    
    df_interfered.to_excel(filepath, index=False, engine='openpyxl')
    print(f"\n✓ 数据已保存: {filepath}")
    
    # 显示统计信息
    print(f"\n{'='*60}")
    print("数据统计:")
    print(f"{'='*60}")
    print(f"总记录数: {len(df)}")
    print(f"干扰小区数: {len(df_interfered)}")
    if len(df) > 0:
        print(f"干扰占比: {len(df_interfered)/len(df)*100:.2f}%")
    
    # 显示前5条数据
    print(f"\n前5条干扰小区数据:")
    print(df_interfered.head().to_string())
    
    return df_interfered


if __name__ == '__main__':
    # 方式1: 直接运行（使用默认参数）
    # quick_extract(network_type='5G', days=7, city='阳江')
    
    # 方式2: 交互式输入
    print("\n" + "="*60)
    print("干扰小区数据快速提取工具")
    print("="*60)
    
    # 选择网络类型
    print("\n请选择网络类型:")
    print("1. 5G")
    print("2. 4G")
    choice = input("请输入选项 (1/2，默认1): ").strip() or '1'
    network_type = '5G' if choice == '1' else '4G'
    
    # 输入查询天数
    days_input = input("\n查询最近几天的数据 (默认7天): ").strip()
    days = int(days_input) if days_input else 7
    
    # 输入城市
    city = input("\n请输入城市名称 (默认'阳江'): ").strip() or '阳江'
    
    # 执行查询
    try:
        quick_extract(network_type=network_type, days=days, city=city)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
