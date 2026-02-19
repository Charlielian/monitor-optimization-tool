-- Recommended indexes for faster dashboard/monitor queries.
-- Run these in PostgreSQL (psql or any DB tool). Safe to re-run.

CREATE INDEX IF NOT EXISTS idx_cell_4g_metrics_start_time
  ON cell_4g_metrics (start_time);

CREATE INDEX IF NOT EXISTS idx_cell_4g_metrics_cell_time
  ON cell_4g_metrics (cell_id, start_time);

CREATE INDEX IF NOT EXISTS idx_cell_4g_metrics_cgi_time
  ON cell_4g_metrics (cgi, start_time);

CREATE INDEX IF NOT EXISTS idx_cell_5g_metrics_start_time
  ON cell_5g_metrics (start_time);

CREATE INDEX IF NOT EXISTS idx_cell_5g_metrics_ncgi_time
  ON cell_5g_metrics ("Ncgi", start_time);

DO $$
BEGIN
  IF to_regclass('cell_4g_metrics_day') IS NOT NULL THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_cell_4g_metrics_day_start_time ON cell_4g_metrics_day (start_time)';
  END IF;
  IF to_regclass('cell_5g_metrics_day') IS NOT NULL THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_cell_5g_metrics_day_start_time ON cell_5g_metrics_day (start_time)';
  END IF;
END $$;
