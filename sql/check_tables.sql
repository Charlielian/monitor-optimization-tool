-- ============================================
-- 检查表是否存在
-- ============================================

\echo '检查数据库表...'
\echo ''

SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size('public.'||tablename)) AS table_size,
    (SELECT COUNT(*) FROM pg_indexes WHERE tablename = t.tablename) AS index_count
FROM pg_tables t
WHERE schemaname = 'public'
    AND tablename IN (
        'cell_4g_metrics',
        'cell_4g_metrics_hour',
        'cell_4g_metrics_day',
        'cell_5g_metrics',
        'cell_5g_metrics_hour',
        'cell_5g_metrics_day'
    )
ORDER BY tablename;

\echo ''
\echo '如果以上显示6个表，说明所有表都存在，可以执行 optimize_indexes.sql'
