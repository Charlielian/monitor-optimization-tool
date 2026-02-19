#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实际MySQL数据库中的高铁小区告警匹配逻辑

功能：
1. 直接连接MySQL数据库读取hsr_info表数据
2. 读取实际告警数据
3. 测试告警匹配到小区和发射点的过程
4. 验证匹配逻辑的有效性
"""

import re
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.mysql import MySQLClient
from config import Config

class RealHSRMatchingTest:
    """测试实际HSR数据库中的告警匹配"""
    
    def __init__(self):
        """初始化测试类"""
        try:
            # 加载配置
            self.config = Config()
            # 连接MySQL数据库
            self.mysql = MySQLClient(self.config.mysql_config)
            print("✓ 成功连接到MySQL数据库")
        except Exception as e:
            print(f"✗ 连接MySQL数据库失败: {e}")
            sys.exit(1)
    
    def get_hsr_info(self):
        """从数据库中获取hsr_info表数据"""
        try:
            sql = """
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
            cells = self.mysql.fetch_all(sql)
            print(f"✓ 成功获取 {len(cells)} 条hsr_info记录")
            return cells
        except Exception as e:
            print(f"✗ 获取hsr_info数据失败: {e}")
            return []
    
    def get_alarm_data(self):
        """从数据库中获取告警数据"""
        try:
            # 查询所有符合条件的告警数量（不限制时间范围）
            count_sql = """
                SELECT COUNT(*)
                FROM cur_alarm
                WHERE site_name LIKE '%GZ%'
            """
            count_result = self.mysql.fetch_one(count_sql)
            total_count = count_result.get('COUNT(*)') if count_result else 0
            print(f"✓ 广湛相关告警总数: {total_count}")
            
            # 查询最近7天的广湛告警数量
            recent_count_sql = """
                SELECT COUNT(*)
                FROM cur_alarm
                WHERE occur_time >= NOW() - INTERVAL 7 DAY
                  AND site_name LIKE '%GZ%'
            """
            recent_count_result = self.mysql.fetch_one(recent_count_sql)
            recent_count = recent_count_result.get('COUNT(*)') if recent_count_result else 0
            print(f"✓ 最近7天广湛相关告警数量: {recent_count}")
            
            # 查询RRU相关告警
            rru_count_sql = """
                SELECT COUNT(*)
                FROM cur_alarm
                WHERE site_name LIKE '%GZ%'
                  AND (alarm_code_name LIKE '%RRU%' OR alarm_title LIKE '%RRU%' OR alarm_reason LIKE '%RRU%')
            """
            rru_count_result = self.mysql.fetch_one(rru_count_sql)
            rru_count = rru_count_result.get('COUNT(*)') if rru_count_result else 0
            print(f"✓ 广湛RRU相关告警数量: {rru_count}")
            
            # 查询所有广湛告警（不限制时间范围）
            sql = """
                SELECT 
                    alarm_code_name, 
                    alarm_title, 
                    alarm_level, 
                    occur_time, 
                    alarm_reason, 
                    ne_id, 
                    alarm_object_name, 
                    additional_info
                FROM cur_alarm
                WHERE site_name LIKE '%GZ%'
                ORDER BY occur_time DESC
                LIMIT 57
            """

            alarms = self.mysql.fetch_all(sql)
            print(f"✓ 成功获取 {len(alarms)} 条广湛相关告警记录")
            return alarms
        except Exception as e:
            print(f"✗ 获取告警数据失败: {e}")
            # 返回模拟告警数据作为备用
            return self._get_mock_alarms()
    
    def _get_mock_alarms(self):
        """获取模拟告警数据"""
        return [
            {
                'alarm_code_name': 'RRU断链',
                'alarm_title': 'RRU链路故障',
                'alarm_level': '严重',
                'occur_time': datetime.now(),
                'alarm_reason': '物理小区ID: 1，逻辑小区ID: 460-00-12672955-1，CPID: 4，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672955。Location：rack=1,shelf=1,board=1。',
                'ne_id': '12672955',
                'alarm_object_name': '测试发射点',
                'additional_info': '物理小区ID: 1，逻辑小区ID: 460-00-12672955-1，CPID: 4，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672955。Location：rack=1,shelf=1,board=1。'
            }
        ]
    
    def extract_alarm_info(self, alarm):
        """从告警数据中提取信息"""
        extracted_info = {
            'extracted_cpid': None,
            'extracted_cgi': None,
            'extracted_rack': None,
            'extracted_gnb_id': None,
            'extracted_enb_id': None
        }
        
        alarm_desc = alarm.get('alarm_reason', '')
        additional_info = alarm.get('additional_info', '')
        
        # 提取CPID
        if additional_info and ('CPID' in str(additional_info) or 'CP ID' in str(additional_info)):
            match = re.search(r'(?:CPID|CP ID)[:：]\s*(\d+)', str(additional_info))
            if match:
                extracted_info['extracted_cpid'] = match.group(1)
        if not extracted_info['extracted_cpid'] and ('CPID' in str(alarm_desc) or 'CP ID' in str(alarm_desc)):
            match = re.search(r'(?:CPID|CP ID)[:：]\s*(\d+)', str(alarm_desc))
            if match:
                extracted_info['extracted_cpid'] = match.group(1)
        
        # 提取逻辑小区ID
        if additional_info and '逻辑小区ID' in str(additional_info):
            match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(additional_info))
            if match:
                extracted_info['extracted_cgi'] = match.group(1)
        if not extracted_info['extracted_cgi'] and '逻辑小区ID' in str(alarm_desc):
            match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(alarm_desc))
            if match:
                extracted_info['extracted_cgi'] = match.group(1)

        # 提取RRU相关信息
        if additional_info:
            # 提取rack（RRU ID）
            rack_match = re.search(r'rack=(\d+)', str(additional_info))
            if rack_match:
                extracted_info['extracted_rack'] = rack_match.group(1)

            # 提取gNBId（5G网元ID）
            gnb_match = re.search(r'(?:NR\s*)?gNBId:([\d]+)', str(additional_info))
            if gnb_match:
                extracted_info['extracted_gnb_id'] = gnb_match.group(1)

            # 提取eNBId（4G网元ID）
            enb_match = re.search(r'eNBId:([\d]+)', str(additional_info))
            if enb_match:
                extracted_info['extracted_enb_id'] = enb_match.group(1)
        
        # 从告警描述中提取信息
        if alarm_desc:
            # 从告警描述中提取逻辑小区ID
            if not extracted_info['extracted_cgi']:
                cgi_match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(alarm_desc))
                if cgi_match:
                    extracted_info['extracted_cgi'] = cgi_match.group(1)
            
            # 从告警描述中提取CPID
            if not extracted_info['extracted_cpid']:
                cpid_match = re.search(r'CPID[:：]\s*(\d+)', str(alarm_desc))
                if cpid_match:
                    extracted_info['extracted_cpid'] = cpid_match.group(1)
            
            # 从告警描述中提取gNBId
            if not extracted_info['extracted_gnb_id']:
                gnb_match = re.search(r'(?:NR\s*)?gNBId:([\d]+)', str(alarm_desc))
                if gnb_match:
                    extracted_info['extracted_gnb_id'] = gnb_match.group(1)
            
            # 从告警描述中提取rack
            if not extracted_info['extracted_rack']:
                rack_match = re.search(r'rack=(\d+)', str(alarm_desc))
                if rack_match:
                    extracted_info['extracted_rack'] = rack_match.group(1)
        
        return extracted_info
    
    def match_alarm_to_site(self, alarm, cells):
        """匹配告警到发射点"""
        # 构建匹配所需的映射
        ne_id_to_cgis = {}  # {ne_id: [cgi1, cgi2, ...]}
        celname_to_cgi = {}  # {celname: cgi} 用于精确匹配
        cpid_to_cgis = {}  # {cpId: [cgi1, cgi2, ...]} 用于超级小区CP退服匹配
        cgi_to_cell = {}  # {cgi: cell} 用于快速查找小区信息
        rru_id_to_cgis = {}  # {rru_id: [cgi1, cgi2, ...]} 用于RRU ID匹配
        
        for cell in cells:
            cgi = cell.get('CGI', '')
            celname = cell.get('celname', '')
            cell_cpid = cell.get('cpId', '')
            cell_rru_id = str(cell.get('rru_id', ''))
            
            # 建立小区名称到CGI的映射
            if celname:
                celname_to_cgi[celname] = cgi
            
            # 建立CPID到CGI的映射
            if cell_cpid:
                cpid_str = str(cell_cpid)
                if cpid_str not in cpid_to_cgis:
                    cpid_to_cgis[cpid_str] = []
                cpid_to_cgis[cpid_str].append(cgi)
            
            # 从CGI中提取网元ID
            cgi_parts = cgi.split('-')
            if len(cgi_parts) >= 3:
                ne_id = cgi_parts[2]
                if ne_id not in ne_id_to_cgis:
                    ne_id_to_cgis[ne_id] = []
                ne_id_to_cgis[ne_id].append(cgi)
            
            # 建立CGI到小区的映射
            if cgi:
                cgi_to_cell[cgi] = cell
            
            # 建立RRU ID到CGI的映射
            if cell_rru_id:
                if cell_rru_id not in rru_id_to_cgis:
                    rru_id_to_cgis[cell_rru_id] = []
                rru_id_to_cgis[cell_rru_id].append(cgi)
        
        # 提取告警信息
        extracted_info = self.extract_alarm_info(alarm)
        extracted_cpid = extracted_info['extracted_cpid']
        extracted_cgi = extracted_info['extracted_cgi']
        extracted_rack = extracted_info['extracted_rack']
        extracted_gnb_id = extracted_info['extracted_gnb_id']
        extracted_enb_id = extracted_info['extracted_enb_id']
        
        # 告警基本信息
        alarm_name = alarm.get('alarm_code_name', '') or alarm.get('alarm_title', '')
        alarm_level = alarm.get('alarm_level', '')
        alarm_time = alarm.get('occur_time', '')
        alarm_desc = alarm.get('alarm_reason', '')
        ne_id = alarm.get('ne_id', '')
        alarm_object_name = alarm.get('alarm_object_name', '')
        
        # 按优先级顺序尝试匹配告警（串行匹配）
        alarm_matched = False
        matched_cells = []
        
        print(f"\n开始匹配告警: {alarm_name}")
        print(f"告警级别: {alarm_level}")
        print(f"告警对象: {alarm_object_name}")
        print(f"提取的信息: CPID={extracted_cpid}, CGI={extracted_cgi}, RACK={extracted_rack}, gNBId={extracted_gnb_id}, NE_ID={ne_id}")
        
        # 1. 超级小区CP退服告警匹配（最高优先级）
        if not alarm_matched and ('超级小区CP退服' in alarm_name or '超级小区CP退出服务' in alarm_name) and extracted_cpid and extracted_cgi:
            # 直接通过CGI查找小区
            if extracted_cgi in cgi_to_cell:
                cell = cgi_to_cell[extracted_cgi]
                cell_cpid = str(cell.get('cpId', ''))
                if cell_cpid == extracted_cpid:
                    matched_cells.append(cell)
                    alarm_matched = True
                    print(f"✓ 通过超级小区CP退服匹配到小区: {cell['celname']} (发射点: {cell['site_name']})")
        
        # 2. 逻辑小区ID匹配（第二优先级）
        if not alarm_matched and extracted_cgi and extracted_cgi in cgi_to_cell:
            cell = cgi_to_cell[extracted_cgi]
            matched_cells.append(cell)
            alarm_matched = True
            print(f"✓ 通过逻辑小区ID匹配到小区: {cell['celname']} (发射点: {cell['site_name']})")
        
        # 3. RRU级别告警匹配（第三优先级）
        if not alarm_matched and extracted_rack:
            # 使用RRU ID到CGI的映射快速查找
            if extracted_rack in rru_id_to_cgis:
                for cgi in rru_id_to_cgis[extracted_rack]:
                    cell = cgi_to_cell.get(cgi)
                    if cell:
                        # 检查网元ID匹配
                        cgi_ne_id = None
                        cgi_parts = cgi.split('-')
                        if len(cgi_parts) >= 3:
                            cgi_ne_id = cgi_parts[2]
                        
                        # 检查网元ID是否匹配
                        ne_matched = False
                        if extracted_gnb_id and cgi_ne_id == extracted_gnb_id:
                            ne_matched = True
                        if extracted_enb_id and cgi_ne_id == extracted_enb_id:
                            ne_matched = True
                        
                        if ne_matched:
                            matched_cells.append(cell)
                            alarm_matched = True
                            print(f"✓ 通过RRU级别告警匹配到小区: {cell['celname']} (发射点: {cell['site_name']})")
                            break  # 只匹配第一个RRU对应的小区
        
        # 4. 告警对象名称匹配（第四优先级）
        if not alarm_matched and alarm_object_name:
            # 快速查找发射点名称匹配
            for cell in cells:
                if cell['site_name'] == alarm_object_name:
                    matched_cells.append(cell)
                    alarm_matched = True
                    print(f"✓ 通过告警对象名称匹配到小区: {cell['celname']} (发射点: {cell['site_name']})")
                    break  # 只匹配第一个发射点对应的小区
        
        # 5. CPID匹配（对于RRU断链等影响多个小区的告警）（第五优先级）
        if not alarm_matched and extracted_cpid:
            # 查找所有使用相同CPID的小区
            if extracted_cpid in cpid_to_cgis:
                for cgi in cpid_to_cgis[extracted_cpid]:
                    cell = cgi_to_cell.get(cgi)
                    if cell:
                        # 检查网元ID是否匹配
                        cgi_ne_id = None
                        cgi_parts = cgi.split('-')
                        if len(cgi_parts) >= 3:
                            cgi_ne_id = cgi_parts[2]
                        
                        # 检查网元ID是否匹配
                        ne_matched = False
                        if extracted_gnb_id and cgi_ne_id == extracted_gnb_id:
                            ne_matched = True
                        if extracted_enb_id and cgi_ne_id == extracted_enb_id:
                            ne_matched = True
                        if not extracted_gnb_id and not extracted_enb_id:
                            # 如果没有提取到网元ID，则直接匹配
                            ne_matched = True
                        
                        if ne_matched:
                            matched_cells.append(cell)
                            alarm_matched = True
                            print(f"✓ 通过CPID匹配到小区: {cell['celname']} (发射点: {cell['site_name']})")
        
        # 6. 网元ID匹配（最低优先级）
        if not alarm_matched and ne_id:
            # 使用网元ID到CGI的映射快速查找
            if ne_id in ne_id_to_cgis:
                for cgi in ne_id_to_cgis[ne_id]:
                    cell = cgi_to_cell.get(cgi)
                    if cell:
                        matched_cells.append(cell)
                        alarm_matched = True
                        print(f"✓ 通过网元ID匹配到小区: {cell['celname']} (发射点: {cell['site_name']})")
        
        if not alarm_matched:
            print("✗ 未匹配到任何小区")
            return None
        
        # 提取匹配到的发射点信息
        matched_sites = {}
        for cell in matched_cells:
            site_name = cell['site_name']
            if site_name not in matched_sites:
                matched_sites[site_name] = {
                    'site_name': site_name,
                    'line_name': cell['line_name'],
                    'area': cell['area'],
                    'matched_cells': [],
                    'alarm_count': 0
                }
            matched_sites[site_name]['matched_cells'].append(cell)
            matched_sites[site_name]['alarm_count'] += 1
        
        # 输出匹配结果
        print(f"\n匹配结果:")
        for site_name, site_info in matched_sites.items():
            print(f"✓ 匹配到发射点: {site_name}")
            print(f"  所属高铁: {site_info['line_name']}")
            print(f"  所属区域: {site_info['area']}")
            print(f"  匹配到 {len(site_info['matched_cells'])} 个小区:")
            for cell in site_info['matched_cells']:
                print(f"    - {cell['celname']} (CGI: {cell['CGI']}, CPID: {cell['cpId']})")
        
        return matched_sites
    
    def run_test(self):
        """运行测试"""
        print("\n" + "="*100)
        print("开始测试实际HSR数据库中的告警匹配")
        print("="*100)
        
        # 获取hsr_info数据
        cells = self.get_hsr_info()
        if not cells:
            print("✗ 没有获取到hsr_info数据，测试无法进行")
            return
        
        # 显示前5条hsr_info记录
        print("\n前5条hsr_info记录:")
        print("-"*100)
        for i, cell in enumerate(cells[:5]):
            print(f"{i+1}. 发射点: {cell['site_name']} | 小区: {cell['celname']} | CGI: {cell['CGI']} | CPID: {cell['cpId']}")
        
        # 获取告警数据
        alarms = self.get_alarm_data()
        if not alarms:
            print("✗ 没有获取到告警数据，测试无法进行")
            return
        
        total_alarms = len(alarms)
        matched_alarms = 0
        
        for i, alarm in enumerate(alarms):
            print(f"\n" + "-"*100)
            print(f"测试告警 {i+1}/{total_alarms}:")
            print(f"告警代码: {alarm['alarm_code_name']}")
            print(f"告警标题: {alarm['alarm_title']}")
            print(f"告警原因: {alarm['alarm_reason'][:100]}...")  # 只显示前100个字符
            print("-"*100)
            
            # 匹配告警到发射点
            matched_sites = self.match_alarm_to_site(alarm, cells)
            
            if matched_sites:
                matched_alarms += 1
                print(f"\n✓ 告警匹配成功，共匹配到 {len(matched_sites)} 个发射点")
            else:
                print("\n✗ 告警匹配失败")
        
        print(f"\n" + "="*100)
        print(f"测试完成: 共 {total_alarms} 个告警，成功匹配 {matched_alarms} 个")
        print(f"匹配率: {(matched_alarms/total_alarms*100):.2f}%")
        print("="*100)

if __name__ == "__main__":
    test = RealHSRMatchingTest()
    test.run_test()
