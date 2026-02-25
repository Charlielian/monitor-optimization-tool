import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Sequence, Tuple, Optional

from db.pg import PostgresClient
from constants import (
    GRANULARITY_1HOUR,
    TABLE_4G_15MIN,
    TABLE_4G_1HOUR,
    TABLE_5G_15MIN,
    TABLE_5G_1HOUR,
    TIME_RANGE_6H,
    TIME_RANGE_12H,
    TIME_RANGE_24H,
)
from utils.formatters import bytes_to_gb


class MetricsService:
    @staticmethod
    def downsample_data(data, max_points=100):
        """
        数据降采样 - 减少前端渲染压力
        
        Args:
            data: 原始数据列表
            max_points: 最大数据点数量
        
        Returns:
            降采样后的数据
        """
        if not data or len(data) <= max_points:
            return data
        
        step = max(1, len(data) // max_points)
        return data[::step]

    def __init__(self, pg_client: PostgresClient, engineering_params_service: Optional[Any] = None) -> None:
        self.pg = pg_client
        self.engineering_params_service = engineering_params_service
        
        # 表名映射，避免字符串拼接
        self._table_map = {
            ("4G", "15m"): TABLE_4G_15MIN,
            ("4G", "1h"): TABLE_4G_1HOUR,
            ("5G", "15m"): TABLE_5G_15MIN,
            ("5G", "1h"): TABLE_5G_1HOUR,
        }
        
        # 时间范围映射
        self._time_range_map = {
            TIME_RANGE_6H: timedelta(hours=6),
            TIME_RANGE_12H: timedelta(hours=12),
            TIME_RANGE_24H: timedelta(hours=24),
        }

    def get_table_name(self, network_type: str, granularity: str = "15m") -> str:
        """根据网络类型和粒度返回表名
        
        Args:
            network_type: "4G" 或 "5G"
            granularity: "15m" (15分钟) 或 "1h" (1小时) 或 "1d" (1天)
        
        Returns:
            表名，如 "cell_4g_metrics" 或 "cell_4g_metrics_day"
        """
        if granularity == "1d":
            # 天级指标表
            if network_type == "4G":
                table_name = "cell_4g_metrics_day"
            else:
                table_name = "cell_5g_metrics_day"
            logging.info(f"📊 查询表: {table_name} (粒度: {granularity}, 制式: {network_type})")
            return table_name
        else:
            # 根据粒度选择相应的表
            table_name = self._table_map.get(
                (network_type, granularity),
                TABLE_4G_15MIN if network_type == "4G" else TABLE_5G_15MIN
            )
            logging.info(f"📊 查询表: {table_name} (粒度: {granularity}, 制式: {network_type})")
            return table_name

    @staticmethod
    def resolve_range(range_key: str, reference_time: datetime | None = None) -> Tuple[datetime, datetime]:
        """Return (start, end) window aligned to reference_time (or now).

        Using reference_time allows us to align to the latest data timestamp
        when数据库时间晚于当前时间（例如时区差导致的“未来”时间），避免空查询。
        """
        now = (reference_time or datetime.now()).replace(second=0, microsecond=0)
        mapping = {
            "6h": timedelta(hours=6),
            "12h": timedelta(hours=12),
            "24h": timedelta(hours=24),
        }
        delta = mapping.get(range_key, mapping["6h"])
        return now - delta, now

    def traffic_series(
        self, network_types: Sequence[str], start: datetime, end: datetime, granularity: str = "15m"
    ) -> List[Dict[str, Any]]:
        data: List[Dict[str, Any]] = []

        if "4G" in network_types:
            table_4g = self.get_table_name("4G", granularity)
            sql_4g = f"""
                SELECT
                    start_time,
                    '4G' AS network_type,
                    SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic,
                    SUM(COALESCE("PDCP_UpOctUl", 0)) / 1000.0 / 1000.0 AS uplink_traffic,
                    SUM(COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS downlink_traffic
                FROM {table_4g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql_4g, (start, end)))

        if "5G" in network_types:
            table_5g = self.get_table_name("5G", granularity)
            sql_5g = f"""
                SELECT
                    start_time,
                    '5G' AS network_type,
                    SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic,
                    SUM(COALESCE("RLC_UpOctUl", 0)) / 1000.0 / 1000.0 AS uplink_traffic,
                    SUM(COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS downlink_traffic
                FROM {table_5g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                HAVING SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql_5g, (start, end)))

        return data

    def voice_series(
        self, network_types: Sequence[str], start: datetime, end: datetime, granularity: str = "15m"
    ) -> List[Dict[str, Any]]:
        data: List[Dict[str, Any]] = []

        if "4G" in network_types:
            table_4g = self.get_table_name("4G", granularity)
            sql_4g = f"""
                SELECT
                    start_time,
                    '4G' AS network_type,
                    SUM(COALESCE("ERAB_NbrMeanEstab_1", 0)) / 4.0 AS voice_erl
                FROM {table_4g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql_4g, (start, end)))

        if "5G" in network_types:
            table_5g = self.get_table_name("5G", granularity)
            sql_5g = f"""
                SELECT
                    start_time,
                    '5G' AS network_type,
                    SUM(COALESCE("Flow_NbrMeanEstab_5QI1", 0)) / 4.0 AS voice_erl
                FROM {table_5g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql_5g, (start, end)))

        return data

    def top_cells(self, network_types: Sequence[str], limit: int = 20, granularity: str = "15m") -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        if "4G" in network_types:
            table_4g = self.get_table_name("4G", granularity)
            latest_4g = self.pg.fetch_one(
                f"SELECT MAX(start_time) AS ts FROM {table_4g}"
            )
            if latest_4g and latest_4g.get("ts"):
                sql = f"""
                    SELECT
                        cell_id,
                        cellname,
                        cgi,
                        '4G' AS network_type,
                        (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                        ul_prb_utilization AS ul_prb_util,
                        dl_prb_utilization AS dl_prb_util,
                        CASE
                            WHEN ul_prb_utilization > dl_prb_utilization THEN ul_prb_utilization
                            ELSE dl_prb_utilization
                        END AS max_prb_util,
                        wireless_connect_rate AS connect_rate,
                        "RRC_ConnMax" AS max_rrc_users,
                        interference
                    FROM {table_4g}
                    WHERE start_time = %s
                    ORDER BY max_prb_util DESC
                    LIMIT %s
                """
                rows.extend(self.pg.fetch_all(sql, (latest_4g["ts"], limit)))

        if "5G" in network_types:
            table_5g = self.get_table_name("5G", granularity)
            latest_5g = self.pg.fetch_one(
                f"SELECT MAX(start_time) AS ts FROM {table_5g}"
            )
            if latest_5g and latest_5g.get("ts"):
                sql = f"""
                    SELECT
                        "Ncgi" AS cell_id,
                        userlabel AS cellname,
                        "Ncgi" AS cgi,
                        '5G' AS network_type,
                        (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                        "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) AS ul_prb_util,
                        "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) AS dl_prb_util,
                        CASE
                            WHEN ("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0)) >
                                 ("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0))
                            THEN ("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0))
                            ELSE ("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0))
                        END AS max_prb_util,
                        ("RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0)) *
                        ("NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0)) *
                        ("Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0)) / 100.0 / 100.0 AS connect_rate,
                        "RRC_ConnMax" AS max_rrc_users,
                        interference
                    FROM {table_5g}
                    WHERE start_time = %s
                    ORDER BY max_prb_util DESC
                    LIMIT %s
                """
                rows.extend(self.pg.fetch_all(sql, (latest_5g["ts"], limit)))

        return rows

    def cell_timeseries(
        self,
        cell_id: str,
        network_type: str,
        start: datetime,
        end: datetime,
        granularity: str = "15m",
    ) -> List[Dict[str, Any]]:
        if network_type == "4G":
            table_4g = self.get_table_name("4G", granularity)
            sql = f"""
                SELECT
                    start_time,
                    cell_id,
                    cgi,
                    cellname,
                    (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                    COALESCE("RRC_SuccConnEstab",0) * 100.0 / NULLIF(COALESCE("RRC_AttConnEstab",0), 0) AS rrc_success_rate,
                    COALESCE("ERAB_NbrSuccEstab",0) * 100.0 / NULLIF(COALESCE("ERAB_NbrAttEstab",0), 0) AS erab_success_rate,
                    wireless_connect_rate,
                    wireless_drop_rate,
                    dl_prb_utilization,
                    ul_prb_utilization,
                    ul_speed_mbps,
                    dl_speed_mbps,
                    interference,
                    "RRC_ConnMax" AS rrc_users,
                    COALESCE("ERAB_NbrMeanEstab_1", 0) / 4.0 AS voice_erl,
                    -- 切换成功率
                    (COALESCE("HO_SuccOutInterEnbS1",0) + COALESCE("HO_SuccOutInterEnbX2",0) + COALESCE("HO_SuccOutIntraEnb",0)) * 100.0 / NULLIF((COALESCE("HO_AttOutInterEnbS1",0) + COALESCE("HO_AttOutInterEnbX2",0) + COALESCE("HO_AttOutIntraEnb",0)), 0) AS ho_success_rate,
                    -- Erab掉线率
                    (COALESCE("ERAB_HoFail",0) - COALESCE("ERAB_NbrReqRelEnb_Normal",0) + COALESCE("ERAB_NbrReqRelEnb",0)) * 100.0 / NULLIF((COALESCE("CONTEXT_NbrLeft",0) + COALESCE("ERAB_NbrSuccEstab",0) + COALESCE("ERAB_NbrHoInc",0)), 0) AS erab_drop_rate
                FROM {table_4g}
                WHERE (cell_id = %s OR cgi = %s) AND start_time BETWEEN %s AND %s
                ORDER BY start_time
            """
            return self.pg.fetch_all(sql, (cell_id, cell_id, start, end))

        table_5g = self.get_table_name("5G", granularity)
        sql = f"""
            SELECT
                start_time,
                "Ncgi" AS cell_id,
                "Ncgi" AS cgi,
                userlabel AS cellname,
                (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                "RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0) AS rrc_success_rate,
                "NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0) AS erab_success_rate,
                "RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0) AS wireless_connect_rate,
                0 AS wireless_drop_rate,
                "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) AS dl_prb_utilization,
                "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) AS ul_prb_utilization,
                0 AS ul_speed_mbps,
                0 AS dl_speed_mbps,
                interference,
                "RRC_ConnMax" AS rrc_users,
                COALESCE("Flow_NbrMeanEstab_5QI1", 0) / 4.0 AS voice_erl,
                    -- 切换成功率
                    (COALESCE("HO_SuccOutInterCuNG",0) + COALESCE("HO_SuccOutInterCuXn",0) + COALESCE("HO_SuccOutIntraCUInterDU",0) + COALESCE("HO_SuccOutIntraDU",0)) * 100.0 / NULLIF((COALESCE("HO_AttOutInterCuNG",0) + COALESCE("HO_AttOutInterCuXn",0) + COALESCE("HO_AttOutIntraCUInterDU",0) + COALESCE("HO_AttOutCUIntraDU",0)), 0) AS ho_success_rate,
                    -- 无线掉线率
                    (COALESCE("CONTEXT_AttRelgNB",0) - COALESCE("CONTEXT_AttRelgNB_Normal",0)) * 100.0 / NULLIF((COALESCE("CONTEXT_SuccInitalSetup",0) + COALESCE("CONTEXT_NbrLeft",0) + COALESCE("HO_SuccExecInc",0) + COALESCE("RRC_SuccConnReestab_NonSrccell",0)), 0) AS wireless_drop_rate_5g,
                    -- Flow接通率
                    "Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0) AS flow_success_rate
            FROM {table_5g}
            WHERE "Ncgi" = %s AND start_time BETWEEN %s AND %s
            ORDER BY start_time
        """
        return self.pg.fetch_all(sql, (cell_id, start, end))

    @staticmethod
    def _dedupe(values: Sequence[str]) -> List[str]:
        seen = set()
        uniq: List[str] = []
        for v in values:
            if v not in seen:
                seen.add(v)
                uniq.append(v)
        return uniq

    def cell_timeseries_bulk(
        self,
        cell_ids: Sequence[str],
        network_type: str,
        start: datetime,
        end: datetime,
        granularity: str = "15m",
    ) -> List[Dict[str, Any]]:
        """查询小区时间序列数据
        
        Args:
            cell_ids: 小区ID列表
            network_type: 网络类型 (4G/5G)
            start: 开始时间
            end: 结束时间
            granularity: 粒度 (15m/1h/1d)
        """
        if not cell_ids:
            return []
        ids = self._dedupe([c for c in cell_ids if c])
        if not ids:
            return []

        if network_type == "4G":
            table_4g = self.get_table_name("4G", granularity)
            placeholders = ",".join(["%s"] * len(ids))
            sql = f"""
                SELECT
                    start_time,
                    cell_id,
                    cgi,
                    cellname,
                    (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                    COALESCE("RRC_SuccConnEstab",0) * 100.0 / NULLIF(COALESCE("RRC_AttConnEstab",0), 0) AS rrc_success_rate,
                    COALESCE("ERAB_NbrSuccEstab",0) * 100.0 / NULLIF(COALESCE("ERAB_NbrAttEstab",0), 0) AS erab_success_rate,
                    wireless_connect_rate,
                    wireless_drop_rate,
                    dl_prb_utilization,
                    ul_prb_utilization,
                    ul_speed_mbps,
                    dl_speed_mbps,
                    interference,
                    "RRC_ConnMax" AS rrc_users,
                    COALESCE("ERAB_NbrMeanEstab_1", 0) / 4.0 AS voice_erl,
                    -- 切换成功率
                    (COALESCE("HO_SuccOutInterEnbS1",0) + COALESCE("HO_SuccOutInterEnbX2",0) + COALESCE("HO_SuccOutIntraEnb",0)) * 100.0 / NULLIF((COALESCE("HO_AttOutInterEnbS1",0) + COALESCE("HO_AttOutInterEnbX2",0) + COALESCE("HO_AttOutIntraEnb",0)), 0) AS ho_success_rate,
                    -- Erab掉线率
                    (COALESCE("ERAB_HoFail",0) - COALESCE("ERAB_NbrReqRelEnb_Normal",0) + COALESCE("ERAB_NbrReqRelEnb",0)) * 100.0 / NULLIF((COALESCE("CONTEXT_NbrLeft",0) + COALESCE("ERAB_NbrSuccEstab",0) + COALESCE("ERAB_NbrHoInc",0)), 0) AS erab_drop_rate
                FROM {table_4g}
                WHERE start_time BETWEEN %s AND %s
                  AND (cell_id IN ({placeholders}) OR cgi IN ({placeholders}))
                ORDER BY start_time, cell_id
            """
            params: List[Any] = [start, end] + list(ids) + list(ids)
            return self.pg.fetch_all(sql, tuple(params))

        table_5g = self.get_table_name("5G", granularity)
        placeholders = ",".join(["%s"] * len(ids))
        sql = f"""
            SELECT
                start_time,
                "Ncgi" AS cell_id,
                "Ncgi" AS cgi,
                userlabel AS cellname,
                (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                "RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0) AS rrc_success_rate,
                "NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0) AS erab_success_rate,
                "RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0) AS wireless_connect_rate,
                0 AS wireless_drop_rate,
                "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) AS dl_prb_utilization,
                "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) AS ul_prb_utilization,
                0 AS ul_speed_mbps,
                0 AS dl_speed_mbps,
                interference,
                "RRC_ConnMax" AS rrc_users,
                COALESCE("Flow_NbrMeanEstab_5QI1", 0) / 4.0 AS voice_erl,
                -- 切换成功率
                (COALESCE("HO_SuccOutInterCuNG",0) + COALESCE("HO_SuccOutInterCuXn",0) + COALESCE("HO_SuccOutIntraCUInterDU",0) + COALESCE("HO_SuccOutIntraDU",0)) * 100.0 / NULLIF((COALESCE("HO_AttOutInterCuNG",0) + COALESCE("HO_AttOutInterCuXn",0) + COALESCE("HO_AttOutIntraCUInterDU",0) + COALESCE("HO_AttOutCUIntraDU",0)), 0) AS ho_success_rate,
                -- 无线掉线率
                (COALESCE("CONTEXT_AttRelgNB",0) - COALESCE("CONTEXT_AttRelgNB_Normal",0)) * 100.0 / NULLIF((COALESCE("CONTEXT_SuccInitalSetup",0) + COALESCE("CONTEXT_NbrLeft",0) + COALESCE("HO_SuccExecInc",0) + COALESCE("RRC_SuccConnReestab_NonSrccell",0)), 0) AS wireless_drop_rate_5g,
                -- Flow接通率
                "Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0) AS flow_success_rate
            FROM {table_5g}
            WHERE "Ncgi" IN ({placeholders}) AND start_time BETWEEN %s AND %s
            ORDER BY start_time, "Ncgi"
        """
        params = list(ids) + [start, end]
        return self.pg.fetch_all(sql, tuple(params))
    
    def cell_timeseries_summary(
        self,
        cell_ids: Sequence[str],
        network_type: str,
        start: datetime,
        end: datetime,
        granularity: str = "15m",
    ) -> List[Dict[str, Any]]:
        """汇总查询：将多个CGI按照时间汇总成一条记录
        
        Args:
            cell_ids: 小区ID列表
            network_type: 网络类型 (4G/5G)
            start: 开始时间
            end: 结束时间
            granularity: 粒度 (15m/1h/1d)
            
        Returns:
            汇总后的指标数据列表
        """
        if network_type == "4G":
            table_4g = self.get_table_name("4G", granularity)
            placeholders = ",".join(["%s"] * len(cell_ids))
            sql = f"""
                SELECT
                    start_time,
                    '4G' AS network_type,
                    '汇总' AS cell_id,
                    '汇总' AS cgi,
                    '汇总' AS cellname,
                    SUM((COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0) AS total_traffic,
                    -- RRC接通率（按成功数和尝试数分别汇总后计算，加权平均）
                    SUM(COALESCE("RRC_SuccConnEstab",0)) * 100.0 / NULLIF(SUM(COALESCE("RRC_AttConnEstab",0)), 0) AS rrc_success_rate,
                    -- ERAB接通率（按成功数和尝试数分别汇总后计算，加权平均）
                    SUM(COALESCE("ERAB_NbrSuccEstab",0)) * 100.0 / NULLIF(SUM(COALESCE("ERAB_NbrAttEstab",0)), 0) AS erab_success_rate,
                    -- 无线接通率（按成功数和尝试数分别汇总后计算，加权平均）
                    (SUM(COALESCE("RRC_SuccConnEstab",0)) * 100.0 / NULLIF(SUM(COALESCE("RRC_AttConnEstab",0)), 0)) * 
                    (SUM(COALESCE("ERAB_NbrSuccEstab",0)) * 100.0 / NULLIF(SUM(COALESCE("ERAB_NbrAttEstab",0)), 0)) / 100.0 AS wireless_connect_rate,
                    -- 掉线率（按分子和分母分别汇总后计算，加权平均）
                    (SUM(COALESCE("ERAB_HoFail",0) - COALESCE("ERAB_NbrReqRelEnb_Normal",0) + COALESCE("ERAB_NbrReqRelEnb",0)) * 100.0) / NULLIF(SUM(COALESCE("CONTEXT_NbrLeft",0) + COALESCE("ERAB_NbrSuccEstab",0) + COALESCE("ERAB_NbrHoInc",0)), 0) AS wireless_drop_rate,
                    -- 下行PRB利用率（分子sum/分母sum）
                    SUM(COALESCE("RRU_PdschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PdschPrbTot", 0)), 0) AS dl_prb_utilization,
                    -- 上行PRB利用率（分子sum/分母sum）
                    SUM(COALESCE("RRU_PuschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PuschPrbTot", 0)), 0) AS ul_prb_utilization,
                    AVG(ul_speed_mbps) AS ul_speed_mbps,
                    AVG(dl_speed_mbps) AS dl_speed_mbps,
                    AVG(interference) AS interference,
                    -- RRC用户数（求和）
                    SUM("RRC_ConnMax") AS rrc_users,
                    SUM(COALESCE("ERAB_NbrMeanEstab_1", 0) / 4.0) AS voice_erl,
                    -- 切换成功率（分子sum/分母sum）
                    SUM(COALESCE("HO_SuccOutInterEnbS1",0) + COALESCE("HO_SuccOutInterEnbX2",0) + COALESCE("HO_SuccOutIntraEnb",0)) * 100.0 / NULLIF(SUM(COALESCE("HO_AttOutInterEnbS1",0) + COALESCE("HO_AttOutInterEnbX2",0) + COALESCE("HO_AttOutIntraEnb",0)), 0) AS ho_success_rate,
                    -- Erab掉线率（分子sum/分母sum）
                    SUM(COALESCE("ERAB_HoFail",0) - COALESCE("ERAB_NbrReqRelEnb_Normal",0) + COALESCE("ERAB_NbrReqRelEnb",0)) * 100.0 / NULLIF(SUM(COALESCE("CONTEXT_NbrLeft",0) + COALESCE("ERAB_NbrSuccEstab",0) + COALESCE("ERAB_NbrHoInc",0)), 0) AS erab_drop_rate
                FROM {table_4g}
                WHERE start_time BETWEEN %s AND %s
                  AND (cell_id IN ({placeholders}) OR cgi IN ({placeholders}))
                GROUP BY start_time
                ORDER BY start_time
            """
            params = [start, end] + list(cell_ids) + list(cell_ids)
            return self.pg.fetch_all(sql, tuple(params))
        else:
            table_5g = self.get_table_name("5G", granularity)
            placeholders = ",".join(["%s"] * len(cell_ids))
            sql = f"""
                SELECT
                    start_time,
                    '5G' AS network_type,
                    '汇总' AS cell_id,
                    '汇总' AS cgi,
                    '汇总' AS cellname,
                    SUM((COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0) AS total_traffic,
                    -- RRC接通率（分子sum/分母sum）
                    SUM(COALESCE("RRC_SuccConnEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRC_AttConnEstab", 0)), 0) AS rrc_success_rate,
                    -- NG接通率（分子sum/分母sum）
                    SUM(COALESCE("NGSIG_ConnEstabSucc", 0)) * 100.0 / NULLIF(SUM(COALESCE("NGSIG_ConnEstabAtt", 0)), 0) AS erab_success_rate,
                    -- 无线接通率（分子sum/分母sum）
                    (SUM(COALESCE("RRC_SuccConnEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRC_AttConnEstab", 0)), 0)) * 
                    (SUM(COALESCE("NGSIG_ConnEstabSucc", 0)) * 100.0 / NULLIF(SUM(COALESCE("NGSIG_ConnEstabAtt", 0)), 0)) * 
                    (SUM(COALESCE("Flow_NbrSuccEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("Flow_NbrAttEstab", 0)), 0)) / 100.0 / 100.0 AS wireless_connect_rate,
                    0 AS wireless_drop_rate,
                    -- 下行PRB利用率（分子sum/分母sum）
                    SUM(COALESCE("RRU_PdschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PdschPrbTot", 0)), 0) AS dl_prb_utilization,
                    -- 上行PRB利用率（分子sum/分母sum）
                    SUM(COALESCE("RRU_PuschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PuschPrbTot", 0)), 0) AS ul_prb_utilization,
                    0 AS ul_speed_mbps,
                    0 AS dl_speed_mbps,
                    AVG(interference) AS interference,
                    -- RRC用户数（求和）
                    SUM("RRC_ConnMax") AS rrc_users,
                    SUM(COALESCE("Flow_NbrMeanEstab_5QI1", 0) / 4.0) AS voice_erl,
                    -- 切换成功率（按成功数和尝试数分别汇总后计算）
                    SUM(COALESCE("HO_SuccOutInterCuNG",0) + COALESCE("HO_SuccOutInterCuXn",0) + COALESCE("HO_SuccOutIntraCUInterDU",0) + COALESCE("HO_SuccOutIntraDU",0)) * 100.0 / NULLIF(SUM(COALESCE("HO_AttOutInterCuNG",0) + COALESCE("HO_AttOutInterCuXn",0) + COALESCE("HO_AttOutIntraCUInterDU",0) + COALESCE("HO_AttOutCUIntraDU",0)), 0) AS ho_success_rate,
                    -- 无线掉线率（按分子和分母分别汇总后计算）
                    SUM(COALESCE("CONTEXT_AttRelgNB",0) - COALESCE("CONTEXT_AttRelgNB_Normal",0)) * 100.0 / NULLIF(SUM(COALESCE("CONTEXT_SuccInitalSetup",0) + COALESCE("CONTEXT_NbrLeft",0) + COALESCE("HO_SuccExecInc",0) + COALESCE("RRC_SuccConnReestab_NonSrccell",0)), 0) AS wireless_drop_rate_5g,
                    -- Flow接通率（分子sum/分母sum）
                    SUM(COALESCE("Flow_NbrSuccEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("Flow_NbrAttEstab", 0)), 0) AS flow_success_rate
                FROM {table_5g}
                WHERE start_time BETWEEN %s AND %s
                  AND "Ncgi" IN ({placeholders})
                GROUP BY start_time
                ORDER BY start_time
            """
            params = [start, end] + list(cell_ids)
            return self.pg.fetch_all(sql, tuple(params))

    def cell_timeseries_mixed(
        self,
        cell_ids: Sequence[str],
        start: datetime,
        end: datetime,
        granularity: str = "15m",
    ) -> tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """混查模式：自动识别CGI并分别查询4G和5G小区
        
        Args:
            cell_ids: 小区ID列表
            start: 开始时间
            end: 结束时间
            granularity: 粒度 (15m/1h/1d)
            
        Returns:
            (数据列表, 自动识别的网络类型字典)
        """
        if not cell_ids:
            return [], {}
        
        # 自动识别CGI类型
        cgi_4g = []
        cgi_5g = []
        auto_detected = {"4G": [], "5G": [], "unknown": []}
        
        for cgi in cell_ids:
            if not cgi:
                continue
            # CGI格式: 460-00-enb-lcrid 或 460-00-gnb-lcrid
            parts = cgi.split('-')
            if len(parts) >= 4:
                # 提取enb/gnb部分（第3个部分）
                enb_gnb = parts[2]
                if len(enb_gnb) == 6:
                    # 6位是4G eNodeB
                    cgi_4g.append(cgi)
                    auto_detected["4G"].append(cgi)
                elif len(enb_gnb) == 8:
                    # 8位是5G gNodeB
                    cgi_5g.append(cgi)
                    auto_detected["5G"].append(cgi)
                else:
                    auto_detected["unknown"].append(cgi)
            else:
                auto_detected["unknown"].append(cgi)
        
        # 分别查询4G和5G数据
        all_data = []
        
        if cgi_4g:
            data_4g = self.cell_timeseries_bulk(cgi_4g, "4G", start, end, granularity)
            for row in data_4g:
                row['network_type'] = '4G'
                if 'cgi' not in row or not row.get('cgi'):
                    row['cgi'] = row.get('cell_id')
                if 'cell_id' not in row or not row.get('cell_id'):
                    row['cell_id'] = row.get('cgi')
            all_data.extend(data_4g)
        
        if cgi_5g:
            data_5g = self.cell_timeseries_bulk(cgi_5g, "5G", start, end, granularity)
            for row in data_5g:
                row['network_type'] = '5G'
                if 'cgi' not in row or not row.get('cgi'):
                    row['cgi'] = row.get('cell_id')
                if 'cell_id' not in row or not row.get('cell_id'):
                    row['cell_id'] = row.get('cgi')
            all_data.extend(data_5g)
        
        # 按时间和小区ID排序
        all_data.sort(key=lambda x: (x.get('start_time', ''), x.get('cell_id', '')))
        
        return all_data, auto_detected

    def connectivity_series(
        self, network_types: Sequence[str], start: datetime, end: datetime, granularity: str = "15m"
    ) -> List[Dict[str, Any]]:
        """查询接通率时间序列（使用加权平均）"""
        data: List[Dict[str, Any]] = []
        if "4G" in network_types:
            table_4g = self.get_table_name("4G", granularity)
            # 4G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
            sql = f"""
                SELECT
                    start_time,
                    '4G' AS network_type,
                    SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0) *
                    SUM("ERAB_NbrSuccEstab") * 100.0 / NULLIF(SUM("ERAB_NbrAttEstab"), 0) / 100.0 AS connect_rate
                FROM {table_4g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql, (start, end)))

        if "5G" in network_types:
            table_5g = self.get_table_name("5G", granularity)
            # 5G无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
            sql = f"""
                SELECT
                    start_time,
                    '5G' AS network_type,
                    (SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0)) *
                    (SUM("NGSIG_ConnEstabSucc") * 100.0 / NULLIF(SUM("NGSIG_ConnEstabAtt"), 0)) *
                    (SUM("Flow_NbrSuccEstab") * 100.0 / NULLIF(SUM("Flow_NbrAttEstab"), 0)) / 100.0 / 100.0 AS connect_rate
                FROM {table_5g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql, (start, end)))
        return data

    def rrc_series(
        self, network_types: Sequence[str], start: datetime, end: datetime, granularity: str = "15m"
    ) -> List[Dict[str, Any]]:
        data: List[Dict[str, Any]] = []
        if "4G" in network_types:
            table_4g = self.get_table_name("4G", granularity)
            sql = f"""
                SELECT
                    start_time,
                    '4G' AS network_type,
                    SUM("RRC_ConnMax") AS rrc_connmax
                FROM {table_4g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql, (start, end)))

        if "5G" in network_types:
            table_5g = self.get_table_name("5G", granularity)
            sql = f"""
                SELECT
                    start_time,
                    '5G' AS network_type,
                    SUM("RRC_ConnMax") AS rrc_connmax
                FROM {table_5g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time
                ORDER BY start_time
            """
            data.extend(self.pg.fetch_all(sql, (start, end)))
        return data

    def top_utilization(self, network: str, limit: int = 50, granularity: str = "15m") -> List[Dict[str, Any]]:
        """获取最新时段的利用率Top小区（按最大PRB降序，利用率一样时按流量降序）"""
        if network == "4G":
            table_4g = self.get_table_name("4G", granularity)
            latest = self.pg.fetch_one(f"SELECT MAX(start_time) as ts FROM {table_4g}") or {}
            ts = latest.get("ts")
            if not ts:
                return []
            sql = f"""
                SELECT 
                    cell_id,
                    cellname,
                    cgi,
                    '4G' AS network_type,
                    (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                    ul_prb_utilization AS ul_prb_util,
                    dl_prb_utilization AS dl_prb_util,
                    GREATEST(COALESCE(ul_prb_utilization,0), COALESCE(dl_prb_utilization,0)) AS max_prb_util,
                    wireless_connect_rate AS connect_rate,
                    "RRC_ConnMax" AS max_rrc_users,
                    interference
                FROM {table_4g}
                WHERE start_time = %s
                ORDER BY max_prb_util DESC, total_traffic DESC
                LIMIT %s
            """
            return self.pg.fetch_all(sql, (ts, limit)) or []
        else:
            table_5g = self.get_table_name("5G", granularity)
            latest = self.pg.fetch_one(f"SELECT MAX(start_time) as ts FROM {table_5g}") or {}
            ts = latest.get("ts")
            if not ts:
                return []
            sql = f"""
                SELECT 
                    "Ncgi" AS cell_id,
                    userlabel AS cellname,
                    "Ncgi" AS cgi,
                    '5G' AS network_type,
                    (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
                    "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) AS ul_prb_util,
                    "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) AS dl_prb_util,
                    GREATEST(
                        COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0),0),
                        COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0),0)
                    ) AS max_prb_util,
                    ("RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0)) *
                    ("NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0)) *
                    ("Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0)) / 100.0 / 100.0 AS connect_rate,
                    "RRC_ConnMax" AS max_rrc_users,
                    interference
                FROM {table_5g}
                WHERE start_time = %s
                ORDER BY max_prb_util DESC, total_traffic DESC
                LIMIT %s
            """
            return self.pg.fetch_all(sql, (ts, limit)) or []

    def latest_full_metrics(self) -> List[Dict[str, Any]]:
        """导出最新时刻全量4G/5G小区指标"""
        latest_4g = self.pg.fetch_one("SELECT MAX(start_time) as ts FROM cell_4g_metrics") or {}
        latest_5g = self.pg.fetch_one("SELECT MAX(start_time) as ts FROM cell_5g_metrics") or {}
        ts_4g, ts_5g = latest_4g.get("ts"), latest_5g.get("ts")
        rows: List[Dict[str, Any]] = []
        if ts_4g:
            sql = """
                SELECT 
                    '4G' AS network,
                    cellname,
                    cell_id, 
                    cgi, 
                    start_time,
                    (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic_gb,
                    ul_prb_utilization, 
                    dl_prb_utilization,
                    wireless_connect_rate, 
                    "RRC_ConnMax" AS rrc_users,
                    interference
                FROM cell_4g_metrics
                WHERE start_time = %s
            """
            rows.extend(self.pg.fetch_all(sql, (ts_4g,)) or [])
        if ts_5g:
            sql = """
                SELECT
                    '5G' AS network,
                    userlabel AS cellname,
                    "Ncgi" AS cell_id, 
                    "Ncgi" AS cgi, 
                    start_time,
                    (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic_gb,
                    "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) AS ul_prb_utilization,
                    "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) AS dl_prb_utilization,
                    ("RRC_SuccConnEstab" * 100.0 / NULLIF("RRC_AttConnEstab", 0)) *
                    ("NGSIG_ConnEstabSucc" * 100.0 / NULLIF("NGSIG_ConnEstabAtt", 0)) *
                    ("Flow_NbrSuccEstab" * 100.0 / NULLIF("Flow_NbrAttEstab", 0)) / 100.0 / 100.0 AS wireless_connect_rate,
                    "RRC_ConnMax" AS rrc_users,
                    interference
                FROM cell_5g_metrics
                WHERE start_time = %s
            """
            rows.extend(self.pg.fetch_all(sql, (ts_5g,)) or [])
        return rows

    def classify_region(self, cellname: str | None, network_type: str, cgi: str | None = None) -> str:
        """根据小区名和CGI判断所属区域
        
        优先级：
        1. 使用工参表 CGI 映射（如果工参服务可用）
        2. 使用 area_compy 字段分类
        3. 使用小区名分类
        4. 默认江城区
        
        Args:
            cellname: 小区名
            network_type: "4G" 或 "5G"
            cgi: 小区 CGI（可选）
            
        Returns:
            区域名称：江城区、阳东县、南区、阳西县、阳春市
        """
        # 如果工参服务可用，优先使用工参表分类
        if self.engineering_params_service:
            return self.engineering_params_service.classify_region_with_fallback(
                cgi=cgi,
                cellname=cellname,
                network_type=network_type
            )
        
        # 回退到原有的小区名分类逻辑
        if not cellname:
            return "江城区"
        
        cellname_str = str(cellname).strip()
        
        if network_type == "5G":
            # 5G小区：中文匹配
            if "阳江阳西" in cellname_str:
                return "阳西县"
            elif "阳江阳春" in cellname_str:
                return "阳春市"
            elif "阳江阳东" in cellname_str:
                return "阳东县"
            elif "阳江南区" in cellname_str:
                return "南区"
            elif "阳江江城" in cellname_str:
                return "江城区"
            else:
                # 5G小区：英文匹配
                cellname_lower = cellname_str.lower()
                if "yangjiangyangxi" in cellname_lower:
                    return "阳西县"
                elif "yangjiangyangchun" in cellname_lower:
                    return "阳春市"
                elif "yangjiangyangdong" in cellname_lower:
                    return "阳东县"
                elif "yangjiangnanqu" in cellname_lower:
                    return "南区"
                elif "yangjiangjiangcheng" in cellname_lower:
                    return "江城区"
                else:
                    return "江城区"  # 其他归类至江城区
        else:
            # 4G小区：判断是英文还是中文
            # 检查是否包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in cellname_str)
            
            if has_chinese:
                # 中文小区名
                if "阳江阳西" in cellname_str:
                    return "阳西县"
                elif "阳江阳春" in cellname_str:
                    return "阳春市"
                elif "阳江阳东" in cellname_str:
                    return "阳东县"
                elif "阳江南区" in cellname_str:
                    return "南区"
                elif "阳江江城" in cellname_str:
                    return "江城区"
                else:
                    return "江城区"  # 其他归类至江城区
            else:
                # 英文小区名
                cellname_lower = cellname_str.lower()
                if "yangjiangyangxi" in cellname_lower:
                    return "阳西县"
                elif "yangjiangyangchun" in cellname_lower:
                    return "阳春市"
                elif "yangjiangyangdong" in cellname_lower:
                    return "阳东县"
                elif "yangjiangnanqu" in cellname_lower:
                    return "南区"
                elif "yangjiangjiangcheng" in cellname_lower:
                    return "江城区"
                else:
                    return "江城区"  # 其他归类至江城区

    def daily_traffic_and_voice(self, target_date: datetime | None = None) -> Dict[str, Any]:
        """查询指定日期的4G/5G总流量和话务量
        
        Args:
            target_date: 目标日期，如果为None则使用前一日
            
        Returns:
            包含4G和5G流量、话务量的字典
        """
        if target_date is None:
            # 默认使用前一日
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        else:
            # 确保是日期（去掉时分秒）
            target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 计算日期范围（当天00:00:00到23:59:59）
        start_date = target_date
        end_date = target_date + timedelta(days=1) - timedelta(seconds=1)
        
        result = {
            "date": target_date.strftime("%Y-%m-%d"),
            "4G": {"traffic_gb": 0, "traffic_tb": 0, "traffic_unit": "GB", "voice_erl": 0, "voice_unit": "Erl", "ul_prb_util": 0, "dl_prb_util": 0, "connect_rate": 0},
            "5G": {"traffic_gb": 0, "traffic_tb": 0, "traffic_unit": "GB", "voice_erl": 0, "voice_unit": "Erl", "ul_prb_util": 0, "dl_prb_util": 0, "connect_rate": 0},
        }
        
        # 查询4G数据（话务量不除以10000，保持Erl单位）
        sql_4g = """
            SELECT
                ROUND(CAST(SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS numeric), 2) AS "上下行总业务量GB",
                ROUND(CAST(SUM(COALESCE("ERAB_NbrMeanEstab_1", 0)) / 4.0 AS numeric), 2) AS "VoLTE话务量Erl",
                ROUND(CAST(SUM(COALESCE("RRU_PuschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PuschPrbTot", 0)), 0) AS numeric), 2) AS "上行PRB利用率%%",
                ROUND(CAST(SUM(COALESCE("RRU_PdschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PdschPrbTot", 0)), 0) AS numeric), 2) AS "下行PRB利用率%%",
                ROUND(CAST((SUM(COALESCE("RRC_SuccConnEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRC_AttConnEstab", 0)), 0)) * (SUM(COALESCE("ERAB_NbrSuccEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("ERAB_NbrAttEstab", 0)), 0)) / 100.0 AS numeric), 2) AS "无线接通率%%"
            FROM cell_4g_metrics_day
            WHERE start_time >= %s AND start_time < %s
        """
        row_4g = self.pg.fetch_one(sql_4g, (start_date, end_date + timedelta(seconds=1)))
        if row_4g:
            traffic_gb_4g = float(row_4g.get("上下行总业务量GB", 0) or 0)
            voice_erl_4g = float(row_4g.get("VoLTE话务量Erl", 0) or 0)
            ul_prb_util_4g = float(row_4g.get("上行PRB利用率%", 0) or 0)
            dl_prb_util_4g = float(row_4g.get("下行PRB利用率%", 0) or 0)
            connect_rate_4g = float(row_4g.get("无线接通率%", 0) or 0)
            
            result["4G"]["traffic_gb"] = traffic_gb_4g
            result["4G"]["ul_prb_util"] = ul_prb_util_4g
            result["4G"]["dl_prb_util"] = dl_prb_util_4g
            result["4G"]["connect_rate"] = connect_rate_4g
            
            # 话务量单位处理：超过10000使用万Erl
            if voice_erl_4g >= 10000:
                result["4G"]["voice_erl"] = round(voice_erl_4g / 10000, 2)
                result["4G"]["voice_unit"] = "万Erl"
            else:
                result["4G"]["voice_erl"] = voice_erl_4g
                result["4G"]["voice_unit"] = "Erl"
            
            # 流量单位处理：超过1024GB使用TB
            if traffic_gb_4g >= 1024:
                result["4G"]["traffic_tb"] = round(traffic_gb_4g / 1024, 2)
                result["4G"]["traffic_unit"] = "TB"
            else:
                result["4G"]["traffic_tb"] = traffic_gb_4g
                result["4G"]["traffic_unit"] = "GB"
        
        # 查询5G数据（话务量不除以10000，保持Erl单位）
        sql_5g = """
            SELECT
                ROUND(CAST(SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS numeric), 2) AS "RLC层总流量GB",
                ROUND(CAST(SUM(COALESCE("Flow_NbrMeanEstab_5QI1", 0)) / 4.0 AS numeric), 2) AS "Vonr话务量Erl",
                ROUND(CAST(SUM(COALESCE("RRU_PuschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PuschPrbTot", 0)), 0) AS numeric), 2) AS "上行PRB利用率%%",
                ROUND(CAST(SUM(COALESCE("RRU_PdschPrbAssn", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRU_PdschPrbTot", 0)), 0) AS numeric), 2) AS "下行PRB利用率%%",
                ROUND(CAST((SUM(COALESCE("RRC_SuccConnEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("RRC_AttConnEstab", 0)), 0)) * (SUM(COALESCE("NGSIG_ConnEstabSucc", 0)) * 100.0 / NULLIF(SUM(COALESCE("NGSIG_ConnEstabAtt", 0)), 0)) * (SUM(COALESCE("Flow_NbrSuccEstab", 0)) * 100.0 / NULLIF(SUM(COALESCE("Flow_NbrAttEstab", 0)), 0)) / 100.0 / 100.0 AS numeric), 2) AS "无线接通率%%"
            FROM cell_5g_metrics_day
            WHERE start_time >= %s AND start_time < %s
        """
        row_5g = self.pg.fetch_one(sql_5g, (start_date, end_date + timedelta(seconds=1)))
        if row_5g:
            traffic_gb_5g = float(row_5g.get("RLC层总流量GB", 0) or 0)
            voice_erl_5g = float(row_5g.get("Vonr话务量Erl", 0) or 0)
            ul_prb_util_5g = float(row_5g.get("上行PRB利用率%", 0) or 0)
            dl_prb_util_5g = float(row_5g.get("下行PRB利用率%", 0) or 0)
            connect_rate_5g = float(row_5g.get("无线接通率%", 0) or 0)
            
            result["5G"]["traffic_gb"] = traffic_gb_5g
            result["5G"]["ul_prb_util"] = ul_prb_util_5g
            result["5G"]["dl_prb_util"] = dl_prb_util_5g
            result["5G"]["connect_rate"] = connect_rate_5g
            
            # 话务量单位处理：超过10000使用万Erl
            if voice_erl_5g >= 10000:
                result["5G"]["voice_erl"] = round(voice_erl_5g / 10000, 2)
                result["5G"]["voice_unit"] = "万Erl"
            else:
                result["5G"]["voice_erl"] = voice_erl_5g
                result["5G"]["voice_unit"] = "Erl"
            
            # 流量单位处理：超过1024GB使用TB
            if traffic_gb_5g >= 1024:
                result["5G"]["traffic_tb"] = round(traffic_gb_5g / 1024, 2)
                result["5G"]["traffic_unit"] = "TB"
            else:
                result["5G"]["traffic_tb"] = traffic_gb_5g
                result["5G"]["traffic_unit"] = "GB"
        
        return result

    def daily_traffic_and_voice_by_region(self, target_date: datetime | None = None) -> Dict[str, Any]:
        """查询指定日期的4G/5G按区域统计的流量和话务量
        
        Args:
            target_date: 目标日期，如果为None则使用前一日
            
        Returns:
            包含各区域4G和5G流量、话务量的字典
        """
        if target_date is None:
            # 默认使用前一日
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        else:
            # 确保是日期（去掉时分秒）
            target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 计算日期范围（当天00:00:00到23:59:59）
        start_date = target_date
        end_date = target_date + timedelta(days=1) - timedelta(seconds=1)
        
        # 初始化结果结构
        regions = ["江城区", "阳东县", "南区", "阳西县", "阳春市"]
        result = {
            "date": target_date.strftime("%Y-%m-%d"),
            "4G": {region: {"traffic_gb": 0, "traffic_tb": 0, "traffic_unit": "GB", "voice_erl": 0, "voice_unit": "Erl", "ul_prb_util": 0, "dl_prb_util": 0, "connect_rate": 0} for region in regions},
            "5G": {region: {"traffic_gb": 0, "traffic_tb": 0, "traffic_unit": "GB", "voice_erl": 0, "voice_unit": "Erl", "ul_prb_util": 0, "dl_prb_util": 0, "connect_rate": 0} for region in regions},
        }
        
        # 查询4G数据（按区域分组计算）
        sql_4g = """
            SELECT 
                cellname,
                cgi,
                ROUND(CAST(SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS numeric), 2) AS "上下行总业务量GB",
                ROUND(CAST(SUM(COALESCE("ERAB_NbrMeanEstab_1", 0)) / 4.0 AS numeric), 2) AS "VoLTE话务量Erl",
                SUM(COALESCE("RRU_PuschPrbAssn", 0)) AS "上行已用PRB",
                SUM(COALESCE("RRU_PuschPrbTot", 0)) AS "上行总PRB",
                SUM(COALESCE("RRU_PdschPrbAssn", 0)) AS "下行已用PRB",
                SUM(COALESCE("RRU_PdschPrbTot", 0)) AS "下行总PRB",
                SUM(COALESCE("RRC_SuccConnEstab", 0)) AS "RRC成功数",
                SUM(COALESCE("RRC_AttConnEstab", 0)) AS "RRC尝试数",
                SUM(COALESCE("ERAB_NbrSuccEstab", 0)) AS "ERAB成功数",
                SUM(COALESCE("ERAB_NbrAttEstab", 0)) AS "ERAB尝试数"
            FROM cell_4g_metrics_day
            WHERE start_time >= %s AND start_time < %s
            GROUP BY cellname, cgi
        """
        rows_4g = self.pg.fetch_all(sql_4g, (start_date, end_date + timedelta(seconds=1))) or []
        
        # 初始化区域累计值
        region_4g_data = {region: {
            "traffic_gb": 0, "voice_erl": 0,
            "ul_used_prb": 0, "ul_total_prb": 0,
            "dl_used_prb": 0, "dl_total_prb": 0,
            "rrc_success": 0, "rrc_attempt": 0,
            "erab_success": 0, "erab_attempt": 0
        } for region in regions}
        
        for row_4g in rows_4g:
            cellname = row_4g.get("cellname")
            cgi = row_4g.get("cgi")
            region = self.classify_region(cellname, "4G", cgi)
            
            region_4g_data[region]["traffic_gb"] += float(row_4g.get("上下行总业务量GB", 0) or 0)
            region_4g_data[region]["voice_erl"] += float(row_4g.get("VoLTE话务量Erl", 0) or 0)
            region_4g_data[region]["ul_used_prb"] += float(row_4g.get("上行已用PRB", 0) or 0)
            region_4g_data[region]["ul_total_prb"] += float(row_4g.get("上行总PRB", 0) or 0)
            region_4g_data[region]["dl_used_prb"] += float(row_4g.get("下行已用PRB", 0) or 0)
            region_4g_data[region]["dl_total_prb"] += float(row_4g.get("下行总PRB", 0) or 0)
            region_4g_data[region]["rrc_success"] += float(row_4g.get("RRC成功数", 0) or 0)
            region_4g_data[region]["rrc_attempt"] += float(row_4g.get("RRC尝试数", 0) or 0)
            region_4g_data[region]["erab_success"] += float(row_4g.get("ERAB成功数", 0) or 0)
            region_4g_data[region]["erab_attempt"] += float(row_4g.get("ERAB尝试数", 0) or 0)
        
        # 计算各区域4G指标
        for region in regions:
            data = region_4g_data[region]
            result["4G"][region]["traffic_gb"] = data["traffic_gb"]
            result["4G"][region]["voice_erl"] = data["voice_erl"]
            
            # 计算PRB利用率
            if data["ul_total_prb"] > 0:
                result["4G"][region]["ul_prb_util"] = round((data["ul_used_prb"] / data["ul_total_prb"]) * 100, 2)
            if data["dl_total_prb"] > 0:
                result["4G"][region]["dl_prb_util"] = round((data["dl_used_prb"] / data["dl_total_prb"]) * 100, 2)
            
            # 计算接通率
            rrc_rate = 0
            erab_rate = 0
            if data["rrc_attempt"] > 0:
                rrc_rate = data["rrc_success"] / data["rrc_attempt"]
            if data["erab_attempt"] > 0:
                erab_rate = data["erab_success"] / data["erab_attempt"]
            result["4G"][region]["connect_rate"] = round(rrc_rate * erab_rate * 100, 2)
        
        # 处理4G各区域的单位转换
        for region in regions:
            traffic_gb = result["4G"][region]["traffic_gb"]
            voice_erl = result["4G"][region]["voice_erl"]
            
            # 流量单位处理
            if traffic_gb >= 1024:
                result["4G"][region]["traffic_tb"] = round(traffic_gb / 1024, 2)
                result["4G"][region]["traffic_unit"] = "TB"
            else:
                result["4G"][region]["traffic_tb"] = traffic_gb
                result["4G"][region]["traffic_unit"] = "GB"
            
            # 话务量单位处理：超过10000使用万Erl
            if voice_erl >= 10000:
                result["4G"][region]["voice_erl"] = round(voice_erl / 10000, 2)
                result["4G"][region]["voice_unit"] = "万Erl"
            else:
                result["4G"][region]["voice_unit"] = "Erl"
        
        # 查询5G数据（按区域分组计算）
        sql_5g = """
            SELECT 
                userlabel AS cellname,
                "Ncgi" AS cgi,
                ROUND(CAST(SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS numeric), 2) AS "RLC层总流量GB",
                ROUND(CAST(SUM(COALESCE("Flow_NbrMeanEstab_5QI1", 0)) / 4.0 AS numeric), 2) AS "Vonr话务量Erl",
                SUM(COALESCE("RRU_PuschPrbAssn", 0)) AS "上行已用PRB",
                SUM(COALESCE("RRU_PuschPrbTot", 0)) AS "上行总PRB",
                SUM(COALESCE("RRU_PdschPrbAssn", 0)) AS "下行已用PRB",
                SUM(COALESCE("RRU_PdschPrbTot", 0)) AS "下行总PRB",
                SUM(COALESCE("RRC_SuccConnEstab", 0)) AS "RRC成功数",
                SUM(COALESCE("RRC_AttConnEstab", 0)) AS "RRC尝试数",
                SUM(COALESCE("NGSIG_ConnEstabSucc", 0)) AS "NGSIG成功数",
                SUM(COALESCE("NGSIG_ConnEstabAtt", 0)) AS "NGSIG尝试数",
                SUM(COALESCE("Flow_NbrSuccEstab", 0)) AS "Flow成功数",
                SUM(COALESCE("Flow_NbrAttEstab", 0)) AS "Flow尝试数"
            FROM cell_5g_metrics_day
            WHERE start_time >= %s AND start_time < %s
            GROUP BY userlabel, "Ncgi"
        """
        rows_5g = self.pg.fetch_all(sql_5g, (start_date, end_date + timedelta(seconds=1))) or []
        
        # 初始化区域累计值
        region_5g_data = {region: {
            "traffic_gb": 0, "voice_erl": 0,
            "ul_used_prb": 0, "ul_total_prb": 0,
            "dl_used_prb": 0, "dl_total_prb": 0,
            "rrc_success": 0, "rrc_attempt": 0,
            "ngsig_success": 0, "ngsig_attempt": 0,
            "flow_success": 0, "flow_attempt": 0
        } for region in regions}
        
        for row_5g in rows_5g:
            cellname = row_5g.get("cellname")
            cgi = row_5g.get("cgi")
            region = self.classify_region(cellname, "5G", cgi)
            
            region_5g_data[region]["traffic_gb"] += float(row_5g.get("RLC层总流量GB", 0) or 0)
            region_5g_data[region]["voice_erl"] += float(row_5g.get("Vonr话务量Erl", 0) or 0)
            region_5g_data[region]["ul_used_prb"] += float(row_5g.get("上行已用PRB", 0) or 0)
            region_5g_data[region]["ul_total_prb"] += float(row_5g.get("上行总PRB", 0) or 0)
            region_5g_data[region]["dl_used_prb"] += float(row_5g.get("下行已用PRB", 0) or 0)
            region_5g_data[region]["dl_total_prb"] += float(row_5g.get("下行总PRB", 0) or 0)
            region_5g_data[region]["rrc_success"] += float(row_5g.get("RRC成功数", 0) or 0)
            region_5g_data[region]["rrc_attempt"] += float(row_5g.get("RRC尝试数", 0) or 0)
            region_5g_data[region]["ngsig_success"] += float(row_5g.get("NGSIG成功数", 0) or 0)
            region_5g_data[region]["ngsig_attempt"] += float(row_5g.get("NGSIG尝试数", 0) or 0)
            region_5g_data[region]["flow_success"] += float(row_5g.get("Flow成功数", 0) or 0)
            region_5g_data[region]["flow_attempt"] += float(row_5g.get("Flow尝试数", 0) or 0)
        
        # 计算各区域5G指标
        for region in regions:
            data = region_5g_data[region]
            result["5G"][region]["traffic_gb"] = data["traffic_gb"]
            result["5G"][region]["voice_erl"] = data["voice_erl"]
            
            # 计算PRB利用率
            if data["ul_total_prb"] > 0:
                result["5G"][region]["ul_prb_util"] = round((data["ul_used_prb"] / data["ul_total_prb"]) * 100, 2)
            if data["dl_total_prb"] > 0:
                result["5G"][region]["dl_prb_util"] = round((data["dl_used_prb"] / data["dl_total_prb"]) * 100, 2)
            
            # 计算接通率
            rrc_rate = 0
            ngsig_rate = 0
            flow_rate = 0
            if data["rrc_attempt"] > 0:
                rrc_rate = data["rrc_success"] / data["rrc_attempt"]
            if data["ngsig_attempt"] > 0:
                ngsig_rate = data["ngsig_success"] / data["ngsig_attempt"]
            if data["flow_attempt"] > 0:
                flow_rate = data["flow_success"] / data["flow_attempt"]
            result["5G"][region]["connect_rate"] = round(rrc_rate * ngsig_rate * flow_rate * 100, 2)
        
        # 处理5G各区域的单位转换
        for region in regions:
            traffic_gb = result["5G"][region]["traffic_gb"]
            voice_erl = result["5G"][region]["voice_erl"]
            
            # 流量单位处理
            if traffic_gb >= 1024:
                result["5G"][region]["traffic_tb"] = round(traffic_gb / 1024, 2)
                result["5G"][region]["traffic_unit"] = "TB"
            else:
                result["5G"][region]["traffic_tb"] = traffic_gb
                result["5G"][region]["traffic_unit"] = "GB"
            
            # 话务量单位处理：超过10000使用万Erl
            if voice_erl >= 10000:
                result["5G"][region]["voice_erl"] = round(voice_erl / 10000, 2)
                result["5G"][region]["voice_unit"] = "万Erl"
            else:
                result["5G"][region]["voice_unit"] = "Erl"
        
        return result
    
    def region_traffic_series(
        self,
        network_types: Sequence[str],
        start: datetime,
        end: datetime,
        granularity: str = "15m",
        fast: bool = False,
    ) -> List[Dict[str, Any]]:
        """查询按区域和网络类型分组的流量时间序列数据
        
        Args:
            network_types: 网络类型列表，如 ["4G", "5G"]
            start: 开始时间
            end: 结束时间
            granularity: 粒度，如 "15m", "1h", "1d"
            fast: 为 True 时，在数据库侧按区域聚合，显著减少返回行数，适合大范围看板
            
        Returns:
            按区域和网络类型分组的流量时间序列数据
        """
        data: List[Dict[str, Any]] = []

        # 高性能模式：在 SQL 中用 CASE 表达式直接根据小区名分类区域，并按时间+区域聚合
        # 这样数据库直接返回 (时间, 区域, 流量) 级别的数据，避免在 Python 侧处理几十万行记录。
        if fast:
            if "4G" in network_types:
                table_4g = self.get_table_name("4G", granularity)
                sql_4g = f"""
                    SELECT
                        start_time,
                        CASE
                            -- 中文小区名
                            WHEN cellname LIKE '%%阳江阳西%%' THEN '阳西县'
                            WHEN cellname LIKE '%%阳江阳春%%' THEN '阳春市'
                            WHEN cellname LIKE '%%阳江阳东%%' THEN '阳东县'
                            WHEN cellname LIKE '%%阳江南区%%' THEN '南区'
                            WHEN cellname LIKE '%%阳江江城%%' THEN '江城区'
                            -- 英文小区名（统一转小写）
                            WHEN LOWER(cellname) LIKE '%%yangjiangyangxi%%' THEN '阳西县'
                            WHEN LOWER(cellname) LIKE '%%yangjiangyangchun%%' THEN '阳春市'
                            WHEN LOWER(cellname) LIKE '%%yangjiangyangdong%%' THEN '阳东县'
                            WHEN LOWER(cellname) LIKE '%%yangjiangnanqu%%' THEN '南区'
                            WHEN LOWER(cellname) LIKE '%%yangjiangjiangcheng%%' THEN '江城区'
                            ELSE '江城区'
                        END AS region,
                        SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic
                    FROM {table_4g}
                    WHERE start_time BETWEEN %s AND %s
                    GROUP BY start_time, region
                    ORDER BY start_time, region
                """
                rows_4g = self.pg.fetch_all(sql_4g, (start, end)) or []
                for row in rows_4g:
                    data.append({
                        "start_time": row.get("start_time"),
                        "network_type": "4G",
                        "region": row.get("region", "江城区"),
                        "total_traffic": row.get("total_traffic", 0),
                    })

            if "5G" in network_types:
                table_5g = self.get_table_name("5G", granularity)
                sql_5g = f"""
                    SELECT
                        start_time,
                        CASE
                            -- 中文小区名
                            WHEN userlabel LIKE '%%阳江阳西%%' THEN '阳西县'
                            WHEN userlabel LIKE '%%阳江阳春%%' THEN '阳春市'
                            WHEN userlabel LIKE '%%阳江阳东%%' THEN '阳东县'
                            WHEN userlabel LIKE '%%阳江南区%%' THEN '南区'
                            WHEN userlabel LIKE '%%阳江江城%%' THEN '江城区'
                            -- 英文小区名（统一转小写）
                            WHEN LOWER(userlabel) LIKE '%%yangjiangyangxi%%' THEN '阳西县'
                            WHEN LOWER(userlabel) LIKE '%%yangjiangyangchun%%' THEN '阳春市'
                            WHEN LOWER(userlabel) LIKE '%%yangjiangyangdong%%' THEN '阳东县'
                            WHEN LOWER(userlabel) LIKE '%%yangjiangnanqu%%' THEN '南区'
                            WHEN LOWER(userlabel) LIKE '%%yangjiangjiangcheng%%' THEN '江城区'
                            ELSE '江城区'
                        END AS region,
                        SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic
                    FROM {table_5g}
                    WHERE start_time BETWEEN %s AND %s
                    GROUP BY start_time, region
                    HAVING SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                    ORDER BY start_time, region
                """
                rows_5g = self.pg.fetch_all(sql_5g, (start, end)) or []
                for row in rows_5g:
                    data.append({
                        "start_time": row.get("start_time"),
                        "network_type": "5G",
                        "region": row.get("region", "江城区"),
                        "total_traffic": row.get("total_traffic", 0),
                    })

            return data

        # 兼容模式：保留原有 Python 侧按 cellname+CGI 分类的实现（可能返回大量行，性能较差）
        if "4G" in network_types:
            table_4g = self.get_table_name("4G", granularity)
            sql_4g = f"""
                SELECT
                    start_time,
                    cellname,
                    cgi,
                    SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic
                FROM {table_4g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time, cellname, cgi
                ORDER BY start_time
            """
            rows_4g = self.pg.fetch_all(sql_4g, (start, end)) or []
            for row in rows_4g:
                cellname = row.get("cellname")
                cgi = row.get("cgi")
                region = self.classify_region(cellname, "4G", cgi)
                data.append({
                    "start_time": row.get("start_time"),
                    "network_type": "4G",
                    "region": region,
                    "total_traffic": row.get("total_traffic", 0),
                })

        if "5G" in network_types:
            table_5g = self.get_table_name("5G", granularity)
            sql_5g = f"""
                SELECT
                    start_time,
                    userlabel AS cellname,
                    "Ncgi" AS cgi,
                    SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic
                FROM {table_5g}
                WHERE start_time BETWEEN %s AND %s
                GROUP BY start_time, userlabel, "Ncgi"
                HAVING SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                ORDER BY start_time
            """
            rows_5g = self.pg.fetch_all(sql_5g, (start, end)) or []
            for row in rows_5g:
                cellname = row.get("cellname")
                cgi = row.get("cgi")
                region = self.classify_region(cellname, "5G", cgi)
                data.append({
                    "start_time": row.get("start_time"),
                    "network_type": "5G",
                    "region": region,
                    "total_traffic": row.get("total_traffic", 0),
                })

        return data
