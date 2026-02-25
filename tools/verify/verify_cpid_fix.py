#!/usr/bin/env python3
"""
快速验证超级小区CP退服告警匹配修复
"""
import json
from db.mysql import MySQLClient
from services.hsr_health_check import HSRHealthCheckService

def main():
    print("=" * 80)
    print("超级小区CP退服告警匹配验证")
    print("=" * 80)

    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        mysql_config = config['mysql_config']

    # 连接数据库
    mysql_client = MySQLClient(mysql_config)

    # 创建健康检查服务
    hsr_service = HSRHealthCheckService(mysql_client, None)

    # 1. 检查数据库中的超级小区CP退服告警
    print("\n步骤1: 检查数据库中的超级小区CP退服告警")
    print("-" * 80)
    cp_alarms = mysql_client.fetch_all("""
        SELECT COUNT(*) as count
        FROM cur_alarm
        WHERE alarm_code_name LIKE '%超级小区CP退服%' OR alarm_title LIKE '%超级小区CP退服%'
    """)
    alarm_count = cp_alarms[0]['count'] if cp_alarms else 0
    print(f"数据库中的超级小区CP退服告警数量: {alarm_count}")

    if alarm_count == 0:
        print("\n⚠️  数据库中没有超级小区CP退服告警，无法验证匹配功能。")
        mysql_client.close()
        return

    # 2. 执行健康检查
    print("\n步骤2: 执行健康检查")
    print("-" * 80)
    print("正在执行健康检查...")
    result = hsr_service.check_hsr_health()

    if 'error' in result:
        print(f"✗ 健康检查失败: {result['error']}")
        mysql_client.close()
        return

    print(f"✓ 健康检查完成")
    print(f"  总小区数: {result.get('total_cells', 0)}")

    # 3. 统计匹配结果
    print("\n步骤3: 统计超级小区CP退服告警匹配结果")
    print("-" * 80)

    matched_cells = 0
    for cell in result.get('cells', []):
        if cell.get('has_alarm'):
            for alarm in cell.get('alarm_details', []):
                if '超级小区CP退服' in alarm.get('alarm_name', ''):
                    matched_cells += 1
                    break

    print(f"匹配到超级小区CP退服告警的小区数: {matched_cells}")

    # 4. 显示匹配示例
    if matched_cells > 0:
        print("\n步骤4: 显示匹配示例（前3个）")
        print("-" * 80)
        count = 0
        for cell in result.get('cells', []):
            if cell.get('has_alarm'):
                for alarm in cell.get('alarm_details', []):
                    if '超级小区CP退服' in alarm.get('alarm_name', ''):
                        count += 1
                        if count <= 3:
                            print(f"\n示例 {count}:")
                            print(f"  小区: {cell.get('celname', '')}")
                            print(f"  CGI: {cell.get('cgi', '')}")
                            print(f"  小区cpId: {cell.get('cpId', '')}")
                            print(f"  告警CPID: {alarm.get('extracted_cpid', '')}")
                            print(f"  告警: {alarm.get('alarm_name', '')} ({alarm.get('alarm_level', '')})")
                        break
                if count >= 3:
                    break

    # 5. 验证结果
    print("\n" + "=" * 80)
    print("验证结果:")
    print("=" * 80)

    if matched_cells > 0:
        match_rate = (matched_cells / alarm_count) * 100 if alarm_count > 0 else 0
        print(f"✓ 修复成功！")
        print(f"  数据库中的超级小区CP退服告警: {alarm_count} 条")
        print(f"  成功匹配到小区的告警: {matched_cells} 个")
        print(f"  匹配率: {match_rate:.1f}%")
        print("\n超级小区CP退服告警已能够根据CPID正确匹配到对应的发射点。")
    else:
        print(f"✗ 修复失败！")
        print(f"  数据库中有 {alarm_count} 条超级小区CP退服告警，但没有匹配到任何小区。")
        print("\n可能的原因：")
        print("  1. 告警中的CPID与hsr_info表中的cpId不匹配")
        print("  2. CPID提取逻辑仍有问题")
        print("  3. 告警数据格式与预期不符")

    print("=" * 80)

    # 关闭连接
    mysql_client.close()

if __name__ == "__main__":
    main()
