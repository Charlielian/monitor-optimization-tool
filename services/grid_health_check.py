"""
网格全量小区体检服务

功能：
1. 检查最新15分钟小区指标（无性能/流量为0）
2. 检查故障告警（影响性能）
3. 判断小区健康状态：
   - 正常：有性能数据且流量>0，无影响性能的告警
   - 不正常（无性能）：无性能数据
   - 不正常（流量为0）：有性能数据但流量为0
   - 不正常（有告警）：有影响性能的告警
   - 不正常（网管无数据）：无性能数据且无告警数据
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class GridHealthCheckService:
    """网格小区体检服务"""
    
    def __init__(self, mysql_client, pg_client=None):
        """初始化体检服务
        
        Args:
            mysql_client: MySQL客户端（用于获取小区映射和告警数据）
            pg_client: PostgreSQL客户端（用于获取性能指标）
        """
        self.mysql = mysql_client
        self.pg = pg_client
    
    def check_grid_health(self, grid_id: str) -> Dict[str, Any]:
        """检查指定网格的小区健康状态
        
        Args:
            grid_id: 网格ID
        
        Returns:
            体检结果，包含：
            - grid_id: 网格ID
            - grid_name: 网格名称
            - check_time: 体检时间
            - total_cells: 总小区数
            - healthy_cells: 健康小区数
            - unhealthy_cells: 不健康小区数
            - cells: 小区详细列表
        """
        try:
            # 1. 获取网格下的所有小区（优先使用grid_info表的网格名称）
            cells_sql = """
                SELECT 
                    cm.cgi,
                    cm.celname,
                    cm.zhishi as network_type,
                    cm.grid_id,
                    COALESCE(
                        NULLIF(gi.grid_name, ''), 
                        NULLIF(cm.grid_name, ''), 
                        cm.grid_id
                    ) as grid_name,
                    gi.grid_pp
                FROM cell_mapping cm
                LEFT JOIN grid_info gi ON cm.grid_id = gi.grid_id
                WHERE cm.grid_id = %s
                ORDER BY cm.zhishi, cm.cgi
            """
            cells = self.mysql.fetch_all(cells_sql, (grid_id,))
            
            if not cells:
                return {
                    'grid_id': grid_id,
                    'grid_name': grid_id,  # 如果没有小区，使用grid_id作为名称
                    'error': '网格下没有小区'
                }
            
            # 网格名称已经通过COALESCE处理，不会为空
            grid_name = cells[0].get('grid_name') or grid_id
            grid_pp = cells[0].get('grid_pp', '')
            
            # 2. 获取最新15分钟的性能数据
            performance_data = self._get_latest_performance(cells)
            
            # 3. 获取影响性能的告警数据
            alarm_data = self._get_performance_alarms(cells)
            
            # 4. 综合判断每个小区的健康状态
            cell_results = []
            healthy_count = 0
            unhealthy_count = 0
            
            for cell in cells:
                cgi = cell['cgi']
                network_type = cell['network_type']
                
                # 获取性能数据
                perf = performance_data.get(cgi, {})
                has_performance = perf.get('has_data', False)
                traffic_gb = perf.get('traffic_gb', 0)
                
                # 获取告警数据
                alarms = alarm_data.get(cgi, [])
                has_alarm = len(alarms) > 0
                
                # 判断健康状态
                status, reason = self._determine_health_status(
                    has_performance, traffic_gb, has_alarm
                )
                
                if status == 'healthy':
                    healthy_count += 1
                else:
                    unhealthy_count += 1
                
                cell_results.append({
                    'cgi': cgi,
                    'celname': cell['celname'],
                    'network_type': network_type,
                    'status': status,
                    'reason': reason,
                    'has_performance': has_performance,
                    'traffic_gb': traffic_gb,
                    'has_alarm': has_alarm,
                    'alarm_count': len(alarms),
                    'alarms': alarms,
                    'last_update': perf.get('last_update')
                })
            
            return {
                'grid_id': grid_id,
                'grid_name': grid_name,
                'grid_pp': grid_pp,
                'check_time': datetime.now(),
                'total_cells': len(cells),
                'healthy_cells': healthy_count,
                'unhealthy_cells': unhealthy_count,
                'healthy_rate': round(healthy_count / len(cells) * 100, 2) if cells else 0,
                'cells': cell_results
            }
            
        except Exception as e:
            logger.error(f"网格体检失败: {e}", exc_info=True)
            return {
                'grid_id': grid_id,
                'error': str(e)
            }
    
    def check_all_grids_health_with_cells(self) -> Dict[str, Any]:
        """检查所有网格的小区健康状态（汇总 + 明细）
        
        说明：
            - 为避免在导出时再次对每个网格调用 check_grid_health(grid_id) 造成重复体检，
              此方法在一次循环中同时收集“汇总结果”和“每个网格的小区明细”。
        
        Returns:
            {
                "results": [ {grid 汇总...}, ... ],
                "cells_by_grid": {grid_id: [cell 明细...], ...}
            }
        """
        try:
            # 获取所有网格列表（优先使用grid_info表的网格名称）
            grids_sql = """
                SELECT DISTINCT 
                    cm.grid_id,
                    COALESCE(
                        NULLIF(gi.grid_name, ''), 
                        NULLIF(cm.grid_name, ''), 
                        cm.grid_id
                    ) as grid_name,
                    gi.grid_pp,
                    gi.grid_area,
                    gi.gird_dd
                FROM cell_mapping cm
                LEFT JOIN grid_info gi ON cm.grid_id = gi.grid_id
                WHERE cm.grid_id IS NOT NULL
                ORDER BY cm.grid_id
            """
            grids = self.mysql.fetch_all(grids_sql)
            
            results: List[Dict[str, Any]] = []
            cells_by_grid: Dict[str, List[Dict[str, Any]]] = {}
            
            for grid in grids:
                grid_id = grid['grid_id']
                
                # 检查该网格（单次体检内已经批量获取性能和告警数据，无 N+1 查询）
                health_result = self.check_grid_health(grid_id)
                
                if 'error' in health_result:
                    logger.warning("网格 %s 体检失败: %s", grid_id, health_result.get('error'))
                    continue
                
                # 优先使用grid_info表的网格名称，如果为空则使用grid_id
                grid_name = grid.get('grid_name') or grid_id
                
                results.append({
                    'grid_id': grid_id,
                    'grid_name': grid_name,
                    'grid_pp': grid.get('grid_pp', ''),
                    'grid_area': grid.get('grid_area', ''),
                    'gird_dd': grid.get('gird_dd', ''),
                    'total_cells': health_result['total_cells'],
                    'healthy_cells': health_result['healthy_cells'],
                    'unhealthy_cells': health_result['unhealthy_cells'],
                    'healthy_rate': health_result['healthy_rate'],
                    'check_time': health_result['check_time'],
                })
                
                # 记录每个网格的小区明细，供导出等功能直接复用
                cells_by_grid[grid_id] = health_result.get('cells', []) or []
            
            return {
                "results": results,
                "cells_by_grid": cells_by_grid,
            }
            
        except Exception as e:
            logger.error("全量网格体检失败: %s", e, exc_info=True)
            return {
                "results": [],
                "cells_by_grid": {},
            }

    def check_all_grids_health(self) -> List[Dict[str, Any]]:
        """检查所有网格的小区健康状态（仅汇总）
        
        兼容旧接口：在内部调用 check_all_grids_health_with_cells，并只返回汇总结果列表。
        """
        data = self.check_all_grids_health_with_cells()
        return data.get("results", [])
    
    def _get_latest_performance(self, cells: List[Dict]) -> Dict[str, Dict]:
        """获取最新时间点的性能数据
        
        Args:
            cells: 小区列表
        
        Returns:
            {cgi: {has_data: bool, traffic_gb: float, last_update: datetime}}
        """
        if not self.pg:
            return {}
        
        try:
            # 分离4G和5G小区
            cgis_4g = [c['cgi'] for c in cells if c['network_type'] == '4g']
            cgis_5g = [c['cgi'] for c in cells if c['network_type'] == '5g']
            
            performance_data = {}
            
            # 计算当天的开始时间（00:00:00）
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 查询4G性能数据
            if cgis_4g:
                cgi_placeholders = ','.join(['%s'] * len(cgis_4g))
                sql_4g = f"""
                    SELECT 
                        cgi,
                        start_time,
                        (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0  AS traffic_gb
                    FROM cell_4g_metrics
                    WHERE cgi IN ({cgi_placeholders})
                      AND start_time >= %s
                    ORDER BY start_time DESC
                """
                params = cgis_4g + [today]
                results = self.pg.fetch_all(sql_4g, tuple(params))
                
                for row in results:
                    cgi = row['cgi']
                    # 只保存每个小区最新的数据
                    if cgi not in performance_data:
                        performance_data[cgi] = {
                            'has_data': True,
                            'traffic_gb': float(row['traffic_gb'] or 0),
                            'last_update': row['start_time']
                        }
            
            # 查询5G性能数据
            if cgis_5g:
                cgi_placeholders = ','.join(['%s'] * len(cgis_5g))
                sql_5g = f"""
                    SELECT 
                        "Ncgi" as cgi,
                        start_time,
                        (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0  AS traffic_gb
                    FROM cell_5g_metrics
                    WHERE "Ncgi" IN ({cgi_placeholders})
                      AND start_time >= %s
                    ORDER BY start_time DESC
                """
                params = cgis_5g + [today]
                results = self.pg.fetch_all(sql_5g, tuple(params))
                
                for row in results:
                    cgi = row['cgi']
                    # 只保存每个小区最新的数据
                    if cgi not in performance_data:
                        performance_data[cgi] = {
                            'has_data': True,
                            'traffic_gb': float(row['traffic_gb'] or 0),
                            'last_update': row['start_time']
                        }
            
            return performance_data
            
        except Exception as e:
            logger.error(f"获取性能数据失败: {e}", exc_info=True)
            return {}
    
    def _get_performance_alarms(self, cells: List[Dict]) -> Dict[str, List[Dict]]:
        """获取影响性能的告警数据
        
        通过网元ID匹配告警：
        1. 从小区CGI中提取网元ID（CGI格式：460-00-网元ID-小区ID）
        2. 查询告警表中该网元的影响性能的告警
        3. 将告警关联到该网元下的所有小区
        
        Args:
            cells: 小区列表
        
        Returns:
            {cgi: [{alarm_name, alarm_time, severity}]} 
        """
        try:
            if not cells:
                return {}
            
            # 从CGI中提取网元ID，建立网元ID到CGI的映射
            ne_id_to_cgis = {}  # {ne_id: [cgi1, cgi2, ...]}
            for cell in cells:
                cgi = cell['cgi']
                # CGI格式：460-00-网元ID-小区ID
                parts = cgi.split('-')
                if len(parts) >= 3:
                    ne_id = parts[2]  # 提取网元ID
                    if ne_id not in ne_id_to_cgis:
                        ne_id_to_cgis[ne_id] = []
                    ne_id_to_cgis[ne_id].append(cgi)
            
            if not ne_id_to_cgis:
                return {}
            
            ne_ids = list(ne_id_to_cgis.keys())
            
            # 定义影响性能的告警类型（根据实际业务调整）
            performance_alarm_types = [
                '小区退服',
                '小区不可用',
                '传输中断',
                '传输故障',
                '硬件故障',
                '板卡故障',
                '光模块故障',
                'RRU故障',
                '天馈故障',
                '驻波比告警',
                '功率异常',
                '时钟失步',
                '同步失步'
            ]
            
            # 构建告警类型的SQL条件
            # 中兴：使用alarm_code_name或alarm_title字段
            alarm_type_conditions_zte = ' OR '.join([
                f"(alarm_code_name LIKE '%{t}%' OR alarm_title LIKE '%{t}%')" 
                for t in performance_alarm_types
            ])
            # 诺基亚：使用fault_name_cn或alarm_description字段
            alarm_type_conditions_nokia = ' OR '.join([
                f"(fault_name_cn LIKE '%{t}%' OR alarm_description LIKE '%{t}%')" 
                for t in performance_alarm_types
            ])
            
            # 查询当前告警（中兴）- 使用ne_id字段
            ne_id_placeholders = ','.join(['%s'] * len(ne_ids))
            sql_zte = f"""
                SELECT 
                    ne_id,
                    alarm_code_name as alarm_name,
                    occur_time as alarm_time,
                    alarm_level as severity,
                    alarm_object_type,
                    alarm_object_name
                FROM cur_alarm
                WHERE ne_id IN ({ne_id_placeholders})
                  AND ({alarm_type_conditions_zte})
                ORDER BY occur_time DESC
            """
            alarms_zte = self.mysql.fetch_all(sql_zte, tuple(ne_ids))
            
            # 查询当前告警（诺基亚）- 使用enb_id字段
            sql_nokia = f"""
                SELECT 
                    enb_id as ne_id,
                    fault_name_cn as alarm_name,
                    alarm_start_time as alarm_time,
                    severity,
                    alarm_object_name
                FROM cur_alarm_nokia
                WHERE enb_id IN ({ne_id_placeholders})
                  AND ({alarm_type_conditions_nokia})
                ORDER BY alarm_start_time DESC
            """
            alarms_nokia = self.mysql.fetch_all(sql_nokia, tuple(ne_ids))
            
            # 合并告警数据
            all_alarms = (alarms_zte or []) + (alarms_nokia or [])
            
            # 建立小区名称到CGI的映射，用于告警关联
            celname_to_cgi = {cell['celname']: cell['cgi'] for cell in cells}
            
            # 合并告警数据：将告警关联到相关的小区
            alarm_data = {}
            
            for alarm in all_alarms:
                ne_id = str(alarm.get('ne_id', ''))
                if ne_id in ne_id_to_cgis:
                    alarm_name = alarm.get('alarm_name', '')
                    alarm_object_name = alarm.get('alarm_object_name', '')
                    
                    # 对于所有告警，先尝试精确匹配到具体小区
                    matched = False
                    
                    # 遍历所有小区，检查告警对象名称是否与小区相关
                    for cell in cells:
                        cgi = cell['cgi']
                        celname = cell['celname']
                        
                        # 检查小区是否属于当前网元
                        if cgi in ne_id_to_cgis[ne_id]:
                            # 从CGI中提取小区ID
                            cell_id = cgi.split('-')[-1] if '-' in cgi else ''
                            
                            # 严格匹配逻辑：
                            # 1. 如果告警对象名称包含完整的小区名称
                            # 2. 或者告警对象名称包含小区ID且是独立的数字（避免部分匹配）
                            # 3. 或者小区名称包含完整的告警对象名称
                            import re
                            # 检查是否是独立的小区ID
                            cell_id_match = re.search(r'\\b' + re.escape(cell_id) + r'\\b', alarm_object_name)
                            
                            if (celname in alarm_object_name or 
                                (cell_id_match and len(cell_id) >= 2) or 
                                (alarm_object_name in celname and len(alarm_object_name) >= 5)):
                                # 只关联匹配到的小区
                                if cgi not in alarm_data:
                                    alarm_data[cgi] = []
                                alarm_data[cgi].append({
                                    'alarm_name': alarm_name,
                                    'alarm_time': alarm.get('alarm_time', ''),
                                    'severity': alarm.get('severity', '未知'),
                                    'alarm_object_name': alarm_object_name
                                })
                                matched = True
                                # 找到匹配的小区后，跳出循环，不再匹配其他小区
                                break
                    
                    # 只有非DU相关告警且没有匹配到小区时，才关联到所有小区
                    if not matched and 'DU' not in alarm_name:
                        for cgi in ne_id_to_cgis[ne_id]:
                            if cgi not in alarm_data:
                                alarm_data[cgi] = []
                            alarm_data[cgi].append({
                                'alarm_name': alarm_name,
                                'alarm_time': alarm.get('alarm_time', ''),
                                'severity': alarm.get('severity', '未知'),
                                'alarm_object_name': alarm_object_name
                            })
            
            return alarm_data
            
        except Exception as e:
            logger.error(f"获取告警数据失败: {e}", exc_info=True)
            return {}
    
    def _determine_health_status(self, has_performance: bool, traffic_gb: float, 
                                 has_alarm: bool) -> tuple:
        """判断小区健康状态
        
        Args:
            has_performance: 是否有性能数据
            traffic_gb: 流量（GB）
            has_alarm: 是否有影响性能的告警
        
        Returns:
            (status, reason)
            status: 'healthy' | 'unhealthy'
            reason: 原因描述
        """
        # 优先级1：无性能数据
        if not has_performance:
            if not has_alarm:
                return ('unhealthy', '网管无数据')
            else:
                return ('unhealthy', '无性能数据')
        
        # 优先级2：有告警
        if has_alarm:
            return ('unhealthy', '有影响性能的告警')
        
        # 优先级3：流量为0
        if traffic_gb == 0:
            return ('unhealthy', '流量为0')
        
        # 正常
        return ('healthy', '正常')


__all__ = ['GridHealthCheckService']
