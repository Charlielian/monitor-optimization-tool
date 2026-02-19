#!/usr/bin/env python3
"""
告警数据诊断脚本

此脚本用于诊断告警数据状态，帮助快速定位告警查询返回0条记录的原因。

功能：
1. 检查中兴和诺基亚告警表是否存在
2. 查询告警表的总记录数
3. 查询最新数据的时间戳
4. 计算最新数据距离现在的时间差
5. 提供修复建议

使用方法：
    python diagnose_alarm_data.py

需求验证：
    - Requirements 6.1: 查询告警表总记录数和最新数据时间
    - Requirements 6.2: 对比查询时间范围和最新数据时间
    - Requirements 6.3: 提供诊断信息和修复建议
"""

import sys
import logging
from datetime import datetime
from config import Config
from db.mysql import MySQLClient
from services.alarm_grid_matcher import AlarmGridMatcher


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "-" * 70)
    print(f"  {title}")
    print("-" * 70)


def format_time_diff(hours: float) -> str:
    """格式化时间差"""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes} 分钟"
    elif hours < 24:
        return f"{hours:.1f} 小时"
    else:
        days = int(hours / 24)
        remaining_hours = hours % 24
        return f"{days} 天 {remaining_hours:.1f} 小时"


def diagnose_alarm_data():
    """执行告警数据诊断"""
    
    print_header("告警数据诊断工具")
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载配置
    try:
        config = Config()
        logger.info("配置加载成功")
    except Exception as e:
        print(f"\n❌ 错误: 无法加载配置文件")
        print(f"   原因: {e}")
        print(f"\n修复建议:")
        print(f"   1. 确保 config.json 文件存在")
        print(f"   2. 检查配置文件格式是否正确")
        return 1
    
    # 连接MySQL
    try:
        mysql_client = MySQLClient(config.mysql_config)
        logger.info("MySQL连接成功")
    except Exception as e:
        print(f"\n❌ 错误: 无法连接到MySQL数据库")
        print(f"   原因: {e}")
        print(f"\n修复建议:")
        print(f"   1. 检查MySQL服务是否运行")
        print(f"   2. 验证config.json中的MySQL配置")
        print(f"   3. 确认网络连接正常")
        return 1
    
    # 创建告警匹配器
    try:
        matcher = AlarmGridMatcher(mysql_client)
        logger.info("告警匹配器初始化成功")
    except Exception as e:
        print(f"\n❌ 错误: 无法初始化告警匹配器")
        print(f"   原因: {e}")
        return 1
    
    # 执行诊断
    print_section("正在诊断告警数据...")
    
    try:
        diag_result = matcher.diagnose_alarm_data()
    except Exception as e:
        print(f"\n❌ 错误: 诊断过程失败")
        print(f"   原因: {e}")
        return 1
    
    # 显示诊断结果
    print_section("中兴告警表 (cur_alarm)")
    
    if diag_result['zte_table_exists']:
        print(f"✓ 表状态: 存在")
        print(f"  总记录数: {diag_result['zte_total_count']:,}")
        
        if diag_result['zte_latest_time']:
            print(f"  最新数据时间: {diag_result['zte_latest_time']}")
            
            if 'zte_time_diff_hours' in diag_result:
                time_diff = diag_result['zte_time_diff_hours']
                print(f"  数据新鲜度: {format_time_diff(time_diff)} 前")
                
                # 评估数据新鲜度
                if time_diff < 1:
                    print(f"  状态: ✓ 数据很新鲜")
                elif time_diff < 6:
                    print(f"  状态: ⚠️ 数据较新，但可能需要检查更新频率")
                elif time_diff < 24:
                    print(f"  状态: ⚠️ 数据有些旧，建议检查数据更新")
                else:
                    print(f"  状态: ❌ 数据过旧，数据更新可能存在问题")
        else:
            print(f"  最新数据时间: 无")
            print(f"  状态: ❌ 表中无数据")
    else:
        print(f"✗ 表状态: 不存在或无法访问")
    
    print_section("诺基亚告警表 (cur_alarm_nokia)")
    
    if diag_result['nokia_table_exists']:
        print(f"✓ 表状态: 存在")
        print(f"  总记录数: {diag_result['nokia_total_count']:,}")
        
        if diag_result['nokia_latest_time']:
            print(f"  最新数据时间: {diag_result['nokia_latest_time']}")
            
            if 'nokia_time_diff_hours' in diag_result:
                time_diff = diag_result['nokia_time_diff_hours']
                print(f"  数据新鲜度: {format_time_diff(time_diff)} 前")
                
                # 评估数据新鲜度
                if time_diff < 1:
                    print(f"  状态: ✓ 数据很新鲜")
                elif time_diff < 6:
                    print(f"  状态: ⚠️ 数据较新，但可能需要检查更新频率")
                elif time_diff < 24:
                    print(f"  状态: ⚠️ 数据有些旧，建议检查数据更新")
                else:
                    print(f"  状态: ❌ 数据过旧，数据更新可能存在问题")
        else:
            print(f"  最新数据时间: 无")
            print(f"  状态: ❌ 表中无数据")
    else:
        print(f"✗ 表状态: 不存在或无法访问")
        print(f"  说明: 如果只使用中兴告警，这是正常的")
    
    # 生成修复建议
    print_section("诊断结果和修复建议")
    
    issues_found = []
    suggestions = []
    
    # 检查中兴告警
    if not diag_result['zte_table_exists']:
        issues_found.append("中兴告警表不存在")
        suggestions.append("1. 确认数据库中是否创建了 cur_alarm 表")
        suggestions.append("2. 检查数据库连接配置是否正确")
    elif diag_result['zte_total_count'] == 0:
        issues_found.append("中兴告警表为空")
        suggestions.append("1. 检查告警数据导入流程是否正常运行")
        suggestions.append("2. 确认告警数据源是否有数据")
    elif 'zte_time_diff_hours' in diag_result and diag_result['zte_time_diff_hours'] > 24:
        issues_found.append("中兴告警数据过旧")
        suggestions.append("1. 检查告警数据更新任务是否正常运行")
        suggestions.append("2. 查看数据导入日志，确认是否有错误")
        suggestions.append("3. 如果使用定时任务，确认任务调度是否正常")
    
    # 检查诺基亚告警
    if diag_result['nokia_table_exists']:
        if diag_result['nokia_total_count'] == 0:
            issues_found.append("诺基亚告警表为空")
            suggestions.append("4. 检查诺基亚告警数据导入流程")
        elif 'nokia_time_diff_hours' in diag_result and diag_result['nokia_time_diff_hours'] > 24:
            issues_found.append("诺基亚告警数据过旧")
            suggestions.append("4. 检查诺基亚告警数据更新任务")
    
    # 显示结果
    if not issues_found:
        print("\n✓ 未发现明显问题")
        print("\n如果告警查询仍返回0条记录，可能的原因：")
        print("  1. 查询时间范围内确实没有告警")
        print("  2. 告警匹配逻辑需要调整")
        print("  3. 小区映射表(cell_mapping)数据不完整")
        print("\n建议：")
        print("  - 使用更大的时间范围查询（如24小时）")
        print("  - 检查日志中的详细匹配信息")
        print("  - 验证cell_mapping表是否包含所有小区")
    else:
        print("\n发现以下问题：")
        for i, issue in enumerate(issues_found, 1):
            print(f"  {i}. {issue}")
        
        print("\n修复建议：")
        for suggestion in suggestions:
            print(f"  {suggestion}")
    
    # 显示配置信息
    print_section("当前配置")
    print(f"默认查询时间范围: {matcher.default_query_hours} 小时")
    print(f"最大自适应扩展范围: {matcher.max_adaptive_hours} 小时")
    
    if 'zte_time_diff_hours' in diag_result:
        zte_diff = diag_result['zte_time_diff_hours']
        if zte_diff > matcher.default_query_hours:
            print(f"\n⚠️ 注意: 中兴告警最新数据({format_time_diff(zte_diff)}前)")
            print(f"         超出默认查询范围({matcher.default_query_hours}小时)")
            print(f"         系统会自动扩大查询范围")
    
    if 'nokia_time_diff_hours' in diag_result:
        nokia_diff = diag_result['nokia_time_diff_hours']
        if nokia_diff > matcher.default_query_hours:
            print(f"\n⚠️ 注意: 诺基亚告警最新数据({format_time_diff(nokia_diff)}前)")
            print(f"         超出默认查询范围({matcher.default_query_hours}小时)")
            print(f"         系统会自动扩大查询范围")
    
    # 关闭连接
    try:
        mysql_client.close()
    except Exception:
        pass
    
    print_header("诊断完成")
    
    # 返回状态码
    if issues_found:
        return 1
    else:
        return 0


if __name__ == '__main__':
    try:
        sys.exit(diagnose_alarm_data())
    except KeyboardInterrupt:
        print("\n\n诊断被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 未预期的错误: {e}")
        logger.exception("诊断过程中发生异常")
        sys.exit(1)
