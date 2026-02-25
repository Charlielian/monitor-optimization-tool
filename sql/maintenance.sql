-- ============================================
-- PostgreSQL 数据库维护脚本
-- 建议每天凌晨执行
-- ============================================

-- 执行时间记录
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '开始执行数据库维护任务';
    RAISE NOTICE '执行时间: %', NOW();
    RAISE NOTICE '========================================';
END $$;

-- ============================================
-- 1. 清理死元组并更新统计信息
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '1. 清理死元组并更新统计信息...';
END $$;

-- 15分钟粒度表
VACUUM ANALYZE cell_4g_metrics;
VACUUM ANALYZE cell_5g_metrics;

-- 小时粒度表
VACUUM ANALYZE cell_4g_metrics_hour;
VACUUM ANALYZE cell_5g_metrics_hour;

-- 天粒度表
VACUUM ANALYZE cell_4g_metrics_day;
VACUUM ANALYZE cell_5g_metrics_day;

DO $$
BEGIN
    RAISE NOTICE '✓ 死元组清理完成';
END $$;

-- ============================================
-- 2. 更新表统计信息
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '2. 更新表统计信息...';
END $$;

ANALYZE cell_4g_metrics;
ANALYZE cell_5g_metrics;
ANALYZE cell_4g_metrics_hour;
ANALYZE cell_5g_metrics_hour;
ANALYZE cell_4g_metrics_day;
ANALYZE cell_5g_metrics_day;

DO $$
BEGIN
    RAISE NOTICE '✓ 统计信息更新完成';
END $$;

-- ============================================
-- 3. 检查表膨胀情况
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '3. 检查表膨胀情况...';
END $$;

SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS total_size,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    ROUND(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND tablename LIKE 'cell_%_metrics%'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;

-- ============================================
-- 4. 检查索引使用情况
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '4. 检查索引使用情况...';
END $$;

-- 显示最常用的索引
SELECT 
    tablename,
    indexname,
    idx_scan AS scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND tablename LIKE 'cell_%_metrics%'
ORDER BY idx_scan DESC
LIMIT 10;

-- 显示未使用的索引
SELECT 
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND idx_scan = 0
    AND indexrelname NOT LIKE '%_pkey'
    AND tablename LIKE 'cell_%_metrics%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================
-- 5. 完成提示
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '数据库维护任务完成';
    RAISE NOTICE '完成时间: %', NOW();
    RAISE NOTICE '========================================';
END $$;
