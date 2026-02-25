"""
快速诊断网格名称问题
"""

from config import Config
from db.mysql import MySQLClient

def diagnose():
    cfg = Config()
    mysql = MySQLClient(cfg.mysql_config)
    
    print("=" * 80)
    print("网格名称诊断")
    print("=" * 80)
    
    # 1. 检查grid_info表
    print("\n1. grid_info表统计")
    print("-" * 80)
    
    sql1 = "SELECT COUNT(*) as total FROM grid_info"
    result1 = mysql.fetch_one(sql1)
    print(f"grid_info表总记录数: {result1.get('total', 0) if result1 else 0}")
    
    sql2 = "SELECT COUNT(*) as count FROM grid_info WHERE grid_name IS NOT NULL AND grid_name != ''"
    result2 = mysql.fetch_one(sql2)
    print(f"有网格名称的记录数: {result2.get('count', 0) if result2 else 0}")
    
    sql3 = "SELECT COUNT(*) as count FROM grid_info WHERE grid_name IS NULL OR grid_name = ''"
    result3 = mysql.fetch_one(sql3)
    print(f"网格名称为空的记录数: {result3.get('count', 0) if result3 else 0}")
    
    # 2. 检查cell_mapping表
    print("\n2. cell_mapping表统计")
    print("-" * 80)
    
    sql4 = "SELECT COUNT(DISTINCT grid_id) as count FROM cell_mapping WHERE grid_id IS NOT NULL"
    result4 = mysql.fetch_one(sql4)
    print(f"cell_mapping表中不同网格数: {result4.get('count', 0) if result4 else 0}")
    
    # 3. 对比两个表
    print("\n3. 两表对比")
    print("-" * 80)
    
    sql5 = """
        SELECT COUNT(DISTINCT cm.grid_id) as count
        FROM cell_mapping cm
        INNER JOIN grid_info gi ON cm.grid_id = gi.grid_id
    """
    result5 = mysql.fetch_one(sql5)
    print(f"两表都有的网格数: {result5.get('count', 0) if result5 else 0}")
    
    sql6 = """
        SELECT COUNT(DISTINCT cm.grid_id) as count
        FROM cell_mapping cm
        LEFT JOIN grid_info gi ON cm.grid_id = gi.grid_id
        WHERE gi.grid_id IS NULL
    """
    result6 = mysql.fetch_one(sql6)
    missing_count = result6.get('count', 0) if result6 else 0
    print(f"cell_mapping有但grid_info没有的网格数: {missing_count}")
    
    # 4. 显示示例数据
    print("\n4. 示例数据（前5个网格）")
    print("-" * 80)
    
    sql7 = """
        SELECT 
            cm.grid_id,
            cm.grid_name as cm_grid_name,
            gi.grid_name as gi_grid_name,
            COALESCE(
                NULLIF(gi.grid_name, ''), 
                NULLIF(cm.grid_name, ''), 
                cm.grid_id
            ) as final_grid_name,
            gi.grid_pp
        FROM cell_mapping cm
        LEFT JOIN grid_info gi ON cm.grid_id = gi.grid_id
        WHERE cm.grid_id IS NOT NULL
        GROUP BY cm.grid_id
        ORDER BY cm.grid_id
        LIMIT 5
    """
    results = mysql.fetch_all(sql7)
    
    print(f"{'网格ID':<15} {'CM名称':<20} {'GI名称':<20} {'最终名称':<20} {'督办标签':<20}")
    print("-" * 100)
    for row in results:
        print(f"{row['grid_id']:<15} "
              f"{(row['cm_grid_name'] or 'NULL'):<20} "
              f"{(row['gi_grid_name'] or 'NULL'):<20} "
              f"{row['final_grid_name']:<20} "
              f"{(row['grid_pp'] or '-'):<20}")
    
    # 5. 如果有缺失的网格，显示详情
    if missing_count > 0:
        print(f"\n5. cell_mapping有但grid_info没有的网格（前5个）")
        print("-" * 80)
        
        sql8 = """
            SELECT 
                cm.grid_id,
                cm.grid_name,
                COUNT(*) as cell_count
            FROM cell_mapping cm
            LEFT JOIN grid_info gi ON cm.grid_id = gi.grid_id
            WHERE gi.grid_id IS NULL AND cm.grid_id IS NOT NULL
            GROUP BY cm.grid_id, cm.grid_name
            ORDER BY cm.grid_id
            LIMIT 5
        """
        missing_grids = mysql.fetch_all(sql8)
        
        print(f"{'网格ID':<15} {'CM名称':<30} {'小区数':<10}")
        print("-" * 60)
        for row in missing_grids:
            print(f"{row['grid_id']:<15} {(row['grid_name'] or 'NULL'):<30} {row['cell_count']:<10}")
        
        print(f"\n建议：将这些网格补充到grid_info表中")
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)


if __name__ == "__main__":
    diagnose()
