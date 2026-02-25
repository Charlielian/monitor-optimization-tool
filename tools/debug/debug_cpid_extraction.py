#!/usr/bin/env python3
"""
调试超级小区CP退服告警匹配逻辑
"""
import json
import re
from db.mysql import MySQLClient

# 读取配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    mysql_config = config['mysql_config']

# 连接数据库
mysql = MySQLClient(mysql_config)

print("=" * 80)
print("调试超级小区CP退服告警的CPID和逻辑小区ID提取")
print("=" * 80)

# 查询所有超级小区CP退服告警
cp_alarms = mysql.fetch_all("""
    SELECT alarm_code_name, alarm_title, ne_id, alarm_object_name,
           alarm_reason, additional_info, occur_time
    FROM cur_alarm
    WHERE (alarm_code_name LIKE '%超级小区CP退服%' OR alarm_title LIKE '%超级小区CP退服%')
    ORDER BY occur_time DESC
    LIMIT 50
""")

print(f"\n找到 {len(cp_alarms)} 条超级小区CP退服告警\n")

# 模拟代码中的提取逻辑
for i, alarm in enumerate(cp_alarms, 1):
    alarm_name = alarm.get('alarm_code_name', '') or alarm.get('alarm_title', '')
    alarm_desc = alarm.get('alarm_reason', '')
    additional_info = alarm.get('additional_info', '')
    ne_id = alarm.get('ne_id', '')

    # 提取CPID
    extracted_cpid = None
    if additional_info and ('CPID' in str(additional_info) or 'CP ID' in str(additional_info)):
        match = re.search(r'(?:CPID|CP ID)[:：]\s*(\d+)', str(additional_info))
        if match:
            extracted_cpid = match.group(1)

    if not extracted_cpid and ('CPID' in str(alarm_desc) or 'CP ID' in str(alarm_desc)):
        match = re.search(r'(?:CPID|CP ID)[:：]\s*(\d+)', str(alarm_desc))
        if match:
            extracted_cpid = match.group(1)

    # 提取逻辑小区ID
    extracted_cgi = None
    if additional_info and '逻辑小区ID' in str(additional_info):
        match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(additional_info))
        if match:
            extracted_cgi = match.group(1)

    if not extracted_cgi and '逻辑小区ID' in str(alarm_desc):
        match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(alarm_desc))
        if match:
            extracted_cgi = match.group(1)

    print(f"告警 {i}:")
    print(f"  告警名称: {alarm_name}")
    print(f"  网元ID: {ne_id}")
    print(f"  提取的CPID: {extracted_cpid}")
    print(f"  提取的逻辑小区ID: {extracted_cgi}")

    # 检查是否会匹配到CGI 460-00-12672294-1
    if extracted_cgi == '460-00-12672294-1':
        print(f"  ⚠️  这个告警会匹配到CGI 460-00-12672294-1")

    print()

    if i >= 20:  # 只显示前20个
        break

# 统计提取情况
print("=" * 80)
print("提取统计:")
print("=" * 80)

cpid_extracted = 0
cgi_extracted = 0
both_extracted = 0

for alarm in cp_alarms:
    alarm_desc = alarm.get('alarm_reason', '')
    additional_info = alarm.get('additional_info', '')

    # 提取CPID
    extracted_cpid = None
    if additional_info and ('CPID' in str(additional_info) or 'CP ID' in str(additional_info)):
        match = re.search(r'(?:CPID|CP ID)[:：]\s*(\d+)', str(additional_info))
        if match:
            extracted_cpid = match.group(1)
            cpid_extracted += 1

    # 提取逻辑小区ID
    extracted_cgi = None
    if additional_info and '逻辑小区ID' in str(additional_info):
        match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(additional_info))
        if match:
            extracted_cgi = match.group(1)
            cgi_extracted += 1

    if extracted_cpid and extracted_cgi:
        both_extracted += 1

print(f"总告警数: {len(cp_alarms)}")
print(f"成功提取CPID的告警数: {cpid_extracted}")
print(f"成功提取逻辑小区ID的告警数: {cgi_extracted}")
print(f"同时提取CPID和逻辑小区ID的告警数: {both_extracted}")

if both_extracted < len(cp_alarms):
    print(f"\n⚠️  有 {len(cp_alarms) - both_extracted} 条告警未能同时提取CPID和逻辑小区ID")
    print("这些告警将不会被匹配（这是正确的行为）")

mysql.close()
