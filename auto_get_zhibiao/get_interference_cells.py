# -*- coding: utf-8 -*-
"""
干扰小区数据提取脚本
功能：单点登录大数据平台，进入即席查询模块，提取4G/5G干扰小区数据
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
project_path = os.path.join(os.getcwd(), 'WNCOP-20250303-debug')
sys.path.insert(0, project_path)

from feature.login import Login
from feature.get_data.JXCX import entry
from feature.get_data.JXCX.payload import ganrao_NR, ganrao_LTE, set_where


class InterferenceCellExtractor:
    """干扰小区数据提取器"""
    
    def __init__(self, username=None, password=None):
        """
        初始化提取器
        :param username: 登录用户名（可选，默认使用配置文件中的账号）
        :param password: 登录密码（可选，默认使用配置文件中的密码）
        """
        self.username = username
        self.password = password
        self.login_obj = None
        self.jxcx = None
        
    def login(self):
        """执行单点登录"""
        print("=" * 60)
        print("开始登录大数据平台...")
        print("=" * 60)
        
        try:
            if self.username and self.password:
                self.login_obj = Login.Login(username=self.username, password=self.password)
            else:
                self.login_obj = Login.Login()  # 使用默认账号
            
            self.login_obj.login()
            print("✓ 登录成功！")
            return True
        except Exception as e:
            print(f"✗ 登录失败: {e}")
            return False
    
    def init_jxcx(self):
        """初始化即席查询对象"""
        print("\n进入即席查询模块...")
        try:
            self.jxcx = entry.Jxcx()
            self.jxcx.sess = self.login_obj.sess
            print("✓ 即席查询模块初始化成功！")
            return True
        except Exception as e:
            print(f"✗ 即席查询模块初始化失败: {e}")
            return False
    
    def get_interference_data(self, network_type='5G', start_date=None, end_date=None, 
                             city='阳江', only_interfered=True):
        """
        提取干扰小区数据
        :param network_type: 网络类型，'4G' 或 '5G'
        :param start_date: 开始日期，格式：'2025-01-13' 或 datetime对象
        :param end_date: 结束日期，格式：'2025-01-19' 或 datetime对象
        :param city: 城市名称
        :param only_interfered: 是否只提取干扰小区（True）还是全部小区（False）
        :return: DataFrame
        """
        print("\n" + "=" * 60)
        print(f"开始提取 {network_type} 干扰小区数据...")
        print("=" * 60)
        
        # 处理日期参数
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)
        
        if isinstance(start_date, str):
            start_time = start_date + ' 00:00:00'
        else:
            start_time = start_date.strftime('%Y-%m-%d 00:00:00')
        
        if isinstance(end_date, str):
            end_time = end_date + ' 23:59:59'
        else:
            end_time = end_date.strftime('%Y-%m-%d 23:59:59')
        
        print(f"查询参数:")
        print(f"  - 网络类型: {network_type}")
        print(f"  - 开始时间: {start_time}")
        print(f"  - 结束时间: {end_time}")
        print(f"  - 城市: {city}")
        print(f"  - 仅干扰小区: {only_interfered}")
        
        try:
            # 选择对应的payload模板
            if network_type == '5G':
                payload = ganrao_NR.data_d.copy()
                interfere_field = 'is_interfere_5g'
            elif network_type == '4G':
                payload = ganrao_LTE.data_d.copy()
                interfere_field = 'is_interfere'
            else:
                raise ValueError("network_type 必须是 '4G' 或 '5G'")
            
            # 设置查询时间范围
            payload = set_where.set_where(payload, start_time, end_time)
            
            # 设置城市条件
            for condition in payload['where']:
                if condition['feild'] == 'city':
                    condition['val'] = city
            
            # 获取数据总行数
            print("\n正在获取数据总行数...")
            count = self.jxcx.getTableCount(payload)
            print(f"✓ 查询到 {count} 条记录")
            
            if count == 0:
                print("⚠ 未查询到数据")
                return pd.DataFrame()
            
            # 设置返回行数并查询数据
            payload['length'] = count
            print("\n正在提取数据...")
            df = self.jxcx.getTable(payload, to_df=True)
            print(f"✓ 数据提取成功，共 {len(df)} 行")
            
            # 如果只需要干扰小区，进行过滤
            if only_interfered and interfere_field in df.columns:
                original_count = len(df)
                df = df[df[interfere_field] == '是']
                print(f"✓ 过滤后保留干扰小区 {len(df)} 个（原始数据 {original_count} 条）")
            
            return df
            
        except Exception as e:
            print(f"✗ 数据提取失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def save_to_excel(self, df, filename=None, network_type='5G'):
        """
        保存数据到Excel
        :param df: DataFrame数据
        :param filename: 文件名（可选）
        :param network_type: 网络类型
        """
        if df.empty:
            print("\n⚠ 数据为空，不保存文件")
            return
        
        # 生成默认文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{network_type}_干扰小区_{timestamp}.xlsx'
        
        # 确保输出目录存在
        output_dir = os.path.join(project_path, 'data', 'out')
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            df.to_excel(filepath, index=False, engine='openpyxl')
            print(f"\n✓ 数据已保存到: {filepath}")
            print(f"  文件大小: {os.path.getsize(filepath) / 1024:.2f} KB")
        except Exception as e:
            print(f"\n✗ 保存文件失败: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("干扰小区数据提取工具")
    print("=" * 60)
    
    # 创建提取器实例（使用默认账号）
    extractor = InterferenceCellExtractor()
    
    # 1. 登录
    if not extractor.login():
        return
    
    # 2. 初始化即席查询
    if not extractor.init_jxcx():
        return
    
    # 3. 提取5G干扰小区数据
    df_5g = extractor.get_interference_data(
        network_type='5G',
        start_date='2025-01-13',
        end_date='2025-01-19',
        city='阳江',
        only_interfered=True  # 只提取干扰小区
    )
    
    # 4. 保存5G数据
    if not df_5g.empty:
        extractor.save_to_excel(df_5g, network_type='5G')
        print(f"\n5G干扰小区数据预览:")
        print(df_5g.head())
    
    # 5. 提取4G干扰小区数据
    df_4g = extractor.get_interference_data(
        network_type='4G',
        start_date='2025-01-13',
        end_date='2025-01-19',
        city='阳江',
        only_interfered=True
    )
    
    # 6. 保存4G数据
    if not df_4g.empty:
        extractor.save_to_excel(df_4g, network_type='4G')
        print(f"\n4G干扰小区数据预览:")
        print(df_4g.head())
    
    print("\n" + "=" * 60)
    print("数据提取完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
