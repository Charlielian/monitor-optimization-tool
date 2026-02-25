-- 告警表性能优化索引
-- 用于加速告警查询页面

USE optimization_toolbox;

-- 检查并删除已存在的索引（如果需要重建）
-- DROP INDEX IF EXISTS idx_ne_id ON cur_alarm;
-- DROP INDEX IF EXISTS idx_alarm_level ON cur_alarm;
-- DROP INDEX IF EXISTS idx_alarm_code_name ON cur_alarm;
-- DROP INDEX IF EXISTS idx_import_time_level ON cur_alarm;
-- DROP INDEX IF EXISTS idx_import_time_ne_id ON cur_alarm;

-- 1. 为 ne_id 添加索引（用于网元ID过滤）
-- 注意：ne_id 是 TEXT 类型，需要指定前缀长度
CREATE INDEX idx_ne_id ON cur_alarm(ne_id(50));

-- 2. 为 alarm_level 添加索引（用于告警级别统计）
CREATE INDEX idx_alarm_level ON cur_alarm(alarm_level(20));

-- 3. 为 alarm_code_name 添加索引（用于告警名称过滤）
CREATE INDEX idx_alarm_code_name ON cur_alarm(alarm_code_name(100));

-- 4. 复合索引：import_time + alarm_level（用于当前告警统计）
CREATE INDEX idx_import_time_level ON cur_alarm(import_time, alarm_level(20));

-- 5. 复合索引：import_time + ne_id（用于按网元ID过滤当前告警）
CREATE INDEX idx_import_time_ne_id ON cur_alarm(import_time, ne_id(50));

-- 查看索引创建结果
SHOW INDEX FROM cur_alarm;

-- 分析表以更新统计信息
ANALYZE TABLE cur_alarm;
