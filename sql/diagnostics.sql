-- ============================================
-- PostgreSQL 性能诊断脚本
-- 用于分析数据库性能问题
-- ============================================

-- ============================================
-- 1. 数据库基本信息
-- ============================================

\echo '========================================='
\echo '1. 数据库基本信息'
\echo '========================================='

SELECT version();

SELECT 
    pg_size_pretty(pg_database_size(current_database())) AS database_size;

-- ============================================
-- 2. 表大小统计
-- ============================================

\echo ''
\echo '========================================='
\echo '2. 表大小统计'
\echo '========================================='

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename LIKE 'cell_%_metrics%'
ORDER BY size_bytes DESC;

-- ============================================
-- 3. 索引使用情况
-- ============================================

\echo ''
\echo '========================================='
\echo '3. 索引使用情况（Top 20）'
\echo '========================================='

SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 20;

-- ============================================
-- 4. 未使用的索引
-- ============================================

\echo ''
\echo '========================================='
\echo '4. 未使用的索引'
\echo '========================================='

SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND indexrelname NOT LIKE '%_pkey'
    AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================
-- 5. 表膨胀情况
-- ============================================

\echo ''
\echo '========================================='
\echo '5. 表膨胀情况'
\echo '========================================='

SELECT 
    schemaname,
    tablename,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    ROUND(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND tablename LIKE 'cell_%_metrics%'
ORDER BY dead_ratio DESC NULLS LAST;

-- ============================================
-- 6. 慢查询统计（需要 pg_stat_statements）
-- ============================================

\echo ''
\echo '========================================='
\echo '6. 慢查询统计（Top 20）'
\echo '========================================='

-- 检查扩展是否存在
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') THEN
        RAISE NOTICE '提示: pg_stat_statements 扩展未安装';
        RAISE NOTICE '安装命令: CREATE EXTENSION pg_stat_statements;';
    END IF;
END $$;

-- 如果扩展存在，显示慢查询
SELECT 
    LEFT(query, 100) AS query_preview,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
    ROUND(max_exec_time::numeric, 2) AS max_time_ms,
    rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
    AND query NOT LIKE '%pg_catalog%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- ============================================
-- 7. 当前活动连接
-- ============================================

\echo ''
\echo '========================================='
\echo '7. 当前活动连接'
\echo '========================================='

SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    state_change,
    wait_event_type,
    wait_event,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE datname = current_database()
    AND pid != pg_backend_pid()
ORDER BY query_start;

-- ============================================
-- 8. 长时间运行的查询
-- ============================================

\echo ''
\echo '========================================='
\echo '8. 长时间运行的查询（>5秒）'
\echo '========================================='

SELECT 
    pid,
    usename,
    application_name,
    state,
    NOW() - query_start AS duration,
    LEFT(query, 150) AS query_preview
FROM pg_stat_activity
WHERE datname = current_database()
    AND state = 'active'
    AND NOW() - query_start > INTERVAL '5 seconds'
    AND pid != pg_backend_pid()
ORDER BY duration DESC;

-- ============================================
-- 9. 锁等待情况
-- ============================================

\echo ''
\echo '========================================='
\echo '9. 锁等待情况'
\echo '========================================='

SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- ============================================
-- 10. 缓存命中率
-- ============================================

\echo ''
\echo '========================================='
\echo '10. 缓存命中率'
\echo '========================================='

SELECT 
    'index hit rate' AS metric,
    ROUND(
        (sum(idx_blks_hit)) / NULLIF(sum(idx_blks_hit + idx_blks_read), 0) * 100,
        2
    ) AS ratio
FROM pg_statio_user_indexes
UNION ALL
SELECT 
    'table hit rate' AS metric,
    ROUND(
        sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0) * 100,
        2
    ) AS ratio
FROM pg_statio_user_tables;

-- ============================================
-- 11. 数据库配置参数
-- ============================================

\echo ''
\echo '========================================='
\echo '11. 关键配置参数'
\echo '========================================='

SELECT 
    name,
    setting,
    unit,
    context
FROM pg_settings
WHERE name IN (
    'shared_buffers',
    'effective_cache_size',
    'work_mem',
    'maintenance_work_mem',
    'max_connections',
    'max_parallel_workers_per_gather',
    'max_parallel_workers',
    'random_page_cost',
    'effective_io_concurrency'
)
ORDER BY name;

\echo ''
\echo '========================================='
\echo '诊断完成'
\echo '========================================='
