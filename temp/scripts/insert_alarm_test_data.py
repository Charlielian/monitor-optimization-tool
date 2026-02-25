"""插入告警测试数据"""
from datetime import datetime, timedelta
import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from db.mysql import MySQLClient

# 从config.json读取MySQL配置
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
    mysql_config = config['mysql_config']

def create_test_data():
    """创建测试数据"""
    print("=" * 60)
    print("插入告警测试数据")
    print("=" * 60)
    
    try:
        # 连接MySQL
        print("\n1. 连接MySQL...")
        mysql_client = MySQLClient(mysql_config)
        print("✓ MySQL连接成功")
        
        # 创建表（如果不存在）
        print("\n2. 创建cur_alarm表...")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS `cur_alarm` (
          `id` INT AUTO_INCREMENT PRIMARY KEY,
          `alarm_id` VARCHAR(100),
          `alarm_name` VARCHAR(200),
          `alarm_level` VARCHAR(50),
          `alarm_type` VARCHAR(100),
          `alarm_source` VARCHAR(100),
          `alarm_time` DATETIME,
          `alarm_status` VARCHAR(50),
          `alarm_desc` TEXT,
          `cell_id` VARCHAR(100),
          `cell_name` VARCHAR(200),
          `network_type` VARCHAR(10),
          `import_time` DATETIME,
          `import_filename` VARCHAR(200),
          `import_batch` VARCHAR(100),
          INDEX `idx_alarm_time` (`alarm_time`),
          INDEX `idx_import_time` (`import_time`),
          INDEX `idx_cell_id` (`cell_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        
        with mysql_client.engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text(create_table_sql))
            conn.commit()
        print("✓ 表创建成功")
        
        # 插入当前告警数据
        print("\n3. 插入当前告警数据...")
        now = datetime.now()
        current_alarms = [
            ('ALM001', '小区退服告警', '紧急', '设备告警', 'OMC', now - timedelta(minutes=10), '未处理', 
             '小区无法正常工作，需要立即处理', '460-00-12345-1', '测试小区A', '4G', 
             now - timedelta(minutes=5), 'alarm_20250105.csv', 'batch001'),
            
            ('ALM002', '传输中断告警', '紧急', '传输告警', 'OMC', now - timedelta(minutes=15), '处理中', 
             '传输链路中断，影响业务', '460-00-12345-2', '测试小区B', '5G', 
             now - timedelta(minutes=5), 'alarm_20250105.csv', 'batch001'),
            
            ('ALM003', 'PRB利用率过高', '重要', '性能告警', 'OMC', now - timedelta(minutes=20), '未处理', 
             'PRB利用率超过90%，可能影响用户体验', '460-00-12345-3', '测试小区C', '4G', 
             now - timedelta(minutes=5), 'alarm_20250105.csv', 'batch001'),
            
            ('ALM004', '接通率低告警', '重要', '性能告警', 'OMC', now - timedelta(minutes=25), '未处理', 
             '无线接通率低于95%', '460-00-12345-4', '测试小区D', '5G', 
             now - timedelta(minutes=5), 'alarm_20250105.csv', 'batch001'),
            
            ('ALM005', '干扰告警', '一般', '质量告警', 'OMC', now - timedelta(minutes=30), '已处理', 
             '小区干扰水平较高', '460-00-12345-5', '测试小区E', '4G', 
             now - timedelta(minutes=5), 'alarm_20250105.csv', 'batch001'),
            
            ('ALM006', '用户数过多', '一般', '容量告警', 'OMC', now - timedelta(minutes=35), '未处理', 
             'RRC连接用户数接近上限', '460-00-12345-6', '测试小区F', '5G', 
             now - timedelta(minutes=5), 'alarm_20250105.csv', 'batch001'),
        ]
        
        insert_sql = """
        INSERT INTO `cur_alarm` (
          `alarm_id`, `alarm_name`, `alarm_level`, `alarm_type`, 
          `alarm_source`, `alarm_time`, `alarm_status`, `alarm_desc`,
          `cell_id`, `cell_name`, `network_type`,
          `import_time`, `import_filename`, `import_batch`
        ) VALUES (
          :alarm_id, :alarm_name, :alarm_level, :alarm_type,
          :alarm_source, :alarm_time, :alarm_status, :alarm_desc,
          :cell_id, :cell_name, :network_type,
          :import_time, :import_filename, :import_batch
        )
        """
        
        with mysql_client.engine.connect() as conn:
            from sqlalchemy import text
            for alarm in current_alarms:
                params = {
                    'alarm_id': alarm[0],
                    'alarm_name': alarm[1],
                    'alarm_level': alarm[2],
                    'alarm_type': alarm[3],
                    'alarm_source': alarm[4],
                    'alarm_time': alarm[5],
                    'alarm_status': alarm[6],
                    'alarm_desc': alarm[7],
                    'cell_id': alarm[8],
                    'cell_name': alarm[9],
                    'network_type': alarm[10],
                    'import_time': alarm[11],
                    'import_filename': alarm[12],
                    'import_batch': alarm[13],
                }
                conn.execute(text(insert_sql), params)
            conn.commit()
        print(f"✓ 插入了 {len(current_alarms)} 条当前告警")
        
        # 插入历史告警数据
        print("\n4. 插入历史告警数据...")
        historical_alarms = [
            ('ALM007', '历史告警1', '重要', '设备告警', 'OMC', now - timedelta(days=2), '已处理', 
             '历史告警测试数据1', '460-00-12345-7', '测试小区G', '4G', 
             now - timedelta(days=2), 'alarm_20250103.csv', 'batch002'),
            
            ('ALM007', '历史告警1', '重要', '设备告警', 'OMC', now - timedelta(days=2), '已处理', 
             '历史告警测试数据1', '460-00-12345-7', '测试小区G', '4G', 
             now - timedelta(days=1), 'alarm_20250104.csv', 'batch003'),
            
            ('ALM008', '历史告警2', '一般', '性能告警', 'OMC', now - timedelta(days=3), '已处理', 
             '历史告警测试数据2', '460-00-12345-8', '测试小区H', '5G', 
             now - timedelta(days=3), 'alarm_20250102.csv', 'batch004'),
            
            ('ALM009', '历史告警3', '紧急', '传输告警', 'OMC', now - timedelta(days=5), '已处理', 
             '历史告警测试数据3', '460-00-12345-9', '测试小区I', '4G', 
             now - timedelta(days=5), 'alarm_20241231.csv', 'batch005'),
        ]
        
        with mysql_client.engine.connect() as conn:
            from sqlalchemy import text
            for alarm in historical_alarms:
                params = {
                    'alarm_id': alarm[0],
                    'alarm_name': alarm[1],
                    'alarm_level': alarm[2],
                    'alarm_type': alarm[3],
                    'alarm_source': alarm[4],
                    'alarm_time': alarm[5],
                    'alarm_status': alarm[6],
                    'alarm_desc': alarm[7],
                    'cell_id': alarm[8],
                    'cell_name': alarm[9],
                    'network_type': alarm[10],
                    'import_time': alarm[11],
                    'import_filename': alarm[12],
                    'import_batch': alarm[13],
                }
                conn.execute(text(insert_sql), params)
            conn.commit()
        print(f"✓ 插入了 {len(historical_alarms)} 条历史告警")
        
        # 验证数据
        print("\n5. 验证数据...")
        
        # 统计当前告警
        count_sql = """
        SELECT 
          alarm_level,
          COUNT(*) as count
        FROM cur_alarm
        WHERE import_time >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
        GROUP BY alarm_level
        """
        stats = mysql_client.fetch_all(count_sql)
        print("  当前告警统计:")
        for stat in stats:
            print(f"    - {stat['alarm_level']}: {stat['count']} 条")
        
        # 统计总数
        total_sql = "SELECT COUNT(*) as total FROM cur_alarm"
        total = mysql_client.fetch_one(total_sql)
        print(f"  总告警数: {total['total']} 条")
        
        # 统计去重后的数量
        distinct_sql = """
        SELECT COUNT(*) as total FROM (
          SELECT DISTINCT 
            alarm_id, alarm_name, alarm_level, alarm_type,
            alarm_source, alarm_time, alarm_status, alarm_desc,
            cell_id, cell_name, network_type
          FROM cur_alarm
        ) as distinct_alarms
        """
        distinct = mysql_client.fetch_one(distinct_sql)
        print(f"  去重后告警数: {distinct['total']} 条")
        
        print("\n" + "=" * 60)
        print("✓ 测试数据插入成功！")
        print("=" * 60)
        print("\n现在可以访问 http://127.0.0.1:5000/alarm 查看告警监控页面")
        
        # 关闭连接
        mysql_client.close()
        
    except Exception as e:
        print(f"\n✗ 插入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_test_data()
