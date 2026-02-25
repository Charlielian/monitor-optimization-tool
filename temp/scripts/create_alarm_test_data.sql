-- 创建告警测试数据
-- 用于测试告警监控功能

-- 1. 创建cur_alarm表（如果不存在）
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 插入测试数据（当前告警）
INSERT INTO `cur_alarm` (
  `alarm_id`, `alarm_name`, `alarm_level`, `alarm_type`, 
  `alarm_source`, `alarm_time`, `alarm_status`, `alarm_desc`,
  `cell_id`, `cell_name`, `network_type`,
  `import_time`, `import_filename`, `import_batch`
) VALUES
-- 紧急告警
('ALM001', '小区退服告警', '紧急', '设备告警', 'OMC', NOW() - INTERVAL 10 MINUTE, '未处理', '小区无法正常工作，需要立即处理', 
 '460-00-12345-1', '测试小区A', '4G', NOW() - INTERVAL 5 MINUTE, 'alarm_20250105.csv', 'batch001'),

('ALM002', '传输中断告警', '紧急', '传输告警', 'OMC', NOW() - INTERVAL 15 MINUTE, '处理中', '传输链路中断，影响业务', 
 '460-00-12345-2', '测试小区B', '5G', NOW() - INTERVAL 5 MINUTE, 'alarm_20250105.csv', 'batch001'),

-- 重要告警
('ALM003', 'PRB利用率过高', '重要', '性能告警', 'OMC', NOW() - INTERVAL 20 MINUTE, '未处理', 'PRB利用率超过90%，可能影响用户体验', 
 '460-00-12345-3', '测试小区C', '4G', NOW() - INTERVAL 5 MINUTE, 'alarm_20250105.csv', 'batch001'),

('ALM004', '接通率低告警', '重要', '性能告警', 'OMC', NOW() - INTERVAL 25 MINUTE, '未处理', '无线接通率低于95%', 
 '460-00-12345-4', '测试小区D', '5G', NOW() - INTERVAL 5 MINUTE, 'alarm_20250105.csv', 'batch001'),

-- 一般告警
('ALM005', '干扰告警', '一般', '质量告警', 'OMC', NOW() - INTERVAL 30 MINUTE, '已处理', '小区干扰水平较高', 
 '460-00-12345-5', '测试小区E', '4G', NOW() - INTERVAL 5 MINUTE, 'alarm_20250105.csv', 'batch001'),

('ALM006', '用户数过多', '一般', '容量告警', 'OMC', NOW() - INTERVAL 35 MINUTE, '未处理', 'RRC连接用户数接近上限', 
 '460-00-12345-6', '测试小区F', '5G', NOW() - INTERVAL 5 MINUTE, 'alarm_20250105.csv', 'batch001');

-- 3. 插入历史告警数据（用于测试去重）
INSERT INTO `cur_alarm` (
  `alarm_id`, `alarm_name`, `alarm_level`, `alarm_type`, 
  `alarm_source`, `alarm_time`, `alarm_status`, `alarm_desc`,
  `cell_id`, `cell_name`, `network_type`,
  `import_time`, `import_filename`, `import_batch`
) VALUES
-- 同一个告警，不同的导入批次（测试去重）
('ALM007', '历史告警1', '重要', '设备告警', 'OMC', NOW() - INTERVAL 2 DAY, '已处理', '历史告警测试数据1', 
 '460-00-12345-7', '测试小区G', '4G', NOW() - INTERVAL 2 DAY, 'alarm_20250103.csv', 'batch002'),

('ALM007', '历史告警1', '重要', '设备告警', 'OMC', NOW() - INTERVAL 2 DAY, '已处理', '历史告警测试数据1', 
 '460-00-12345-7', '测试小区G', '4G', NOW() - INTERVAL 1 DAY, 'alarm_20250104.csv', 'batch003'),

('ALM008', '历史告警2', '一般', '性能告警', 'OMC', NOW() - INTERVAL 3 DAY, '已处理', '历史告警测试数据2', 
 '460-00-12345-8', '测试小区H', '5G', NOW() - INTERVAL 3 DAY, 'alarm_20250102.csv', 'batch004'),

('ALM009', '历史告警3', '紧急', '传输告警', 'OMC', NOW() - INTERVAL 5 DAY, '已处理', '历史告警测试数据3', 
 '460-00-12345-9', '测试小区I', '4G', NOW() - INTERVAL 5 DAY, 'alarm_20241231.csv', 'batch005');

-- 4. 查询验证
SELECT '当前告警统计' as info;
SELECT 
  alarm_level,
  COUNT(*) as count
FROM cur_alarm
WHERE import_time >= NOW() - INTERVAL 30 MINUTE
GROUP BY alarm_level;

SELECT '历史告警统计（去重前）' as info;
SELECT COUNT(*) as total FROM cur_alarm;

SELECT '历史告警统计（去重后）' as info;
SELECT COUNT(*) as total FROM (
  SELECT DISTINCT 
    alarm_id, alarm_name, alarm_level, alarm_type,
    alarm_source, alarm_time, alarm_status, alarm_desc,
    cell_id, cell_name, network_type
  FROM cur_alarm
) as distinct_alarms;

-- 5. 显示最新的告警
SELECT '最新告警列表' as info;
SELECT 
  alarm_time,
  alarm_level,
  alarm_name,
  cell_name,
  network_type,
  alarm_status
FROM cur_alarm
ORDER BY import_time DESC
LIMIT 10;
