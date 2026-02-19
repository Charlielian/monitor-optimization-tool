-- 数据库索引优化脚本
-- 用于提升查询性能

-- ============================================
-- PostgreSQL 索引优化
-- ============================================

-- 4G指标表索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_time ON metrics_4g(time DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_4g_cgi ON metrics_4g(cgi);
CREATE INDEX IF NOT EXISTS idx_metrics_4g_time_cgi ON metrics_4g(time DESC, cgi);
CREATE INDEX IF NOT EXISTS idx_metrics_4g_time_network ON metrics_4g(time DESC, network);

-- 5G指标表索引
CREATE INDEX IF NOT EXISTS idx_metrics_5g_time ON metrics_5g(time DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_5g_cgi ON metrics_5g(cgi);
CREATE INDEX IF NOT EXISTS idx_metrics_5g_time_cgi ON metrics_5g(time DESC, cgi);
CREATE INDEX IF NOT EXISTS idx_metrics_5g_time_network ON metrics_5g(time DESC, network);

-- 场景表索引（如果存在）
CREATE INDEX IF NOT EXISTS idx_scenarios_id ON scenarios(id);
CREATE INDEX IF NOT EXISTS idx_scenarios_name ON scenarios(name);

-- 场景小区关联表索引（如果存在）
CREATE INDEX IF NOT EXISTS idx_scenario_cells_scenario_id ON scenario_cells(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_cells_cgi ON scenario_cells(cgi);
CREATE INDEX IF NOT EXISTS idx_scenario_cells_network ON scenario_cells(network);

-- 复合索引优化（针对常见查询）
-- 时间范围 + CGI 查询
CREATE INDEX IF NOT EXISTS idx_metrics_4g_time_range_cgi ON metrics_4g(time DESC, cgi) WHERE time >= NOW() - INTERVAL '7 days';
CREATE INDEX IF NOT EXISTS idx_metrics_5g_time_range_cgi ON metrics_5g(time DESC, cgi) WHERE time >= NOW() - INTERVAL '7 days';

-- 利用率查询优化（假设有 utilization 字段）
-- CREATE INDEX IF NOT EXISTS idx_metrics_4g_utilization ON metrics_4g(utilization DESC) WHERE utilization IS NOT NULL;
-- CREATE INDEX IF NOT EXISTS idx_metrics_5g_utilization ON metrics_5g(utilization DESC) WHERE utilization IS NOT NULL;

-- ============================================
-- 查询性能分析
-- ============================================

-- 查看表大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY size_bytes DESC;

-- 查看索引使用情况
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- 查找未使用的索引
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;

-- 查看慢查询（需要启用 pg_stat_statements 扩展）
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- SELECT 
--     query,
--     calls,
--     total_time,
--     mean_time,
--     max_time
-- FROM pg_stat_statements
-- ORDER BY mean_time DESC
-- LIMIT 20;

-- ============================================
-- 表维护
-- ============================================

-- 分析表统计信息（帮助查询优化器）
ANALYZE metrics_4g;
ANALYZE metrics_5g;

-- 清理死元组（可选，定期执行）
-- VACUUM ANALYZE metrics_4g;
-- VACUUM ANALYZE metrics_5g;

-- ============================================
-- 分区表优化（如果数据量很大，建议使用分区）
-- ============================================

-- 示例：按月分区 metrics_4g 表
-- CREATE TABLE metrics_4g_partitioned (
--     LIKE metrics_4g INCLUDING ALL
-- ) PARTITION BY RANGE (time);

-- CREATE TABLE metrics_4g_2024_01 PARTITION OF metrics_4g_partitioned
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- CREATE TABLE metrics_4g_2024_02 PARTITION OF metrics_4g_partitioned
--     FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- ============================================
-- 性能优化建议
-- ============================================

-- 1. 定期执行 VACUUM ANALYZE 清理和更新统计信息
-- 2. 监控慢查询日志，优化慢查询
-- 3. 考虑使用物化视图缓存复杂查询结果
-- 4. 对于大表，考虑使用分区表
-- 5. 定期检查索引使用情况，删除未使用的索引
-- 6. 使用连接池减少连接开销
-- 7. 考虑使用 Redis 等缓存层
