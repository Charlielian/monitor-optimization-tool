#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试高铁小区告警匹配逻辑

功能：
1. 模拟告警信息提取
2. 模拟小区数据
3. 测试告警匹配过程
4. 验证RRU断链告警是否能正确匹配到小区
"""

import re
from datetime import datetime

# 模拟告警信息提取函数
def extract_alarm_info(alarm_desc):
    """从告警描述中提取告警信息"""
    extracted_info = {
        'extracted_cpid': None,
        'extracted_cgi': None,
        'extracted_rack': None,
        'extracted_gnb_id': None,
        'extracted_enb_id': None
    }
    
    # 提取CPID
    cpid_match = re.search(r'CPID[:：]\s*(\d+)', alarm_desc)
    if cpid_match:
        extracted_info['extracted_cpid'] = cpid_match.group(1)
    
    # 提取逻辑小区ID
    cgi_match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', alarm_desc)
    if cgi_match:
        extracted_info['extracted_cgi'] = cgi_match.group(1)
    
    # 提取rack（RRU ID）
    rack_match = re.search(r'rack=(\d+)', alarm_desc)
    if rack_match:
        extracted_info['extracted_rack'] = rack_match.group(1)
    
    # 提取gNBId（5G网元ID）
    gnb_match = re.search(r'(?:NR\s*)?gNBId:(\d+)', alarm_desc)
    if gnb_match:
        extracted_info['extracted_gnb_id'] = gnb_match.group(1)
    
    # 提取eNBId（4G网元ID）
    enb_match = re.search(r'eNBId:(\d+)', alarm_desc)
    if enb_match:
        extracted_info['extracted_enb_id'] = enb_match.group(1)
    
    return extracted_info

# 模拟告警匹配函数
def match_alarm_to_cell(alarm_info, cells):
    """模拟告警匹配到小区的过程"""
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
    
    # 模拟告警数据
    alarm_name = "RRU断链"
    alarm_level = "严重"
    alarm_time = datetime.now()
    alarm_desc = alarm_info['alarm_desc']
    extracted_cpid = alarm_info['extracted_cpid']
    extracted_cgi = alarm_info['extracted_cgi']
    extracted_rack = alarm_info['extracted_rack']
    extracted_gnb_id = alarm_info['extracted_gnb_id']
    extracted_enb_id = alarm_info['extracted_enb_id']
    alarm_object_name = "测试对象"
    
    # 按优先级顺序尝试匹配告警（串行匹配）
    alarm_matched = False
    matched_cells = []
    
    print(f"\n开始匹配告警: {alarm_name}")
    print(f"提取的信息: CPID={extracted_cpid}, CGI={extracted_cgi}, RACK={extracted_rack}, gNBId={extracted_gnb_id}")
    
    # 1. 逻辑小区ID匹配（第二优先级）
    if not alarm_matched and extracted_cgi and extracted_cgi in cgi_to_cell:
        cgi = extracted_cgi
        matched_cells.append(cgi)
        alarm_matched = True
        print(f"✓ 通过逻辑小区ID匹配到: {cgi}")
    
    # 2. RRU级别告警匹配（第三优先级）
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
                        matched_cells.append(cgi)
                        alarm_matched = True
                        print(f"✓ 通过RRU级别告警匹配到: {cgi}")
                        break  # 只匹配第一个RRU对应的小区
    
    # 3. CPID匹配（对于RRU断链等影响多个小区的告警）（第五优先级）
    if not alarm_matched and extracted_cpid:
        # 查找所有使用相同CPID的小区
        if extracted_cpid in cpid_to_cgis:
            for cgi in cpid_to_cgis[extracted_cpid]:
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
                    matched_cells.append(cgi)
                    alarm_matched = True
                    print(f"✓ 通过CPID匹配到: {cgi}")
                    # 对于CPID匹配，不使用break，因为一个CPID可能对应多个小区
    
    # 4. 网元ID匹配（最低优先级）
    if not alarm_matched and extracted_gnb_id:
        # 使用网元ID到CGI的映射快速查找
        if extracted_gnb_id in ne_id_to_cgis:
            for cgi in ne_id_to_cgis[extracted_gnb_id]:
                matched_cells.append(cgi)
                alarm_matched = True
                print(f"✓ 通过网元ID匹配到: {cgi}")
                # 对于网元ID匹配，不使用break，因为一个网元可能对应多个小区
    
    if not alarm_matched:
        print("✗ 未匹配到任何小区")
    
    return matched_cells

# 模拟小区数据
def get_mock_cells():
    """获取模拟小区数据"""
    return [
        {
            'id': 1,
            'line_name': '测试高铁',
            'site_name': '测试站点1',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU1',
            'celname': 'CELL1',
            'CGI': '460-00-12672955-1',
            'cpId': '4',
            'rru_id': '1'
        },
        {
            'id': 2,
            'line_name': '测试高铁',
            'site_name': '测试站点1',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU1',
            'celname': 'CELL2',
            'CGI': '460-00-12672934-1',
            'cpId': '3',
            'rru_id': '1'
        },
        {
            'id': 3,
            'line_name': '测试高铁',
            'site_name': '测试站点1',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU1',
            'celname': 'CELL3',
            'CGI': '460-00-12672934-1',
            'cpId': '0',
            'rru_id': '1'
        },
        {
            'id': 4,
            'line_name': '测试高铁',
            'site_name': '测试站点1',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU1',
            'celname': 'CELL4',
            'CGI': '460-00-12672934-1',
            'cpId': '1',
            'rru_id': '1'
        },
        {
            'id': 5,
            'line_name': '测试高铁',
            'site_name': '测试站点2',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU2',
            'celname': 'CELL5',
            'CGI': '460-00-12672916-1',
            'cpId': '2',
            'rru_id': '1'
        },
        {
            'id': 6,
            'line_name': '测试高铁',
            'site_name': '测试站点2',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU2',
            'celname': 'CELL6',
            'CGI': '460-00-12672916-1',
            'cpId': '3',
            'rru_id': '1'
        },
        {
            'id': 7,
            'line_name': '测试高铁',
            'site_name': '测试站点3',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU3',
            'celname': 'CELL7',
            'CGI': '460-00-12672931-1',
            'cpId': '3',
            'rru_id': '1'
        },
        {
            'id': 8,
            'line_name': '测试高铁',
            'site_name': '测试站点3',
            'area': '测试区域',
            'site_type': '高铁站点',
            'bbu_name': 'BBU3',
            'celname': 'CELL8',
            'CGI': '460-00-12672931-1',
            'cpId': '2',
            'rru_id': '1'
        }
    ]

# 测试告警
def test_alarm_matching():
    """测试告警匹配"""
    # 获取模拟小区数据
    cells = get_mock_cells()
    print(f"\n模拟小区数据加载完成，共 {len(cells)} 个小区")
    
    # 测试告警列表
    test_alarms = [
        "物理小区ID: 1，逻辑小区ID: 460-00-12672955-1，CPID: 4，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672955。Location：rack=1,shelf=1,board=1。",
        "物理小区ID: 1，逻辑小区ID: 460-00-12672934-1，CPID: 3，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672934。Location：rack=1,shelf=1,board=1。",
        "物理小区ID: 1，逻辑小区ID: 460-00-12672934-1，CPID: 0，CP类型: 主CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672934。Location：rack=1,shelf=1,board=1。",
        "物理小区ID: 1，逻辑小区ID: 460-00-12672934-1，CPID: 1，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672934。Location：rack=1,shelf=1,board=1。",
        "物理小区ID: 1，逻辑小区ID: 460-00-12672916-1，CPID: 2，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672916。Location：rack=1,shelf=1,board=1。",
        "物理小区ID: 1，逻辑小区ID: 460-00-12672916-1，CPID: 3，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672916。Location：rack=1,shelf=1,board=1。",
        "物理小区ID: 1，逻辑小区ID: 460-00-12672931-1，CPID: 3，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672931。Location：rack=1,shelf=1,board=1。",
        "物理小区ID: 1，逻辑小区ID: 460-00-12672931-1，CPID: 2，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672931。Location：rack=1,shelf=1,board=1。"
    ]
    
    print("\n" + "="*80)
    print("开始测试RRU断链告警匹配")
    print("="*80)
    
    total_alarms = len(test_alarms)
    matched_alarms = 0
    
    for i, alarm_desc in enumerate(test_alarms):
        print(f"\n测试告警 {i+1}/{total_alarms}:")
        print(f"告警描述: {alarm_desc}")
        
        # 提取告警信息
        extracted_info = extract_alarm_info(alarm_desc)
        extracted_info['alarm_desc'] = alarm_desc
        
        # 匹配告警到小区
        matched_cells = match_alarm_to_cell(extracted_info, cells)
        
        if matched_cells:
            matched_alarms += 1
            print(f"\n✓ 告警匹配成功，共匹配到 {len(matched_cells)} 个小区:")
            for cgi in matched_cells:
                print(f"  - {cgi}")
        else:
            print("\n✗ 告警匹配失败")
        
        print("-"*80)
    
    print("\n" + "="*80)
    print(f"测试完成: 共 {total_alarms} 个告警，成功匹配 {matched_alarms} 个")
    print(f"匹配率: {(matched_alarms/total_alarms*100):.2f}%")
    print("="*80)

if __name__ == "__main__":
    test_alarm_matching()
