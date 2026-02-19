#!/usr/bin/env python3
"""验证网格体检功能是否正常工作"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from db.mysql import MySQLClient
from db.pg import PostgresClient
from services.grid_health_check import GridHealthCheckService

def verify():
    """验证网格体检功能"""
    
    print("=" * 80)
    print("验证网格体检功能")
    print("=" * 80)
    print()
    
    try:
        # 初始化
        cfg = Config()
        mysql_client = MySQLClient(cfg.mysql_config)
        pg_client = PostgresClient(cfg.pgsql_config)
        service = GridHealthCheckService(mysql_client, pg_client)
        
        # 测试1：全量网格体检（汇总）
        print("测试1：全量网格体检（汇总）")
        print("-" * 80)
        
        results = service.check_all_grids_health()
        
        if not results:
            print("❌ 没有获取到网格数据")
            return False
        
        print(f"✓ 成功获取 {len(results)} 个网格的体检结果")
        print()
        
        # 显示前5个网格的统计
        print("前5个网格统计:")
        for i, grid in enumerate(results[:5], 1):
            print(f"  {i}. {grid['grid_name']} ({grid['grid_id']})")
            print(f"     总小区: {grid['total_cells']}, "
                  f"健康: {grid['healthy_cells']}, "
                  f"不健康: {grid['unhealthy_cells']}, "
                  f"健康率: {grid['healthy_rate']}%")
        
        print()
        
        # 测试2：单个网格详细体检
        print("测试2：单个网格详细体检")
        print("-" * 80)
        
        test_grid_id = results[0]['grid_id']
        print(f"测试网格: {test_grid_id}")
        
        detail_result = service.check_grid_health(test_grid_id)
        
        if 'error' in detail_result:
            print(f"❌ 体检失败: {detail_result['error']}")
            return False
        
        print(f"✓ 体检成功")
        print(f"  网格名称: {detail_result['grid_name']}")
        print(f"  总小区数: {detail_result['total_cells']}")
        print(f"  健康小区: {detail_result['healthy_cells']}")
        print(f"  不健康小区: {detail_result['unhealthy_cells']}")
        print(f"  健康率: {detail_result['healthy_rate']}%")
        print()
        
        # 统计不健康原因
        reason_stats = {}
        for cell in detail_result['cells']:
            if cell['status'] == 'unhealthy':
                reason = cell['reason']
                reason_stats[reason] = reason_stats.get(reason, 0) + 1
        
        if reason_stats:
            print("  不健康原因统计:")
            for reason, count in sorted(reason_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"    - {reason}: {count} 个小区")
        
        print()
        
        # 测试3：检查是否有告警数据
        print("测试3：检查告警数据")
        print("-" * 80)
        
        cells_with_alarms = [c for c in detail_result['cells'] if c['alarm_count'] > 0]
        
        if cells_with_alarms:
            print(f"✓ 发现 {len(cells_with_alarms)} 个小区有告警")
            print("  告警示例:")
            for cell in cells_with_alarms[:3]:
                print(f"    {cell['celname']} ({cell['cgi']}): {cell['alarm_count']} 条告警")
                for alarm in cell['alarms'][:2]:
                    print(f"      - {alarm['alarm_name']} ({alarm['severity']})")
        else:
            print("  该网格下的小区暂无影响性能的告警")
        
        print()
        print("=" * 80)
        print("✓ 所有验证通过！网格体检功能正常")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
