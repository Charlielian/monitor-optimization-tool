"""
保障小区体检服务

功能：
1. 检查保障小区的最新性能指标
2. 检查故障告警（影响性能）
3. 判断小区健康状态
4. 输出指定的字段：场景名，小区名，CGI，制式，健康状态，原因，是否有性能数据，当日累计流量，是否有告警，告警明细，前一日忙时利用率，当日忙时利用率
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class GuaranteeHealthCheckService:
    """保障小区体检服务"""
    
    def __init__(self, mysql_client, pg_client=None):
        """初始化体检服务
        
        Args:
            mysql_client: MySQL客户端（用于获取小区映射和告警数据）
            pg_client: PostgreSQL客户端（用于获取性能指标）
        """
        self.mysql = mysql_client
        self.pg = pg_client
        
        # 初始化场景服务
        from services.scenario_service import ScenarioService
        self.scenario_service = ScenarioService(pg_client) if pg_client else None
    
    def check_guarantee_health(self, selected_scenes: List[str] = None) -> Dict[str, Any]:
        """检查保障小区的健康状态
        
        Args:
            selected_scenes: 选择的场景列表，如果为None则检查所有场景
        
        Returns:
            体检结果，包含：
            - check_time: 体检时间
            - total_cells: 总小区数
            - healthy_cells: 健康小区数
            - unhealthy_cells: 不健康小区数
            - cells: 小区详细列表
        """
        try:
            # 1. 获取保障小区列表
            cells = self._get_guarantee_cells(selected_scenes)
            
            if not cells:
                return {
                    'error': '没有找到保障小区'
                }
            
            # 2. 获取最新性能数据
            performance_data = self._get_latest_performance(cells)
            
            # 3. 获取影响性能的告警数据
            alarm_data = self._get_performance_alarms(cells)
            
            # 4. 获取忙时利用率数据
            busy_hour_data = self._get_busy_hour_utilization(cells)
            
            # 5. 综合判断每个小区的健康状态
            cell_results = []
            healthy_count = 0
            unhealthy_count = 0
            no_traffic_cells = []  # 无流量小区
            no_performance_cells = []  # 无性能数据小区
            
            for cell in cells:
                cgi = cell['cgi']
                network_type = cell['network_type']
                scene_name = cell.get('scene_name', '未知场景')
                
                # 获取性能数据
                perf = performance_data.get(cgi, {})
                has_performance = perf.get('has_data', False)
                traffic_gb = perf.get('traffic_gb', 0)
                
                # 获取告警数据
                alarms = alarm_data.get(cgi, [])
                has_alarm = len(alarms) > 0
                
                # 获取忙时利用率
                busy_hour = busy_hour_data.get(cgi, {})
                yesterday_busy_hour_util = busy_hour.get('yesterday_busy_hour_util', 0)
                today_busy_hour_util = busy_hour.get('today_busy_hour_util', 0)
                
                # 判断健康状态
                status, reason = self._determine_health_status(
                    has_performance, traffic_gb, has_alarm
                )
                
                if status == 'healthy':
                    healthy_count += 1
                else:
                    unhealthy_count += 1
                
                # 构建告警明细
                alarm_details = '; '.join([f"{alarm.get('alarm_name', '')} ({alarm.get('severity', '')})" for alarm in alarms]) if alarms else '无告警'
                
                cell_info = {
                    'scene_name': scene_name,
                    'celname': cell['celname'],
                    'cgi': cgi,
                    'network_type': network_type,
                    'status': '健康' if status == 'healthy' else '不健康',
                    'reason': reason,
                    'has_performance': '是' if has_performance else '否',
                    'today_traffic_gb': traffic_gb,
                    'has_alarm': '是' if has_alarm else '否',
                    'alarm_details': alarm_details,
                    'yesterday_busy_hour_util': yesterday_busy_hour_util,
                    'today_busy_hour_util': today_busy_hour_util
                }
                
                cell_results.append(cell_info)
                
                # 筛选无流量和无性能小区
                if not has_performance:
                    no_performance_cells.append(cell_info)
                elif traffic_gb == 0:
                    no_traffic_cells.append(cell_info)
            
            return {
                'check_time': datetime.now(),
                'total_cells': len(cells),
                'healthy_cells': healthy_count,
                'unhealthy_cells': unhealthy_count,
                'cells': cell_results,
                'no_traffic_cells': no_traffic_cells,
                'no_performance_cells': no_performance_cells
            }
            
        except Exception as e:
            logger.error(f"保障小区体检失败: {e}", exc_info=True)
            return {
                'error': f"体检失败: {str(e)}"
            }
    
    def _get_guarantee_cells(self, selected_scenes: List[str] = None) -> List[Dict]:
        """获取保障小区列表
        
        Args:
            selected_scenes: 选择的场景列表，如果为None则获取所有场景的小区
        
        Returns:
            保障小区列表
        """
        try:
            # 检查是否选择了"全网"场景
            if selected_scenes and '全网' in selected_scenes:
                # 获取映射表中的所有小区
                sql = """
                    SELECT 
                        cm.cgi,
                        cm.celname,
                        cm.zhishi as network_type,
                        cm.grid_id,
                        cm.grid_name,
                        '全网' as scene_name
                    FROM cell_mapping cm
                    ORDER BY cm.zhishi, cm.cgi
                """
                cells = self.mysql.fetch_all(sql)
                return cells
            
            # 使用场景管理模块获取场景小区
            if self.scenario_service:
                # 获取所有场景
                all_scenes = self.scenario_service.list_scenarios()
                
                # 根据选择的场景过滤
                if selected_scenes:
                    filtered_scenes = [s for s in all_scenes if s.get('scenario_name') in selected_scenes]
                else:
                    filtered_scenes = all_scenes
                
                # 收集所有场景的小区
                cells = []
                for scene in filtered_scenes:
                    scene_id = scene.get('id')
                    scene_name = scene.get('scenario_name', '未知场景')
                    
                    # 获取场景下的小区
                    scene_cells = self.scenario_service.list_cells(scene_id)
                    
                    for cell in scene_cells:
                        cells.append({
                            'cgi': cell.get('cgi', ''),
                            'celname': cell.get('cell_name', ''),
                            'network_type': cell.get('network_type', ''),
                            'grid_id': '',  # 场景小区可能没有网格信息
                            'grid_name': '',  # 场景小区可能没有网格信息
                            'scene_name': scene_name
                        })
                
                return cells
            else:
                # 如果场景服务不可用，使用旧的方式获取保障小区
                sql = """
                    SELECT 
                        cm.cgi,
                        cm.celname,
                        cm.zhishi as network_type,
                        cm.grid_id,
                        cm.grid_name,
                        CASE 
                            WHEN cm.celname LIKE '%保障%' THEN '保障场景'
                            WHEN cm.celname LIKE '%应急%' THEN '应急场景'
                            WHEN cm.celname LIKE '%通信车%' THEN '通信车场景'
                            WHEN cm.celname LIKE '%龙舟%' THEN '龙舟赛场景'
                            ELSE '其他场景'
                        END as scene_name
                    FROM cell_mapping cm
                    WHERE cm.celname LIKE '%保障%' 
                        OR cm.celname LIKE '%应急%' 
                        OR cm.celname LIKE '%通信车%'
                        OR cm.celname LIKE '%龙舟%'
                    ORDER BY cm.zhishi, cm.cgi
                """
                cells = self.mysql.fetch_all(sql)
                
                # 根据场景过滤小区
                if selected_scenes:
                    filtered_cells = []
                    for cell in cells:
                        scene_name = cell.get('scene_name', '')
                        if scene_name in selected_scenes:
                            filtered_cells.append(cell)
                    cells = filtered_cells
                
                return cells
            
        except Exception as e:
            logger.error(f"获取保障小区列表失败: {e}", exc_info=True)
            return []
    
    def _get_total_cell_count(self) -> int:
        """获取映射表中的总小区数"""
        try:
            sql = "SELECT COUNT(*) as total FROM cell_mapping"
            result = self.mysql.fetch_one(sql)
            return result.get('total', 0) if result else 0
        except Exception as e:
            logger.error(f"获取总小区数失败: {e}", exc_info=True)
            return 0
    
    def get_available_scenes(self) -> List[Dict]:
        """获取可用的保障场景列表
        
        Returns:
            场景列表，每个场景包含：
            - scene_name: 场景名称
            - cell_count: 该场景下的小区数量
        """
        try:
            scenes = []
            
            # 使用场景管理模块获取场景列表
            if self.scenario_service:
                all_scenes = self.scenario_service.list_scenarios()
                
                for scene in all_scenes:
                    scene_id = scene.get('id')
                    scene_name = scene.get('scenario_name', '未知场景')
                    
                    # 获取场景下的小区数量
                    scene_cells = self.scenario_service.list_cells(scene_id)
                    cell_count = len(scene_cells)
                    
                    scenes.append({
                        'scene_name': scene_name,
                        'cell_count': cell_count
                    })
            else:
                # 如果场景服务不可用，使用旧的方式
                cells = self._get_guarantee_cells()
                scene_stats = {}
                for cell in cells:
                    scene_name = cell.get('scene_name', '其他场景')
                    if scene_name not in scene_stats:
                        scene_stats[scene_name] = 0
                    scene_stats[scene_name] += 1
                
                for scene_name, cell_count in scene_stats.items():
                    scenes.append({
                        'scene_name': scene_name,
                        'cell_count': cell_count
                    })
            
            # 添加"全网"场景
            total_cells = self._get_total_cell_count()
            scenes.append({
                'scene_name': '全网',
                'cell_count': total_cells
            })
            
            return scenes
            
        except Exception as e:
            logger.error(f"获取保障场景列表失败: {e}", exc_info=True)
            return []
    
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
            performance_data = {}
            
            # 计算当天的开始时间（00:00:00）
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 分离4G和5G小区
            cgis_4g = []
            cgis_5g = []
            cell_info_map = {}  # 保存小区信息，用于后续处理
            
            for cell in cells:
                cgi = cell['cgi']
                network_type = cell.get('network_type', '')
                cell_info_map[cgi] = cell
                
                # 根据网络类型分类
                if network_type == '4g':
                    cgis_4g.append(cgi)
                elif network_type == '5g':
                    cgis_5g.append(cgi)
                else:
                    # 尝试自动识别CGI类型
                    parts = cgi.split('-')
                    if len(parts) >= 4:
                        enb_gnb = parts[2]
                        if len(enb_gnb) == 6:
                            # 6位是4G eNodeB
                            cgis_4g.append(cgi)
                        elif len(enb_gnb) == 8:
                            # 8位是5G gNodeB
                            cgis_5g.append(cgi)
                    else:
                        # 无法识别，尝试同时查询4G和5G
                        cgis_4g.append(cgi)
                        cgis_5g.append(cgi)
            
            # 查询4G性能数据（使用小时表）
            if cgis_4g:
                # 限制每个查询的小区数量，避免SQL语句过长
                batch_size = 1000
                for i in range(0, len(cgis_4g), batch_size):
                    batch_cgis = cgis_4g[i:i+batch_size]
                    cgi_placeholders = ','.join(['%s'] * len(batch_cgis))
                    sql_4g = f"""
                        SELECT 
                            cgi,
                            cell_id,
                            start_time,
                            (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                        FROM cell_4g_metrics_hour
                        WHERE (cgi IN ({cgi_placeholders}) OR cell_id IN ({cgi_placeholders}))
                          AND start_time >= %s
                        ORDER BY start_time DESC
                    """
                    params = batch_cgis + batch_cgis + [today]
                    try:
                        results = self.pg.fetch_all(sql_4g, tuple(params))
                        logger.info(f"获取4G性能数据批次成功，返回 {len(results)} 条记录")
                        for row in results:
                            # 使用查询结果中的cgi作为键，确保一致性
                            result_cgi = row.get('cgi') or row.get('cell_id')
                            if result_cgi and result_cgi not in performance_data:
                                performance_data[result_cgi] = {
                                    'has_data': True,
                                    'traffic_gb': float(row.get('traffic_gb', 0) or 0),
                                    'last_update': row.get('start_time')
                                }
                    except Exception as batch_error:
                        logger.error(f"获取4G性能数据批次失败: {batch_error}")
            
            # 查询5G性能数据（使用小时表）
            if cgis_5g:
                # 限制每个查询的小区数量，避免SQL语句过长
                batch_size = 1000
                for i in range(0, len(cgis_5g), batch_size):
                    batch_cgis = cgis_5g[i:i+batch_size]
                    cgi_placeholders = ','.join(['%s'] * len(batch_cgis))
                    sql_5g = f"""
                        SELECT 
                            "Ncgi" as cgi,
                            start_time,
                            (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic_gb
                        FROM cell_5g_metrics_hour
                        WHERE "Ncgi" IN ({cgi_placeholders})
                          AND start_time >= %s
                        ORDER BY start_time DESC
                    """

                    params = batch_cgis + [today]
                    try:
                        results = self.pg.fetch_all(sql_5g, tuple(params))
                        logger.info(f"获取5G性能数据批次成功，返回 {len(results)} 条记录")
                        for row in results:
                            cgi = row.get('cgi')
                            if cgi and cgi not in performance_data:
                                performance_data[cgi] = {
                                    'has_data': True,
                                    'traffic_gb': float(row.get('traffic_gb', 0) or 0),
                                    'last_update': row.get('start_time')
                                }
                    except Exception as batch_error:
                        logger.error(f"获取5G性能数据批次失败: {batch_error}")
            
            # 处理小区信息映射，确保所有小区都有性能数据记录
            for cgi in cell_info_map:
                if cgi not in performance_data:
                    performance_data[cgi] = {
                        'has_data': False,
                        'traffic_gb': 0,
                        'last_update': None
                    }
            
            logger.info(f"性能数据查询完成，共处理 {len(performance_data)} 个小区")
            return performance_data
            
        except Exception as e:
            logger.error(f"获取性能数据失败: {e}", exc_info=True)
            return {}
    
    def _get_performance_alarms(self, cells: List[Dict]) -> Dict[str, List[Dict]]:
        """获取影响性能的告警数据
        
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
    
    def _get_busy_hour_utilization(self, cells: List[Dict]) -> Dict[str, Dict]:
        """获取忙时利用率数据
        
        Args:
            cells: 小区列表
        
        Returns:
            {cgi: {yesterday_busy_hour_util: float, today_busy_hour_util: float}}
        """
        if not self.pg:
            return {}
        
        try:
            result = {}
            
            # 计算昨天和今天的日期
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # 分离4G和5G小区
            cgis_4g = []
            cgis_5g = []
            cell_info_map = {}  # 保存小区信息，用于后续处理
            
            for cell in cells:
                cgi = cell['cgi']
                network_type = cell.get('network_type', '')
                cell_info_map[cgi] = cell
                
                # 根据网络类型分类
                if network_type == '4g':
                    cgis_4g.append(cgi)
                elif network_type == '5g':
                    cgis_5g.append(cgi)
                else:
                    # 尝试自动识别CGI类型
                    parts = cgi.split('-')
                    if len(parts) >= 4:
                        enb_gnb = parts[2]
                        if len(enb_gnb) == 6:
                            # 6位是4G eNodeB
                            cgis_4g.append(cgi)
                        elif len(enb_gnb) == 8:
                            # 8位是5G gNodeB
                            cgis_5g.append(cgi)
                    else:
                        # 无法识别，尝试同时查询4G和5G
                        cgis_4g.append(cgi)
                        cgis_5g.append(cgi)
            
            # 查询4G忙时利用率（流量最大小时的利用率）
            if cgis_4g:
                # 限制每个查询的小区数量，避免SQL语句过长
                batch_size = 1000
                for i in range(0, len(cgis_4g), batch_size):
                    batch_cgis = cgis_4g[i:i+batch_size]
                    cgi_placeholders = ','.join(['%s'] * len(batch_cgis))
                    
                    # 昨天忙时利用率（流量最大小时）
                    sql_4g_yesterday = f"""
                        WITH hourly_data AS (
                            SELECT 
                                cgi,
                                cell_id,
                                start_time,
                                dl_prb_utilization,
                                ul_prb_utilization,
                                GREATEST(COALESCE(dl_prb_utilization, 0), COALESCE(ul_prb_utilization, 0)) AS max_prb_util,
                                (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) AS total_traffic
                            FROM cell_4g_metrics_hour
                            WHERE cgi IN ({cgi_placeholders})
                              AND DATE(start_time) = %s
                        ),
                        max_traffic_hours AS (
                            SELECT 
                                cgi,
                                cell_id,
                                MAX(total_traffic) AS max_traffic
                            FROM hourly_data
                            GROUP BY cgi, cell_id
                        )
                        SELECT 
                            hd.cgi,
                            hd.cell_id,
                            hd.max_prb_util
                        FROM hourly_data hd
                        JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.cell_id = mth.cell_id AND hd.total_traffic = mth.max_traffic
                    """
                    params_4g_yesterday = batch_cgis + [yesterday]
                    try:
                        yesterday_results = self.pg.fetch_all(sql_4g_yesterday, tuple(params_4g_yesterday))
                        logger.info(f"获取4G昨天忙时利用率批次成功，返回 {len(yesterday_results)} 条记录")
                        for row in yesterday_results:
                            # 使用查询结果中的cgi作为键，确保一致性
                            row_cgi = row.get('cgi') or row.get('cell_id')
                            if row_cgi:
                                if row_cgi not in result:
                                    result[row_cgi] = {}
                                result[row_cgi]['yesterday_busy_hour_util'] = float(row.get('max_prb_util', 0))
                    except Exception as batch_error:
                        logger.error(f"获取4G昨天忙时利用率批次失败: {batch_error}")
                    
                    # 今天忙时利用率（流量最大小时）
                    sql_4g_today = f"""
                        WITH hourly_data AS (
                            SELECT 
                                cgi,
                                cell_id,
                                start_time,
                                dl_prb_utilization,
                                ul_prb_utilization,
                                GREATEST(COALESCE(dl_prb_utilization, 0), COALESCE(ul_prb_utilization, 0)) AS max_prb_util,
                                (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) AS total_traffic
                            FROM cell_4g_metrics_hour
                            WHERE cgi IN ({cgi_placeholders})
                              AND DATE(start_time) = %s
                        ),
                        max_traffic_hours AS (
                            SELECT 
                                cgi,
                                cell_id,
                                MAX(total_traffic) AS max_traffic
                            FROM hourly_data
                            GROUP BY cgi, cell_id
                        )
                        SELECT 
                            hd.cgi,
                            hd.cell_id,
                            hd.max_prb_util
                        FROM hourly_data hd
                        JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.cell_id = mth.cell_id AND hd.total_traffic = mth.max_traffic
                    """
                    params_4g_today = batch_cgis + [today]
                    try:
                        today_results = self.pg.fetch_all(sql_4g_today, tuple(params_4g_today))
                        logger.info(f"获取4G今天忙时利用率批次成功，返回 {len(today_results)} 条记录")
                        for row in today_results:
                            # 使用查询结果中的cgi作为键，确保一致性
                            row_cgi = row.get('cgi') or row.get('cell_id')
                            if row_cgi:
                                if row_cgi not in result:
                                    result[row_cgi] = {}
                                result[row_cgi]['today_busy_hour_util'] = float(row.get('max_prb_util', 0))
                    except Exception as batch_error:
                        logger.error(f"获取4G今天忙时利用率批次失败: {batch_error}")
            
            # 查询5G忙时利用率（流量最大小时的利用率）
            if cgis_5g:
                # 限制每个查询的小区数量，避免SQL语句过长
                batch_size = 1000
                for i in range(0, len(cgis_5g), batch_size):
                    batch_cgis = cgis_5g[i:i+batch_size]
                    cgi_placeholders = ','.join(['%s'] * len(batch_cgis))
                    
                    # 昨天忙时利用率（流量最大小时）
                    sql_5g_yesterday = f"""
                        WITH hourly_data AS (
                            SELECT 
                                "Ncgi" as cgi,
                                start_time,
                                "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) AS ul_prb_util,
                                "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) AS dl_prb_util,
                                GREATEST(
                                    COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                                    COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                                ) AS max_prb_util,
                                (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) AS total_traffic
                            FROM cell_5g_metrics_hour
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND DATE(start_time) = %s
                        ),
                        max_traffic_hours AS (
                            SELECT 
                                cgi,
                                MAX(total_traffic) AS max_traffic
                            FROM hourly_data
                            GROUP BY cgi
                        )
                        SELECT 
                            hd.cgi,
                            hd.max_prb_util
                        FROM hourly_data hd
                        JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.total_traffic = mth.max_traffic
                    """
                    params_5g_yesterday = batch_cgis + [yesterday]
                    try:
                        yesterday_results = self.pg.fetch_all(sql_5g_yesterday, tuple(params_5g_yesterday))
                        logger.info(f"获取5G昨天忙时利用率批次成功，返回 {len(yesterday_results)} 条记录")
                        for row in yesterday_results:
                            cgi = row['cgi']
                            if cgi:
                                if cgi not in result:
                                    result[cgi] = {}
                                result[cgi]['yesterday_busy_hour_util'] = float(row.get('max_prb_util', 0))
                    except Exception as batch_error:
                        logger.error(f"获取5G昨天忙时利用率批次失败: {batch_error}")
                    
                    # 今天忙时利用率（流量最大小时）
                    sql_5g_today = f"""
                        WITH hourly_data AS (
                            SELECT 
                                "Ncgi" as cgi,
                                start_time,
                                "RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0) AS ul_prb_util,
                                "RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0) AS dl_prb_util,
                                GREATEST(
                                    COALESCE("RRU_PuschPrbAssn" * 100.0 / NULLIF("RRU_PuschPrbTot", 0), 0),
                                    COALESCE("RRU_PdschPrbAssn" * 100.0 / NULLIF("RRU_PdschPrbTot", 0), 0)
                                ) AS max_prb_util,
                                (COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) AS total_traffic
                            FROM cell_5g_metrics_hour
                            WHERE "Ncgi" IN ({cgi_placeholders})
                              AND DATE(start_time) = %s
                        ),
                        max_traffic_hours AS (
                            SELECT 
                                cgi,
                                MAX(total_traffic) AS max_traffic
                            FROM hourly_data
                            GROUP BY cgi
                        )
                        SELECT 
                            hd.cgi,
                            hd.max_prb_util
                        FROM hourly_data hd
                        JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.total_traffic = mth.max_traffic
                    """
                    params_5g_today = batch_cgis + [today]
                    try:
                        today_results = self.pg.fetch_all(sql_5g_today, tuple(params_5g_today))
                        logger.info(f"获取5G今天忙时利用率批次成功，返回 {len(today_results)} 条记录")
                        for row in today_results:
                            cgi = row['cgi']
                            if cgi:
                                if cgi not in result:
                                    result[cgi] = {}
                                result[cgi]['today_busy_hour_util'] = float(row.get('max_prb_util', 0))
                    except Exception as batch_error:
                        logger.error(f"获取5G今天忙时利用率批次失败: {batch_error}")
            
            # 处理小区信息映射，确保所有小区都有忙时利用率记录
            for cgi in cell_info_map:
                if cgi not in result:
                    result[cgi] = {
                        'yesterday_busy_hour_util': 0,
                        'today_busy_hour_util': 0
                    }
                else:
                    # 确保两个字段都存在
                    if 'yesterday_busy_hour_util' not in result[cgi]:
                        result[cgi]['yesterday_busy_hour_util'] = 0
                    if 'today_busy_hour_util' not in result[cgi]:
                        result[cgi]['today_busy_hour_util'] = 0
            
            logger.info(f"忙时利用率查询完成，共处理 {len(result)} 个小区")
            return result
            
        except Exception as e:
            logger.error(f"获取忙时利用率失败: {e}", exc_info=True)
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


__all__ = ['GuaranteeHealthCheckService']
