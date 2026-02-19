#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真实环境下的高铁小区告警匹配逻辑

功能：
1. 模拟真实数据库中的告警数据结构
2. 测试告警信息提取
3. 测试告警匹配过程
4. 找出实际部署服务无法匹配RRU断链告警的原因
"""

import re
from datetime import datetime

# 模拟实际数据库中的告警数据结构
real_alarm_data = [
    {
        'alarm_code_name': 'RRU断链',
        'alarm_title': 'RRU链路故障',
        'alarm_level': '严重',
        'occur_time': datetime.now(),
        'alarm_reason': '物理小区ID: 1，逻辑小区ID: 460-00-12672955-1，CPID: 4，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672955。Location：rack=1,shelf=1,board=1。',
        'ne_id': '12672955',
        'alarm_object_name': 'TEST_SITE_1',
        'additional_info': '物理小区ID: 1，逻辑小区ID: 460-00-12672955-1，CPID: 4，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672955。Location：rack=1,shelf=1,board=1。'
    },
    {
        'alarm_code_name': 'RRU断链',
        'alarm_title': 'RRU链路故障',
        'alarm_level': '严重',
        'occur_time': datetime.now(),
        'alarm_reason': '物理小区ID: 1，逻辑小区ID: 460-00-12672934-1，CPID: 3，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672934。Location：rack=1,shelf=1,board=1。',
        'ne_id': '12672934',
        'alarm_object_name': 'TEST_SITE_2',
        'additional_info': '物理小区ID: 1，逻辑小区ID: 460-00-12672934-1，CPID: 3，CP类型: 辅CP，失败原因：RRU断链，错误码: 7-100。NR gNBId:12672934。Location：rack=1,shelf=1,board=1。'
    }
]

# 模拟实际数据库中的小区数据
real_cell_data = [
    {
        'id': 1,
        'line_name': '测试高铁',
        'Transmitting_Point_Name': 'TEST_SITE_1',
        'area': '测试区域',
        'site_type': '高铁站点',
        'bbu_name': 'BBU1',
        'celname': 'CELL1',
        'CGI': '460-00-12672955-1',
        'cpId': '4',
        'cpId_key': 'cpId',
        'rru_id_key': 'rru_id',
        'rru_id': '1',
        'rru_type': 'RRU3908'
    },
    {
        'id': 2,
        'line_name': '测试高铁',
        'Transmitting_Point_Name': 'TEST_SITE_2',
        'area': '测试区域',
        'site_type': '高铁站点',
        'bbu_name': 'BBU2',
        'celname': 'CELL2',
        'CGI': '460-00-12672934-1',
        'cpId': '3',
        'cpId_key': 'cpId',
        'rru_id_key': 'rru_id',
        'rru_id': '1',
        'rru_type': 'RRU3908'
    }
]

# 模拟告警信息提取函数（与实际服务中相同）
def extract_alarm_info(alarm):
    """从告警数据中提取信息（与实际服务中相同的逻辑）"""
    extracted_info = {
        'extracted_cpid': None,
        'extracted_cgi': None,
        'extracted_rack': None,
        'extracted_gnb_id': None,
        'extracted_enb_id': None
    }
    
    alarm_desc = alarm.get('alarm_reason', '')
    additional_info = alarm.get('additional_info', '')
    
    # 提取CPID（用于超级小区CP退服匹配）
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

        # 提取gNBId（5G网元ID），支持"gNBId:123"和"NR gNBId:123"格式
        gnb_match = re.search(r'(?:NR\s*)?gNBId:(\d+)', str(additional_info))
        if gnb_match:
            extracted_info['extracted_gnb_id'] = gnb_match.group(1)

        # 提取eNBId（4G网元ID）
        enb_match = re.search(r'eNBId:(\d+)', str(additional_info))
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
            gnb_match = re.search(r'(?:NR\s*)?gNBId:(\d+)', str(alarm_desc))
            if gnb_match:
                extracted_info['extracted_gnb_id'] = gnb_match.group(1)
        
        # 从告警描述中提取rack
        if not extracted_info['extracted_rack']:
            rack_match = re.search(r'rack=(\d+)', str(alarm_desc))
            if rack_match:
                extracted_info['extracted_rack'] = rack_match.group(1)
    
    return extracted_info

# 模拟告警匹配函数（与实际服务中相同）
def match_alarm_to_cell(alarm, cells):
    """模拟告警匹配到小区的过程（与实际服务中相同的逻辑）"""
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
    extracted_info = extract_alarm_info(alarm)
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
    print(f"告警对象: {alarm_object_name}")
    print(f"提取的信息: CPID={extracted_cpid}, CGI={extracted_cgi}, RACK={extracted_rack}, gNBId={extracted_gnb_id}, NE_ID={ne_id}")
    
    # 1. 超级小区CP退服告警匹配（最高优先级）
    if not alarm_matched and ('超级小区CP退服' in alarm_name or '超级小区CP退出服务' in alarm_name) and extracted_cpid and extracted_cgi:
        # 直接通过CGI查找小区
        if extracted_cgi in cgi_to_cell:
            cell = cgi_to_cell[extracted_cgi]
            cell_cpid = str(cell.get('cpId', ''))
            if cell_cpid == extracted_cpid:
                matched_cells.append(extracted_cgi)
                alarm_matched = True
                print(f"✓ 通过超级小区CP退服匹配到: {extracted_cgi}")
    
    # 2. 逻辑小区ID匹配（第二优先级）
    if not alarm_matched and extracted_cgi and extracted_cgi in cgi_to_cell:
        cgi = extracted_cgi
        matched_cells.append(cgi)
        alarm_matched = True
        print(f"✓ 通过逻辑小区ID匹配到: {cgi}")
    
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
                        matched_cells.append(cgi)
                        alarm_matched = True
                        print(f"✓ 通过RRU级别告警匹配到: {cgi}")
                        break  # 只匹配第一个RRU对应的小区
    
    # 4. 告警对象名称匹配（第四优先级）
    if not alarm_matched and alarm_object_name:
        # 快速查找小区名称匹配
        for celname, cgi in celname_to_cgi.items():
            if celname in alarm_object_name or (alarm_object_name in celname and len(alarm_object_name) >= 5):
                matched_cells.append(cgi)
                alarm_matched = True
                print(f"✓ 通过告警对象名称匹配到: {cgi}")
                break  # 只匹配第一个名称对应的小区
    
    # 5. CPID匹配（对于RRU断链等影响多个小区的告警）（第五优先级）
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
    
    # 6. 网元ID匹配（最低优先级）
    if not alarm_matched and ne_id and not ('超级小区CP退服' in alarm_name or '超级小区CP退出服务' in alarm_name) and not extracted_rack:
        # 使用网元ID到CGI的映射快速查找
        if ne_id in ne_id_to_cgis:
            for cgi in ne_id_to_cgis[ne_id]:
                matched_cells.append(cgi)
                alarm_matched = True
                print(f"✓ 通过网元ID匹配到: {cgi}")
                # 对于网元ID匹配，不使用break，因为一个网元可能对应多个小区
    
    if not alarm_matched:
        print("✗ 未匹配到任何小区")
    
    return matched_cells

# 测试告警匹配
def test_real_alarm_matching():
    """测试真实环境下的告警匹配"""
    print("\n" + "="*80)
    print("开始测试真实环境下的RRU断链告警匹配")
    print("="*80)
    
    # 转换小区数据格式
    cells = []
    for cell in real_cell_data:
        cells.append({
            'id': cell['id'],
            'line_name': cell['line_name'],
            'site_name': cell['Transmitting_Point_Name'],
            'area': cell['area'],
            'site_type': cell['site_type'],
            'bbu_name': cell['bbu_name'],
            'celname': cell['celname'],
            'CGI': cell['CGI'],
            'cpId': cell['cpId'],
            'rru_id': cell['rru_id']
        })
    
    print(f"\n小区数据加载完成，共 {len(cells)} 个小区")
    for cell in cells:
        print(f"  - 小区: {cell['celname']}, CGI: {cell['CGI']}, CPID: {cell['cpId']}, RRU ID: {cell['rru_id']}")
    
    total_alarms = len(real_alarm_data)
    matched_alarms = 0
    
    for i, alarm in enumerate(real_alarm_data):
        print(f"\n测试告警 {i+1}/{total_alarms}:")
        print(f"告警代码: {alarm['alarm_code_name']}")
        print(f"告警标题: {alarm['alarm_title']}")
        print(f"告警原因: {alarm['alarm_reason']}")
        
        # 匹配告警到小区
        matched_cells = match_alarm_to_cell(alarm, cells)
        
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

# 测试告警信息提取
def test_alarm_info_extraction():
    """测试告警信息提取"""
    print("\n" + "="*80)
    print("开始测试告警信息提取")
    print("="*80)
    
    for i, alarm in enumerate(real_alarm_data):
        print(f"\n测试告警 {i+1}:")
        print(f"告警代码: {alarm['alarm_code_name']}")
        print(f"告警原因: {alarm['alarm_reason']}")
        
        # 提取告警信息
        extracted_info = extract_alarm_info(alarm)
        
        print(f"提取结果:")
        print(f"  CPID: {extracted_info['extracted_cpid']}")
        print(f"  逻辑小区ID: {extracted_info['extracted_cgi']}")
        print(f"  RACK: {extracted_info['extracted_rack']}")
        print(f"  gNBId: {extracted_info['extracted_gnb_id']}")
        print(f"  eNBId: {extracted_info['extracted_enb_id']}")
        
        print("-"*80)

if __name__ == "__main__":
    # 测试告警信息提取
    test_alarm_info_extraction()
    
    # 测试告警匹配
    test_real_alarm_matching()
