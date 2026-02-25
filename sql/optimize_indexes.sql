-- ============================================
-- PostgreSQL 索引优化脚本
-- 用于提升查询性能
-- ============================================

-- 说明：
-- 1. 本脚本基于现有表结构和查询模式创建优化索引
-- 2. 使用 IF NOT EXISTS 避免重复创建
-- 3. 索引已存在时会自动跳过
-- 4. 建议在业务低峰期执行

\echo '========================================'
\echo '开始执行索引优化'
\echo '========================================'

-- ============================================
-- 4G指标表索引优化（15分钟粒度）
-- ============================================

\echo '1. 优化 cell_4g_metrics 表（15分钟粒度）...'

-- 基础时间索引（已存在，确保存在）
CREATE INDEX IF NOT EXISTS idx_metrics_4g_time 
ON cell_4g_metrics(start_time DESC);

-- CGI索引（已存在，确保存在）
CREATE INDEX IF NOT EXISTS idx_metrics_4g_cgi 
ON cell_4g_metrics(cgi);

-- 复合索引：时间+CGI（已存在，确保存在）
CREATE INDEX IF NOT EXISTS idx_metrics_4g_time_cgi 
ON cell_4g_metrics(start_time DESC, cgi);

-- 新增：cell_id索引（用于小区查询）
CREATE INDEX IF NOT EXISTS idx_metrics_4g_cell_id 
ON cell_4g_metrics(cell_id);

-- 新增：cellname索引（用于区域分类）
CREATE INDEX IF NOT EXISTS idx_metrics_4g_cellname 
ON cell_4g_metrics(cellname);

\echo '✓ cell_4g_metrics 索引创建完成'

-- ============================================
-- 5G指标表索引优化（15分钟粒度）
-- ============================================

\echo '2. 优化 cell_5g_metrics 表（15分钟粒度）...'

-- 基础时间索引（已存在，确保存在）
CREATE INDEX IF NOT EXISTS idx_metrics_5g_time 
ON cell_5g_metrics(start_time DESC);

-- CGI索引（已存在，确保存在）
CREATE INDEX IF NOT EXISTS idx_metrics_5g_cgi 
ON cell_5g_metrics("Ncgi");

-- 复合索引：时间+CGI（已存在，确保存在）
CREATE INDEX IF NOT EXISTS idx_metrics_5g_time_cgi 
ON cell_5g_metrics(start_time DESC, "Ncgi");

-- 新增：userlabel索引（用于区域分类）
CREATE INDEX IF NOT EXISTS idx_metrics_5g_userlabel 
ON cell_5g_metrics(userlabel);

\echo '✓ cell_5g_metrics 索引创建完成'

-- ============================================
-- 4G小时粒度表索引优化
-- ============================================

\echo '3. 优化 cell_4g_metrics_hour 表（小时粒度）...'

-- 时间索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_hour_time 
ON cell_4g_metrics_hour(start_time DESC);

-- CGI索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_hour_cgi 
ON cell_4g_metrics_hour(cgi);

-- 复合索引：时间+CGI
CREATE INDEX IF NOT EXISTS idx_metrics_4g_hour_time_cgi 
ON cell_4g_metrics_hour(start_time DESC, cgi);

-- cell_id索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_hour_cell_id 
ON cell_4g_metrics_hour(cell_id);

-- cellname索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_hour_cellname 
ON cell_4g_metrics_hour(cellname);

\echo '✓ cell_4g_metrics_hour 索引创建完成'

-- ============================================
-- 5G小时粒度表索引优化
-- ============================================

\echo '4. 优化 cell_5g_metrics_hour 表（小时粒度）...'

-- 时间索引
CREATE INDEX IF NOT EXISTS idx_metrics_5g_hour_time 
ON cell_5g_metrics_hour(start_time DESC);

-- CGI索引
CREATE INDEX IF NOT EXISTS idx_metrics_5g_hour_cgi 
ON cell_5g_metrics_hour("Ncgi");

-- 复合索引：时间+CGI
CREATE INDEX IF NOT EXISTS idx_metrics_5g_hour_time_cgi 
ON cell_5g_metrics_hour(start_time DESC, "Ncgi");

-- userlabel索引
CREATE INDEX IF NOT EXISTS idx_metrics_5g_hour_userlabel 
ON cell_5g_metrics_hour(userlabel);

\echo '✓ cell_5g_metrics_hour 索引创建完成'

-- ============================================
-- 4G天粒度表索引优化
-- ============================================

\echo '5. 优化 cell_4g_metrics_day 表（天粒度）...'

-- 时间索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_day_time 
ON cell_4g_metrics_day(start_time DESC);

-- CGI索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_day_cgi 
ON cell_4g_metrics_day(cgi);

-- 复合索引：时间+CGI
CREATE INDEX IF NOT EXISTS idx_metrics_4g_day_time_cgi 
ON cell_4g_metrics_day(start_time DESC, cgi);

-- cell_id索引
CREATE INDEX IF NOT EXISTS idx_metrics_4g_day_cell_id 
ON cell_4g_metrics_day(cell_id);

-- cellname索引（用于区域统计）
CREATE INDEX IF NOT EXISTS idx_metrics_4g_day_cellname 
ON cell_4g_metrics_day(cellname);

\echo '✓ cell_4g_metrics_day 索引创建完成'

-- ============================================
-- 5G天粒度表索引优化
-- ============================================

\echo '6. 优化 cell_5g_metrics_day 表（天粒度）...'

-- 时间索引
CREATE INDEX IF NOT EXISTS idx_metrics_5g_day_time 
ON cell_5g_metrics_day(start_time DESC);

-- CGI索引
CREATE INDEX IF NOT EXISTS idx_metrics_5g_day_cgi 
ON cell_5g_metrics_day("Ncgi");

-- 复合索引：时间+CGI
CREATE INDEX IF NOT EXISTS idx_metrics_5g_day_time_cgi 
ON cell_5g_metrics_day(start_time DESC, "Ncgi");

-- userlabel索引（用于区域统计）
CREATE INDEX IF NOT EXISTS idx_metrics_5g_day_userlabel 
ON cell_5g_metrics_day(userlabel);

\echo '✓ cell_5g_metrics_day 索引创建完成'

-- ============================================
-- 更新表统计信息
-- ============================================

\echo '7. 更新表统计信息...'

ANALYZE cell_4g_metrics;
ANALYZE cell_5g_metrics;
ANALYZE cell_4g_metrics_hour;
ANALYZE cell_5g_metrics_hour;
ANALYZE cell_4g_metrics_day;
ANALYZE cell_5g_metrics_day;

\echo '✓ 统计信息更新完成'

-- ============================================
-- 查看索引创建结果
-- ============================================

\echo ''
\echo '========================================'
\echo '索引创建结果汇总'
\echo '========================================'

-- 查看所有4G表索引
\echo ''
\echo '4G表索引:'
SELECT 
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename LIKE 'cell_4g_metrics%'
ORDER BY tablename, indexname;

-- 查看所有5G表索引
\echo ''
\echo '5G表索引:'
SELECT 
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename LIKE 'cell_5g_metrics%'
ORDER BY tablename, indexname;

-- ============================================
-- 执行完成提示
-- ============================================

\echo ''
\echo '========================================'
\echo '✓ 索引优化完成！'
\echo '========================================'
\echo '已优化的表:'
\echo '  - cell_4g_metrics (15分钟)'
\echo '  - cell_5g_metrics (15分钟)'
\echo '  - cell_4g_metrics_hour (小时)'
\echo '  - cell_5g_metrics_hour (小时)'
\echo '  - cell_4g_metrics_day (天)'
\echo '  - cell_5g_metrics_day (天)'
\echo ''
\echo '建议:'
\echo '  1. 定期执行 VACUUM ANALYZE 维护数据库'
\echo '  2. 监控索引使用情况'
\echo '  3. 运行 sql/diagnostics.sql 查看优化效果'
\echo '========================================'
