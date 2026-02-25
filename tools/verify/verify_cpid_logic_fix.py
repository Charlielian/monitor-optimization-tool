#!/usr/bin/env python3
"""
验证超级小区CP退服告警匹配逻辑修复
检查CGI 460-00-12672294-1是否还会错误匹配告警
"""
import json
from db.mysql import MySQLClient
from services.hsr_health_check import HSRHealthCheckService

def main():
    print("=" * 80)
    print("验证超级小区CP退服告警匹配逻辑修复")
    print("=" * 80)

    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        mysql_config = config['mysql_config']

    # 连接数据库
    mysql_client = MySQLClient(mysql_config)

    # 1. 检查CGI 460-00-12672294-1的实际告警情况
    print("\n步骤1: 检查CGI 460-00-12672294-1的实际告警情况")
    print("-" * 80)

    # 从CGI提取网元ID
    ne_id = '12672294'
    print(f"CGI: 460-00-12672294-1")
    print(f"网元ID: {ne_id}")

    # 查询这个网元的告警
    alarms = mysql_client.fetch_all(f"""
        SELECT COUNT(*) as count
        FROM cur_alarm
        WHERE ne_id = '{ne_id}'
    """)
    alarm_count = alarms[0]['count'] if alarms else 0
    print(f"网元ID={ne_id}的告警数量: {alarm_count}")

    if alarm_count == 0:
        print("✓ 这个网元没有告警（正确）")
    else:
        print("✗ 这个网元有告警")

    # 2. 执行健康检查
    print("\n步骤2: 执行健康检查")
    print("-" * 80)
    print("正在执行健康检查...")

    hsr_service = HSRHealthCheckService(mysql_client, None)
    result = hsr_service.check_hsr_health()

    if 'error' in result:
        print(f"✗ 健康检查失败: {result['error']}")
        mysql_client.close()
        return

    print(f"✓ 健康检查完成")

    # 3. 检查CGI 460-00-12672294-1的匹配结果
    print("\n步骤3: 检查CGI 460-00-12672294-1的匹配结果")
    print("-" * 80)

    target_cgi = '460-00-12672294-1'
    target_cells = [cell for cell in result.get('cells', []) if cell.get('cgi') == target_cgi]

    print(f"找到 {len(target_cells)} 个CGI为 {target_cgi} 的小区记录\n")

    has_wrong_match = False
    for i, cell in enumerate(target_cells, 1):
        cpid = cell.get('cpId', '')
        has_alarm = cell.get('has_alarm', False)
        alarm_count = cell.get('alarm_count', 0)

        print(f"小区 {i}:")
        print(f"  小区名称: {cell.get('celname', '')}")
        print(f"  CGI: {cell.get('cgi', '')}")
        print(f"  cpId: {cpid}")
        print(f"  发射点: {cell.get('site_name', '')}")
        print(f"  有告警: {has_alarm}")
        print(f"  告警数量: {alarm_count}")

        if has_alarm:
            print(f"  告警详情:")
            for alarm in cell.get('alarm_details', []):
                print(f"    - {alarm.get('alarm_name', '')} (CPID={alarm.get('extracted_cpid', '')})")
            has_wrong_match = True
        print()

    # 4. 验证结果
    print("=" * 80)
    print("验证结果:")
    print("=" * 80)

    if alarm_count == 0 and not has_wrong_match:
        print("✓ 修复成功！")
        print(f"  网元ID={ne_id}没有告警")
        print(f"  CGI {target_cgi} 的小区也没有匹配到告警")
        print("\n超级小区CP退服告警匹配逻辑已正确修复。")
    elif alarm_count == 0 and has_wrong_match:
        print("✗ 修复失败！")
        print(f"  网元ID={ne_id}没有告警")
        print(f"  但CGI {target_cgi} 的小区仍然匹配到了告警")
        print("\n问题：仍然存在错误匹配，只按CPID匹配而没有检查逻辑小区ID。")
    else:
        print("⚠️  网元有告警，需要进一步检查")

    # 5. 统计总体匹配情况
    print("\n" + "=" * 80)
    print("总体匹配统计:")
    print("=" * 80)

    total_cells = result.get('total_cells', 0)
    cells_with_cp_alarms = 0

    for cell in result.get('cells', []):
        if cell.get('has_alarm'):
            for alarm in cell.get('alarm_details', []):
                if '超级小区CP退服' in alarm.get('alarm_name', ''):
                    cells_with_cp_alarms += 1
                    break

    print(f"总小区数: {total_cells}")
    print(f"匹配到超级小区CP退服告警的小区数: {cells_with_cp_alarms}")

    # 关闭连接
    mysql_client.close()

if __name__ == "__main__":
    main()
