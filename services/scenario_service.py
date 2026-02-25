from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from db.pg import PostgresClient
from db.mysql import MySQLClient
from services.cache import cache_1m, cache_5m
from utils.formatters import format_traffic_with_unit
from constants import DEFAULT_PAGE_SIZE, DEFAULT_THRESHOLD_4G, DEFAULT_THRESHOLD_5G


class ScenarioService:
    def __init__(self, pg: PostgresClient, mysql: Optional[MySQLClient] = None) -> None:
        self.pg = pg
        self.mysql = mysql
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS scenarios (
            id SERIAL PRIMARY KEY,
            scenario_name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS scenario_cells (
            id SERIAL PRIMARY KEY,
            scenario_id INTEGER NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
            cell_id TEXT NOT NULL,
            cell_name TEXT,
            cgi TEXT,
            network_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(scenario_id, cell_id, network_type)
        );
        """
        # psycopg2 executes one statement at a time; split by semicolon
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            self.pg.execute(stmt)

    # --- scenario CRUD ---
    def list_scenarios(self) -> List[Dict[str, Any]]:
        return cache_1m.get(
            "scenario_list",
            lambda: self.pg.fetch_all(
                "SELECT id, scenario_name, description, created_at, updated_at FROM scenarios ORDER BY scenario_name"
            ),
        )

    def create_scenario(self, name: str, desc: str = "") -> None:
        self.pg.execute(
            """
            INSERT INTO scenarios (scenario_name, description, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (scenario_name) DO UPDATE SET description = EXCLUDED.description, updated_at = NOW()
            """,
            (name, desc),
        )
        cache_1m.invalidate("scenario_list")

    def delete_scenario(self, scenario_id: int) -> None:
        self.pg.execute("DELETE FROM scenarios WHERE id = %s", (scenario_id,))
        cache_1m.invalidate("scenario_list")
        cache_1m.invalidate(f"scenario_name:{scenario_id}")
        cache_1m.invalidate(f"scenario_cells:{scenario_id}")

    def add_cells(self, scenario_id: int, cells: Sequence[Dict[str, Any]]) -> int:
        if not cells:
            return 0
        inserted = 0
        for cell in cells:
            inserted += self.pg.execute(
                """
                INSERT INTO scenario_cells (scenario_id, cell_id, cell_name, cgi, network_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (scenario_id, cell_id, network_type) DO NOTHING
                """,
                (
                    scenario_id,
                    cell.get("cell_id", ""),
                    cell.get("cell_name", ""),
                    cell.get("cgi", ""),
                    cell.get("network_type", "4G"),
                ),
            )
        cache_1m.invalidate(f"scenario_cells:{scenario_id}")
        return inserted

    def remove_cell(self, scenario_id: int, cell_id: str, network_type: str) -> None:
        self.pg.execute(
            "DELETE FROM scenario_cells WHERE scenario_id = %s AND cell_id = %s AND network_type = %s",
            (scenario_id, cell_id, network_type),
        )
        cache_1m.invalidate(f"scenario_cells:{scenario_id}")

    def list_cells(self, scenario_id: int) -> List[Dict[str, Any]]:
        return cache_1m.get(
            f"scenario_cells:{scenario_id}",
            lambda: self.pg.fetch_all(
                """
                SELECT id, cell_id, cell_name, cgi, network_type
                FROM scenario_cells
                WHERE scenario_id = %s
                ORDER BY network_type, cell_id
                """,
                (scenario_id,),
            ),
        )

    def list_cells_batch(self, scenario_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        """
        批量获取多个场景的小区数据（解决N+1查询问题）

        Args:
            scenario_ids: 场景ID列表

        Returns:
            字典，key为scenario_id，value为该场景的小区列表
        """
        if not scenario_ids:
            return {}

        # 构建IN子句的占位符
        placeholders = ','.join(['%s'] * len(scenario_ids))
        sql = f"""
            SELECT scenario_id, id, cell_id, cell_name, cgi, network_type
            FROM scenario_cells
            WHERE scenario_id IN ({placeholders})
            ORDER BY scenario_id, network_type, cell_id
        """

        rows = self.pg.fetch_all(sql, tuple(scenario_ids))

        # 按scenario_id分组
        result = {sid: [] for sid in scenario_ids}
        for row in rows:
            sid = row.pop('scenario_id')
            result[sid].append(row)

        return result

    def _scenario_name(self, scenario_id: int) -> Optional[str]:
        def _load():
            row = self.pg.fetch_one("SELECT scenario_name FROM scenarios WHERE id = %s", (scenario_id,))
            return row["scenario_name"] if row else None

        return cache_1m.get(f"scenario_name:{scenario_id}", _load)

    def get_scenario_name(self, scenario_id: int) -> Optional[str]:
        return self._scenario_name(scenario_id)

    # --- monitoring ---
    def latest_time(self) -> Dict[str, Any]:
        def _load():
            # 查询15分钟表的最新时间
            latest_4g_15m = self.pg.fetch_one("SELECT MAX(start_time) AS ts FROM cell_4g_metrics") or {}
            latest_5g_15m = self.pg.fetch_one("SELECT MAX(start_time) AS ts FROM cell_5g_metrics") or {}
            
            # 查询小时表的最新时间
            latest_4g_1h = self.pg.fetch_one("SELECT MAX(start_time) AS ts FROM cell_4g_metrics_hour") or {}
            latest_5g_1h = self.pg.fetch_one("SELECT MAX(start_time) AS ts FROM cell_5g_metrics_hour") or {}
            
            # 取各制式的最大时间
            latest_4g = max(
                [ts for ts in [latest_4g_15m.get("ts"), latest_4g_1h.get("ts")] if ts],
                default=None
            )
            latest_5g = max(
                [ts for ts in [latest_5g_15m.get("ts"), latest_5g_1h.get("ts")] if ts],
                default=None
            )
            
            return {"4g": latest_4g, "5g": latest_5g}

        return cache_5m.get("latest_ts", _load)

    def scenario_metrics(
        self,
        scenario_ids: Sequence[int],
        threshold_4g: float = DEFAULT_THRESHOLD_4G,
        threshold_5g: float = DEFAULT_THRESHOLD_5G,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        if not scenario_ids:
            return []
        
        # 如果没有提供时间范围，使用最新时间点
        if start_time is None or end_time is None:
            latest = self.latest_time()
            ts_4g, ts_5g = latest.get("4g"), latest.get("5g")
            use_time_range = False
        else:
            ts_4g, ts_5g = end_time, end_time  # 用于显示时间
            use_time_range = True

        results: List[Dict[str, Any]] = []
        for sid in scenario_ids:
            s_name = self._scenario_name(sid)
            if not s_name:
                continue
            cells = self.list_cells(sid)
            cells_4g = [c for c in cells if c["network_type"] == "4G"]
            cells_5g = [c for c in cells if c["network_type"] == "5G"]

            # 处理4G数据
            if cells_4g:
                if ts_4g:
                    cgids = [c.get("cgi") for c in cells_4g if c.get("cgi")]
                    if cgids:
                        if use_time_range:
                            # 使用时间范围查询
                            params = [threshold_4g, threshold_4g, start_time, end_time] + cgids
                            sql = f"""
                                SELECT
                                    SUM(total_traffic_gb) AS total_traffic,
                                    -- 4G PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                                    SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS avg_ul_prb_util,
                                    SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS avg_dl_prb_util,
                                    -- 4G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                                    SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0) *
                                    SUM("ERAB_NbrSuccEstab") * 100.0 / NULLIF(SUM("ERAB_NbrAttEstab"), 0) / 100.0 AS avg_connect_rate,
                                    SUM("RRC_ConnMax") AS total_rrc_users,
                                    COUNT(CASE WHEN ul_prb_utilization > %s OR dl_prb_utilization > %s THEN 1 END) AS cells_over_threshold,
                                    COUNT(CASE WHEN interference > -105 THEN 1 END) AS interference_cells,
                                    COUNT(CASE WHEN total_traffic_gb = 0 THEN 1 END) AS no_traffic_cells,
                                    COUNT(CASE WHEN total_traffic_gb = 0 AND ul_prb_utilization = 0 AND dl_prb_utilization = 0 THEN 1 END) AS no_performance_cells,
                                    COUNT(*) AS cells_with_data
                                FROM cell_4g_metrics
                                WHERE start_time BETWEEN %s AND %s AND cgi IN ({','.join(['%s']*len(cgids))})
                            """
                        else:
                            # 使用最新时间点查询
                            params = [threshold_4g, threshold_4g, ts_4g] + cgids
                            sql = f"""
                                SELECT
                                    SUM(total_traffic_gb) AS total_traffic,
                                    -- 4G PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                                    SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS avg_ul_prb_util,
                                    SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS avg_dl_prb_util,
                                    -- 4G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                                    SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0) *
                                    SUM("ERAB_NbrSuccEstab") * 100.0 / NULLIF(SUM("ERAB_NbrAttEstab"), 0) / 100.0 AS avg_connect_rate,
                                    SUM("RRC_ConnMax") AS total_rrc_users,
                                    COUNT(CASE WHEN ul_prb_utilization > %s OR dl_prb_utilization > %s THEN 1 END) AS cells_over_threshold,
                                    COUNT(CASE WHEN interference > -105 THEN 1 END) AS interference_cells,
                                    COUNT(CASE WHEN total_traffic_gb = 0 THEN 1 END) AS no_traffic_cells,
                                    COUNT(CASE WHEN total_traffic_gb = 0 AND ul_prb_utilization = 0 AND dl_prb_utilization = 0 THEN 1 END) AS no_performance_cells,
                                    COUNT(*) AS cells_with_data
                                FROM cell_4g_metrics
                                WHERE start_time = %s AND cgi IN ({','.join(['%s']*len(cgids))})
                            """
                        row = self.pg.fetch_one(sql, tuple(params)) or {}
                        # 计算关联不到数据的小区数
                        cells_with_data = int(row.get("cells_with_data") or 0)
                        cells_without_data = len(cgids) - cells_with_data
                    else:
                        row = {}
                        cells_without_data = 0
                    
                    traffic_gb = row.get("total_traffic") or 0
                    traffic_value, traffic_unit = format_traffic_with_unit(traffic_gb)
                    # 无性能小区数 = 数据库中无性能的 + 关联不到数据的
                    no_performance_in_db = int(row.get("no_performance_cells") or 0)
                    total_no_performance = no_performance_in_db + cells_without_data
                    
                    results.append(
                        {
                            "scenario": s_name,
                            "network": "4G",
                            "ts": ts_4g,
                            "流量值": traffic_value,
                            "流量单位": traffic_unit,
                            "流量(GB)": traffic_value if traffic_unit == "GB" else traffic_value * 1024,  # 兼容旧代码
                            "上行PRB利用率(%)": round(row.get("avg_ul_prb_util") or 0, 2),
                            "下行PRB利用率(%)": round(row.get("avg_dl_prb_util") or 0, 2),
                            "无线接通率(%)": round(row.get("avg_connect_rate") or 0, 2),
                            "最大用户数": int(row.get("total_rrc_users") or 0),
                            "超阈值小区数": int(row.get("cells_over_threshold") or 0),
                            "干扰小区数": int(row.get("interference_cells") or 0),
                            "无流量小区数": int(row.get("no_traffic_cells") or 0),
                            "无性能小区数": total_no_performance,
                            "总小区数": len(cells_4g),
                        }
                    )
                else:
                    # 没有最新4G数据，返回空数据行
                    results.append(
                        {
                            "scenario": s_name,
                            "network": "4G",
                            "ts": "暂无数据",
                            "流量值": 0.0,
                            "流量单位": "GB",
                            "流量(GB)": 0.0,
                            "上行PRB利用率(%)": 0.0,
                            "下行PRB利用率(%)": 0.0,
                            "无线接通率(%)": 0.0,
                            "最大用户数": 0,
                            "超阈值小区数": 0,
                            "干扰小区数": 0,
                            "无流量小区数": 0,
                            "无性能小区数": 0,
                            "总小区数": len(cells_4g),
                        }
                    )

            # 处理5G数据
            if cells_5g:
                if ts_5g:
                    cgids = [c.get("cgi") for c in cells_5g if c.get("cgi")]
                    if cgids:
                        if use_time_range:
                            # 使用时间范围查询
                            params = [threshold_5g, threshold_5g, start_time, end_time] + cgids
                            sql = f"""
                                SELECT
                                    SUM((COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0) AS total_traffic,
                                    -- 5G PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                                    SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS avg_ul_prb_util,
                                    SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS avg_dl_prb_util,
                                    -- 5G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                                    (SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0)) *
                                    (SUM("NGSIG_ConnEstabSucc") * 100.0 / NULLIF(SUM("NGSIG_ConnEstabAtt"), 0)) *
                                    (SUM("Flow_NbrSuccEstab") * 100.0 / NULLIF(SUM("Flow_NbrAttEstab"), 0)) / 100.0 / 100.0 AS avg_connect_rate,
                                    SUM("RRC_ConnMax") AS total_rrc_users,
                                    COUNT(CASE WHEN ("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) > %s)
                                               OR ("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) > %s) THEN 1 END) AS cells_over_threshold,
                                    COUNT(CASE WHEN interference > -105 THEN 1 END) AS interference_cells,
                                    COUNT(CASE WHEN (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) = 0 THEN 1 END) AS no_traffic_cells,
                                    COUNT(CASE WHEN (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) = 0 
                                               AND COALESCE("RRU_PuschPrbAssn", 0) = 0 
                                               AND COALESCE("RRU_PdschPrbAssn", 0) = 0 THEN 1 END) AS no_performance_cells,
                                    COUNT(*) AS cells_with_data
                                FROM cell_5g_metrics
                                WHERE start_time BETWEEN %s AND %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                            """
                        else:
                            # 使用最新时间点查询
                            params = [threshold_5g, threshold_5g, ts_5g] + cgids
                            sql = f"""
                                SELECT
                                    SUM((COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0) AS total_traffic,
                                    -- 5G PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                                    SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS avg_ul_prb_util,
                                    SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS avg_dl_prb_util,
                                    -- 5G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                                    (SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0)) *
                                    (SUM("NGSIG_ConnEstabSucc") * 100.0 / NULLIF(SUM("NGSIG_ConnEstabAtt"), 0)) *
                                    (SUM("Flow_NbrSuccEstab") * 100.0 / NULLIF(SUM("Flow_NbrAttEstab"), 0)) / 100.0 / 100.0 AS avg_connect_rate,
                                    SUM("RRC_ConnMax") AS total_rrc_users,
                                    COUNT(CASE WHEN ("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) > %s)
                                               OR ("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) > %s) THEN 1 END) AS cells_over_threshold,
                                    COUNT(CASE WHEN interference > -105 THEN 1 END) AS interference_cells,
                                    COUNT(CASE WHEN (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) = 0 THEN 1 END) AS no_traffic_cells,
                                    COUNT(CASE WHEN (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) = 0 
                                               AND COALESCE("RRU_PuschPrbAssn", 0) = 0 
                                               AND COALESCE("RRU_PdschPrbAssn", 0) = 0 THEN 1 END) AS no_performance_cells,
                                    COUNT(*) AS cells_with_data
                                FROM cell_5g_metrics
                                WHERE start_time = %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                            """
                        row = self.pg.fetch_one(sql, tuple(params)) or {}
                        # 计算关联不到数据的小区数
                        cells_with_data = int(row.get("cells_with_data") or 0)
                        cells_without_data = len(cgids) - cells_with_data
                    else:
                        row = {}
                        cells_without_data = 0
                    # 5G计算结果是GB，但需要检查是否应该显示为TB
                    traffic_gb = row.get("total_traffic") or 0
                    traffic_value, traffic_unit = format_traffic_with_unit(traffic_gb)
                    # 无性能小区数 = 数据库中无性能的 + 关联不到数据的
                    no_performance_in_db = int(row.get("no_performance_cells") or 0)
                    total_no_performance = no_performance_in_db + cells_without_data
                    
                    results.append(
                        {
                            "scenario": s_name,
                            "network": "5G",
                            "ts": ts_5g,
                            "流量值": traffic_value,
                            "流量单位": traffic_unit,
                            "流量(GB)": traffic_value if traffic_unit == "GB" else traffic_value * 1024,  # 兼容旧代码
                            "上行PRB利用率(%)": round(row.get("avg_ul_prb_util") or 0, 2),
                            "下行PRB利用率(%)": round(row.get("avg_dl_prb_util") or 0, 2),
                            "无线接通率(%)": round(row.get("avg_connect_rate") or 0, 2),
                            "最大用户数": int(row.get("total_rrc_users") or 0),
                            "超阈值小区数": int(row.get("cells_over_threshold") or 0),
                            "干扰小区数": int(row.get("interference_cells") or 0),
                            "无流量小区数": int(row.get("no_traffic_cells") or 0),
                            "无性能小区数": total_no_performance,
                            "总小区数": len(cells_5g),
                        }
                    )
                else:
                    # 没有最新5G数据，返回空数据行
                    results.append(
                        {
                            "scenario": s_name,
                            "network": "5G",
                            "ts": "暂无数据",
                            "流量值": 0.0,
                            "流量单位": "GB",
                            "流量(GB)": 0.0,
                            "上行PRB利用率(%)": 0.0,
                            "下行PRB利用率(%)": 0.0,
                            "无线接通率(%)": 0.0,
                            "最大用户数": 0,
                            "超阈值小区数": 0,
                            "干扰小区数": 0,
                            "无流量小区数": 0,
                            "无性能小区数": 0,
                            "总小区数": len(cells_5g),
                        }
                    )
        return results

    # --- hotspot / busy-hour rules for scenarios ---
    def _busy_hour_4g_for_cgis(
        self,
        cgis: Sequence[str],
        target_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        获取指定 4G CGI 列表在目标日期内的忙时利用率。
        忙时定义：前一日“流量最大”的那个小时，对应该小时的 PRB 利用率。
        """
        if not cgis:
            return []
        
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        placeholders = ",".join(["%s"] * len(cgis))
        sql = f"""
            SELECT
                t.cgi,
                t.cellname,
                t.max_prb
            FROM (
                SELECT
                    cgi,
                    cellname,
                    GREATEST(COALESCE(ul_prb_utilization,0), COALESCE(dl_prb_utilization,0)) AS max_prb,
                    -- 上下行总流量（MB），用于判断忙时
                    (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic_gb,
                    ROW_NUMBER() OVER (
                        PARTITION BY cgi
                        ORDER BY (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) DESC
                    ) AS rn
                FROM cell_4g_metrics_hour
                WHERE start_time >= %s AND start_time < %s
                  AND cgi IN ({placeholders})
            ) AS t
            WHERE t.rn = 1
        """
        params = (day_start, day_end, *cgis)
        return self.pg.fetch_all(sql, params) or []

    def _busy_hour_5g_for_cgis(
        self,
        cgis: Sequence[str],
        target_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        获取指定 5G CGI 列表在目标日期内的忙时利用率。
        忙时定义：前一日“流量最大”的那个小时，对应该小时的 PRB 利用率。
        """
        if not cgis:
            return []
        
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        placeholders = ",".join(["%s"] * len(cgis))
        sql = f"""
            SELECT
                t.cgi,
                t.cellname,
                t.max_prb
            FROM (
                SELECT
                    "Ncgi" AS cgi,
                    userlabel AS cellname,
                    GREATEST(
                        COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                        COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                    ) AS max_prb,
                    -- RLC 上下行总流量（MB），用于判断忙时
                    (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic_gb,
                    ROW_NUMBER() OVER (
                        PARTITION BY "Ncgi"
                        ORDER BY (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) DESC
                    ) AS rn
                FROM cell_5g_metrics_hour
                WHERE start_time >= %s AND start_time < %s
                  AND "Ncgi" IN ({placeholders})
            ) AS t
            WHERE t.rn = 1
        """
        params = (day_start, day_end, *cgis)
        return self.pg.fetch_all(sql, params) or []

    @staticmethod
    def _is_high_load_4g(cellname: str | None, max_prb: float) -> bool:
        """
        4G 高负荷判定规则：
        - 小区名包含 GS- 或 DC- 且 max_prb >= 80% 视为高负荷
        - 小区名包含 RD- 且 max_prb >= 70% 视为高负荷
        """
        if cellname is None:
            return False
        name = str(cellname)
        if ("GS-" in name or "DC-" in name) and max_prb >= 80.0:
            return True
        if "RD-" in name and max_prb >= 70.0:
            return True
        return False

    @staticmethod
    def _is_high_load_5g(max_prb: float) -> bool:
        """
        5G 高负荷判定规则：忙时 PRB 利用率 max_prb >= 70% 视为高负荷。
        """
        return max_prb >= 70.0

    def scenario_busy_hour_summary(
        self,
        scenario_id: int,
        target_date: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        计算单个监控场景在指定日期的忙时负荷情况，用于高铁/高速等热点区域通报。
        
        返回字段包括：
        - scenario_id, scenario_name
        - total_cells_4g / total_cells_5g
        - high_load_cells_4g / high_load_cells_5g
        - max_prb_4g / max_prb_5g / max_prb_overall
        """
        name = self._scenario_name(scenario_id)
        if not name:
            return {
                "scenario_id": scenario_id,
                "scenario_name": None,
                "total_cells_4g": 0,
                "total_cells_5g": 0,
                "high_load_cells_4g": 0,
                "high_load_cells_5g": 0,
                "max_prb_4g": 0.0,
                "max_prb_5g": 0.0,
                "max_prb_overall": 0.0,
            }
        
        if target_date is None:
            # 默认对前一日进行评估
            target_date = datetime.now() - timedelta(days=1)
        
        cells = self.list_cells(scenario_id)
        cells_4g = [c for c in cells if c.get("network_type") == "4G"]
        cells_5g = [c for c in cells if c.get("network_type") == "5G"]
        cgis_4g = [c.get("cgi") for c in cells_4g if c.get("cgi")]
        cgis_5g = [c.get("cgi") for c in cells_5g if c.get("cgi")]
        
        busy_4g = self._busy_hour_4g_for_cgis(cgis_4g, target_date) if cgis_4g else []
        busy_5g = self._busy_hour_5g_for_cgis(cgis_5g, target_date) if cgis_5g else []
        
        high_4g = 0
        max_prb_4g = 0.0
        for row in busy_4g:
            m = float(row.get("max_prb") or 0.0)
            max_prb_4g = max(max_prb_4g, m)
            if self._is_high_load_4g(row.get("cellname"), m):
                high_4g += 1
        
        high_5g = 0
        max_prb_5g = 0.0
        for row in busy_5g:
            m = float(row.get("max_prb") or 0.0)
            max_prb_5g = max(max_prb_5g, m)
            if self._is_high_load_5g(m):
                high_5g += 1
        
        return {
            "scenario_id": scenario_id,
            "scenario_name": name,
            "total_cells_4g": len(cgis_4g),
            "total_cells_5g": len(cgis_5g),
            "high_load_cells_4g": high_4g,
            "high_load_cells_5g": high_5g,
            "max_prb_4g": round(max_prb_4g, 2),
            "max_prb_5g": round(max_prb_5g, 2),
            "max_prb_overall": round(max(max_prb_4g, max_prb_5g), 2),
        }

    def hotspot_busy_hour_report(
        self,
        target_date: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        高铁 / 高速等重点场景忙时负荷业务规则入口。
        
        预置场景（基于 scenarios.sql 中的 ID）：
        - 高铁：22 广湛高铁、23 深湛高铁
        - 高速：34 罗阳高速、35 汕湛高速、36 沈海高速、
                37 西部沿海高速、38 信阳高速、39 中阳高速
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        high_speed_ids = [22, 23]
        highway_ids = [34, 35, 36, 37, 38, 39]
        
        high_speed = [
            self.scenario_busy_hour_summary(sid, target_date) for sid in high_speed_ids
        ]
        highway = [
            self.scenario_busy_hour_summary(sid, target_date) for sid in highway_ids
        ]
        
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "high_speed": high_speed,
            "highway": highway,
        }

    def scenario_cell_metrics(
        self,
        scenario_ids: Sequence[int],
        page_4g: int = 1,
        page_5g: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filter_text: str = "",
    ) -> Dict[str, Dict[str, Any]]:
        """
        获取场景下所有小区的详细指标（仅最新时段），分页，按利用率最高降序。
        返回结构：
        {
          "4G": {"data": [...], "total": N, "page": p, "pages": k},
          "5G": {...}
        }
        
        注意：即使小区CGI在数据表中查不到数据，也会显示该小区，指标值为空。
        """
        if not scenario_ids:
            return {
                "4G": {"data": [], "total": 0, "page": 1, "pages": 0},
                "5G": {"data": [], "total": 0, "page": 1, "pages": 0},
            }

        latest = self.latest_time()
        ts_4g, ts_5g = latest.get("4g"), latest.get("5g")

        # 汇总所有场景的小区列表
        def collect_cells(network: str):
            cells_all = []
            for sid in scenario_ids:
                s_name = self._scenario_name(sid)
                if not s_name:
                    continue
                cells = [c for c in self.list_cells(sid) if c["network_type"] == network]
                for c in cells:
                    cells_all.append({"scenario": s_name, **c})
            return cells_all

        cells_4g = collect_cells("4G")
        cells_5g = collect_cells("5G")

        def build_result(network: str, cells: List[Dict[str, Any]], page: int):
            if not cells:
                return {"data": [], "total": 0, "page": page, "pages": 0}
            
            # 创建小区映射（CGI -> 小区信息）
            cell_map = {}
            for c in cells:
                cgi = c.get("cgi", "")
                if cgi:
                    cell_map[cgi] = {
                        "scenario": c.get("scenario", ""),
                        "cell_id": c.get("cell_id", ""),
                        "cell_name": c.get("cell_name", ""),
                        "cgi": cgi,
                    }
            
            cgids = list(cell_map.keys())
            if not cgids:
                return {"data": [], "total": 0, "page": page, "pages": 0}
            
            # 查询数据库中有数据的小区
            metrics_map = {}
            if network == "4G":
                if not ts_4g:
                    # 没有最新时间戳，返回所有小区但指标为空
                    all_cells_with_empty_metrics = []
                    for cgi, cell_info in cell_map.items():
                        all_cells_with_empty_metrics.append({
                            "scenario": cell_info["scenario"],
                            "cell_id": cell_info["cell_id"],
                            "cgi": cgi,
                            "cellname": cell_info["cell_name"],
                            "start_time": None,
                            "traffic_gb": 0,
                            "ul_prb_util": 0,
                            "dl_prb_util": 0,
                            "max_prb_util": 0,
                            "connect_rate": 0,
                            "rrc_users": 0,
                            "interference": 0,
                            "traffic_value": 0,
                            "traffic_unit": "GB",
                            "has_data": False,
                        })
                    # 分页
                    total = len(all_cells_with_empty_metrics)
                    pages = (total + page_size - 1) // page_size if total else 0
                    offset = (page - 1) * page_size
                    return {
                        "data": all_cells_with_empty_metrics[offset:offset + page_size],
                        "total": total,
                        "page": page,
                        "pages": pages
                    }
                
                sql = f"""
                    SELECT 
                        cell_id, cgi, start_time, cellname,
                        total_traffic_gb as traffic_gb,
                        ul_prb_utilization as ul_prb_util,
                        dl_prb_utilization as dl_prb_util,
                        wireless_connect_rate as connect_rate,
                        "RRC_ConnMax" as rrc_users,
                        interference,
                        GREATEST(COALESCE(ul_prb_utilization,0), COALESCE(dl_prb_utilization,0)) AS max_prb_util
                    FROM cell_4g_metrics
                    WHERE start_time = %s AND cgi IN ({','.join(['%s']*len(cgids))})
                """
                params = [ts_4g] + cgids
                rows = self.pg.fetch_all(sql, tuple(params)) or []
                
                # 建立指标映射
                for row in rows:
                    cgi = row.get("cgi", "")
                    if cgi:
                        metrics_map[cgi] = row
            else:
                if not ts_5g:
                    # 没有最新时间戳，返回所有小区但指标为空
                    all_cells_with_empty_metrics = []
                    for cgi, cell_info in cell_map.items():
                        all_cells_with_empty_metrics.append({
                            "scenario": cell_info["scenario"],
                            "cell_id": cell_info["cell_id"],
                            "cgi": cgi,
                            "cellname": cell_info["cell_name"],
                            "start_time": None,
                            "traffic_gb": 0,
                            "ul_prb_util": 0,
                            "dl_prb_util": 0,
                            "max_prb_util": 0,
                            "connect_rate": 0,
                            "rrc_users": 0,
                            "interference": 0,
                            "traffic_value": 0,
                            "traffic_unit": "GB",
                            "has_data": False,
                        })
                    # 分页
                    total = len(all_cells_with_empty_metrics)
                    pages = (total + page_size - 1) // page_size if total else 0
                    offset = (page - 1) * page_size
                    return {
                        "data": all_cells_with_empty_metrics[offset:offset + page_size],
                        "total": total,
                        "page": page,
                        "pages": pages
                    }
                
                sql = f"""
                    SELECT 
                        "Ncgi" as cell_id, "Ncgi" as cgi, start_time, userlabel as cellname,
                        (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 as traffic_gb,
                        "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) as ul_prb_util,
                        "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) as dl_prb_util,
                        ("RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0)) *
                        ("NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0)) *
                        ("Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0)) / 100.0 / 100.0 as connect_rate,
                        "RRC_ConnMax" as rrc_users,
                        interference,
                        GREATEST(
                            COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0),0),
                            COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0),0)
                        ) AS max_prb_util
                    FROM cell_5g_metrics
                    WHERE start_time = %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                """
                params = [ts_5g] + cgids
                rows = self.pg.fetch_all(sql, tuple(params)) or []
                
                # 建立指标映射
                for row in rows:
                    cgi = row.get("cgi", "")
                    if cgi:
                        metrics_map[cgi] = row
            
            # 合并小区信息和指标数据
            all_cells = []
            for cgi, cell_info in cell_map.items():
                if cgi in metrics_map:
                    # 有数据的小区
                    metrics = metrics_map[cgi]
                    traffic_gb = metrics.get("traffic_gb") or 0
                    traffic_value, traffic_unit = format_traffic_with_unit(traffic_gb)
                    
                    all_cells.append({
                        "scenario": cell_info["scenario"],
                        "cell_id": metrics.get("cell_id") or cell_info["cell_id"],
                        "cgi": cgi,
                        "cellname": metrics.get("cellname") or cell_info["cell_name"],
                        "start_time": metrics.get("start_time"),
                        "traffic_gb": traffic_gb,
                        "ul_prb_util": metrics.get("ul_prb_util") or 0,
                        "dl_prb_util": metrics.get("dl_prb_util") or 0,
                        "max_prb_util": metrics.get("max_prb_util") or 0,
                        "connect_rate": metrics.get("connect_rate") or 0,
                        "rrc_users": metrics.get("rrc_users") or 0,
                        "interference": metrics.get("interference") or 0,
                        "traffic_value": traffic_value,
                        "traffic_unit": traffic_unit,
                        "has_data": True,
                    })
                else:
                    # 没有数据的小区，显示空值
                    all_cells.append({
                        "scenario": cell_info["scenario"],
                        "cell_id": cell_info["cell_id"],
                        "cgi": cgi,
                        "cellname": cell_info["cell_name"],
                        "start_time": ts_4g if network == "4G" else ts_5g,
                        "traffic_gb": 0,
                        "ul_prb_util": 0,
                        "dl_prb_util": 0,
                        "max_prb_util": 0,
                        "connect_rate": 0,
                        "rrc_users": 0,
                        "interference": 0,
                        "traffic_value": 0,
                        "traffic_unit": "GB",
                        "has_data": False,
                    })
            
            # 过滤小区
            if filter_text:
                filter_text_upper = filter_text.upper()
                filtered_cells = []
                for cell in all_cells:
                    cellname = str(cell.get("cellname", "")).upper()
                    cgi = str(cell.get("cgi", "")).upper()
                    if filter_text_upper in cellname or filter_text_upper in cgi:
                        filtered_cells.append(cell)
                all_cells = filtered_cells
            
            # 排序：有数据的按max_prb_util降序，没数据的排在后面
            all_cells.sort(key=lambda x: (not x["has_data"], -x["max_prb_util"]))
            
            # 分页
            total = len(all_cells)
            pages = (total + page_size - 1) // page_size if total else 0
            offset = (page - 1) * page_size
            
            return {
                "data": all_cells[offset:offset + page_size],
                "total": total,
                "page": page,
                "pages": pages
            }

        def build_result(network: str, cells: List[Dict[str, Any]], page: int):
            if not cells:
                return {"data": [], "total": 0, "page": page, "pages": 0}
            
            # 创建小区映射（CGI -> 小区信息）
            cell_map = {}
            for c in cells:
                cgi = c.get("cgi", "")
                if cgi:
                    cell_map[cgi] = {
                        "scenario": c.get("scenario", ""),
                        "cell_id": c.get("cell_id", ""),
                        "cell_name": c.get("cell_name", ""),
                        "cgi": cgi,
                    }
            
            cgids = list(cell_map.keys())
            if not cgids:
                return {"data": [], "total": 0, "page": page, "pages": 0}
            
            # 查询数据库中有数据的小区
            metrics_map = {}
            if network == "4G":
                if not ts_4g:
                    # 没有最新时间戳，返回所有小区但指标为空
                    all_cells_with_empty_metrics = []
                    for cgi, cell_info in cell_map.items():
                        all_cells_with_empty_metrics.append({
                            "scenario": cell_info["scenario"],
                            "cell_id": cell_info["cell_id"],
                            "cgi": cgi,
                            "cellname": cell_info["cell_name"],
                            "start_time": None,
                            "traffic_gb": 0,
                            "ul_prb_util": 0,
                            "dl_prb_util": 0,
                            "max_prb_util": 0,
                            "connect_rate": 0,
                            "rrc_users": 0,
                            "interference": 0,
                            "traffic_value": 0,
                            "traffic_unit": "GB",
                            "has_data": False,
                        })
                    # 过滤小区
                    if filter_text:
                        filter_text_upper = filter_text.upper()
                        filtered_cells = []
                        for cell in all_cells_with_empty_metrics:
                            cellname = str(cell.get("cellname", "")).upper()
                            cgi = str(cell.get("cgi", "")).upper()
                            if filter_text_upper in cellname or filter_text_upper in cgi:
                                filtered_cells.append(cell)
                        all_cells_with_empty_metrics = filtered_cells
                    # 分页
                    total = len(all_cells_with_empty_metrics)
                    pages = (total + page_size - 1) // page_size if total else 0
                    offset = (page - 1) * page_size
                    return {
                        "data": all_cells_with_empty_metrics[offset:offset + page_size],
                        "total": total,
                        "page": page,
                        "pages": pages
                    }
                
                sql = f"""
                    SELECT 
                        cell_id, cgi, start_time, cellname,
                        total_traffic_gb as traffic_gb,
                        ul_prb_utilization as ul_prb_util,
                        dl_prb_utilization as dl_prb_util,
                        wireless_connect_rate as connect_rate,
                        "RRC_ConnMax" as rrc_users,
                        interference,
                        GREATEST(COALESCE(ul_prb_utilization,0), COALESCE(dl_prb_utilization,0)) AS max_prb_util
                    FROM cell_4g_metrics
                    WHERE start_time = %s AND cgi IN ({','.join(['%s']*len(cgids))})
                """
                params = [ts_4g] + cgids
                rows = self.pg.fetch_all(sql, tuple(params)) or []
                
                # 建立指标映射
                for row in rows:
                    cgi = row.get("cgi", "")
                    if cgi:
                        metrics_map[cgi] = row
            else:
                if not ts_5g:
                    # 没有最新时间戳，返回所有小区但指标为空
                    all_cells_with_empty_metrics = []
                    for cgi, cell_info in cell_map.items():
                        all_cells_with_empty_metrics.append({
                            "scenario": cell_info["scenario"],
                            "cell_id": cell_info["cell_id"],
                            "cgi": cgi,
                            "cellname": cell_info["cell_name"],
                            "start_time": None,
                            "traffic_gb": 0,
                            "ul_prb_util": 0,
                            "dl_prb_util": 0,
                            "max_prb_util": 0,
                            "connect_rate": 0,
                            "rrc_users": 0,
                            "interference": 0,
                            "traffic_value": 0,
                            "traffic_unit": "GB",
                            "has_data": False,
                        })
                    # 过滤小区
                    if filter_text:
                        filter_text_upper = filter_text.upper()
                        filtered_cells = []
                        for cell in all_cells_with_empty_metrics:
                            cellname = str(cell.get("cellname", "")).upper()
                            cgi = str(cell.get("cgi", "")).upper()
                            if filter_text_upper in cellname or filter_text_upper in cgi:
                                filtered_cells.append(cell)
                        all_cells_with_empty_metrics = filtered_cells
                    # 分页
                    total = len(all_cells_with_empty_metrics)
                    pages = (total + page_size - 1) // page_size if total else 0
                    offset = (page - 1) * page_size
                    return {
                        "data": all_cells_with_empty_metrics[offset:offset + page_size],
                        "total": total,
                        "page": page,
                        "pages": pages
                    }
                
                sql = f"""
                    SELECT 
                        "Ncgi" as cell_id, "Ncgi" as cgi, start_time, userlabel as cellname,
                        (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 as traffic_gb,
                        "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) as ul_prb_util,
                        "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) as dl_prb_util,
                        ("RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0)) *
                        ("NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0)) *
                        ("Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0)) / 100.0 / 100.0 as connect_rate,
                        "RRC_ConnMax" as rrc_users,
                        interference,
                        GREATEST(
                            COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0),0),
                            COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0),0)
                        ) AS max_prb_util
                    FROM cell_5g_metrics
                    WHERE start_time = %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                """
                params = [ts_5g] + cgids
                rows = self.pg.fetch_all(sql, tuple(params)) or []
                
                # 建立指标映射
                for row in rows:
                    cgi = row.get("cgi", "")
                    if cgi:
                        metrics_map[cgi] = row
            
            # 合并小区信息和指标数据
            all_cells = []
            for cgi, cell_info in cell_map.items():
                if cgi in metrics_map:
                    # 有数据的小区
                    metrics = metrics_map[cgi]
                    traffic_gb = metrics.get("traffic_gb") or 0
                    traffic_value, traffic_unit = format_traffic_with_unit(traffic_gb)
                    
                    all_cells.append({
                        "scenario": cell_info["scenario"],
                        "cell_id": metrics.get("cell_id") or cell_info["cell_id"],
                        "cgi": cgi,
                        "cellname": metrics.get("cellname") or cell_info["cell_name"],
                        "start_time": metrics.get("start_time"),
                        "traffic_gb": traffic_gb,
                        "ul_prb_util": metrics.get("ul_prb_util") or 0,
                        "dl_prb_util": metrics.get("dl_prb_util") or 0,
                        "max_prb_util": metrics.get("max_prb_util") or 0,
                        "connect_rate": metrics.get("connect_rate") or 0,
                        "rrc_users": metrics.get("rrc_users") or 0,
                        "interference": metrics.get("interference") or 0,
                        "traffic_value": traffic_value,
                        "traffic_unit": traffic_unit,
                        "has_data": True,
                    })
                else:
                    # 没有数据的小区，显示空值
                    all_cells.append({
                        "scenario": cell_info["scenario"],
                        "cell_id": cell_info["cell_id"],
                        "cgi": cgi,
                        "cellname": cell_info["cell_name"],
                        "start_time": ts_4g if network == "4G" else ts_5g,
                        "traffic_gb": 0,
                        "ul_prb_util": 0,
                        "dl_prb_util": 0,
                        "max_prb_util": 0,
                        "connect_rate": 0,
                        "rrc_users": 0,
                        "interference": 0,
                        "traffic_value": 0,
                        "traffic_unit": "GB",
                        "has_data": False,
                    })
            
            # 过滤小区
            if filter_text:
                filter_text_upper = filter_text.upper()
                filtered_cells = []
                for cell in all_cells:
                    cellname = str(cell.get("cellname", "")).upper()
                    cgi = str(cell.get("cgi", "")).upper()
                    if filter_text_upper in cellname or filter_text_upper in cgi:
                        filtered_cells.append(cell)
                all_cells = filtered_cells
            
            # 排序：有数据的按max_prb_util降序，没数据的排在后面
            all_cells.sort(key=lambda x: (not x["has_data"], -x["max_prb_util"]))
            
            # 分页
            total = len(all_cells)
            pages = (total + page_size - 1) // page_size if total else 0
            offset = (page - 1) * page_size
            
            return {
                "data": all_cells[offset:offset + page_size],
                "total": total,
                "page": page,
                "pages": pages
            }

        return {
            "4G": build_result("4G", cells_4g, page_4g),
            "5G": build_result("5G", cells_5g, page_5g),
        }

    def traffic_trend(self, scenario_ids: Sequence[int], start: datetime, end: datetime, network: str) -> List[Dict[str, Any]]:
        if not scenario_ids:
            return []
        results: List[Dict[str, Any]] = []
        for sid in scenario_ids:
            s_name = self._scenario_name(sid)
            if not s_name:
                continue
            cells = [c for c in self.list_cells(sid) if c["network_type"] == network]
            if not cells:
                continue
            cgids = [c.get("cgi") for c in cells if c.get("cgi")]
            if not cgids:
                continue
            
            rows: List[Dict[str, Any]] = []
            # 主查询：时间范围内
            if network == "4G":
                sql = f"""
                    SELECT start_time, SUM(total_traffic_gb) AS total_traffic
                    FROM cell_4g_metrics
                    WHERE start_time BETWEEN %s AND %s AND cgi IN ({','.join(['%s']*len(cgids))})
                    GROUP BY start_time
                    ORDER BY start_time
                """
                params = (start, end, *cgids)
                rows = self.pg.fetch_all(sql, params)
                # 兜底：若无数据，取最近 48 个时间点，并按时间升序返回
                if not rows:
                    sql = f"""
                        SELECT start_time, SUM(total_traffic_gb) AS total_traffic
                        FROM cell_4g_metrics
                        WHERE cgi IN ({','.join(['%s']*len(cgids))})
                        GROUP BY start_time
                        ORDER BY start_time DESC
                        LIMIT 48
                    """
                    rows = self.pg.fetch_all(sql, tuple(cgids)) or []
                    rows = list(reversed(rows))
            else:
                sql = f"""
                    SELECT start_time,
                           SUM((COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0) AS total_traffic
                    FROM cell_5g_metrics
                    WHERE start_time BETWEEN %s AND %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                    GROUP BY start_time
                    ORDER BY start_time
                """
                params = (start, end, *cgids)
                rows = self.pg.fetch_all(sql, params)
                if not rows:
                    sql = f"""
                        SELECT start_time,
                               SUM((COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0) AS total_traffic
                        FROM cell_5g_metrics
                        WHERE "Ncgi" IN ({','.join(['%s']*len(cgids))})
                        GROUP BY start_time
                        ORDER BY start_time DESC
                        LIMIT 48
                    """
                    rows = self.pg.fetch_all(sql, tuple(cgids)) or []
                    rows = list(reversed(rows))
            for r in rows:
                results.append(
                    {
                        "scenario": s_name,
                        "network": network,
                        "start_time": str(r["start_time"]),  # 确保start_time是字符串格式
                        "total_traffic": r.get("total_traffic") or 0,
                    }
                )
        return results

    def connect_rate_trend(self, scenario_ids: Sequence[int], start: datetime, end: datetime, network: str) -> List[Dict[str, Any]]:
        if not scenario_ids:
            return []
        results: List[Dict[str, Any]] = []
        for sid in scenario_ids:
            s_name = self._scenario_name(sid)
            if not s_name:
                continue
            cells = [c for c in self.list_cells(sid) if c["network_type"] == network]
            if not cells:
                continue
            cgids = [c.get("cgi") for c in cells if c.get("cgi")]
            if not cgids:
                continue
            
            if network == "4G":
                # 4G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                sql = f"""
                    SELECT start_time, 
                           SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0) *
                           SUM("ERAB_NbrSuccEstab") * 100.0 / NULLIF(SUM("ERAB_NbrAttEstab"), 0) / 100.0 AS connect_rate
                    FROM cell_4g_metrics
                    WHERE start_time BETWEEN %s AND %s AND cgi IN ({','.join(['%s']*len(cgids))})
                    GROUP BY start_time
                    ORDER BY start_time
                """
            else:
                # 5G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                sql = f"""
                    SELECT start_time,
                           (SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0)) *
                           (SUM("NGSIG_ConnEstabSucc") * 100.0 / NULLIF(SUM("NGSIG_ConnEstabAtt"), 0)) *
                           (SUM("Flow_NbrSuccEstab") * 100.0 / NULLIF(SUM("Flow_NbrAttEstab"), 0)) / 100.0 / 100.0 AS connect_rate
                    FROM cell_5g_metrics
                    WHERE start_time BETWEEN %s AND %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                    GROUP BY start_time
                    ORDER BY start_time
                """
            params = (start, end, *cgids)
            rows = self.pg.fetch_all(sql, params)
            # 兜底：无数据时取最近 48 个时间点
            if not rows:
                if network == "4G":
                    # 4G无线接通率使用加权平均
                    sql = f"""
                        SELECT start_time, 
                               SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0) *
                               SUM("ERAB_NbrSuccEstab") * 100.0 / NULLIF(SUM("ERAB_NbrAttEstab"), 0) / 100.0 AS connect_rate
                        FROM cell_4g_metrics
                        WHERE cgi IN ({','.join(['%s']*len(cgids))})
                        GROUP BY start_time
                        ORDER BY start_time DESC
                        LIMIT 48
                    """
                    rows = self.pg.fetch_all(sql, tuple(cgids)) or []
                    rows = list(reversed(rows))
                else:
                    # 5G无线接通率使用加权平均
                    sql = f"""
                        SELECT start_time,
                               (SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0)) *
                               (SUM("NGSIG_ConnEstabSucc") * 100.0 / NULLIF(SUM("NGSIG_ConnEstabAtt"), 0)) *
                               (SUM("Flow_NbrSuccEstab") * 100.0 / NULLIF(SUM("Flow_NbrAttEstab"), 0)) / 100.0 / 100.0 AS connect_rate
                        FROM cell_5g_metrics
                        WHERE "Ncgi" IN ({','.join(['%s']*len(cgids))})
                        GROUP BY start_time
                        ORDER BY start_time DESC
                        LIMIT 48
                    """
                    rows = self.pg.fetch_all(sql, tuple(cgids)) or []
                    rows = list(reversed(rows))
            for r in rows:
                results.append(
                    {
                        "scenario": s_name,
                        "network": network,
                        "start_time": str(r["start_time"]),  # 确保start_time是字符串格式
                        "connect_rate": r.get("connect_rate") or 0,
                    }
                )
        return results

    def get_no_data_cells(self, scenario_ids: Sequence[int]) -> List[Dict[str, Any]]:
        """
        获取场景下无性能+无流量的小区列表
        
        Args:
            scenario_ids: 场景ID列表
        
        Returns:
            无性能+无流量小区列表
        """
        if not scenario_ids:
            return []

        latest = self.latest_time()
        ts_4g, ts_5g = latest.get("4g"), latest.get("5g")

        # 汇总所有场景的小区列表
        def collect_cells(network: str):
            cells_all = []
            for sid in scenario_ids:
                s_name = self._scenario_name(sid)
                if not s_name:
                    continue
                cells = [c for c in self.list_cells(sid) if c["network_type"] == network]
                for c in cells:
                    cells_all.append({"scenario": s_name, "network": network, **c})
            return cells_all

        cells_4g = collect_cells("4G")
        cells_5g = collect_cells("5G")
        all_cells = cells_4g + cells_5g

        # 创建小区映射（CGI -> 小区信息）
        cell_map = {}
        for c in all_cells:
            cgi = c.get("cgi", "")
            if cgi:
                cell_map[cgi] = {
                    "scenario": c.get("scenario", ""),
                    "network": c.get("network", ""),
                    "cell_id": c.get("cell_id", ""),
                    "cell_name": c.get("cell_name", ""),
                    "cgi": cgi,
                }

        cgids = list(cell_map.keys())
        if not cgids:
            return []

        # 查询数据库中有数据的小区
        metrics_map = {}
        
        # 查询4G数据
        if ts_4g:
            sql_4g = f"""
                SELECT 
                    cell_id, cgi, start_time, cellname,
                    total_traffic_gb as traffic_gb,
                    ul_prb_utilization as ul_prb_util,
                    dl_prb_utilization as dl_prb_util,
                    wireless_connect_rate as connect_rate,
                    "RRC_ConnMax" as rrc_users
                FROM cell_4g_metrics
                WHERE start_time = %s AND cgi IN ({','.join(['%s']*len(cgids))})
            """
            params_4g = [ts_4g] + cgids
            try:
                rows_4g = self.pg.fetch_all(sql_4g, tuple(params_4g)) or []
                for row in rows_4g:
                    cgi = row.get("cgi", "")
                    if cgi:
                        metrics_map[cgi] = row
            except Exception as e:
                pass
        
        # 查询5G数据
        if ts_5g:
            sql_5g = f"""
                SELECT 
                    "Ncgi" as cell_id, "Ncgi" as cgi, start_time, userlabel as cellname,
                    (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 as traffic_gb,
                    "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) as ul_prb_util,
                    "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) as dl_prb_util,
                    ("RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0)) *
                    ("NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0)) *
                    ("Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0)) / 100.0 / 100.0 as connect_rate,
                    "RRC_ConnMax" as rrc_users
                FROM cell_5g_metrics
                WHERE start_time = %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
            """
            params_5g = [ts_5g] + cgids
            try:
                rows_5g = self.pg.fetch_all(sql_5g, tuple(params_5g)) or []
                for row in rows_5g:
                    cgi = row.get("cgi", "")
                    if cgi:
                        metrics_map[cgi] = row
            except Exception as e:
                pass
        
        # 获取告警信息
        cgi_alarms = {}
        if self.mysql:
            try:
                # 查询中兴告警
                start_time = datetime.now() - timedelta(hours=1)
                sql_zte = """
                    SELECT 
                        alarm_object_type,
                        alarm_object_name,
                        alarm_object_id,
                        ne_id,
                        ne_name,
                        alarm_code_name as alarm_name,
                        import_time
                    FROM cur_alarm
                    WHERE import_time >= %s
                """
                zte_alarms = self.mysql.fetch_all(sql_zte, (start_time,)) or []
                
                # 查询诺基亚告警
                sql_nokia = """
                    SELECT 
                        enb_id as ne_id,
                        cgi,
                        fault_name_cn as alarm_name,
                        import_time
                    FROM cur_alarm_nokia
                    WHERE import_time >= %s
                """
                nokia_alarms = self.mysql.fetch_all(sql_nokia, (start_time,)) or []
                
                # 匹配告警到CGI
                # 对于中兴告警，需要从CGI中提取网元ID进行匹配
                ne_id_to_cgis = {}
                for cgi in cgids:
                    parts = cgi.split('-')
                    if len(parts) >= 3:
                        ne_id = parts[2]
                        if ne_id not in ne_id_to_cgis:
                            ne_id_to_cgis[ne_id] = []
                        ne_id_to_cgis[ne_id].append(cgi)
                
                # 匹配中兴告警
                for alarm in zte_alarms:
                    ne_id = alarm.get('ne_id')
                    if ne_id and ne_id in ne_id_to_cgis:
                        for cgi in ne_id_to_cgis[ne_id]:
                            if cgi not in cgi_alarms:
                                cgi_alarms[cgi] = []
                            cgi_alarms[cgi].append(alarm.get('alarm_name', '未知告警'))
                
                # 匹配诺基亚告警（直接使用CGI）
                for alarm in nokia_alarms:
                    cgi = alarm.get('cgi')
                    if cgi and cgi in cell_map:
                        if cgi not in cgi_alarms:
                            cgi_alarms[cgi] = []
                        cgi_alarms[cgi].append(alarm.get('alarm_name', '未知告警'))
            except Exception as e:
                pass
        
        # 筛选无性能+无流量的小区
        no_data_cells = []
        for cgi, cell_info in cell_map.items():
            if cgi in metrics_map:
                # 有数据的小区，但流量为0且PRB利用率为0
                metrics = metrics_map[cgi]
                traffic_gb = metrics.get("traffic_gb") or 0
                ul_prb = metrics.get("ul_prb_util") or 0
                dl_prb = metrics.get("dl_prb_util") or 0
                
                if traffic_gb == 0 and ul_prb == 0 and dl_prb == 0:
                    traffic_value, traffic_unit = format_traffic_with_unit(traffic_gb)
                    alarms = cgi_alarms.get(cgi, [])
                    no_data_cells.append({
                        "scenario": cell_info["scenario"],
                        "network": cell_info["network"],
                        "cell_id": metrics.get("cell_id") or cell_info["cell_id"],
                        "cgi": cgi,
                        "cellname": metrics.get("cellname") or cell_info["cell_name"],
                        "start_time": metrics.get("start_time"),
                        "traffic_gb": traffic_gb,
                        "traffic_value": traffic_value,
                        "traffic_unit": traffic_unit,
                        "ul_prb_util": ul_prb,
                        "dl_prb_util": dl_prb,
                        "connect_rate": metrics.get("connect_rate") or 0,
                        "rrc_users": metrics.get("rrc_users") or 0,
                        "has_data": True,
                        "has_alarm": len(alarms) > 0,
                        "alarm_details": "；".join(alarms) if alarms else "无"
                    })
            else:
                # 没有数据的小区
                alarms = cgi_alarms.get(cgi, [])
                no_data_cells.append({
                    "scenario": cell_info["scenario"],
                    "network": cell_info["network"],
                    "cell_id": cell_info["cell_id"],
                    "cgi": cgi,
                    "cellname": cell_info["cell_name"],
                    "start_time": ts_4g if cell_info["network"] == "4G" else ts_5g,
                    "traffic_gb": 0,
                    "traffic_value": 0,
                    "traffic_unit": "GB",
                    "ul_prb_util": 0,
                    "dl_prb_util": 0,
                    "connect_rate": 0,
                    "rrc_users": 0,
                    "has_data": False,
                    "has_alarm": len(alarms) > 0,
                    "alarm_details": "；".join(alarms) if alarms else "无"
                })
        
        return no_data_cells

    def util_trend(self, scenario_ids: Sequence[int], start: datetime, end: datetime, network: str) -> List[Dict[str, Any]]:
        """获取场景利用率趋势（上下行一起返回）。"""
        if not scenario_ids:
            return []
        results: List[Dict[str, Any]] = []
        for sid in scenario_ids:
            s_name = self._scenario_name(sid)
            if not s_name:
                continue
            cells = [c for c in self.list_cells(sid) if c["network_type"] == network]
            if not cells:
                continue
            cgids = [c.get("cgi") for c in cells if c.get("cgi")]
            if not cgids:
                continue
            
            rows: List[Dict[str, Any]] = []
            if network == "4G":
                # 4G PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                sql = f"""
                    SELECT start_time,
                           SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS ul_prb,
                           SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS dl_prb
                    FROM cell_4g_metrics
                    WHERE start_time BETWEEN %s AND %s AND cgi IN ({','.join(['%s']*len(cgids))})
                    GROUP BY start_time
                    ORDER BY start_time
                """
                params = (start, end, *cgids)
                rows = self.pg.fetch_all(sql, params)
                if not rows:
                    sql = f"""
                        SELECT start_time,
                               SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS ul_prb,
                               SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS dl_prb
                        FROM cell_4g_metrics
                        WHERE cgi IN ({','.join(['%s']*len(cgids))})
                        GROUP BY start_time
                        ORDER BY start_time DESC
                        LIMIT 48
                    """
                    rows = self.pg.fetch_all(sql, tuple(cgids)) or []
                    rows = list(reversed(rows))
            else:
                # 5G PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                sql = f"""
                    SELECT start_time,
                           SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS ul_prb,
                           SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS dl_prb
                    FROM cell_5g_metrics
                    WHERE start_time BETWEEN %s AND %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                    GROUP BY start_time
                    ORDER BY start_time
                """
                params = (start, end, *cgids)
                rows = self.pg.fetch_all(sql, params)
                if not rows:
                    sql = f"""
                        SELECT start_time,
                               SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS ul_prb,
                               SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS dl_prb
                        FROM cell_5g_metrics
                        WHERE "Ncgi" IN ({','.join(['%s']*len(cgids))})
                        GROUP BY start_time
                        ORDER BY start_time DESC
                        LIMIT 48
                    """
                    rows = self.pg.fetch_all(sql, tuple(cgids)) or []
                    rows = list(reversed(rows))

            for r in rows:
                results.append(
                    {
                        "scenario": s_name,
                        "network": network,
                        "start_time": str(r["start_time"]),
                        "ul_prb": r.get("ul_prb") or 0,
                        "dl_prb": r.get("dl_prb") or 0,
                    }
                )
        return results

    def util_snapshot(self, scenario_ids: Sequence[int]) -> Dict[str, Dict[str, float | str]]:
        """获取最新时刻的平均上/下行PRB利用率（按场景汇总）。"""
        result = {"4g": {"ts": None, "ul": 0.0, "dl": 0.0}, "5g": {"ts": None, "ul": 0.0, "dl": 0.0}}
        latest = self.latest_time()
        ts_4g, ts_5g = latest.get("4g"), latest.get("5g")
        if not scenario_ids:
            return result
        # 4G - 使用加权平均：SUM(已用PRB)/SUM(总PRB)
        if ts_4g:
            cells_4g = []
            for sid in scenario_ids:
                cells_4g.extend([c for c in self.list_cells(sid) if c["network_type"] == "4G"])
            if cells_4g:
                cgids = [c.get("cgi") for c in cells_4g if c.get("cgi")]
                if cgids:
                    sql = f"""
                        SELECT 
                            SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS ul,
                            SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS dl
                        FROM cell_4g_metrics
                        WHERE start_time = %s AND cgi IN ({','.join(['%s']*len(cgids))})
                    """
                    row = self.pg.fetch_one(sql, (ts_4g, *cgids)) or {}
                    result["4g"] = {"ts": ts_4g, "ul": row.get("ul") or 0.0, "dl": row.get("dl") or 0.0}
        # 5G - 使用加权平均：SUM(已用PRB)/SUM(总PRB)
        if ts_5g:
            cells_5g = []
            for sid in scenario_ids:
                cells_5g.extend([c for c in self.list_cells(sid) if c["network_type"] == "5G"])
            if cells_5g:
                cgids = [c.get("cgi") for c in cells_5g if c.get("cgi")]
                if cgids:
                    sql = f"""
                        SELECT
                            SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) AS ul,
                            SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) AS dl
                        FROM cell_5g_metrics
                        WHERE start_time = %s AND "Ncgi" IN ({','.join(['%s']*len(cgids))})
                    """
                    row = self.pg.fetch_one(sql, (ts_5g, *cgids)) or {}
                    result["5g"] = {"ts": ts_5g, "ul": row.get("ul") or 0.0, "dl": row.get("dl") or 0.0}
        return result
