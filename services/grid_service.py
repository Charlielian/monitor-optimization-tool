"""网格监控服务"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GridService:
    """网格监控服务类"""
    
    def __init__(self, mysql_client, pg_client=None):
        """初始化网格服务
        
        Args:
            mysql_client: MySQL客户端实例（用于获取网格映射）
            pg_client: PostgreSQL客户端实例（用于获取指标数据，可选）
        """
        self.mysql = mysql_client
        self.pg = pg_client
        
        # 初始化告警匹配器
        self.alarm_matcher = None
        if mysql_client and pg_client:
            try:
                from services.alarm_grid_matcher import AlarmGridMatcher
                self.alarm_matcher = AlarmGridMatcher(mysql_client, pg_client)
                logger.info("告警网格匹配器初始化成功")
            except Exception as e:
                logger.warning(f"告警网格匹配器初始化失败: {e}")
    
    def get_grid_list(self, search: str = None) -> List[Dict[str, Any]]:
        """获取网格列表（优化版本 - 显示所有网格，包括没有小区的）
        
        Args:
            search: 搜索关键字（网格ID或网格名称）
        
        Returns:
            网格列表，包含网格ID、名称、4G小区数、5G小区数、网格信息
        """
        import time
        method_start = time.time()
        
        try:
            # 构建查询条件
            params = []
            
            if search and search.strip():
                # 有搜索条件时，需要在外层WHERE中过滤
                search_pattern = f"%{search.strip()}%"
                
                # 从 grid_info 开始查询，LEFT JOIN cell_mapping，显示所有网格
                sql = """
                    SELECT 
                        gi.grid_id,
                        gi.grid_name,
                        gi.grid_pp,
                        gi.grid_area,
                        gi.gird_dd,
                        gi.grid_regration,
                        COALESCE(cm_agg.cell_4g_count, 0) as cell_4g_count,
                        COALESCE(cm_agg.cell_5g_count, 0) as cell_5g_count,
                        COALESCE(cm_agg.total_cells, 0) as total_cells
                    FROM grid_info gi
                    LEFT JOIN (
                        SELECT 
                            grid_id,
                            SUM(CASE WHEN zhishi = '4g' THEN 1 ELSE 0 END) as cell_4g_count,
                            SUM(CASE WHEN zhishi = '5g' THEN 1 ELSE 0 END) as cell_5g_count,
                            COUNT(*) as total_cells
                        FROM cell_mapping
                        WHERE grid_id IS NOT NULL
                        GROUP BY grid_id
                    ) cm_agg ON gi.grid_id = cm_agg.grid_id
                    WHERE gi.grid_id LIKE %s OR gi.grid_name LIKE %s
                    ORDER BY gi.grid_id
                """
                params = [search_pattern, search_pattern]
            else:
                # 无搜索条件时，查询所有网格（从 grid_info 开始）
                sql = """
                    SELECT 
                        gi.grid_id,
                        gi.grid_name,
                        gi.grid_pp,
                        gi.grid_area,
                        gi.gird_dd,
                        gi.grid_regration,
                        COALESCE(cm_agg.cell_4g_count, 0) as cell_4g_count,
                        COALESCE(cm_agg.cell_5g_count, 0) as cell_5g_count,
                        COALESCE(cm_agg.total_cells, 0) as total_cells
                    FROM grid_info gi
                    LEFT JOIN (
                        SELECT 
                            grid_id,
                            SUM(CASE WHEN zhishi = '4g' THEN 1 ELSE 0 END) as cell_4g_count,
                            SUM(CASE WHEN zhishi = '5g' THEN 1 ELSE 0 END) as cell_5g_count,
                            COUNT(*) as total_cells
                        FROM cell_mapping
                        WHERE grid_id IS NOT NULL
                        GROUP BY grid_id
                    ) cm_agg ON gi.grid_id = cm_agg.grid_id
                    ORDER BY gi.grid_id
                """
            
            grids = self.mysql.fetch_all(sql, tuple(params))
            
            elapsed = (time.time() - method_start) * 1000
            logger.info(f"查询到 {len(grids)} 个网格，耗时: {elapsed:.2f}ms")
            
            return grids
            
        except Exception as e:
            logger.error(f"获取网格列表失败: {e}", exc_info=True)
            return []
    
    def get_grid_cells(self, grid_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取网格下的小区列表
        
        Args:
            grid_id: 网格ID
        
        Returns:
            包含4G和5G小区列表的字典，以及网格详细信息
        """
        try:
            # 查询小区列表
            sql = """
                SELECT 
                    cgi,
                    celname,
                    zhishi as network_type,
                    grid_id,
                    grid_name,
                    lon,
                    lat
                FROM cell_mapping
                WHERE grid_id = %s
                ORDER BY zhishi, cgi
            """
            
            cells = self.mysql.fetch_all(sql, (grid_id,))
            
            # 按制式分组
            cells_4g = [c for c in cells if c.get('network_type') == '4g']
            cells_5g = [c for c in cells if c.get('network_type') == '5g']
            
            # 查询网格详细信息
            grid_info_sql = """
                SELECT 
                    grid_id,
                    grid_name,
                    grid_pp,
                    grid_area,
                    gird_dd,
                    grid_regration
                FROM grid_info
                WHERE grid_id = %s
            """
            grid_info = self.mysql.fetch_one(grid_info_sql, (grid_id,))
            
            return {
                '4g': cells_4g,
                '5g': cells_5g,
                'total': len(cells),
                'grid_info': grid_info  # 添加网格详细信息
            }
            
        except Exception as e:
            logger.error(f"获取网格小区列表失败: {e}", exc_info=True)
            return {'4g': [], '5g': [], 'total': 0, 'grid_info': None}
    
    def get_grid_metrics(self, grid_id: str, start_time: datetime = None, 
                        end_time: datetime = None, granularity: str = 'auto') -> Dict[str, Any]:
        """获取网格的聚合指标
        
        Args:
            grid_id: 网格ID
            start_time: 开始时间
            end_time: 结束时间
            granularity: 数据粒度 ('auto', '15min', 'hour', 'day')
        
        Returns:
            网格聚合指标
        """
        import time
        method_start = time.time()
        
        try:
            # 默认查询最近1小时
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time - timedelta(hours=1)
            
            # 计算时间跨度（小时）
            time_span_hours = (end_time - start_time).total_seconds() / 3600
            
            # 自动选择粒度
            if granularity == 'auto':
                if time_span_hours <= 6:
                    granularity = '15min'
                elif time_span_hours <= 72:  # 3天
                    granularity = 'hour'
                else:
                    granularity = 'day'
            
            # 计算预期数据点数
            if granularity == '15min':
                expected_points = int(time_span_hours * 4)
                granularity_display = '15分钟'
            elif granularity == 'hour':
                expected_points = int(time_span_hours)
                granularity_display = '小时'
            else:  # day
                expected_points = int(time_span_hours / 24)
                granularity_display = '天'
            
            logger.info(f"查询网格 {grid_id} 指标，时间范围: {start_time} 至 {end_time}，粒度: {granularity}")
            
            # 获取网格下的小区列表
            cells = self.get_grid_cells(grid_id)
            
            if cells['total'] == 0:
                return {
                    'grid_id': grid_id,
                    'grid_name': None,
                    '4g': None,
                    '5g': None,
                    'error': '网格下没有小区',
                    'granularity': granularity,
                    'granularity_display': granularity_display,
                }
            
            grid_name = cells['4g'][0].get('grid_name') if cells['4g'] else \
                       cells['5g'][0].get('grid_name') if cells['5g'] else None
            
            # 查询4G指标
            metrics_4g = None
            if cells['4g']:
                cgis_4g = [c['cgi'] for c in cells['4g']]
                logger.info(f"查询 {len(cgis_4g)} 个4G小区的指标")
                metrics_4g = self._get_network_metrics(cgis_4g, '4G', start_time, end_time, granularity)
            
            # 查询5G指标
            metrics_5g = None
            if cells['5g']:
                cgis_5g = [c['cgi'] for c in cells['5g']]
                logger.info(f"查询 {len(cgis_5g)} 个5G小区的指标")
                metrics_5g = self._get_network_metrics(cgis_5g, '5G', start_time, end_time, granularity)
            
            elapsed = (time.time() - method_start) * 1000
            logger.info(f"查询网格 {grid_id} 指标完成，耗时: {elapsed:.2f}ms")
            
            return {
                'grid_id': grid_id,
                'grid_name': grid_name,
                'cell_4g_count': len(cells['4g']),
                'cell_5g_count': len(cells['5g']),
                '4g': metrics_4g,
                '5g': metrics_5g,
                'start_time': start_time,
                'end_time': end_time,
                'granularity': granularity,
                'granularity_display': granularity_display,
                'expected_data_points': expected_points,
            }
            
        except Exception as e:
            logger.error(f"获取网格指标失败: {e}", exc_info=True)
            return {
                'grid_id': grid_id,
                'error': str(e)
            }
    
    def get_grid_cell_stats(self, grid_id: str, start_time: datetime = None,
                           end_time: datetime = None, prb_threshold_4g: float = 50.0,
                           prb_threshold_5g: float = 50.0) -> Dict[str, Dict[str, int]]:
        """获取网格小区统计信息（无流量小区、高负荷小区）
        
        Args:
            grid_id: 网格ID
            start_time: 开始时间
            end_time: 结束时间
            prb_threshold_4g: 4G PRB利用率阈值
            prb_threshold_5g: 5G PRB利用率阈值
        
        Returns:
            小区统计信息
        """
        try:
            # 默认查询当日累积
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 获取网格下的小区列表
            cells = self.get_grid_cells(grid_id)
            
            stats = {
                '4g': {'no_traffic': 0, 'high_load': 0, 'total': len(cells.get('4g', []))},
                '5g': {'no_traffic': 0, 'high_load': 0, 'total': len(cells.get('5g', []))}
            }
            
            if not self.pg:
                return stats
            
            # 统计4G小区
            if cells.get('4g'):
                cgis_4g = [c['cgi'] for c in cells['4g']]
                
                # 无流量小区：总流量为0
                no_traffic_sql = f"""
                    SELECT COUNT(DISTINCT cgi) as count
                    FROM cell_4g_metrics_hour
                    WHERE start_time >= %s AND start_time < %s
                      AND cgi IN ({','.join(['%s']*len(cgis_4g))})
                    GROUP BY cgi
                    HAVING SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) = 0
                """
                no_traffic_result = self.pg.fetch_all(no_traffic_sql, (start_time, end_time, *cgis_4g))
                stats['4g']['no_traffic'] = len(no_traffic_result) if no_traffic_result else 0
                
                # 高负荷小区：忙时PRB利用率超过阈值
                high_load_sql = f"""
                    WITH busy_hour_prb AS (
                        SELECT 
                            cgi,
                            MAX(GREATEST(
                                COALESCE(ul_prb_utilization, 0),
                                COALESCE(dl_prb_utilization, 0)
                            )) as max_prb_util
                        FROM (
                            SELECT 
                                cgi,
                                start_time,
                                ul_prb_utilization,
                                dl_prb_utilization,
                                (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) as traffic,
                                ROW_NUMBER() OVER (
                                    PARTITION BY cgi 
                                    ORDER BY (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) DESC
                                ) as rn
                            FROM cell_4g_metrics_hour
                            WHERE start_time >= %s AND start_time < %s
                              AND cgi IN ({','.join(['%s']*len(cgis_4g))})
                        ) ranked
                        WHERE rn = 1
                        GROUP BY cgi
                    )
                    SELECT COUNT(*) as count
                    FROM busy_hour_prb
                    WHERE max_prb_util > %s
                """
                high_load_result = self.pg.fetch_one(high_load_sql, (start_time, end_time, *cgis_4g, prb_threshold_4g))
                stats['4g']['high_load'] = high_load_result.get('count', 0) if high_load_result else 0
            
            # 统计5G小区
            if cells.get('5g'):
                cgis_5g = [c['cgi'] for c in cells['5g']]
                
                # 无流量小区：总流量为0
                no_traffic_sql = f"""
                    SELECT COUNT(DISTINCT "Ncgi") as count
                    FROM cell_5g_metrics_hour
                    WHERE start_time >= %s AND start_time < %s
                      AND "Ncgi" IN ({','.join(['%s']*len(cgis_5g))})
                    GROUP BY "Ncgi"
                    HAVING SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) = 0
                """
                no_traffic_result = self.pg.fetch_all(no_traffic_sql, (start_time, end_time, *cgis_5g))
                stats['5g']['no_traffic'] = len(no_traffic_result) if no_traffic_result else 0
                
                # 高负荷小区：忙时PRB利用率超过阈值
                high_load_sql = f"""
                    WITH busy_hour_prb AS (
                        SELECT 
                            "Ncgi",
                            MAX(GREATEST(
                                COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                                COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                            )) as max_prb_util
                        FROM (
                            SELECT 
                                "Ncgi",
                                start_time,
                                "RRU_PuschPrbAssn",
                                "RRU_PuschPrbTot",
                                "RRU_PdschPrbAssn",
                                "RRU_PdschPrbTot",
                                (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) as traffic,
                                ROW_NUMBER() OVER (
                                    PARTITION BY "Ncgi" 
                                    ORDER BY (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) DESC
                                ) as rn
                            FROM cell_5g_metrics_hour
                            WHERE start_time >= %s AND start_time < %s
                              AND "Ncgi" IN ({','.join(['%s']*len(cgis_5g))})
                        ) ranked
                        WHERE rn = 1
                        GROUP BY "Ncgi"
                    )
                    SELECT COUNT(*) as count
                    FROM busy_hour_prb
                    WHERE max_prb_util > %s
                """
                high_load_result = self.pg.fetch_one(high_load_sql, (start_time, end_time, *cgis_5g, prb_threshold_5g))
                stats['5g']['high_load'] = high_load_result.get('count', 0) if high_load_result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"获取网格小区统计失败: {e}", exc_info=True)
            return {
                '4g': {'no_traffic': 0, 'high_load': 0, 'total': 0},
                '5g': {'no_traffic': 0, 'high_load': 0, 'total': 0}
            }
    
    def _get_table_name(self, base_table: str, granularity: str) -> str:
        """根据粒度获取表名
        
        Args:
            base_table: 基础表名 (如 'cell_4g_metrics')
            granularity: 粒度 ('15min', 'hour', 'day')
        
        Returns:
            完整表名
        """
        if granularity == '15min':
            return base_table
        elif granularity == 'hour':
            return f"{base_table}_hour"
        else:  # day
            return f"{base_table}_day"
    
    def _get_network_metrics(self, cgis: List[str], network_type: str,
                            start_time: datetime, end_time: datetime, granularity: str = '15min') -> Dict[str, Any]:
        """获取指定小区列表的聚合指标
        
        Args:
            cgis: 小区CGI列表
            network_type: 网络类型（4G或5G）
            start_time: 开始时间
            end_time: 结束时间
            granularity: 数据粒度 ('15min', 'hour', 'day')
        
        Returns:
            聚合指标
        """
        try:
            if not cgis:
                return None
            
            if network_type == '4G':
                return self._get_4g_metrics(cgis, start_time, end_time, granularity)
            else:
                return self._get_5g_metrics(cgis, start_time, end_time, granularity)
                
        except Exception as e:
            logger.error(f"获取{network_type}指标失败: {e}", exc_info=True)
            return None
    
    def _get_4g_metrics(self, cgis: List[str], start_time: datetime, 
                       end_time: datetime, granularity: str = '15min') -> Dict[str, Any]:
        """获取4G小区聚合指标（使用加权平均）"""
        try:
            # 获取表名
            table_name = self._get_table_name('cell_4g_metrics', granularity)
            
            # 构建CGI列表的SQL
            cgi_placeholders = ','.join(['%s'] * len(cgis))
            
            # 使用加权平均：SUM(已用PRB)/SUM(总PRB)，SUM(成功数)/SUM(尝试数)
            sql = f"""
                SELECT 
                    COUNT(DISTINCT cgi) as cell_count,
                    SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0  AS total_traffic_gb,
                    -- PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                    SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) as avg_ul_prb_util,
                    SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) as avg_dl_prb_util,
                    MAX(GREATEST(COALESCE(ul_prb_utilization, 0), COALESCE(dl_prb_utilization, 0))) as max_prb_util,
                    -- 无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                    SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0) *
                    SUM("ERAB_NbrSuccEstab") * 100.0 / NULLIF(SUM("ERAB_NbrAttEstab"), 0) / 100.0 as avg_connect_rate,
                    SUM("RRC_ConnMax") as total_rrc_users,
                    MAX("RRC_ConnMax") as max_rrc_users
                FROM {table_name}
                WHERE cgi IN ({cgi_placeholders})
                  AND start_time BETWEEN %s AND %s
            """
            
            params = cgis + [start_time, end_time]
            result = self.pg.fetch_one(sql, tuple(params))
            
            if result:
                return {
                    'cell_count': result.get('cell_count', 0),
                    'total_traffic_gb': float(result.get('total_traffic_gb') or 0),
                    'avg_ul_prb_util': float(result.get('avg_ul_prb_util') or 0),
                    'avg_dl_prb_util': float(result.get('avg_dl_prb_util') or 0),
                    'max_prb_util': float(result.get('max_prb_util') or 0),
                    'avg_connect_rate': float(result.get('avg_connect_rate') or 0),
                    'total_rrc_users': int(result.get('total_rrc_users') or 0),
                    'max_rrc_users': int(result.get('max_rrc_users') or 0),
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取4G指标失败: {e}", exc_info=True)
            return None
    
    def _get_5g_metrics(self, cgis: List[str], start_time: datetime,
                       end_time: datetime, granularity: str = '15min') -> Dict[str, Any]:
        """获取5G小区聚合指标（使用加权平均）"""
        try:
            # 获取表名
            table_name = self._get_table_name('cell_5g_metrics', granularity)
            
            # 构建CGI列表的SQL
            cgi_placeholders = ','.join(['%s'] * len(cgis))
            
            # 使用加权平均：SUM(已用PRB)/SUM(总PRB)，SUM(成功数)/SUM(尝试数)
            sql = f"""
                SELECT 
                    COUNT(DISTINCT "Ncgi") as cell_count,
                    SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0  AS total_traffic_gb,
                    -- PRB利用率使用加权平均：SUM(已用PRB)/SUM(总PRB)
                    SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) as avg_ul_prb_util,
                    SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) as avg_dl_prb_util,
                    MAX(GREATEST(
                        COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                        COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                    )) as max_prb_util,
                    -- 无线接通率使用加权平均：SUM(成功数)/SUM(尝试数)
                    (SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0)) *
                    (SUM("NGSIG_ConnEstabSucc") * 100.0 / NULLIF(SUM("NGSIG_ConnEstabAtt"), 0)) *
                    (SUM("Flow_NbrSuccEstab") * 100.0 / NULLIF(SUM("Flow_NbrAttEstab"), 0)) / 100.0 / 100.0 as avg_connect_rate,
                    SUM("RRC_ConnMax") as total_rrc_users,
                    MAX("RRC_ConnMax") as max_rrc_users
                FROM {table_name}
                WHERE "Ncgi" IN ({cgi_placeholders})
                  AND start_time BETWEEN %s AND %s
            """
            
            params = cgis + [start_time, end_time]
            result = self.pg.fetch_one(sql, tuple(params))
            
            if result:
                return {
                    'cell_count': result.get('cell_count', 0),
                    'total_traffic_gb': float(result.get('total_traffic_gb') or 0),
                    'avg_ul_prb_util': float(result.get('avg_ul_prb_util') or 0),
                    'avg_dl_prb_util': float(result.get('avg_dl_prb_util') or 0),
                    'max_prb_util': float(result.get('max_prb_util') or 0),
                    'avg_connect_rate': float(result.get('avg_connect_rate') or 0),
                    'total_rrc_users': int(result.get('total_rrc_users') or 0),
                    'max_rrc_users': int(result.get('max_rrc_users') or 0),
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取5G指标失败: {e}", exc_info=True)
            return None

    def get_grid_daily_traffic(self, grid_id: str) -> Dict[str, Any]:
        """获取网格当天累计流量（从00:00到现在）
        
        Args:
            grid_id: 网格ID
        
        Returns:
            当天累计流量数据
        """
        try:
            # 获取网格下的小区列表
            cells = self.get_grid_cells(grid_id)
            
            if cells['total'] == 0:
                return {'4g': {'traffic_gb': 0, 'cell_count': 0}, '5g': {'traffic_gb': 0, 'cell_count': 0}}
            
            # 当天时间范围
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            result = {
                '4g': {'traffic_gb': 0, 'cell_count': 0},
                '5g': {'traffic_gb': 0, 'cell_count': 0}
            }
            
            if not self.pg:
                return result
            
            # 查询4G当天累计流量（使用小时表）
            if cells['4g']:
                cgis_4g = [c['cgi'] for c in cells['4g']]
                cgi_placeholders = ','.join(['%s'] * len(cgis_4g))
                sql_4g = f"""
                    SELECT 
                        COUNT(DISTINCT cgi) as cell_count,
                        SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0  AS traffic_gb
                    FROM cell_4g_metrics_hour
                    WHERE cgi IN ({cgi_placeholders})
                      AND start_time >= %s AND start_time <= %s
                """
                params = cgis_4g + [start_of_day, now]
                row = self.pg.fetch_one(sql_4g, tuple(params))
                if row:
                    result['4g']['traffic_gb'] = float(row.get('traffic_gb') or 0)
                    result['4g']['cell_count'] = int(row.get('cell_count') or 0)
            
            # 查询5G当天累计流量（使用小时表）
            if cells['5g']:
                cgis_5g = [c['cgi'] for c in cells['5g']]
                cgi_placeholders = ','.join(['%s'] * len(cgis_5g))
                sql_5g = f"""
                    SELECT 
                        COUNT(DISTINCT "Ncgi") as cell_count,
                        SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0  AS traffic_gb
                    FROM cell_5g_metrics_hour
                    WHERE "Ncgi" IN ({cgi_placeholders})
                      AND start_time >= %s AND start_time <= %s
                """
                params = cgis_5g + [start_of_day, now]
                row = self.pg.fetch_one(sql_5g, tuple(params))
                if row:
                    result['5g']['traffic_gb'] = float(row.get('traffic_gb') or 0)
                    result['5g']['cell_count'] = int(row.get('cell_count') or 0)
            
            return result
            
        except Exception as e:
            logger.error(f"获取网格当天累计流量失败: {e}", exc_info=True)
            return {'4g': {'traffic_gb': 0, 'cell_count': 0}, '5g': {'traffic_gb': 0, 'cell_count': 0}}

    def get_grid_latest_hour_metrics(self, grid_id: str) -> Dict[str, Any]:
        """获取网格最新1小时指标（PRB利用率、接通率等）
        
        Args:
            grid_id: 网格ID
        
        Returns:
            最新1小时指标数据
        """
        try:
            # 获取网格下的小区列表
            cells = self.get_grid_cells(grid_id)
            
            if cells['total'] == 0:
                return {'4g': None, '5g': None}
            
            result = {'4g': None, '5g': None}
            
            if not self.pg:
                return result
            
            # 获取4G最新时间点
            if cells['4g']:
                cgis_4g = [c['cgi'] for c in cells['4g']]
                latest_4g = self.pg.fetch_one("SELECT MAX(start_time) as ts FROM cell_4g_metrics_hour")
                ts_4g = latest_4g.get('ts') if latest_4g else None
                
                if ts_4g:
                    cgi_placeholders = ','.join(['%s'] * len(cgis_4g))
                    sql_4g = f"""
                        SELECT 
                            COUNT(DISTINCT cgi) as cell_count,
                            SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0  AS traffic_gb,
                            SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) as avg_ul_prb_util,
                            SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) as avg_dl_prb_util,
                            MAX(GREATEST(COALESCE(ul_prb_utilization, 0), COALESCE(dl_prb_utilization, 0))) as max_prb_util,
                            SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0) *
                            SUM("ERAB_NbrSuccEstab") * 100.0 / NULLIF(SUM("ERAB_NbrAttEstab"), 0) / 100.0 as avg_connect_rate,
                            SUM("RRC_ConnMax") as total_rrc_users,
                            MAX("RRC_ConnMax") as max_rrc_users
                        FROM cell_4g_metrics_hour
                        WHERE cgi IN ({cgi_placeholders})
                          AND start_time = %s
                    """
                    params = cgis_4g + [ts_4g]
                    row = self.pg.fetch_one(sql_4g, tuple(params))
                    if row:
                        result['4g'] = {
                            'ts': ts_4g,
                            'cell_count': int(row.get('cell_count') or 0),
                            'traffic_gb': float(row.get('traffic_gb') or 0),
                            'avg_ul_prb_util': float(row.get('avg_ul_prb_util') or 0),
                            'avg_dl_prb_util': float(row.get('avg_dl_prb_util') or 0),
                            'max_prb_util': float(row.get('max_prb_util') or 0),
                            'avg_connect_rate': float(row.get('avg_connect_rate') or 0),
                            'total_rrc_users': int(row.get('total_rrc_users') or 0),
                            'max_rrc_users': int(row.get('max_rrc_users') or 0),
                        }
            
            # 获取5G最新时间点
            if cells['5g']:
                cgis_5g = [c['cgi'] for c in cells['5g']]
                latest_5g = self.pg.fetch_one("SELECT MAX(start_time) as ts FROM cell_5g_metrics_hour")
                ts_5g = latest_5g.get('ts') if latest_5g else None
                
                if ts_5g:
                    cgi_placeholders = ','.join(['%s'] * len(cgis_5g))
                    sql_5g = f"""
                        SELECT 
                            COUNT(DISTINCT "Ncgi") as cell_count,
                            SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0  AS traffic_gb,
                            SUM("RRU_PuschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PuschPrbTot"), 0) as avg_ul_prb_util,
                            SUM("RRU_PdschPrbAssn") * 100.0 / NULLIF(SUM("RRU_PdschPrbTot"), 0) as avg_dl_prb_util,
                            MAX(GREATEST(
                                COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                                COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                            )) as max_prb_util,
                            (SUM("RRC_SuccConnEstab") * 100.0 / NULLIF(SUM("RRC_AttConnEstab"), 0)) *
                            (SUM("NGSIG_ConnEstabSucc") * 100.0 / NULLIF(SUM("NGSIG_ConnEstabAtt"), 0)) *
                            (SUM("Flow_NbrSuccEstab") * 100.0 / NULLIF(SUM("Flow_NbrAttEstab"), 0)) / 100.0 / 100.0 as avg_connect_rate,
                            SUM("RRC_ConnMax") as total_rrc_users,
                            MAX("RRC_ConnMax") as max_rrc_users
                        FROM cell_5g_metrics_hour
                        WHERE "Ncgi" IN ({cgi_placeholders})
                          AND start_time = %s
                    """
                    params = cgis_5g + [ts_5g]
                    row = self.pg.fetch_one(sql_5g, tuple(params))
                    if row:
                        result['5g'] = {
                            'ts': ts_5g,
                            'cell_count': int(row.get('cell_count') or 0),
                            'traffic_gb': float(row.get('traffic_gb') or 0),
                            'avg_ul_prb_util': float(row.get('avg_ul_prb_util') or 0),
                            'avg_dl_prb_util': float(row.get('avg_dl_prb_util') or 0),
                            'max_prb_util': float(row.get('max_prb_util') or 0),
                            'avg_connect_rate': float(row.get('avg_connect_rate') or 0),
                            'total_rrc_users': int(row.get('total_rrc_users') or 0),
                            'max_rrc_users': int(row.get('max_rrc_users') or 0),
                        }
            
            return result
            
        except Exception as e:
            logger.error(f"获取网格最新1小时指标失败: {e}", exc_info=True)
            return {'4g': None, '5g': None}
    
    def get_dashboard_stats(self, prb_threshold_4g: float = 50.0, 
                           prb_threshold_5g: float = 50.0,
                           use_cache: bool = True,
                           comparison_mode: str = 'daily') -> Dict[str, Any]:
        """获取网格监控仪表盘统计数据（优化版本 - 减少数据库查询）
        
        Args:
            prb_threshold_4g: 4G PRB利用率阈值（默认50%）
            prb_threshold_5g: 5G PRB利用率阈值（默认50%）
            use_cache: 是否使用缓存（默认True，缓存5分钟）
            comparison_mode: 对比模式 ('daily': 天级对比, 'current': 当前对比)
        
        Returns:
            仪表盘统计数据
        """
        import time
        method_start = time.time()
        
        try:
            # 1. 获取网格总数（从MySQL快速查询）
            total_grids_sql = """
                SELECT COUNT(DISTINCT grid_id) as total
                FROM cell_mapping
                WHERE grid_id IS NOT NULL
            """
            total_grids_result = self.mysql.fetch_one(total_grids_sql)
            total_grids = total_grids_result.get('total', 0) if total_grids_result else 0
            
            # 1.1 统计督办标签数量（支持多标签，用逗号分隔）
            # 先获取所有有标签的网格
            supervision_grids_sql = """
                SELECT 
                    grid_id,
                    grid_pp
                FROM grid_info
                WHERE grid_pp IS NOT NULL AND grid_pp != ''
            """
            supervision_grids = self.mysql.fetch_all(supervision_grids_sql)
            
            # 拆分标签并统计
            tag_counts = {}
            for grid in supervision_grids:
                grid_pp = grid.get('grid_pp', '')
                if grid_pp:
                    # 按英文逗号分隔标签
                    tags = [tag.strip() for tag in grid_pp.split(',') if tag.strip()]
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # 转换为列表格式，按数量降序排序
            supervision_tags = [
                {'grid_pp': tag, 'count': count}
                for tag, count in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
            ]
            
            # 计算督办总数（注意：一个网格可能有多个标签，这里统计的是标签总数）
            supervision_count = sum(tag['count'] for tag in supervision_tags)
            
            # 初始化统计
            stats = {
                'total_grids': total_grids,
                'supervision_count': supervision_count,  # 督办标签总数
                'supervision_tags': supervision_tags,  # 督办标签详情（标签名+数量）
                'supervision_grids_count': len(supervision_grids),  # 有督办标签的网格数
                'total_traffic_gb': 0,
                'traffic_degraded_grids': [],  # 流量劣化网格
                'no_traffic_increased_grids': [],  # 无流量小区增加的网格
                'high_load_4g_cells': 0,  # 4G高负荷小区数
                'high_load_5g_cells': 0,  # 5G高负荷小区数
                'high_load_grids': [],  # 高负荷小区按网格分组
                'fault_count': 0,  # 故障数量（待实现）
                'query_time': datetime.now(),
                'comparison_mode': comparison_mode,  # 对比模式
            }
            
            # 如果PostgreSQL不可用，只返回基础统计
            if not self.pg:
                logger.warning("PostgreSQL未连接，仅返回基础统计数据")
                return stats
            
            # 2. 根据对比模式设置时间范围
            now = datetime.now()
            
            if comparison_mode == 'current':
                # 当前对比模式：当天累计 vs 前7天同时段累计
                # 当天累计：今天0点到现在
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = now
                
                # 前7天同时段累计：前7天的每天0点到当前时刻
                # 例如：现在是14:30，则对比前7天每天0点到14:30的累计
                past_7days_ranges = []
                for i in range(1, 8):
                    day_start = today_start - timedelta(days=i)
                    day_end = day_start + (now - today_start)  # 同样的时间段
                    past_7days_ranges.append((day_start, day_end))
                
                # 用于显示的时间范围
                comparison_start = today_start
                comparison_end = today_end
                comparison_label = f"当天累计 vs 前7天同时段日均"
                
            else:
                # 天级对比模式（默认）：昨天 vs 前7天平均
                # 今天的时间范围（0点到现在）
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = now
                
                # 昨天的时间范围（用于对比）
                comparison_start = today_start - timedelta(days=1)
                comparison_end = today_start
                
                # 前7天的时间范围（7天前0点到昨天23:59:59）
                past_7days_end = comparison_start
                past_7days_start = past_7days_end - timedelta(days=7)
                
                comparison_label = f"昨天 vs 前7天日均"
            
            logger.info(f"开始查询网格监控仪表盘统计数据（共 {total_grids} 个网格，对比模式: {comparison_mode}）...")
            logger.info(f"  对比说明: {comparison_label}")
            if comparison_mode == 'current':
                logger.info(f"  当天累计: {today_start} 至 {today_end}")
                logger.info(f"  前7天同时段: {len(past_7days_ranges)} 个时间段")
            else:
                logger.info(f"  昨天: {comparison_start} 至 {comparison_end}")
                logger.info(f"  前7天: {past_7days_start} 至 {past_7days_end}")
            
            # 3. 查询总流量（使用日级数据，聚合查询）
            try:
                # 4G总流量（今天）
                traffic_4g_sql = """
                    SELECT 
                        SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0  AS total_traffic_gb
                    FROM cell_4g_metrics_day
                    WHERE start_time BETWEEN %s AND %s
                """
                traffic_4g_result = self.pg.fetch_one(traffic_4g_sql, (today_start, today_end))
                if traffic_4g_result:
                    stats['total_traffic_gb'] += float(traffic_4g_result.get('total_traffic_gb') or 0)
                
                # 5G总流量（今天）
                traffic_5g_sql = """
                    SELECT 
                        SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0  AS total_traffic_gb
                    FROM cell_5g_metrics_day
                    WHERE start_time BETWEEN %s AND %s
                """
                traffic_5g_result = self.pg.fetch_one(traffic_5g_sql, (today_start, today_end))
                if traffic_5g_result:
                    stats['total_traffic_gb'] += float(traffic_5g_result.get('total_traffic_gb') or 0)
                
                logger.info(f"总流量查询完成: {stats['total_traffic_gb']:.2f} GB")
            except Exception as e:
                logger.warning(f"查询总流量失败: {e}")
            
            # 4. 查询高负荷小区数（使用小时数据，以忙时利用率为准）
            # 忙时利用率 = 小区当天流量最大的小时的最大利用率
            try:
                # 先获取网格到小区的映射
                grid_cells_mapping_sql = """
                    SELECT grid_id, grid_name, cgi, zhishi
                    FROM cell_mapping
                    WHERE grid_id IS NOT NULL
                """
                grid_cells_mapping = self.mysql.fetch_all(grid_cells_mapping_sql)
                
                # 获取网格名称映射（从 grid_info 表获取更准确的名称）
                grid_name_map = {}
                grid_pp_map_high_load = {}
                try:
                    grids = self.get_grid_list()
                    grid_name_map = {g['grid_id']: g.get('grid_name') for g in grids}
                    grid_pp_map_high_load = {g['grid_id']: g.get('grid_pp', '') for g in grids}
                except Exception as e:
                    logger.warning(f"获取网格名称映射失败: {e}")
                
                # 构建 cgi -> grid_id 的映射
                cgi_to_grid = {}
                grid_info = {}
                for row in grid_cells_mapping:
                    cgi = row.get('cgi')
                    grid_id = row.get('grid_id')
                    if cgi and grid_id:
                        cgi_to_grid[cgi] = grid_id
                        if grid_id not in grid_info:
                            # 优先使用 grid_info 表的名称，其次使用 cell_mapping 的名称
                            grid_name = grid_name_map.get(grid_id) or row.get('grid_name') or ''
                            grid_info[grid_id] = {
                                'grid_name': grid_name,
                                'grid_pp': grid_pp_map_high_load.get(grid_id, ''),
                                'total_cells': 0,
                                'high_load_4g': 0,
                                'high_load_5g': 0
                            }
                        grid_info[grid_id]['total_cells'] += 1
                
                # 4G高负荷小区（忙时利用率）- 获取具体小区列表
                high_load_4g_sql = """
                    WITH busy_hour_prb AS (
                        SELECT 
                            cgi,
                            MAX(GREATEST(
                                COALESCE(ul_prb_utilization, 0), 
                                COALESCE(dl_prb_utilization, 0)
                            )) as max_prb_util
                        FROM (
                            SELECT 
                                cgi,
                                start_time,
                                ul_prb_utilization,
                                dl_prb_utilization,
                                (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) as traffic,
                                ROW_NUMBER() OVER (
                                    PARTITION BY cgi 
                                    ORDER BY (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) DESC
                                ) as rn
                            FROM cell_4g_metrics_hour
                            WHERE start_time >= %s
                              AND start_time < %s
                        ) ranked
                        WHERE rn = 1
                        GROUP BY cgi
                    )
                    SELECT cgi, max_prb_util
                    FROM busy_hour_prb
                    WHERE max_prb_util > %s
                """
                high_load_4g_cells = self.pg.fetch_all(
                    high_load_4g_sql, 
                    (today_start, today_end, prb_threshold_4g)
                )
                stats['high_load_4g_cells'] = len(high_load_4g_cells) if high_load_4g_cells else 0
                
                # 统计每个网格的4G高负荷小区
                for cell in (high_load_4g_cells or []):
                    cgi = cell.get('cgi')
                    if cgi and cgi in cgi_to_grid:
                        grid_id = cgi_to_grid[cgi]
                        if grid_id in grid_info:
                            grid_info[grid_id]['high_load_4g'] += 1
                
                # 5G高负荷小区（忙时利用率）- 获取具体小区列表
                high_load_5g_sql = """
                    WITH busy_hour_prb AS (
                        SELECT 
                            "Ncgi",
                            MAX(GREATEST(
                                COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                                COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                            )) as max_prb_util
                        FROM (
                            SELECT 
                                "Ncgi",
                                start_time,
                                "RRU_PuschPrbAssn",
                                "RRU_PuschPrbTot",
                                "RRU_PdschPrbAssn",
                                "RRU_PdschPrbTot",
                                (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) as traffic,
                                ROW_NUMBER() OVER (
                                    PARTITION BY "Ncgi" 
                                    ORDER BY (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) DESC
                                ) as rn
                            FROM cell_5g_metrics_hour
                            WHERE start_time >= %s
                              AND start_time < %s
                        ) ranked
                        WHERE rn = 1
                        GROUP BY "Ncgi"
                    )
                    SELECT "Ncgi" as cgi, max_prb_util
                    FROM busy_hour_prb
                    WHERE max_prb_util > %s
                """
                high_load_5g_cells = self.pg.fetch_all(
                    high_load_5g_sql, 
                    (today_start, today_end, prb_threshold_5g)
                )
                stats['high_load_5g_cells'] = len(high_load_5g_cells) if high_load_5g_cells else 0
                
                # 统计每个网格的5G高负荷小区
                for cell in (high_load_5g_cells or []):
                    cgi = cell.get('cgi')
                    if cgi and cgi in cgi_to_grid:
                        grid_id = cgi_to_grid[cgi]
                        if grid_id in grid_info:
                            grid_info[grid_id]['high_load_5g'] += 1
                
                # 汇总有高负荷小区的网格
                high_load_grids = []
                for grid_id, info in grid_info.items():
                    total_high_load = info['high_load_4g'] + info['high_load_5g']
                    if total_high_load > 0:
                        high_load_grids.append({
                            'grid_id': grid_id,
                            'grid_name': info['grid_name'],
                            'grid_pp': info.get('grid_pp', ''),
                            'high_load_4g': info['high_load_4g'],
                            'high_load_5g': info['high_load_5g'],
                            'total_high_load': total_high_load,
                            'total_cells': info['total_cells']
                        })
                
                # 按高负荷小区总数降序排序
                high_load_grids.sort(key=lambda x: x['total_high_load'], reverse=True)
                stats['high_load_grids'] = high_load_grids
                
                logger.info(f"高负荷小区查询完成（忙时利用率）: 4G={stats['high_load_4g_cells']}, 5G={stats['high_load_5g_cells']}, 涉及网格={len(high_load_grids)}")
            except Exception as e:
                logger.warning(f"查询高负荷小区失败: {e}")
            
            # 5. 查询流量劣化网格（支持天级和当前对比）
            try:
                logger.info("开始查询流量劣化网格（批量聚合）...")
                
                # 先从MySQL获取网格到小区的映射
                grid_cells_sql = """
                    SELECT grid_id, cgi, zhishi
                    FROM cell_mapping
                    WHERE grid_id IS NOT NULL
                """
                grid_cells_data = self.mysql.fetch_all(grid_cells_sql)
                
                # 构建网格到小区的映射
                grid_to_cells = {}
                for row in grid_cells_data:
                    grid_id = row['grid_id']
                    cgi = row['cgi']
                    zhishi = row['zhishi']
                    if grid_id not in grid_to_cells:
                        grid_to_cells[grid_id] = {'4g': [], '5g': []}
                    if zhishi == '4g':
                        grid_to_cells[grid_id]['4g'].append(cgi)
                    else:
                        grid_to_cells[grid_id]['5g'].append(cgi)
                
                # 获取所有小区的CGI列表
                all_4g_cgis = []
                all_5g_cgis = []
                for cells in grid_to_cells.values():
                    all_4g_cgis.extend(cells['4g'])
                    all_5g_cgis.extend(cells['5g'])
                
                if comparison_mode == 'current':
                    # 当前对比模式：使用15分钟粒度表
                    # 查询当天累计流量（4G）
                    current_4g_traffic = {}
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        sql = f"""
                            SELECT 
                                cgi,
                                SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                            FROM cell_4g_metrics
                            WHERE cgi IN ({cgi_placeholders})
                              AND start_time >= %s AND start_time < %s
                            GROUP BY cgi
                        """
                        params = all_4g_cgis + [today_start, today_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        current_4g_traffic = {row['cgi']: float(row['traffic_gb'] or 0) for row in results}
                    
                    # 查询当天累计流量（5G）
                    current_5g_traffic = {}
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        sql = f"""
                            SELECT 
                                "Ncgi" as cgi,
                                SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                            FROM cell_5g_metrics
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND start_time >= %s AND start_time < %s
                            GROUP BY "Ncgi"
                        """
                        params = all_5g_cgis + [today_start, today_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        current_5g_traffic = {row['cgi']: float(row['traffic_gb'] or 0) for row in results}
                    
                    # 查询前7天同时段累计流量（4G）
                    past_7days_4g_traffic = {}
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        # 构建7个时间段的查询
                        time_conditions = []
                        params = list(all_4g_cgis)
                        for day_start, day_end in past_7days_ranges:
                            time_conditions.append("(start_time >= %s AND start_time < %s)")
                            params.extend([day_start, day_end])
                        
                        sql = f"""
                            SELECT 
                                cgi,
                                SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic_gb
                            FROM cell_4g_metrics
                            WHERE cgi IN ({cgi_placeholders})
                              AND ({' OR '.join(time_conditions)})
                            GROUP BY cgi
                        """
                        results = self.pg.fetch_all(sql, tuple(params))
                        past_7days_4g_traffic = {row['cgi']: float(row['total_traffic_gb'] or 0) for row in results}
                    
                    # 查询前7天同时段累计流量（5G）
                    past_7days_5g_traffic = {}
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        # 构建7个时间段的查询
                        time_conditions = []
                        params = list(all_5g_cgis)
                        for day_start, day_end in past_7days_ranges:
                            time_conditions.append("(start_time >= %s AND start_time < %s)")
                            params.extend([day_start, day_end])
                        
                        sql = f"""
                            SELECT 
                                "Ncgi" as cgi,
                                SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic_gb
                            FROM cell_5g_metrics
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND ({' OR '.join(time_conditions)})
                            GROUP BY "Ncgi"
                        """
                        results = self.pg.fetch_all(sql, tuple(params))
                        past_7days_5g_traffic = {row['cgi']: float(row['total_traffic_gb'] or 0) for row in results}
                    
                    # 使用当天累计和前7天同时段日均
                    comparison_traffic_4g = current_4g_traffic
                    comparison_traffic_5g = current_5g_traffic
                    comparison_label_current = "当天累计"
                    comparison_label_past = "前7天同时段日均"
                    
                else:
                    # 天级对比模式：使用天级表
                    # 批量查询昨天的流量（4G）
                    comparison_traffic_4g = {}
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        sql = f"""
                            SELECT 
                                cgi,
                                SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                            FROM cell_4g_metrics_day
                            WHERE cgi IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                            GROUP BY cgi
                        """
                        params = all_4g_cgis + [comparison_start, comparison_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        comparison_traffic_4g = {row['cgi']: float(row['traffic_gb'] or 0) for row in results}
                    
                    # 批量查询昨天的流量（5G）
                    comparison_traffic_5g = {}
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        sql = f"""
                            SELECT 
                                "Ncgi" as cgi,
                                SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                            FROM cell_5g_metrics_day
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                            GROUP BY "Ncgi"
                        """
                        params = all_5g_cgis + [comparison_start, comparison_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        comparison_traffic_5g = {row['cgi']: float(row['traffic_gb'] or 0) for row in results}
                    
                    # 批量查询前7天的流量（4G）- 总和而不是平均
                    past_7days_4g_traffic = {}
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        sql = f"""
                            SELECT 
                                cgi,
                                SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic_gb
                            FROM cell_4g_metrics_day
                            WHERE cgi IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                            GROUP BY cgi
                        """
                        params = all_4g_cgis + [past_7days_start, past_7days_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        past_7days_4g_traffic = {row['cgi']: float(row['total_traffic_gb'] or 0) for row in results}
                    
                    # 批量查询前7天的流量（5G）- 总和而不是平均
                    past_7days_5g_traffic = {}
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        sql = f"""
                            SELECT 
                                "Ncgi" as cgi,
                                SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic_gb
                            FROM cell_5g_metrics_day
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                            GROUP BY "Ncgi"
                        """
                        params = all_5g_cgis + [past_7days_start, past_7days_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        past_7days_5g_traffic = {row['cgi']: float(row['total_traffic_gb'] or 0) for row in results}
                    
                    comparison_label_current = "昨天"
                    comparison_label_past = "前7天日均"
                
                # 获取网格名称映射和督办标签映射
                grids = self.get_grid_list()
                grid_name_map = {g['grid_id']: g.get('grid_name') for g in grids}
                grid_pp_map = {g['grid_id']: g.get('grid_pp', '') for g in grids}
                
                # 按网格聚合流量并计算劣化
                for grid_id, cells in grid_to_cells.items():
                    # 计算对比期的总流量（整个网格的所有小区流量汇总）
                    comparison_traffic = 0
                    for cgi in cells['4g']:
                        comparison_traffic += comparison_traffic_4g.get(cgi, 0)
                    for cgi in cells['5g']:
                        comparison_traffic += comparison_traffic_5g.get(cgi, 0)
                    
                    # 计算前7天的日均流量（整个网格的所有小区流量汇总后除以7）
                    past_7days_total = 0
                    for cgi in cells['4g']:
                        past_7days_total += past_7days_4g_traffic.get(cgi, 0)
                    for cgi in cells['5g']:
                        past_7days_total += past_7days_5g_traffic.get(cgi, 0)
                    
                    # 计算日均流量
                    past_7days_avg = past_7days_total / 7.0
                    
                    # 调试日志：输出前几个网格的流量数据
                    if len(stats['traffic_degraded_grids']) < 3:
                        logger.debug(f"网格 {grid_id}: 对比期流量={comparison_traffic:.2f}GB, 前7天总流量={past_7days_total:.2f}GB, 前7天日均={past_7days_avg:.2f}GB, 4G小区数={len(cells['4g'])}, 5G小区数={len(cells['5g'])}")
                    
                    # 检查流量劣化：整个网格的总流量对比前7天的日均流量
                    if past_7days_avg > 0:
                        change_rate = (comparison_traffic - past_7days_avg) / past_7days_avg * 100
                        if change_rate < -30:  # 下降超过30%
                            stats['traffic_degraded_grids'].append({
                                'grid_id': grid_id,
                                'grid_name': grid_name_map.get(grid_id),
                                'grid_pp': grid_pp_map.get(grid_id, ''),
                                'comparison_traffic': comparison_traffic,
                                'past_7days_avg_traffic': past_7days_avg,  # 前7天日均流量
                                'change_rate': change_rate,
                                'comparison_label_current': comparison_label_current,
                                'comparison_label_past': comparison_label_past,
                            })
                
                # 按劣化程度排序
                stats['traffic_degraded_grids'].sort(key=lambda x: x['change_rate'])
                
                logger.info(f"流量劣化网格查询完成: {len(stats['traffic_degraded_grids'])} 个")
            except Exception as e:
                logger.warning(f"查询流量劣化网格失败: {e}", exc_info=True)
            
            # 6. 查询无流量小区增加的网格（支持天级和当前对比）
            try:
                logger.info("开始查询无流量小区增加网格...")
                
                # 使用已有的grid_to_cells映射
                if not grid_to_cells:
                    # 如果上面的查询失败了，重新获取
                    grid_cells_sql = """
                        SELECT grid_id, cgi, zhishi
                        FROM cell_mapping
                        WHERE grid_id IS NOT NULL
                    """
                    grid_cells_data = self.mysql.fetch_all(grid_cells_sql)
                    grid_to_cells = {}
                    for row in grid_cells_data:
                        grid_id = row['grid_id']
                        cgi = row['cgi']
                        zhishi = row['zhishi']
                        if grid_id not in grid_to_cells:
                            grid_to_cells[grid_id] = {'4g': [], '5g': []}
                        if zhishi == '4g':
                            grid_to_cells[grid_id]['4g'].append(cgi)
                        else:
                            grid_to_cells[grid_id]['5g'].append(cgi)
                    
                    # 重新获取所有小区的CGI列表
                    all_4g_cgis = []
                    all_5g_cgis = []
                    for cells in grid_to_cells.values():
                        all_4g_cgis.extend(cells['4g'])
                        all_5g_cgis.extend(cells['5g'])
                
                if comparison_mode == 'current':
                    # 当前对比模式：使用15分钟粒度表
                    # 查询当天累计有流量的小区（4G）
                    current_4g_has_traffic = set()
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        sql = f"""
                            SELECT DISTINCT cgi
                            FROM cell_4g_metrics
                            WHERE cgi IN ({cgi_placeholders})
                              AND start_time >= %s AND start_time < %s
                              AND (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) > 0
                        """
                        params = all_4g_cgis + [today_start, today_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        current_4g_has_traffic = {row['cgi'] for row in results}
                    
                    # 查询当天累计有流量的小区（5G）
                    current_5g_has_traffic = set()
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        sql = f"""
                            SELECT DISTINCT "Ncgi" as cgi
                            FROM cell_5g_metrics
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND start_time >= %s AND start_time < %s
                              AND (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                        """
                        params = all_5g_cgis + [today_start, today_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        current_5g_has_traffic = {row['cgi'] for row in results}
                    
                    # 查询前7天同时段有流量的小区（4G）- 按天分组
                    past_7days_4g_traffic_by_day = {}
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        for idx, (day_start, day_end) in enumerate(past_7days_ranges):
                            sql = f"""
                                SELECT DISTINCT cgi
                                FROM cell_4g_metrics
                                WHERE cgi IN ({cgi_placeholders})
                                  AND start_time >= %s AND start_time < %s
                                  AND (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) > 0
                            """
                            params = all_4g_cgis + [day_start, day_end]
                            results = self.pg.fetch_all(sql, tuple(params))
                            day_date = day_start.date()
                            past_7days_4g_traffic_by_day[day_date] = {row['cgi'] for row in results}
                    
                    # 查询前7天同时段有流量的小区（5G）- 按天分组
                    past_7days_5g_traffic_by_day = {}
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        for idx, (day_start, day_end) in enumerate(past_7days_ranges):
                            sql = f"""
                                SELECT DISTINCT "Ncgi" as cgi
                                FROM cell_5g_metrics
                                WHERE "Ncgi" IN ({cgi_placeholders})
                                  AND start_time >= %s AND start_time < %s
                                  AND (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                            """
                            params = all_5g_cgis + [day_start, day_end]
                            results = self.pg.fetch_all(sql, tuple(params))
                            day_date = day_start.date()
                            past_7days_5g_traffic_by_day[day_date] = {row['cgi'] for row in results}
                    
                    # 使用当天累计和前7天同时段
                    comparison_4g_has_traffic = current_4g_has_traffic
                    comparison_5g_has_traffic = current_5g_has_traffic
                    comparison_label_no_traffic_current = "当天累计无流量"
                    comparison_label_no_traffic_past = "前7天同时段平均无流量"
                    
                else:
                    # 天级对比模式：使用天级表
                    # 批量查询昨天有流量的小区（4G）
                    comparison_4g_has_traffic = set()
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        sql = f"""
                            SELECT DISTINCT cgi
                            FROM cell_4g_metrics_day
                            WHERE cgi IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                              AND (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) > 0
                        """
                        params = all_4g_cgis + [comparison_start, comparison_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        comparison_4g_has_traffic = {row['cgi'] for row in results}
                    
                    # 批量查询昨天有流量的小区（5G）
                    comparison_5g_has_traffic = set()
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        sql = f"""
                            SELECT DISTINCT "Ncgi" as cgi
                            FROM cell_5g_metrics_day
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                              AND (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                        """
                        params = all_5g_cgis + [comparison_start, comparison_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        comparison_5g_has_traffic = {row['cgi'] for row in results}
                    
                    # 批量查询前7天每天有流量的小区（4G）- 按天分组
                    past_7days_4g_traffic_by_day = {}
                    if all_4g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_4g_cgis))
                        sql = f"""
                            SELECT 
                                DATE(start_time) as date,
                                cgi
                            FROM cell_4g_metrics_day
                            WHERE cgi IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                              AND (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) > 0
                            GROUP BY DATE(start_time), cgi
                        """
                        params = all_4g_cgis + [past_7days_start, past_7days_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        for row in results:
                            date = row['date']
                            cgi = row['cgi']
                            if date not in past_7days_4g_traffic_by_day:
                                past_7days_4g_traffic_by_day[date] = set()
                            past_7days_4g_traffic_by_day[date].add(cgi)
                    
                    # 批量查询前7天每天有流量的小区（5G）- 按天分组
                    past_7days_5g_traffic_by_day = {}
                    if all_5g_cgis:
                        cgi_placeholders = ','.join(['%s'] * len(all_5g_cgis))
                        sql = f"""
                            SELECT 
                                DATE(start_time) as date,
                                "Ncgi" as cgi
                            FROM cell_5g_metrics_day
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND start_time BETWEEN %s AND %s
                              AND (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                            GROUP BY DATE(start_time), "Ncgi"
                        """
                        params = all_5g_cgis + [past_7days_start, past_7days_end]
                        results = self.pg.fetch_all(sql, tuple(params))
                        for row in results:
                            date = row['date']
                            cgi = row['cgi']
                            if date not in past_7days_5g_traffic_by_day:
                                past_7days_5g_traffic_by_day[date] = set()
                            past_7days_5g_traffic_by_day[date].add(cgi)
                    
                    comparison_label_no_traffic_current = "昨天无流量"
                    comparison_label_no_traffic_past = "前7天平均无流量"
                
                # 按网格计算无流量小区数
                for grid_id, cells in grid_to_cells.items():
                    total_cells = len(cells['4g']) + len(cells['5g'])
                    
                    # 对比期的无流量小区数
                    comparison_no_traffic_count = 0
                    for cgi in cells['4g']:
                        if cgi not in comparison_4g_has_traffic:
                            comparison_no_traffic_count += 1
                    for cgi in cells['5g']:
                        if cgi not in comparison_5g_has_traffic:
                            comparison_no_traffic_count += 1
                    
                    # 前7天每天的无流量小区数
                    past_7days_no_traffic_counts = []
                    if comparison_mode == 'current':
                        # 当前对比：使用前7天同时段的数据
                        for day_date in sorted(past_7days_4g_traffic_by_day.keys()):
                            day_4g_has_traffic = past_7days_4g_traffic_by_day.get(day_date, set())
                            day_5g_has_traffic = past_7days_5g_traffic_by_day.get(day_date, set())
                            
                            day_no_traffic_count = 0
                            for cgi in cells['4g']:
                                if cgi not in day_4g_has_traffic:
                                    day_no_traffic_count += 1
                            for cgi in cells['5g']:
                                if cgi not in day_5g_has_traffic:
                                    day_no_traffic_count += 1
                            
                            past_7days_no_traffic_counts.append(day_no_traffic_count)
                    else:
                        # 天级对比：使用前7天全天的数据
                        for i in range(7):
                            day_date = (past_7days_start + timedelta(days=i)).date()
                            
                            # 该天有流量的4G小区
                            day_4g_has_traffic = past_7days_4g_traffic_by_day.get(day_date, set())
                            # 该天有流量的5G小区
                            day_5g_has_traffic = past_7days_5g_traffic_by_day.get(day_date, set())
                            
                            # 该天无流量小区数
                            day_no_traffic_count = 0
                            for cgi in cells['4g']:
                                if cgi not in day_4g_has_traffic:
                                    day_no_traffic_count += 1
                            for cgi in cells['5g']:
                                if cgi not in day_5g_has_traffic:
                                    day_no_traffic_count += 1
                            
                            past_7days_no_traffic_counts.append(day_no_traffic_count)
                    
                    # 前7天平均无流量小区数
                    past_7days_avg_no_traffic = sum(past_7days_no_traffic_counts) / len(past_7days_no_traffic_counts) if past_7days_no_traffic_counts else 0
                    
                    # 检查无流量小区增加
                    if past_7days_avg_no_traffic > 0:
                        increase_rate = (comparison_no_traffic_count - past_7days_avg_no_traffic) / past_7days_avg_no_traffic * 100
                        if increase_rate >= 30:  # 增加超过30%
                            stats['no_traffic_increased_grids'].append({
                                'grid_id': grid_id,
                                'grid_name': grid_name_map.get(grid_id),
                                'grid_pp': grid_pp_map.get(grid_id, ''),
                                'comparison_no_traffic_count': comparison_no_traffic_count,
                                'past_7days_avg_no_traffic': past_7days_avg_no_traffic,
                                'increase_rate': increase_rate,
                                'total_cells': total_cells,
                                'comparison_label_current': comparison_label_no_traffic_current,
                                'comparison_label_past': comparison_label_no_traffic_past,
                            })
                    elif past_7days_avg_no_traffic == 0 and comparison_no_traffic_count > 0:
                        # 前7天平均为0，对比期有无流量小区，也算告警
                        stats['no_traffic_increased_grids'].append({
                            'grid_id': grid_id,
                            'grid_name': grid_name_map.get(grid_id),
                            'grid_pp': grid_pp_map.get(grid_id, ''),
                            'comparison_no_traffic_count': comparison_no_traffic_count,
                            'past_7days_avg_no_traffic': past_7days_avg_no_traffic,
                            'increase_rate': 100.0,
                            'total_cells': total_cells,
                            'comparison_label_current': comparison_label_no_traffic_current,
                            'comparison_label_past': comparison_label_no_traffic_past,
                        })
                
                # 按增加率排序
                stats['no_traffic_increased_grids'].sort(key=lambda x: x['increase_rate'], reverse=True)
                
                logger.info(f"无流量小区增加网格查询完成: {len(stats['no_traffic_increased_grids'])} 个")
            except Exception as e:
                logger.warning(f"查询无流量小区增加网格失败: {e}", exc_info=True)
            
            # 计算问题标签与督办标签的交叉统计
            try:
                # 获取所有网格的 grid_pp 信息
                grid_pp_sql = """
                    SELECT grid_id, grid_pp
                    FROM grid_info
                    WHERE grid_pp IS NOT NULL AND grid_pp != ''
                """
                grid_pp_data = self.mysql.fetch_all(grid_pp_sql)
                grid_pp_map = {row['grid_id']: row['grid_pp'] for row in grid_pp_data}
                
                # 定义督办标签分类
                supervision_categories = {
                    '2024年遗留督办网格': ['2024年遗留督办网格'],
                    '2025年督办网格': ['2025年督办网格'],
                    '2026年督办网格': ['2026年督办网格'],
                    '其他': []  # 其他标签或无标签
                }
                
                # 初始化交叉统计
                issue_tag_stats = {
                    '流量劣化': {'2024年遗留督办网格': 0, '2025年督办网格': 0, '2026年督办网格': 0, '其他': 0},
                    '无流量增加': {'2024年遗留督办网格': 0, '2025年督办网格': 0, '2026年督办网格': 0, '其他': 0},
                    '高负荷小区': {'2024年遗留督办网格': 0, '2025年督办网格': 0, '2026年督办网格': 0, '其他': 0},
                    '故障': {'2024年遗留督办网格': 0, '2025年督办网格': 0, '2026年督办网格': 0, '其他': 0},
                }
                
                # 统计流量劣化网格
                for grid in stats.get('traffic_degraded_grids', []):
                    grid_id = grid['grid_id']
                    grid_pp = grid_pp_map.get(grid_id, '')
                    
                    categorized = False
                    for category, tags in supervision_categories.items():
                        if category == '其他':
                            continue
                        for tag in tags:
                            if tag in grid_pp:
                                issue_tag_stats['流量劣化'][category] += 1
                                categorized = True
                                break
                        if categorized:
                            break
                    
                    if not categorized:
                        issue_tag_stats['流量劣化']['其他'] += 1
                
                # 统计无流量小区增加网格
                for grid in stats.get('no_traffic_increased_grids', []):
                    grid_id = grid['grid_id']
                    grid_pp = grid_pp_map.get(grid_id, '')
                    
                    categorized = False
                    for category, tags in supervision_categories.items():
                        if category == '其他':
                            continue
                        for tag in tags:
                            if tag in grid_pp:
                                issue_tag_stats['无流量增加'][category] += 1
                                categorized = True
                                break
                        if categorized:
                            break
                    
                    if not categorized:
                        issue_tag_stats['无流量增加']['其他'] += 1
                
                # 统计高负荷小区网格
                for grid in stats.get('high_load_grids', []):
                    grid_id = grid['grid_id']
                    grid_pp = grid.get('grid_pp', '') or grid_pp_map.get(grid_id, '')
                    
                    categorized = False
                    for category, tags in supervision_categories.items():
                        if category == '其他':
                            continue
                        for tag in tags:
                            if tag in grid_pp:
                                issue_tag_stats['高负荷小区'][category] += 1
                                categorized = True
                                break
                        if categorized:
                            break
                    
                    if not categorized:
                        issue_tag_stats['高负荷小区']['其他'] += 1
                
                # 统计故障网格（需要先获取故障数据）
                # 注意：这里需要在故障统计完成后再填充，所以先初始化为0
                # 实际统计会在后面的故障统计部分完成
                
                stats['issue_tag_stats'] = issue_tag_stats
                logger.info(f"问题标签交叉统计完成")
                
            except Exception as e:
                logger.warning(f"计算问题标签交叉统计失败: {e}", exc_info=True)
                stats['issue_tag_stats'] = {}
            
            # 8. 统计故障数量（基于告警匹配，只统计影响性能的告警）
            try:
                if self.alarm_matcher:
                    logger.info("开始统计网格故障数量（只统计影响性能的告警）...")
                    grid_faults = self.alarm_matcher.get_grid_fault_stats(performance_only=True)
                    stats['fault_count'] = sum(grid_faults.values())  # 总故障小区数
                    
                    # 为故障网格添加详细信息（网格名称和督办标签）
                    fault_grids_detail = []
                    for grid_id, fault_count in grid_faults.items():
                        # 从grids列表中查找网格信息
                        grid_info = next((g for g in grids if g['grid_id'] == grid_id), None)
                        if grid_info:
                            fault_grids_detail.append({
                                'grid_id': grid_id,
                                'grid_name': grid_info.get('grid_name', grid_id),
                                'grid_pp': grid_info.get('grid_pp', ''),
                                'fault_count': fault_count
                            })
                        else:
                            fault_grids_detail.append({
                                'grid_id': grid_id,
                                'grid_name': grid_id,
                                'grid_pp': '',
                                'fault_count': fault_count
                            })
                    
                    # 按故障数量降序排序
                    fault_grids_detail.sort(key=lambda x: x['fault_count'], reverse=True)
                    
                    stats['fault_grids'] = grid_faults  # 保留原有的字典格式（兼容性）
                    stats['fault_grids_detail'] = fault_grids_detail  # 新增详细信息列表
                    logger.info(f"故障统计完成: 总故障小区={stats['fault_count']}, 故障网格数={len(grid_faults)}")
                    
                    # 统计故障网格的标签分布（添加到issue_tag_stats）
                    if 'issue_tag_stats' in stats and fault_grids_detail:
                        # 定义督办标签分类（与上面保持一致）
                        supervision_categories = {
                            '2024年遗留督办网格': ['2024年遗留督办网格'],
                            '2025年督办网格': ['2025年督办网格'],
                            '2026年督办网格': ['2026年督办网格'],
                            '其他': []
                        }
                        
                        for grid in fault_grids_detail:
                            grid_pp = grid.get('grid_pp', '') or ''  # 确保不是None
                            
                            categorized = False
                            for category, tags in supervision_categories.items():
                                if category == '其他':
                                    continue
                                for tag in tags:
                                    if tag and tag in grid_pp:  # 确保tag不是空
                                        stats['issue_tag_stats']['故障'][category] += 1
                                        categorized = True
                                        break
                                if categorized:
                                    break
                            
                            if not categorized:
                                stats['issue_tag_stats']['故障']['其他'] += 1
                        
                        logger.info(f"故障标签统计完成")
                else:
                    logger.warning("告警匹配器未初始化，跳过故障统计")
            except Exception as e:
                logger.warning(f"统计故障数量失败: {e}", exc_info=True)
                stats['fault_count'] = 0
                stats['fault_grids'] = {}
                stats['fault_grids_detail'] = []
            
            elapsed = (time.time() - method_start) * 1000
            logger.info(f"仪表盘统计数据查询完成，耗时: {elapsed:.2f}ms")
            
            return stats
            
        except Exception as e:
            logger.error(f"获取仪表盘统计数据失败: {e}", exc_info=True)
            return {
                'total_grids': 0,
                'supervision_count': 0,
                'total_traffic_gb': 0,
                'traffic_degraded_grids': [],
                'no_traffic_increased_grids': [],
                'high_load_4g_cells': 0,
                'high_load_5g_cells': 0,
                'high_load_grids': [],
                'fault_count': 0,
                'error': str(e),
            }
    
    def _get_grid_traffic(self, cells: Dict[str, List], start_time: datetime, 
                         end_time: datetime, granularity: str = 'day') -> float:
        """获取网格的总流量
        
        Args:
            cells: 网格小区字典
            start_time: 开始时间
            end_time: 结束时间
            granularity: 数据粒度
        
        Returns:
            总流量（GB）
        """
        total_traffic = 0
        
        try:
            # 4G流量
            if cells.get('4g'):
                cgis_4g = [c['cgi'] for c in cells['4g']]
                table_name = self._get_table_name('cell_4g_metrics', granularity)
                cgi_placeholders = ','.join(['%s'] * len(cgis_4g))
                
                sql = f"""
                    SELECT 
                        SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                    FROM {table_name}
                    WHERE cgi IN ({cgi_placeholders})
                      AND start_time BETWEEN %s AND %s
                """
                params = cgis_4g + [start_time, end_time]
                result = self.pg.fetch_one(sql, tuple(params))
                if result:
                    total_traffic += float(result.get('traffic_gb') or 0)
            
            # 5G流量
            if cells.get('5g'):
                cgis_5g = [c['cgi'] for c in cells['5g']]
                table_name = self._get_table_name('cell_5g_metrics', granularity)
                cgi_placeholders = ','.join(['%s'] * len(cgis_5g))
                
                sql = f"""
                    SELECT 
                        SUM(COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                    FROM {table_name}
                    WHERE "Ncgi" IN ({cgi_placeholders})
                      AND start_time BETWEEN %s AND %s
                """
                params = cgis_5g + [start_time, end_time]
                result = self.pg.fetch_one(sql, tuple(params))
                if result:
                    total_traffic += float(result.get('traffic_gb') or 0)
        
        except Exception as e:
            logger.debug(f"获取网格流量失败: {e}")
        
        return total_traffic
    
    def _get_no_traffic_cell_count(self, cells: Dict[str, List], start_time: datetime, 
                                   end_time: datetime) -> int:
        """获取网格内无流量小区数量
        
        Args:
            cells: 网格小区字典
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            无流量小区数量（流量为空或为0的小区）
        """
        no_traffic_count = 0
        
        try:
            # 4G无流量小区
            if cells.get('4g'):
                cgis_4g = [c['cgi'] for c in cells['4g']]
                table_name = self._get_table_name('cell_4g_metrics', 'day')
                cgi_placeholders = ','.join(['%s'] * len(cgis_4g))
                
                # 查询有流量的小区
                sql = f"""
                    SELECT COUNT(DISTINCT cgi) as has_traffic_count
                    FROM {table_name}
                    WHERE cgi IN ({cgi_placeholders})
                      AND start_time BETWEEN %s AND %s
                      AND (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) > 0
                """
                params = cgis_4g + [start_time, end_time]
                result = self.pg.fetch_one(sql, tuple(params))
                has_traffic_count = int(result.get('has_traffic_count', 0)) if result else 0
                
                # 无流量小区 = 总小区数 - 有流量小区数
                no_traffic_count += len(cgis_4g) - has_traffic_count
            
            # 5G无流量小区
            if cells.get('5g'):
                cgis_5g = [c['cgi'] for c in cells['5g']]
                table_name = self._get_table_name('cell_5g_metrics', 'day')
                cgi_placeholders = ','.join(['%s'] * len(cgis_5g))
                
                # 查询有流量的小区
                sql = f"""
                    SELECT COUNT(DISTINCT "Ncgi") as has_traffic_count
                    FROM {table_name}
                    WHERE "Ncgi" IN ({cgi_placeholders})
                      AND start_time BETWEEN %s AND %s
                      AND (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                """
                params = cgis_5g + [start_time, end_time]
                result = self.pg.fetch_one(sql, tuple(params))
                has_traffic_count = int(result.get('has_traffic_count', 0)) if result else 0
                
                # 无流量小区 = 总小区数 - 有流量小区数
                no_traffic_count += len(cgis_5g) - has_traffic_count
        
        except Exception as e:
            logger.debug(f"获取无流量小区数量失败: {e}")
        
        return no_traffic_count
    
    def backfill_grid_names(self) -> Dict[str, Any]:
        """自动回填网格中文名
        
        从已有中文名的小区记录中，回填到同一网格ID下没有中文名的小区
        
        Returns:
            回填结果统计
        """
        import time
        method_start = time.time()
        
        try:
            logger.info("=" * 60)
            logger.info("开始自动回填网格中文名...")
            logger.info("=" * 60)
            
            # 1. 查找每个网格ID的有效中文名（不为空且不等于grid_id）
            sql_find_names = """
                SELECT 
                    grid_id,
                    grid_name
                FROM cell_mapping
                WHERE grid_id IS NOT NULL
                  AND grid_name IS NOT NULL
                  AND grid_name != ''
                  AND grid_name != grid_id
                GROUP BY grid_id, grid_name
                ORDER BY grid_id
            """
            
            grid_names = self.mysql.fetch_all(sql_find_names)
            logger.info(f"找到 {len(grid_names)} 个有效的网格中文名")
            
            if not grid_names:
                return {
                    'success': True,
                    'total_grids': 0,
                    'updated_grids': 0,
                    'updated_cells': 0,
                    'message': '没有找到需要回填的网格'
                }
            
            # 2. 为每个网格ID回填中文名
            total_updated_cells = 0
            updated_grids = []
            
            for item in grid_names:
                grid_id = item['grid_id']
                grid_name = item['grid_name']
                
                # 更新该网格下所有没有中文名或中文名等于grid_id的小区
                sql_update = """
                    UPDATE cell_mapping
                    SET grid_name = %s,
                        updated_at = NOW()
                    WHERE grid_id = %s
                      AND (grid_name IS NULL 
                           OR grid_name = '' 
                           OR grid_name = grid_id)
                """
                
                affected_rows = self.mysql.execute(sql_update, (grid_name, grid_id))
                
                if affected_rows > 0:
                    total_updated_cells += affected_rows
                    updated_grids.append({
                        'grid_id': grid_id,
                        'grid_name': grid_name,
                        'updated_cells': affected_rows
                    })
                    logger.info(f"  ✓ 网格 {grid_id} ({grid_name}): 回填 {affected_rows} 个小区")
            
            elapsed = (time.time() - method_start) * 1000
            
            logger.info("=" * 60)
            logger.info(f"回填完成！共更新 {len(updated_grids)} 个网格，{total_updated_cells} 个小区")
            logger.info(f"耗时: {elapsed:.2f}ms")
            logger.info("=" * 60)
            
            return {
                'success': True,
                'total_grids': len(grid_names),
                'updated_grids': len(updated_grids),
                'updated_cells': total_updated_cells,
                'details': updated_grids[:10],  # 只返回前10个详情
                'elapsed_ms': elapsed
            }
            
        except Exception as e:
            logger.error(f"回填网格中文名失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_grid_name(self, grid_id: str, grid_name: str) -> bool:
        """更新网格的中文名称
        
        Args:
            grid_id: 网格ID
            grid_name: 新的网格中文名称
        
        Returns:
            是否更新成功
        """
        try:
            # 更新该网格下所有小区的grid_name
            sql = """
                UPDATE cell_mapping
                SET grid_name = %s,
                    updated_at = NOW()
                WHERE grid_id = %s
            """
            
            affected_rows = self.mysql.execute(sql, (grid_name, grid_id))
            
            if affected_rows > 0:
                logger.info(f"成功更新网格 {grid_id} 的中文名为 '{grid_name}'，影响 {affected_rows} 条记录")
                return True
            else:
                logger.warning(f"网格 {grid_id} 不存在或没有小区")
                return False
                
        except Exception as e:
            logger.error(f"更新网格名称失败: {e}", exc_info=True)
            return False
    
    def get_traffic_degraded_details(self) -> List[Dict[str, Any]]:
        """获取流量劣化网格的详细数据（用于导出）
        
        Returns:
            流量劣化网格详细数据列表
        """
        try:
            # 获取仪表盘统计数据（包含流量劣化网格）
            stats = self.get_dashboard_stats()
            
            if not stats or not stats.get('traffic_degraded_grids'):
                return []
            
            # 获取网格详细信息
            degraded_grids = stats['traffic_degraded_grids']
            
            # 为每个网格获取小区详细数据
            detailed_data = []
            for grid_data in degraded_grids:
                grid_id = grid_data['grid_id']
                
                # 获取网格下的小区列表
                cells = self.get_grid_cells(grid_id)
                
                # 获取网格信息
                grid_info = cells.get('grid_info', {})
                
                # 添加网格汇总行
                detailed_data.append({
                    'grid_id': grid_id,
                    'grid_name': grid_data.get('grid_name') or grid_info.get('grid_name', ''),
                    'grid_pp': grid_info.get('grid_pp', ''),
                    'grid_area': grid_info.get('grid_area', ''),
                    'gird_dd': grid_info.get('gird_dd', ''),
                    'grid_regration': grid_info.get('grid_regration', ''),
                    'yesterday_traffic': grid_data.get('comparison_traffic', 0),  # 对比期流量
                    'past_7days_avg_traffic': grid_data.get('past_7days_avg_traffic', 0),  # 前7天总流量
                    'change_rate': grid_data.get('change_rate', 0),
                    'cell_4g_count': len(cells.get('4g', [])),
                    'cell_5g_count': len(cells.get('5g', [])),
                    'total_cells': cells.get('total', 0),
                    'is_summary': True,  # 标记为汇总行
                })
                
                # 添加4G小区详细数据
                for cell in cells.get('4g', []):
                    detailed_data.append({
                        'grid_id': grid_id,
                        'grid_name': grid_data.get('grid_name') or grid_info.get('grid_name', ''),
                        'grid_pp': grid_info.get('grid_pp', ''),  # 添加网格标签
                        'cgi': cell.get('cgi'),
                        'celname': cell.get('celname'),
                        'network_type': '4G',
                        'lon': cell.get('lon'),
                        'lat': cell.get('lat'),
                        'is_summary': False,  # 标记为小区行
                    })
                
                # 添加5G小区详细数据
                for cell in cells.get('5g', []):
                    detailed_data.append({
                        'grid_id': grid_id,
                        'grid_name': grid_data.get('grid_name') or grid_info.get('grid_name', ''),
                        'grid_pp': grid_info.get('grid_pp', ''),  # 添加网格标签
                        'cgi': cell.get('cgi'),
                        'celname': cell.get('celname'),
                        'network_type': '5G',
                        'lon': cell.get('lon'),
                        'lat': cell.get('lat'),
                        'is_summary': False,  # 标记为小区行
                    })
            
            return detailed_data
            
        except Exception as e:
            logger.error(f"获取流量劣化详细数据失败: {e}", exc_info=True)
            return []
    
    def get_no_traffic_increased_details(self) -> List[Dict[str, Any]]:
        """获取无流量小区增加网格的详细数据（用于导出）
        
        Returns:
            无流量小区增加网格详细数据列表
        """
        try:
            # 获取仪表盘统计数据（包含无流量小区增加网格）
            stats = self.get_dashboard_stats()
            
            if not stats or not stats.get('no_traffic_increased_grids'):
                return []
            
            # 获取时间范围
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_start
            
            # 获取网格详细信息
            increased_grids = stats['no_traffic_increased_grids']
            
            # 为每个网格获取小区详细数据
            detailed_data = []
            for grid_data in increased_grids:
                grid_id = grid_data['grid_id']
                
                # 获取网格下的小区列表
                cells = self.get_grid_cells(grid_id)
                
                # 获取网格信息
                grid_info = cells.get('grid_info', {})
                
                # 添加网格汇总行
                detailed_data.append({
                    'grid_id': grid_id,
                    'grid_name': grid_data.get('grid_name') or grid_info.get('grid_name', ''),
                    'grid_pp': grid_info.get('grid_pp', ''),
                    'grid_area': grid_info.get('grid_area', ''),
                    'gird_dd': grid_info.get('gird_dd', ''),
                    'grid_regration': grid_info.get('grid_regration', ''),
                    'yesterday_no_traffic_count': grid_data['yesterday_no_traffic_count'],
                    'past_7days_avg_no_traffic': grid_data['past_7days_avg_no_traffic'],
                    'increase_rate': grid_data['increase_rate'],
                    'total_cells': grid_data['total_cells'],
                    'is_summary': True,  # 标记为汇总行
                })
                
                # 查询昨天无流量的小区（4G）
                no_traffic_4g_cgis = set()
                if cells.get('4g'):
                    cgis_4g = [c['cgi'] for c in cells['4g']]
                    cgi_placeholders = ','.join(['%s'] * len(cgis_4g))
                    
                    # 查询昨天有流量的小区
                    sql = f"""
                        SELECT DISTINCT cgi
                        FROM cell_4g_metrics_day
                        WHERE cgi IN ({cgi_placeholders})
                          AND start_time BETWEEN %s AND %s
                          AND (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) > 0
                    """
                    params = cgis_4g + [yesterday_start, yesterday_end]
                    has_traffic_results = self.pg.fetch_all(sql, tuple(params))
                    has_traffic_cgis = {row['cgi'] for row in has_traffic_results}
                    
                    # 无流量小区 = 所有小区 - 有流量小区
                    no_traffic_4g_cgis = set(cgis_4g) - has_traffic_cgis
                
                # 查询昨天无流量的小区（5G）
                no_traffic_5g_cgis = set()
                if cells.get('5g'):
                    cgis_5g = [c['cgi'] for c in cells['5g']]
                    cgi_placeholders = ','.join(['%s'] * len(cgis_5g))
                    
                    # 查询昨天有流量的小区
                    sql = f"""
                        SELECT DISTINCT "Ncgi" as cgi
                        FROM cell_5g_metrics_day
                        WHERE "Ncgi" IN ({cgi_placeholders})
                          AND start_time BETWEEN %s AND %s
                          AND (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) > 0
                    """
                    params = cgis_5g + [yesterday_start, yesterday_end]
                    has_traffic_results = self.pg.fetch_all(sql, tuple(params))
                    has_traffic_cgis = {row['cgi'] for row in has_traffic_results}
                    
                    # 无流量小区 = 所有小区 - 有流量小区
                    no_traffic_5g_cgis = set(cgis_5g) - has_traffic_cgis
                
                # 添加4G小区详细数据（只包含无流量小区）
                for cell in cells.get('4g', []):
                    cgi = cell.get('cgi')
                    has_traffic = cgi not in no_traffic_4g_cgis
                    
                    detailed_data.append({
                        'grid_id': grid_id,
                        'grid_name': grid_data.get('grid_name') or grid_info.get('grid_name', ''),
                        'grid_pp': grid_info.get('grid_pp', ''),  # 添加网格标签
                        'cgi': cgi,
                        'celname': cell.get('celname'),
                        'network_type': '4G',
                        'lon': cell.get('lon'),
                        'lat': cell.get('lat'),
                        'has_traffic': '有流量' if has_traffic else '无流量',
                        'is_summary': False,  # 标记为小区行
                    })
                
                # 添加5G小区详细数据（只包含无流量小区）
                for cell in cells.get('5g', []):
                    cgi = cell.get('cgi')
                    has_traffic = cgi not in no_traffic_5g_cgis
                    
                    detailed_data.append({
                        'grid_id': grid_id,
                        'grid_name': grid_data.get('grid_name') or grid_info.get('grid_name', ''),
                        'grid_pp': grid_info.get('grid_pp', ''),  # 添加网格标签
                        'cgi': cgi,
                        'celname': cell.get('celname'),
                        'network_type': '5G',
                        'lon': cell.get('lon'),
                        'lat': cell.get('lat'),
                        'has_traffic': '有流量' if has_traffic else '无流量',
                        'is_summary': False,  # 标记为小区行
                    })
            
            return detailed_data
            
        except Exception as e:
            logger.error(f"获取无流量小区增加详细数据失败: {e}", exc_info=True)
            return []
    
    def get_high_load_cells_details(self, prb_threshold_4g: float = 50.0, prb_threshold_5g: float = 50.0) -> List[Dict[str, Any]]:
        """
        获取高负荷小区的详细数据（用于导出）
        
        Args:
            prb_threshold_4g: 4G PRB利用率阈值
            prb_threshold_5g: 5G PRB利用率阈值
        
        Returns:
            高负荷小区详细数据列表
        """
        try:
            if not self.pg:
                logger.warning("PostgreSQL未连接，无法获取高负荷小区数据")
                return []
            
            # 获取今天的时间范围
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now
            
            # 获取小区到网格的映射和网格信息
            cgi_to_grid = {}
            grid_info_map = {}
            if self.mysql:
                # 获取小区映射
                mapping_sql = """
                    SELECT cgi, grid_id, grid_name, celname
                    FROM cell_mapping
                    WHERE grid_id IS NOT NULL
                """
                mapping_data = self.mysql.fetch_all(mapping_sql)
                for row in mapping_data:
                    cgi_to_grid[row['cgi']] = {
                        'grid_id': row['grid_id'],
                        'grid_name': row.get('grid_name', ''),
                        'celname': row.get('celname', '')
                    }
                
                # 获取网格信息（包括网格标签）
                grid_info_sql = """
                    SELECT grid_id, grid_name, grid_pp
                    FROM grid_info
                    WHERE grid_id IS NOT NULL
                """
                grid_info_data = self.mysql.fetch_all(grid_info_sql)
                for row in grid_info_data:
                    grid_info_map[row['grid_id']] = {
                        'grid_name': row.get('grid_name', ''),
                        'grid_pp': row.get('grid_pp', '')
                    }
            
            detailed_data = []
            
            # 查询4G高负荷小区（忙时利用率）
            high_load_4g_sql = """
                WITH busy_hour_prb AS (
                    SELECT 
                        cgi,
                        MAX(GREATEST(
                            COALESCE(ul_prb_utilization, 0), 
                            COALESCE(dl_prb_utilization, 0)
                        )) as max_prb_util
                    FROM (
                        SELECT 
                            cgi,
                            start_time,
                            ul_prb_utilization,
                            dl_prb_utilization,
                            (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) as traffic,
                            ROW_NUMBER() OVER (
                                PARTITION BY cgi 
                                ORDER BY (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) DESC
                            ) as rn
                        FROM cell_4g_metrics_hour
                        WHERE start_time >= %s
                          AND start_time < %s
                    ) ranked
                    WHERE rn = 1
                    GROUP BY cgi
                )
                SELECT cgi, max_prb_util
                FROM busy_hour_prb
                WHERE max_prb_util > %s
            """
            high_load_4g_cells = self.pg.fetch_all(
                high_load_4g_sql, 
                (today_start, today_end, prb_threshold_4g)
            )
            
            for cell in (high_load_4g_cells or []):
                cgi = cell.get('cgi')
                if cgi and cgi in cgi_to_grid:
                    cell_info = cgi_to_grid[cgi]
                    grid_id = cell_info['grid_id']
                    grid_info = grid_info_map.get(grid_id, {})
                    
                    detailed_data.append({
                        'grid_id': grid_id,
                        'grid_name': grid_info.get('grid_name', cell_info['grid_name']),
                        'grid_pp': grid_info.get('grid_pp', ''),  # 添加网格标签
                        'cgi': cgi,
                        'celname': cell_info['celname'],
                        'network_type': '4G',
                        'max_prb_util': round(cell.get('max_prb_util', 0), 2)
                    })
            
            # 查询5G高负荷小区（忙时利用率）
            high_load_5g_sql = """
                WITH busy_hour_prb AS (
                    SELECT 
                        "Ncgi",
                        MAX(GREATEST(
                            COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                            COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                        )) as max_prb_util
                    FROM (
                        SELECT 
                            "Ncgi",
                            start_time,
                            "RRU_PuschPrbAssn",
                            "RRU_PuschPrbTot",
                            "RRU_PdschPrbAssn",
                            "RRU_PdschPrbTot",
                            (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) as traffic,
                            ROW_NUMBER() OVER (
                                PARTITION BY "Ncgi" 
                                ORDER BY (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) DESC
                            ) as rn
                        FROM cell_5g_metrics_hour
                        WHERE start_time >= %s
                          AND start_time < %s
                    ) ranked
                    WHERE rn = 1
                    GROUP BY "Ncgi"
                )
                SELECT "Ncgi" as cgi, max_prb_util
                FROM busy_hour_prb
                WHERE max_prb_util > %s
            """
            high_load_5g_cells = self.pg.fetch_all(
                high_load_5g_sql, 
                (today_start, today_end, prb_threshold_5g)
            )
            
            for cell in (high_load_5g_cells or []):
                cgi = cell.get('cgi')
                if cgi and cgi in cgi_to_grid:
                    cell_info = cgi_to_grid[cgi]
                    grid_id = cell_info['grid_id']
                    grid_info = grid_info_map.get(grid_id, {})
                    
                    detailed_data.append({
                        'grid_id': grid_id,
                        'grid_name': grid_info.get('grid_name', cell_info['grid_name']),
                        'grid_pp': grid_info.get('grid_pp', ''),  # 添加网格标签
                        'cgi': cgi,
                        'celname': cell_info['celname'],
                        'network_type': '5G',
                        'max_prb_util': round(cell.get('max_prb_util', 0), 2)
                    })
            
            # 按网格ID排序
            detailed_data.sort(key=lambda x: x.get('grid_id', ''))
            
            logger.info(f"获取高负荷小区明细: 共{len(detailed_data)}个小区")
            return detailed_data
            
        except Exception as e:
            logger.error(f"获取高负荷小区详细数据失败: {e}", exc_info=True)
            return []


__all__ = ['GridService']
