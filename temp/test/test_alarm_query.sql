-- 测试告警查询性能

USE optimization_toolbox;

-- 1. 测试今日告警统计（优化后）
SELECT '=== 今日告警统计（优化后）===' as test;
SELECT COUNT(*) as total
FROM cur_alarm
WHERE DATE(import_time) = CURDATE();

-- 2. 测试当前告警统计（最近1小时）
SELECT '=== 当前告警统计（最近1小时）===' as test;
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN alarm_level = '紧急' THEN 1 ELSE 0 END) as urgent,
    SUM(CASE WHEN alarm_level = '重要' THEN 1 ELSE 0 END) as important,
    SUM(CASE WHEN alarm_level = '主要' THEN 1 ELSE 0 END) as major,
    SUM(CASE WHEN alarm_level = '一般' THEN 1 ELSE 0 END) as normal
FROM cur_alarm
WHERE import_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR);

-- 3. 测试按网元ID过滤
SELECT '=== 按网元ID过滤（单个）===' as test;
SELECT COUNT(*) as total
FROM cur_alarm
WHERE import_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
    AND ne_id LIKE '%12635595%';

-- 4. 测试按告警名称过滤
SELECT '=== 按告警名称过滤 ===' as test;
SELECT COUNT(*) as total
FROM cur_alarm
WHERE import_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
    AND (alarm_code_name LIKE '%网元断链%' OR alarm_code_name LIKE '%网元断链%');

-- 5. 查看索引使用情况
SELECT '=== 索引列表 ===' as test;
SHOW INDEX FROM cur_alarm;

-- 6. 查看表大小
SELECT '=== 表大小 ===' as test;
SELECT 
    table_name,
    table_rows,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS "Size_MB",
    ROUND((data_length / 1024 / 1024), 2) AS "Data_MB",
    ROUND((index_length / 1024 / 1024), 2) AS "Index_MB"
FROM information_schema.TABLES
WHERE table_schema = "optimization_toolbox"
    AND table_name = "cur_alarm";
