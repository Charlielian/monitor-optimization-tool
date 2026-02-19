"""
高铁小区健康检查服务

功能：
1. 检查高铁小区的最新性能指标
2. 检查故障告警（全量告警）
3. 判断小区健康状态
4. 基于 hsr_info 表的配置信息
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class HSRHealthCheckService:
    """高铁小区健康检查服务"""
    
    def __init__(self, mysql_client, pg_client=None):
        """初始化体检服务
        
        Args:
            mysql_client: MySQL客户端（用于获取高铁小区配置和告警数据）
            pg_client: PostgreSQL客户端（用于获取性能指标）
        """
        self.mysql = mysql_client
        self.pg = pg_client
    
    def check_hsr_health(self) -> Dict[str, Any]:
        """检查所有高铁小区的健康状态

        Returns:
            体检结果，包含：
            - check_time: 体检时间
            - total_cells: 总小区数
            - healthy_cells: 健康小区数
            - unhealthy_cells: 不健康小区数
            - healthy_rate: 健康率
            - cells: 小区详细列表
        """
        try:
            # 1. 获取所有高铁小区（从hsr_info表）
            cells_sql = """
                SELECT 
                    id,
                    line_name,
                    Transmitting_Point_Name as site_name,
                    area,
                    site_type,
                    bbu_name,
                    celname,
                    CGI,
                    lng,
                    lat,
                    high,
                    ant_dir,
                    zhishi as network_type,
                    cpId,
                    cpId_key,
                    rru_id_key,
                    rru_id,
                    rru_type
                FROM hsr_info
                ORDER BY line_name, site_name, celname
            """
            cells = self.mysql.fetch_all(cells_sql)
            
            if not cells:
                return {
                    'error': '没有找到高铁小区数据',
                    'check_time': datetime.now()
                }
            
            # 2. 获取当前时间
            check_time = datetime.now()
            logger.info(f"开始高铁小区体检，本次共 {len(cells)} 个小区，检查时间: {check_time}")
            
            # 3. 获取告警数据（参考网格小区匹配告警和超级小区CP退服的匹配规则）
            alarm_data = self._get_alarm_data(cells)
            
            # 4. 检查每个小区的健康状态
            checked_cells = []
            healthy_count = 0
            
            for cell in cells:
                cgi = cell.get('CGI', '')
                network_type = cell.get('network_type', '')
                
                # 详细日志
                logger.debug(
                    "小区 %s 开始检查告警状态",
                    cgi
                )
                
                # 获取告警数据
                has_alarm = False
                alarm_count = 0
                alarm_details = []

                # 获取小区的CPID和rru_id
                cell_cpid = cell.get('cpId', '')
                cell_cpid_str = str(cell_cpid) if cell_cpid is not None else ''
                cell_rru_id = str(cell.get('rru_id', ''))

                # 1. 尝试直接匹配（同时考虑CGI、CPID和rru_id）
                if cgi in alarm_data:
                    matched_alarms = []
                    for alarm in alarm_data[cgi]:
                        # 检查CPID是否匹配（如果有CPID的话）
                        alarm_cpid = alarm.get('extracted_cpid', '')
                        cpid_match = (not alarm_cpid or not cell_cpid_str or alarm_cpid == cell_cpid_str)

                        # 检查rru_id是否匹配（如果告警有matched_rru_id的话）
                        matched_rru_id = alarm.get('matched_rru_id', '')
                        rru_match = (not matched_rru_id or matched_rru_id == cell_rru_id)

                        logger.debug(
                            "[告警分配调试] CGI=%s, cell_rru_id=%s, alarm=%s, matched_rru_id=%s, cpid_match=%s, rru_match=%s",
                            cgi,
                            cell_rru_id,
                            alarm.get('alarm_name', ''),
                            matched_rru_id,
                            cpid_match,
                            rru_match,
                        )

                        if cpid_match and rru_match:
                            matched_alarms.append(alarm)
                            logger.debug(
                                "[告警已添加] CGI=%s, cell_rru_id=%s, alarm=%s",
                                cgi,
                                cell_rru_id,
                                alarm.get('alarm_name', ''),
                            )

                    if matched_alarms:
                        has_alarm = True
                        alarm_count = len(matched_alarms)
                        alarm_details = matched_alarms
                        logger.debug(f"直接匹配到告警: CGI={cgi}, rru_id={cell_rru_id}, 告警数量={alarm_count}")
                
                # 2. 尝试CPID匹配（针对超级小区CP退服告警）
                # 注意：超级小区CP退服告警必须同时匹配CPID和逻辑小区ID
                if not has_alarm and cell_cpid_str:
                    for alarm_cgi, alarms in alarm_data.items():
                        for alarm in alarms:
                            # 检查是否是超级小区CP退服告警
                            is_super_cell_cp_alarm = any(keyword in alarm.get('alarm_name', '') for keyword in ['超级小区CP退服', '超级小区CP退出服务'])
                            if is_super_cell_cp_alarm:
                                # 检查CPID和逻辑小区ID是否都匹配
                                alarm_cpid = alarm.get('extracted_cpid', '')
                                alarm_cgi = alarm.get('extracted_cgi', '')
                                # 必须同时满足：CPID匹配 AND 逻辑小区ID匹配
                                if alarm_cpid == cell_cpid_str and alarm_cgi == cgi:
                                    matched_alarms = []
                                    matched_alarms.append(alarm)
                                    has_alarm = True
                                    alarm_count = len(matched_alarms)
                                    alarm_details = matched_alarms
                                    logger.debug(f"CPID和逻辑小区ID匹配到超级小区CP退服告警: CPID={cell_cpid_str}, CGI={cgi}")
                                    break
                        if has_alarm:
                            break
                
                # 2. 尝试部分匹配（小区名称、BBU名称、站点名称或其他标识）
                if not has_alarm:
                    celname = cell.get('celname', '')
                    bbu_name = cell.get('bbu_name', '')
                    site_name = cell.get('site_name', '')
                    line_name = cell.get('line_name', '')
                    
                    # 遍历所有告警，尝试部分匹配
                    for alarm_cgi, alarms in alarm_data.items():
                        # 检查是否有部分匹配
                        partial_match = False
                        
                        # 检查小区名称
                        if celname:
                            # 宽松匹配：告警CGI中包含小区名称的任何部分
                            if any(part in alarm_cgi for part in celname.split() if part):
                                partial_match = True
                                logger.debug(f"小区名称部分匹配: {celname} 在 {alarm_cgi} 中")
                        
                        # 检查BBU名称
                        if not partial_match and bbu_name:
                            if bbu_name in alarm_cgi:
                                partial_match = True
                                logger.debug(f"BBU名称匹配: {bbu_name} 在 {alarm_cgi} 中")
                        
                        # 检查站点名称
                        if not partial_match and site_name:
                            if site_name in alarm_cgi:
                                partial_match = True
                                logger.debug(f"站点名称匹配: {site_name} 在 {alarm_cgi} 中")
                        
                        # 检查线路名称
                        if not partial_match and line_name:
                            if line_name in alarm_cgi:
                                partial_match = True
                                logger.debug(f"线路名称匹配: {line_name} 在 {alarm_cgi} 中")
                        
                        # 检查CGI的部分匹配（去掉分隔符后匹配）
                        if not partial_match:
                            # 移除CGI中的分隔符
                            cgi_no_dash = cgi.replace('-', '')
                            alarm_cgi_no_dash = alarm_cgi.replace('-', '')
                            # 检查是否有部分匹配
                            if len(cgi_no_dash) > 6 and cgi_no_dash in alarm_cgi_no_dash:
                                partial_match = True
                                logger.debug(f"CGI部分匹配: {cgi} 在 {alarm_cgi} 中")
                        
                        if partial_match:
                            # 匹配所有告警（不严格检查CPID）
                            matched_alarms = []
                            for alarm in alarms:
                                # 宽松匹配：如果有CPID则检查，否则直接匹配
                                alarm_cpid = alarm.get('extracted_cpid', '')
                                cpid_match = (not alarm_cpid or not cell_cpid_str or alarm_cpid == cell_cpid_str)

                                # 检查rru_id是否匹配（如果告警有matched_rru_id的话）
                                matched_rru_id = alarm.get('matched_rru_id', '')
                                rru_match = (not matched_rru_id or matched_rru_id == cell_rru_id)

                                if cpid_match and rru_match:
                                    matched_alarms.append(alarm)

                            if matched_alarms:
                                has_alarm = True
                                alarm_count = len(matched_alarms)
                                alarm_details = matched_alarms
                                logger.debug(f"部分匹配到告警: {alarm_cgi}, 告警数量={alarm_count}")
                                break
                
                # 3. 尝试网元ID匹配（从CGI中提取网元ID）
                if not has_alarm:
                    # 从CGI中提取网元ID（假设CGI格式为：460-00-网元ID-小区ID）
                    cgi_parts = cgi.split('-')
                    if len(cgi_parts) >= 3:
                        ne_id = cgi_parts[2]
                        # 遍历所有告警，尝试网元ID匹配
                        for alarm_cgi, alarms in alarm_data.items():
                            if ne_id in alarm_cgi:
                                matched_alarms = []
                                for alarm in alarms:
                                    # 检查是否是超级小区CP退服告警
                                    is_super_cell_cp_alarm = any(keyword in alarm.get('alarm_name', '') for keyword in ['超级小区CP退服', '超级小区CP退出服务'])
                                    # 检查是否是网元链路断告警
                                    is_ne_link_alarm = '网元链路断' in alarm.get('alarm_name', '')

                                    if is_super_cell_cp_alarm:
                                        # 超级小区CP退服告警需要检查CPID匹配
                                        alarm_cpid = alarm.get('extracted_cpid', '')
                                        if not alarm_cpid or not cell_cpid_str or alarm_cpid == cell_cpid_str:
                                            matched_alarms.append(alarm)
                                    elif is_ne_link_alarm:
                                        # 网元链路断告警匹配所有该网元下的小区，不检查rru_id
                                        matched_alarms.append(alarm)
                                    else:
                                        # 其他告警需要检查rru_id匹配（如果有的话）
                                        matched_rru_id = alarm.get('matched_rru_id', '')
                                        rru_match = (not matched_rru_id or matched_rru_id == cell_rru_id)
                                        if rru_match:
                                            matched_alarms.append(alarm)
                                
                                if matched_alarms:
                                    has_alarm = True
                                    alarm_count = len(matched_alarms)
                                    alarm_details = matched_alarms
                                    logger.debug(f"网元ID匹配到告警: NE_ID={ne_id}, 告警数量={alarm_count}")
                                    break
                
                # 判断健康状态
                status, reason = self._judge_health_status(
                    has_alarm
                )
                
                if status == 'healthy':
                    healthy_count += 1
                
                # 构建小区详情
                cell_detail = {
                    'id': cell.get('id'),
                    'line_name': cell.get('line_name'),
                    'site_name': cell.get('site_name'),
                    'area': cell.get('area'),
                    'site_type': cell.get('site_type'),
                    'bbu_name': cell.get('bbu_name'),
                    'celname': cell.get('celname'),
                    'cgi': cgi,
                    'network_type': network_type,
                    'lng': cell.get('lng'),
                    'lat': cell.get('lat'),
                    'high': cell.get('high'),
                    'ant_dir': cell.get('ant_dir'),
                    'cpId': cell.get('cpId'),
                    'cpId_key': cell.get('cpId_key'),
                    'rru_id_key': cell.get('rru_id_key'),
                    'rru_id': cell.get('rru_id'),
                    'rru_type': cell.get('rru_type'),
                    'status': status,
                    'reason': reason,
                    'has_alarm': has_alarm,
                    'alarm_count': alarm_count,
                    'alarm_details': alarm_details,
                    'check_time': check_time
                }
                
                checked_cells.append(cell_detail)
            
            # 计算统计数据
            total_count = len(checked_cells)
            unhealthy_count = total_count - healthy_count
            healthy_rate = round(healthy_count / total_count * 100, 2) if total_count > 0 else 0
            
            # 返回结果
            logger.info(
                "高铁小区体检完成: 总小区=%d, 健康=%d, 不健康=%d, 健康率=%.2f%%",
                total_count,
                healthy_count,
                unhealthy_count,
                healthy_rate,
            )
            return {
                'check_time': check_time,
                'total_cells': total_count,
                'healthy_cells': healthy_count,
                'unhealthy_cells': unhealthy_count,
                'healthy_rate': healthy_rate,
                'cells': checked_cells
            }
            
        except Exception as e:
            logger.error(f"高铁小区健康检查失败: {e}", exc_info=True)
            return {
                'error': str(e),
                'check_time': datetime.now()
            }
    
    def _get_performance_data(self, start_time, end_time, cells=None) -> Dict[str, Dict[str, Any]]:
        """获取性能指标数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            cells: 小区列表（可选，用于优化查询）
            
        Returns:
            以CGI为键的性能数据字典，包含流量和忙时利用率
        """
        import time
        try:
            performance_data = {}
            
            # 快速检查PostgreSQL连接是否可用
            if not self.pg:
                logger.info("PostgreSQL客户端未初始化，跳过性能数据查询")
                return performance_data
            
            # 测试PostgreSQL连接
            try:
                # 执行简单查询测试连接
                test_start = time.time()
                self.pg.fetch_one("SELECT 1")
                test_end = time.time()
                logger.info(f"PostgreSQL连接测试成功，耗时: {(test_end - test_start):.3f}秒")
            except Exception as e:
                logger.warning(f"PostgreSQL连接不可用: {e}")
                logger.info("跳过性能数据查询，避免连接超时")
                return performance_data
            
            # 测试表是否存在
            try:
                # 检查4G小时表是否存在
                test_start = time.time()
                self.pg.fetch_one("SELECT COUNT(*) FROM cell_4g_metrics_hour LIMIT 1")
                test_end = time.time()
                logger.info(f"cell_4g_metrics_hour 表存在，检查耗时: {(test_end - test_start):.3f}秒")
            except Exception as e:
                logger.warning(f"检查cell_4g_metrics_hour表失败: {e}")
                logger.info("尝试使用其他表查询性能数据")
                # 尝试检查其他可能的表
                try:
                    self.pg.fetch_one("SELECT COUNT(*) FROM cell_4g_metrics LIMIT 1")
                    logger.info("cell_4g_metrics 表存在")
                except Exception as e2:
                    logger.warning(f"检查cell_4g_metrics表失败: {e2}")
                    logger.info("无法找到性能数据表格，跳过查询")
                    return performance_data
            
            # 提取所有CGI（高铁小区可能存在重复 CGI，这里先在内存中去重，避免后续 SQL IN 列表重复放大）
            cgis = []
            cell_info_map = {}
            if cells:
                for cell in cells:
                    cgi = cell.get('CGI', '')
                    if cgi:
                        # 只保留每个 CGI 的第一条记录，后面的重复 CGI 不再加入查询列表
                        if cgi not in cell_info_map:
                            cgis.append(cgi)
                            cell_info_map[cgi] = cell
                        else:
                            # 已存在则仅覆盖映射（如果你希望以最后一条为准）
                            cell_info_map[cgi] = cell
            
            logger.info(f"提取到 {len(cgis)} 个小区的CGI")
            
            # 计算昨天和今天的开始时间（00:00:00）
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = today - timedelta(days=1)
            logger.info(f"使用时间窗口: 昨天 {yesterday} 到 今天 {end_time}")
            
            # 批量查询性能数据，避免生成过长的SQL语句
            if cgis:
                # 分离4G和5G小区
                cgis_4g = []
                cgis_5g = []
                
                for cgi in cgis:
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
                    else:
                        # 无法识别，尝试同时查询4G和5G
                        cgis_4g.append(cgi)
                        cgis_5g.append(cgi)
                
                # 再次按制式去重，避免同一 CGI 被同时判定为 4G/5G 或重复加入批次
                cgis_4g = list(dict.fromkeys(cgis_4g))
                cgis_5g = list(dict.fromkeys(cgis_5g))
                logger.info(f"分离完成: 4G小区 {len(cgis_4g)} 个，5G小区 {len(cgis_5g)} 个（已按 CGI 去重）")
                
                # 查询4G性能数据（使用小时表，增加匹配机会）
                if cgis_4g:
                    # 限制每次查询的小区数量，避免SQL过长
                    batch_size = 1000
                    total_4g_rows = 0
                    for i in range(0, len(cgis_4g), batch_size):
                        batch_cgis = cgis_4g[i:i+batch_size]
                        
                        # 使用参数化查询，避免SQL注入和过长SQL
                        placeholders = ','.join(['%s'] * len(batch_cgis))
                        # 同时查询cgi和cell_id字段，增加匹配机会
                        # 查询昨天的流量数据并汇总
                        sql_4g_yesterday = f"""
                            SELECT 
                                cgi,
                                cell_id,
                                SUM((COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0) AS total_traffic_gb
                            FROM cell_4g_metrics_hour
                            WHERE (cgi IN ({placeholders}) OR cell_id IN ({placeholders}))
                              AND start_time >= %s
                              AND start_time < %s
                            GROUP BY cgi, cell_id
                        """
                        params_yesterday = batch_cgis + batch_cgis + [yesterday, today]
                        
                        # 查询今天的流量数据并汇总
                        sql_4g_today = f"""
                            SELECT 
                                cgi,
                                cell_id,
                                SUM((COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0) AS total_traffic_gb
                            FROM cell_4g_metrics_hour
                            WHERE (cgi IN ({placeholders}) OR cell_id IN ({placeholders}))
                              AND start_time >= %s
                            GROUP BY cgi, cell_id
                        """
                        params_today = batch_cgis + batch_cgis + [today]
                        
                        try:
                            # 查询昨天的流量数据
                            query_start = time.time()
                            yesterday_rows = self.pg.fetch_all(sql_4g_yesterday, params_yesterday)
                            query_end = time.time()
                            logger.info(f"获取4G昨天流量数据批次 {i//batch_size + 1} 成功，返回 {len(yesterday_rows)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            # 处理昨天的流量数据
                            for row in yesterday_rows:
                                result_cgi = row.get('cgi') or row.get('cell_id')
                                if result_cgi:
                                    if result_cgi not in performance_data:
                                        performance_data[result_cgi] = {
                                            'traffic': 0.0,
                                            'yesterday_traffic': row.get('total_traffic_gb', 0.0),
                                            'today_traffic': 0.0,
                                            'yesterday_busy_hour_traffic': 0.0,
                                            'today_busy_hour_traffic': 0.0,
                                            'has_performance': True,
                                            'last_update': None
                                        }
                                    else:
                                        performance_data[result_cgi]['yesterday_traffic'] = row.get('total_traffic_gb', 0.0)
                                    logger.debug(f"添加4G昨天流量数据: CGI={result_cgi}, 流量={row.get('total_traffic_gb', 0.0):.2f}GB")
                            
                            # 查询今天的流量数据
                            query_start = time.time()
                            today_rows = self.pg.fetch_all(sql_4g_today, params_today)
                            query_end = time.time()
                            logger.info(f"获取4G今天流量数据批次 {i//batch_size + 1} 成功，返回 {len(today_rows)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            # 处理今天的流量数据
                            for row in today_rows:
                                result_cgi = row.get('cgi') or row.get('cell_id')
                                if result_cgi:
                                    if result_cgi not in performance_data:
                                        performance_data[result_cgi] = {
                                            'traffic': row.get('total_traffic_gb', 0.0),
                                            'yesterday_traffic': 0.0,
                                            'today_traffic': row.get('total_traffic_gb', 0.0),
                                            'yesterday_busy_hour_traffic': 0.0,
                                            'today_busy_hour_traffic': 0.0,
                                            'has_performance': True,
                                            'last_update': None
                                        }
                                    else:
                                        performance_data[result_cgi]['traffic'] = row.get('total_traffic_gb', 0.0)
                                        performance_data[result_cgi]['today_traffic'] = row.get('total_traffic_gb', 0.0)
                                    logger.debug(f"添加4G今天流量数据: CGI={result_cgi}, 流量={row.get('total_traffic_gb', 0.0):.2f}GB")
                        except Exception as e:
                            logger.warning(f"查询4G性能数据失败: {e}")
                            import traceback
                            traceback.print_exc()
                    logger.info(f"4G性能数据查询完成，共获取 {total_4g_rows} 条记录")
                
                # 查询5G性能数据（使用小时表，增加匹配机会）
                if cgis_5g:
                    # 限制每次查询的小区数量，避免SQL过长
                    batch_size = 1000
                    total_5g_rows = 0
                    for i in range(0, len(cgis_5g), batch_size):
                        batch_cgis = cgis_5g[i:i+batch_size]
                        
                        # 使用参数化查询，避免SQL注入和过长SQL
                        placeholders = ','.join(['%s'] * len(batch_cgis))
                        
                        # 查询昨天的5G流量数据并汇总
                        sql_5g_yesterday = f"""
                            SELECT 
                                "Ncgi" as cgi,
                                SUM((COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0) AS total_traffic_gb
                            FROM cell_5g_metrics_hour
                            WHERE "Ncgi" IN ({placeholders})
                              AND start_time >= %s
                              AND start_time < %s
                            GROUP BY "Ncgi"
                        """
                        params_5g_yesterday = batch_cgis + [yesterday, today]
                        
                        # 查询今天的5G流量数据并汇总
                        sql_5g_today = f"""
                            SELECT 
                                "Ncgi" as cgi,
                                SUM((COALESCE("RLC_UpOctUl", 0) + COALESCE("RLC_UpOctDl", 0)) / 1000.0 / 1000.0) AS total_traffic_gb
                            FROM cell_5g_metrics_hour
                            WHERE "Ncgi" IN ({placeholders})
                              AND start_time >= %s
                            GROUP BY "Ncgi"
                        """
                        params_5g_today = batch_cgis + [today]
                        
                        try:
                            # 查询昨天的5G流量数据
                            query_start = time.time()
                            yesterday_rows = self.pg.fetch_all(sql_5g_yesterday, params_5g_yesterday)
                            query_end = time.time()
                            logger.info(f"获取5G昨天流量数据批次 {i//batch_size + 1} 成功，返回 {len(yesterday_rows)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            # 处理昨天的5G流量数据
                            for row in yesterday_rows:
                                cgi = row.get('cgi', '')
                                if cgi:
                                    if cgi not in performance_data:
                                        performance_data[cgi] = {
                                            'traffic': 0.0,
                                            'yesterday_traffic': row.get('total_traffic_gb', 0.0),
                                            'today_traffic': 0.0,
                                            'yesterday_busy_hour_traffic': 0.0,
                                            'today_busy_hour_traffic': 0.0,
                                            'has_performance': True,
                                            'last_update': None
                                        }
                                    else:
                                        performance_data[cgi]['yesterday_traffic'] = row.get('total_traffic_gb', 0.0)
                                    logger.debug(f"添加5G昨天流量数据: CGI={cgi}, 流量={row.get('total_traffic_gb', 0.0):.2f}GB")
                            
                            # 查询今天的5G流量数据
                            query_start = time.time()
                            today_rows = self.pg.fetch_all(sql_5g_today, params_5g_today)
                            query_end = time.time()
                            logger.info(f"获取5G今天流量数据批次 {i//batch_size + 1} 成功，返回 {len(today_rows)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            # 处理今天的5G流量数据
                            for row in today_rows:
                                cgi = row.get('cgi', '')
                                if cgi:
                                    if cgi not in performance_data:
                                        performance_data[cgi] = {
                                            'traffic': row.get('total_traffic_gb', 0.0),
                                            'yesterday_traffic': 0.0,
                                            'today_traffic': row.get('total_traffic_gb', 0.0),
                                            'yesterday_busy_hour_traffic': 0.0,
                                            'today_busy_hour_traffic': 0.0,
                                            'has_performance': True,
                                            'last_update': None
                                        }
                                    else:
                                        performance_data[cgi]['traffic'] = row.get('total_traffic_gb', 0.0)
                                        performance_data[cgi]['today_traffic'] = row.get('total_traffic_gb', 0.0)
                                    logger.debug(f"添加5G今天流量数据: CGI={cgi}, 流量={row.get('total_traffic_gb', 0.0):.2f}GB")
                        except Exception as e:
                            logger.warning(f"查询5G性能数据失败: {e}")
                            import traceback
                            traceback.print_exc()
                    logger.info(f"5G性能数据查询完成，共获取 {total_5g_rows} 条记录")
                
                # 查询4G忙时利用率
                if cgis_4g:
                    batch_size = 1000
                    total_4g_busy_rows = 0
                    for i in range(0, len(cgis_4g), batch_size):
                        batch_cgis = cgis_4g[i:i+batch_size]
                        placeholders = ','.join(['%s'] * len(batch_cgis))
                        
                        # 计算昨天和今天的日期
                        today_date = datetime.now().date()
                        yesterday_date = today_date - timedelta(days=1)
                        
                        logger.info(f"查询4G忙时利用率，批次 {i//batch_size + 1}，小区数: {len(batch_cgis)}")
                        
                        # 昨天忙时利用率
                        sql_4g_yesterday = f"""
                            WITH hourly_data AS (
                                SELECT 
                                    cgi,
                                    cell_id,
                                    start_time,
                                    "dl_prb_utilization",
                                    "ul_prb_utilization",
                                    GREATEST(COALESCE("dl_prb_utilization", 0), COALESCE("ul_prb_utilization", 0)) AS max_prb_util,
                                    (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) AS total_traffic
                                FROM cell_4g_metrics_hour
                                WHERE cgi IN ({placeholders})
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
                                hd.max_prb_util,
                                hd.total_traffic / 1000.0 / 1000.0 AS busy_hour_traffic_gb
                            FROM hourly_data hd
                            JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.cell_id = mth.cell_id AND hd.total_traffic = mth.max_traffic
                        """
                        
                        params_4g_yesterday = batch_cgis + [yesterday_date]
                        try:
                            query_start = time.time()
                            yesterday_results = self.pg.fetch_all(sql_4g_yesterday, params_4g_yesterday)
                            query_end = time.time()
                            total_4g_busy_rows += len(yesterday_results)
                            logger.info(f"获取4G昨天忙时利用率批次成功，返回 {len(yesterday_results)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            for row in yesterday_results:
                                row_cgi = row.get('cgi') or row.get('cell_id')
                                if row_cgi:
                                    if row_cgi not in performance_data:
                                        performance_data[row_cgi] = {'traffic': 0.0, 'has_performance': False}
                                    performance_data[row_cgi]['yesterday_busy_hour_util'] = float(row.get('max_prb_util', 0))
                                    performance_data[row_cgi]['yesterday_busy_hour_traffic'] = float(row.get('busy_hour_traffic_gb', 0.0))
                                    logger.debug(f"添加4G昨天忙时利用率和流量: CGI={row_cgi}, 利用率={float(row.get('max_prb_util', 0)):.2f}%, 流量={float(row.get('busy_hour_traffic_gb', 0.0)):.2f}GB")
                        except Exception as e:
                            logger.warning(f"查询4G昨天忙时利用率失败: {e}")
                            import traceback
                            traceback.print_exc()
                        
                        # 今天忙时利用率
                        sql_4g_today = f"""
                            WITH hourly_data AS (
                                SELECT 
                                    cgi,
                                    cell_id,
                                    start_time,
                                    "dl_prb_utilization",
                                    "ul_prb_utilization",
                                    GREATEST(COALESCE("dl_prb_utilization", 0), COALESCE("ul_prb_utilization", 0)) AS max_prb_util,
                                    (COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) AS total_traffic
                                FROM cell_4g_metrics_hour
                                WHERE cgi IN ({placeholders})
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
                                hd.max_prb_util,
                                hd.total_traffic / 1000.0 / 1000.0 AS busy_hour_traffic_gb
                            FROM hourly_data hd
                            JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.cell_id = mth.cell_id AND hd.total_traffic = mth.max_traffic
                        """
                        
                        params_4g_today = batch_cgis + [today_date]
                        try:
                            query_start = time.time()
                            today_results = self.pg.fetch_all(sql_4g_today, params_4g_today)
                            query_end = time.time()
                            total_4g_busy_rows += len(today_results)
                            logger.info(f"获取4G今天忙时利用率批次成功，返回 {len(today_results)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            for row in today_results:
                                row_cgi = row.get('cgi') or row.get('cell_id')
                                if row_cgi:
                                    if row_cgi not in performance_data:
                                        performance_data[row_cgi] = {'traffic': 0.0, 'has_performance': False}
                                    performance_data[row_cgi]['today_busy_hour_util'] = float(row.get('max_prb_util', 0))
                                    performance_data[row_cgi]['today_busy_hour_traffic'] = float(row.get('busy_hour_traffic_gb', 0.0))
                                    logger.debug(f"添加4G今天忙时利用率和流量: CGI={row_cgi}, 利用率={float(row.get('max_prb_util', 0)):.2f}%, 流量={float(row.get('busy_hour_traffic_gb', 0.0)):.2f}GB")
                        except Exception as e:
                            logger.warning(f"查询4G今天忙时利用率失败: {e}")
                            import traceback
                            traceback.print_exc()
                    logger.info(f"4G忙时利用率查询完成，共获取 {total_4g_busy_rows} 条记录")
                
                # 查询5G忙时利用率
                if cgis_5g:
                    batch_size = 1000
                    total_5g_busy_rows = 0
                    for i in range(0, len(cgis_5g), batch_size):
                        batch_cgis = cgis_5g[i:i+batch_size]
                        placeholders = ','.join(['%s'] * len(batch_cgis))
                        
                        # 计算昨天和今天的日期
                        today_date = datetime.now().date()
                        yesterday_date = today_date - timedelta(days=1)
                        
                        logger.info(f"查询5G忙时利用率，批次 {i//batch_size + 1}，小区数: {len(batch_cgis)}")
                        
                        # 昨天忙时利用率
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
                                WHERE "Ncgi" IN ({placeholders})
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
                                hd.max_prb_util,
                                hd.total_traffic / 1000.0 / 1000.0 AS busy_hour_traffic_gb
                            FROM hourly_data hd
                            JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.total_traffic = mth.max_traffic
                        """
                        
                        params_5g_yesterday = batch_cgis + [yesterday_date]
                        try:
                            query_start = time.time()
                            yesterday_results = self.pg.fetch_all(sql_5g_yesterday, params_5g_yesterday)
                            query_end = time.time()
                            total_5g_busy_rows += len(yesterday_results)
                            logger.info(f"获取5G昨天忙时利用率批次成功，返回 {len(yesterday_results)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            for row in yesterday_results:
                                cgi = row.get('cgi', '')
                                if cgi:
                                    if cgi not in performance_data:
                                        performance_data[cgi] = {'traffic': 0.0, 'has_performance': False}
                                    performance_data[cgi]['yesterday_busy_hour_util'] = float(row.get('max_prb_util', 0))
                                    performance_data[cgi]['yesterday_busy_hour_traffic'] = float(row.get('busy_hour_traffic_gb', 0.0))
                                    logger.debug(f"添加5G昨天忙时利用率和流量: CGI={cgi}, 利用率={float(row.get('max_prb_util', 0)):.2f}%, 流量={float(row.get('busy_hour_traffic_gb', 0.0)):.2f}GB")
                        except Exception as e:
                            logger.warning(f"查询5G昨天忙时利用率失败: {e}")
                            import traceback
                            traceback.print_exc()
                        
                        # 今天忙时利用率
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
                                WHERE "Ncgi" IN ({placeholders})
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
                                hd.max_prb_util,
                                hd.total_traffic / 1000.0 / 1000.0 AS busy_hour_traffic_gb
                            FROM hourly_data hd
                            JOIN max_traffic_hours mth ON hd.cgi = mth.cgi AND hd.total_traffic = mth.max_traffic
                        """
                        
                        params_5g_today = batch_cgis + [today_date]
                        try:
                            query_start = time.time()
                            today_results = self.pg.fetch_all(sql_5g_today, params_5g_today)
                            query_end = time.time()
                            total_5g_busy_rows += len(today_results)
                            logger.info(f"获取5G今天忙时利用率批次成功，返回 {len(today_results)} 条记录，耗时: {(query_end - query_start):.3f}秒")
                            
                            for row in today_results:
                                cgi = row.get('cgi', '')
                                if cgi:
                                    if cgi not in performance_data:
                                        performance_data[cgi] = {'traffic': 0.0, 'has_performance': False}
                                    performance_data[cgi]['today_busy_hour_util'] = float(row.get('max_prb_util', 0))
                                    performance_data[cgi]['today_busy_hour_traffic'] = float(row.get('busy_hour_traffic_gb', 0.0))
                                    logger.debug(f"添加5G今天忙时利用率和流量: CGI={cgi}, 利用率={float(row.get('max_prb_util', 0)):.2f}%, 流量={float(row.get('busy_hour_traffic_gb', 0.0)):.2f}GB")
                        except Exception as e:
                            logger.warning(f"查询5G今天忙时利用率失败: {e}")
                            import traceback
                            traceback.print_exc()
                    logger.info(f"5G忙时利用率查询完成，共获取 {total_5g_busy_rows} 条记录")
            
            # 确保所有小区都有性能数据记录
            logger.info(f"处理小区性能数据映射，总小区数: {len(cell_info_map)}")
            for cgi in cell_info_map:
                if cgi not in performance_data:
                    performance_data[cgi] = {
                        'traffic': 0.0,
                        'yesterday_traffic': 0.0,
                        'today_traffic': 0.0,
                        'yesterday_busy_hour_traffic': 0.0,
                        'today_busy_hour_traffic': 0.0,
                        'has_performance': False,
                        'yesterday_busy_hour_util': 0.0,
                        'today_busy_hour_util': 0.0
                    }
                    logger.debug(f"添加默认性能数据: CGI={cgi}, 无性能数据")
                else:
                    # 确保所有字段都存在
                    if 'has_performance' not in performance_data[cgi]:
                        performance_data[cgi]['has_performance'] = False
                    if 'yesterday_traffic' not in performance_data[cgi]:
                        performance_data[cgi]['yesterday_traffic'] = 0.0
                    if 'today_traffic' not in performance_data[cgi]:
                        performance_data[cgi]['today_traffic'] = 0.0
                    if 'yesterday_busy_hour_traffic' not in performance_data[cgi]:
                        performance_data[cgi]['yesterday_busy_hour_traffic'] = 0.0
                    if 'today_busy_hour_traffic' not in performance_data[cgi]:
                        performance_data[cgi]['today_busy_hour_traffic'] = 0.0
                    if 'yesterday_busy_hour_util' not in performance_data[cgi]:
                        performance_data[cgi]['yesterday_busy_hour_util'] = 0.0
                    if 'today_busy_hour_util' not in performance_data[cgi]:
                        performance_data[cgi]['today_busy_hour_util'] = 0.0
                    logger.debug(f"小区 {cgi} 性能数据完整: {performance_data[cgi]}")
            
            # 统计性能数据匹配情况
            has_perf_count = sum(1 for data in performance_data.values() if data.get('has_performance', False))
            traffic_gt_zero_count = sum(1 for data in performance_data.values() if data.get('traffic', 0.0) > 0)
            has_busy_hour_count = sum(1 for data in performance_data.values() if data.get('yesterday_busy_hour_util', 0.0) > 0 or data.get('today_busy_hour_util', 0.0) > 0)
            
            logger.info(f"性能数据查询完成，共处理 {len(performance_data)} 个小区")
            logger.info(f"有性能数据的小区数: {has_perf_count}")
            logger.info(f"流量大于0的小区数: {traffic_gt_zero_count}")
            logger.info(f"有忙时利用率数据的小区数: {has_busy_hour_count}")
            
            return performance_data
            
        except Exception as e:
            logger.error(f"获取性能数据失败: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_alarm_data(self, cells=None) -> Dict[str, List[Dict[str, Any]]]:
        """获取告警数据（参考网格小区匹配告警和超级小区CP退服的匹配规则）
        
        Args:
            cells: 小区列表（可选，用于更准确的告警匹配）
            
        Returns:
            以CGI为键的告警数据字典
        """
        try:
            alarm_data = {}
            
            # 从CGI中提取网元ID，建立网元ID到CGI的映射（参考网格小区匹配规则）
            ne_id_to_cgis = {}  # {ne_id: [cgi1, cgi2, ...]}
            celname_to_cgi = {}  # {celname: cgi} 用于精确匹配
            cpid_to_cgis = {}  # {cpId: [cgi1, cgi2, ...]} 用于超级小区CP退服匹配
            cgi_to_cell = {}  # {cgi: cell} 用于快速查找小区信息
            rru_id_to_cgis = {}  # {rru_id: [cgi1, cgi2, ...]} 用于RRU ID匹配
            
            if cells:
                for cell in cells:
                    cgi = cell.get('CGI', '')
                    celname = cell.get('celname', '')
                    cell_cpid = cell.get('cpId', '')
                    cell_rru_id = str(cell.get('rru_id', ''))
                    
                    # 建立小区名称到CGI的映射
                    if celname:
                        celname_to_cgi[celname] = cgi
                    
                    # 建立CPID到CGI的映射
                    if cell_cpid:
                        cpid_str = str(cell_cpid)
                        if cpid_str not in cpid_to_cgis:
                            cpid_to_cgis[cpid_str] = []
                        cpid_to_cgis[cpid_str].append(cgi)
                    
                    # 从CGI中提取网元ID
                    cgi_parts = cgi.split('-')
                    if len(cgi_parts) >= 3:
                        ne_id = cgi_parts[2]
                        if ne_id not in ne_id_to_cgis:
                            ne_id_to_cgis[ne_id] = []
                        ne_id_to_cgis[ne_id].append(cgi)
                    
                    # 建立CGI到小区的映射
                    if cgi:
                        cgi_to_cell[cgi] = cell
                    
                    # 建立RRU ID到CGI的映射
                    if cell_rru_id:
                        if cell_rru_id not in rru_id_to_cgis:
                            rru_id_to_cgis[cell_rru_id] = []
                        rru_id_to_cgis[cell_rru_id].append(cgi)
            
            # 定义影响性能的告警类型（参考网格小区匹配规则）
            performance_alarm_types = [
                '小区退服', '小区退出服务', 'LTE小区退出服务', '小区不可用', '传输中断', '传输故障', '硬件故障',
                '板卡故障', '光模块故障', 'RRU故障', 'RRU链路断', 'RRU断链', '天馈故障', '驻波比',
                '功率异常', '时钟失步', '同步失步', '超级小区CP退服', '超级小区CP退出服务',
                '网元断链', '网元链路断', '网元离线', '基站退服', '基站离线', 'gnb断链',
                '电源断', '电源故障', '断电', '供电异常', '电源中断'
            ]
            
            # 构建告警类型的SQL条件（使用更高效的查询方式）
            # 使用IN子句和LIKE组合，减少OR条件的使用
            try:
                # 只选择必要的字段，减少数据传输，查询所有广湛相关告警
                sql = """
                    SELECT 
                        alarm_code_name, 
                        alarm_title, 
                        alarm_level, 
                        occur_time, 
                        alarm_reason, 
                        ne_id, 
                        alarm_object_name, 
                        additional_info
                    FROM cur_alarm
                    WHERE site_name LIKE '%GZ%'
                    ORDER BY occur_time DESC
                """
                all_alarms = self.mysql.fetch_all(sql)
                
                # 在Python端过滤影响性能的告警
                alarms_zte = []
                for alarm in all_alarms:
                    alarm_name = alarm.get('alarm_code_name', '') or alarm.get('alarm_title', '')
                    alarm_reason = alarm.get('alarm_reason', '')
                    
                    # 检查是否是影响性能的告警类型
                    is_performance_alarm = any(keyword in (alarm_name + alarm_reason) for keyword in performance_alarm_types)
                    if is_performance_alarm:
                        alarms_zte.append(alarm)
                
                logger.info(f"获取到 {len(alarms_zte)} 条中兴影响性能的告警")
                
                for alarm in alarms_zte:
                    alarm_name = alarm.get('alarm_code_name', '') or alarm.get('alarm_title', '')
                    alarm_level = alarm.get('alarm_level', '')
                    alarm_time = alarm.get('occur_time', '')
                    alarm_desc = alarm.get('alarm_reason', '')  # 使用alarm_reason字段
                    ne_id = str(alarm.get('ne_id', ''))
                    alarm_object_name = alarm.get('alarm_object_name', '')
                    additional_info = alarm.get('additional_info', '')  # 获取附加信息字段

                    # 提取CPID（用于超级小区CP退服匹配）
                    extracted_cpid = None
                    import re
                    if additional_info and ('CPID' in str(additional_info) or 'CP ID' in str(additional_info)):
                        match = re.search(r'(?:CPID|CP ID)[:：]\s*(\d+)', str(additional_info))
                        if match:
                            extracted_cpid = match.group(1)
                    if not extracted_cpid and ('CPID' in str(alarm_desc) or 'CP ID' in str(alarm_desc)):
                        match = re.search(r'(?:CPID|CP ID)[:：]\s*(\d+)', str(alarm_desc))
                        if match:
                            extracted_cpid = match.group(1)
                    
                    # 提取逻辑小区ID
                    extracted_cgi = None
                    if additional_info and '逻辑小区ID' in str(additional_info):
                        match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(additional_info))
                        if match:
                            extracted_cgi = match.group(1)
                    if not extracted_cgi and '逻辑小区ID' in str(alarm_desc):
                        match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(alarm_desc))
                        if match:
                            extracted_cgi = match.group(1)

                    # 提取RRU相关信息
                    extracted_rack = None  # RRU ID
                    extracted_gnb_id = None  # 5G网元ID
                    extracted_enb_id = None  # 4G网元ID

                    if additional_info:
                        # 提取rack（RRU ID）
                        rack_match = re.search(r'rack=(\d+)', str(additional_info))
                        if rack_match:
                            extracted_rack = rack_match.group(1)
                            logger.debug(f"提取到rack: {extracted_rack}")

                        # 提取gNBId（5G网元ID），支持"gNBId:123"和"NR gNBId:123"格式
                        gnb_match = re.search(r'(?:NR\s*)?gNBId:(\d+)', str(additional_info))
                        if gnb_match:
                            extracted_gnb_id = gnb_match.group(1)
                            logger.debug(f"提取到gNBId: {extracted_gnb_id}")

                        # 提取eNBId（4G网元ID）
                        enb_match = re.search(r'eNBId:(\d+)', str(additional_info))
                        if enb_match:
                            extracted_enb_id = enb_match.group(1)
                            logger.debug(f"提取到eNBId: {extracted_enb_id}")
                    
                    # 从告警描述中提取信息
                    if alarm_desc:
                        # 从告警描述中提取逻辑小区ID
                        if not extracted_cgi:
                            cgi_match = re.search(r'逻辑小区ID[:：]\s*([\d\-]+)', str(alarm_desc))
                            if cgi_match:
                                extracted_cgi = cgi_match.group(1)
                                logger.debug(f"从告警描述中提取到逻辑小区ID: {extracted_cgi}")
                        
                        # 从告警描述中提取CPID
                        if not extracted_cpid:
                            cpid_match = re.search(r'CPID[:：]\s*(\d+)', str(alarm_desc))
                            if cpid_match:
                                extracted_cpid = cpid_match.group(1)
                                logger.debug(f"从告警描述中提取到CPID: {extracted_cpid}")
                        
                        # 从告警描述中提取gNBId
                        if not extracted_gnb_id:
                            gnb_match = re.search(r'(?:NR\s*)?gNBId:(\d+)', str(alarm_desc))
                            if gnb_match:
                                extracted_gnb_id = gnb_match.group(1)
                                logger.debug(f"从告警描述中提取到gNBId: {extracted_gnb_id}")
                        
                        # 从告警描述中提取rack
                        if not extracted_rack:
                            rack_match = re.search(r'rack=(\d+)', str(alarm_desc))
                            if rack_match:
                                extracted_rack = rack_match.group(1)
                                logger.debug(f"从告警描述中提取到rack: {extracted_rack}")
                    
                    # 按优先级顺序尝试匹配告警（串行匹配）
                    alarm_matched = False
                    
                    # 1. 超级小区CP退服告警匹配（最高优先级）
                    if not alarm_matched and ('超级小区CP退服' in alarm_name or '超级小区CP退出服务' in alarm_name) and extracted_cpid and extracted_cgi:
                        # 直接通过CGI查找小区
                        if extracted_cgi in cgi_to_cell:
                            cell = cgi_to_cell[extracted_cgi]
                            cell_cpid = str(cell.get('cpId', ''))
                            if cell_cpid == extracted_cpid:
                                if extracted_cgi not in alarm_data:
                                    alarm_data[extracted_cgi] = []
                                # 检查告警是否已经存在
                                alarm_exists = any(
                                    a.get('alarm_name') == alarm_name and
                                    a.get('alarm_time') == alarm_time and
                                    a.get('extracted_cpid') == extracted_cpid
                                    for a in alarm_data[extracted_cgi]
                                )
                                if not alarm_exists:
                                    alarm_data[extracted_cgi].append({
                                        'alarm_name': alarm_name,
                                        'alarm_level': alarm_level,
                                        'alarm_time': alarm_time,
                                        'alarm_desc': alarm_desc,
                                        'vendor': '中兴',
                                        'extracted_cpid': extracted_cpid,
                                        'extracted_cgi': extracted_cgi,
                                        'alarm_object_name': alarm_object_name
                                    })
                                    alarm_matched = True
            
                    # 2. 逻辑小区ID匹配（第二优先级）
                    if not alarm_matched and extracted_cgi and extracted_cgi in cgi_to_cell:
                        cgi = extracted_cgi
                        if cgi not in alarm_data:
                            alarm_data[cgi] = []
                        alarm_exists = any(a.get('alarm_name') == alarm_name and a.get('alarm_time') == alarm_time for a in alarm_data[cgi])
                        if not alarm_exists:
                            alarm_data[cgi].append({
                                'alarm_name': alarm_name,
                                'alarm_level': alarm_level,
                                'alarm_time': alarm_time,
                                'alarm_desc': alarm_desc,
                                'vendor': '中兴',
                                'extracted_cpid': extracted_cpid,
                                'alarm_object_name': alarm_object_name
                            })
                            alarm_matched = True
            
                    # 3. RRU级别告警匹配（第三优先级）
                    if not alarm_matched and extracted_rack:
                        # 使用RRU ID到CGI的映射快速查找
                        if extracted_rack in rru_id_to_cgis:
                            for cgi in rru_id_to_cgis[extracted_rack]:
                                cell = cgi_to_cell.get(cgi)
                                if cell:
                                    # 检查网元ID匹配
                                    cgi_ne_id = None
                                    cgi_parts = cgi.split('-')
                                    if len(cgi_parts) >= 3:
                                        cgi_ne_id = cgi_parts[2]
                                    
                                    # 检查网元ID是否匹配
                                    ne_matched = False
                                    if extracted_gnb_id and cgi_ne_id == extracted_gnb_id:
                                        ne_matched = True
                                    if extracted_enb_id and cgi_ne_id == extracted_enb_id:
                                        ne_matched = True
                                    
                                    if ne_matched:
                                        if cgi not in alarm_data:
                                            alarm_data[cgi] = []
                                        # 检查告警是否已经存在
                                        alarm_exists = any(a.get('alarm_name') == alarm_name and a.get('alarm_time') == alarm_time for a in alarm_data[cgi])
                                        if not alarm_exists:
                                            alarm_data[cgi].append({
                                                'alarm_name': alarm_name,
                                                'alarm_level': alarm_level,
                                                'alarm_time': alarm_time,
                                                'alarm_desc': alarm_desc,
                                                'vendor': '中兴',
                                                'extracted_cpid': extracted_cpid,
                                                'extracted_cgi': extracted_cgi,
                                                'extracted_rack': extracted_rack,
                                                'matched_rru_id': extracted_rack,
                                                'alarm_object_name': alarm_object_name
                                            })
                                            alarm_matched = True
                                            break  # 只匹配第一个RRU对应的小区
            
                    # 4. 告警对象名称匹配（第四优先级）
                    if not alarm_matched and alarm_object_name:
                        # 快速查找小区名称匹配
                        for celname, cgi in celname_to_cgi.items():
                            if celname in alarm_object_name or (alarm_object_name in celname and len(alarm_object_name) >= 5):
                                if cgi not in alarm_data:
                                    alarm_data[cgi] = []
                                alarm_exists = any(a.get('alarm_name') == alarm_name and a.get('alarm_time') == alarm_time for a in alarm_data[cgi])
                                if not alarm_exists:
                                    alarm_data[cgi].append({
                                        'alarm_name': alarm_name,
                                        'alarm_level': alarm_level,
                                        'alarm_time': alarm_time,
                                        'alarm_desc': alarm_desc,
                                        'vendor': '中兴',
                                        'extracted_cpid': extracted_cpid,
                                        'extracted_cgi': extracted_cgi,
                                        'alarm_object_name': alarm_object_name
                                    })
                                    alarm_matched = True
                                    break  # 只匹配第一个名称对应的小区
            
                    # 5. CPID匹配（对于RRU断链等影响多个小区的告警）（第五优先级）
                    if not alarm_matched and extracted_cpid:
                        # 查找所有使用相同CPID的小区
                        if extracted_cpid in cpid_to_cgis:
                            for cgi in cpid_to_cgis[extracted_cpid]:
                                # 只匹配尚未匹配到的小区
                                if cgi not in alarm_data:
                                    # 检查网元ID是否匹配
                                    cgi_ne_id = None
                                    cgi_parts = cgi.split('-')
                                    if len(cgi_parts) >= 3:
                                        cgi_ne_id = cgi_parts[2]
                                    
                                    # 检查网元ID是否匹配
                                    ne_matched = False
                                    if extracted_gnb_id and cgi_ne_id == extracted_gnb_id:
                                        ne_matched = True
                                    if extracted_enb_id and cgi_ne_id == extracted_enb_id:
                                        ne_matched = True
                                    if not extracted_gnb_id and not extracted_enb_id:
                                        # 如果没有提取到网元ID，则直接匹配
                                        ne_matched = True
                                    
                                    if ne_matched:
                                        if cgi not in alarm_data:
                                            alarm_data[cgi] = []
                                        # 检查告警是否已经存在
                                        alarm_exists = any(a.get('alarm_name') == alarm_name and a.get('alarm_time') == alarm_time for a in alarm_data[cgi])
                                        if not alarm_exists:
                                            alarm_data[cgi].append({
                                                'alarm_name': alarm_name,
                                                'alarm_level': alarm_level,
                                                'alarm_time': alarm_time,
                                                'alarm_desc': alarm_desc,
                                                'vendor': '中兴',
                                                'extracted_cpid': extracted_cpid,
                                                'extracted_cgi': extracted_cgi,
                                                'alarm_object_name': alarm_object_name
                                            })
                                            alarm_matched = True
                                            # 对于CPID匹配，不使用break，因为一个CPID可能对应多个小区
            
                    # 6. 网元ID匹配（最低优先级）
                    if not alarm_matched and ne_id and not ('超级小区CP退服' in alarm_name or '超级小区CP退出服务' in alarm_name) and not extracted_rack:
                        # 使用网元ID到CGI的映射快速查找
                        if ne_id in ne_id_to_cgis:
                            for cgi in ne_id_to_cgis[ne_id]:
                                if cgi not in alarm_data:
                                    alarm_data[cgi] = []
                                alarm_exists = any(a.get('alarm_name') == alarm_name and a.get('alarm_time') == alarm_time for a in alarm_data[cgi])
                                if not alarm_exists:
                                    alarm_data[cgi].append({
                                        'alarm_name': alarm_name,
                                        'alarm_level': alarm_level,
                                        'alarm_time': alarm_time,
                                        'alarm_desc': alarm_desc,
                                        'vendor': '中兴',
                                        'extracted_cpid': extracted_cpid,
                                        'alarm_object_name': alarm_object_name
                                    })
                                    alarm_matched = True
                                    # 对于网元ID匹配，不使用break，因为一个网元可能对应多个小区
                    
                    if not alarm_matched:
                        logger.debug(f"告警未匹配到小区: {alarm_name}, 对象: {alarm_object_name}")
                
                # 统计匹配情况
                matched_count = 0
                for cgi, alarms in alarm_data.items():
                    if alarms:
                        matched_count += 1
                
                logger.info(f"成功处理 {len(alarms_zte)} 条中兴告警，匹配到 {matched_count} 个小区")
            except Exception as e:
                logger.warning(f"查询中兴告警失败: {e}")
                import traceback
                traceback.print_exc()
            
            return alarm_data
            
        except Exception as e:
            logger.error(f"获取告警数据失败: {e}", exc_info=True)
            return {}
    
    def _judge_health_status(self, has_alarm: bool) -> tuple:
        """判断小区健康状态
        
        Args:
            has_alarm: 是否有告警
            
        Returns:
            (status, reason) 元组，status为'healthy'或'unhealthy'，reason为原因
        """
        if has_alarm:
            return 'unhealthy', '有告警'
        
        return 'healthy', '正常'
    
    def check_hsr_line_health(self, line_name: str) -> Dict[str, Any]:
        """检查指定高铁线路的小区健康状态
        
        Args:
            line_name: 高铁线路名称
            
        Returns:
            体检结果
        """
        try:
            # 1. 获取指定线路的所有小区
            cells_sql = """
                SELECT 
                    id,
                    line_name,
                    Transmitting_Point_Name as site_name,
                    area,
                    site_type,
                    bbu_name,
                    celname,
                    CGI,
                    lng,
                    lat,
                    high,
                    ant_dir,
                    zhishi as network_type,
                    cpId,
                    cpId_key,
                    rru_id_key,
                    rru_id,
                    rru_type
                FROM hsr_info
                WHERE line_name = %s
                ORDER BY site_name, celname
            """
            cells = self.mysql.fetch_all(cells_sql, (line_name,))
            
            if not cells:
                return {
                    'error': f'没有找到线路 {line_name} 的小区数据',
                    'check_time': datetime.now()
                }
            
            # 2. 获取当前时间
            check_time = datetime.now()
            logger.info(f"开始高铁线路 {line_name} 小区体检，本次共 {len(cells)} 个小区，检查时间: {check_time}")
            
            # 3. 获取告警数据（参考网格小区匹配告警和超级小区CP退服的匹配规则）
            alarm_data = self._get_alarm_data(cells)
            
            # 4. 检查每个小区的健康状态
            checked_cells = []
            healthy_count = 0
            
            for cell in cells:
                cgi = cell.get('CGI', '')
                network_type = cell.get('network_type', '')
                
                # 详细日志
                logger.debug(
                    "小区 %s 开始检查告警状态",
                    cgi
                )
                
                # 获取告警数据
                has_alarm = False
                alarm_count = 0
                alarm_details = []

                # 获取小区的CPID和rru_id
                cell_cpid = cell.get('cpId', '')
                cell_cpid_str = str(cell_cpid) if cell_cpid is not None else ''
                cell_rru_id = str(cell.get('rru_id', ''))

                # 1. 尝试直接匹配（同时考虑CGI、CPID和rru_id）
                if cgi in alarm_data:
                    matched_alarms = []
                    for alarm in alarm_data[cgi]:
                        # 检查CPID是否匹配（如果有CPID的话）
                        alarm_cpid = alarm.get('extracted_cpid', '')
                        cpid_match = (not alarm_cpid or not cell_cpid_str or alarm_cpid == cell_cpid_str)

                        # 检查rru_id是否匹配（如果告警有matched_rru_id的话）
                        matched_rru_id = alarm.get('matched_rru_id', '')
                        rru_match = (not matched_rru_id or matched_rru_id == cell_rru_id)

                        logger.info(f"[告警分配调试] CGI={cgi}, cell_rru_id={cell_rru_id}, alarm={alarm.get('alarm_name', '')}, matched_rru_id={matched_rru_id}, cpid_match={cpid_match}, rru_match={rru_match}")

                        if cpid_match and rru_match:
                            matched_alarms.append(alarm)
                            logger.info(f"[告警已添加] CGI={cgi}, cell_rru_id={cell_rru_id}, alarm={alarm.get('alarm_name', '')}")

                    if matched_alarms:
                        has_alarm = True
                        alarm_count = len(matched_alarms)
                        alarm_details = matched_alarms
                        logger.debug(f"直接匹配到告警: CGI={cgi}, rru_id={cell_rru_id}, 告警数量={alarm_count}")
                
                # 2. 尝试部分匹配（小区名称、BBU名称、站点名称或其他标识）
                if not has_alarm:
                    celname = cell.get('celname', '')
                    bbu_name = cell.get('bbu_name', '')
                    site_name = cell.get('site_name', '')
                    line_name = cell.get('line_name', '')
                    
                    # 遍历所有告警，尝试部分匹配
                    for alarm_cgi, alarms in alarm_data.items():
                        # 检查是否有部分匹配
                        partial_match = False
                        
                        # 检查小区名称
                        if celname:
                            # 宽松匹配：告警CGI中包含小区名称的任何部分
                            if any(part in alarm_cgi for part in celname.split() if part):
                                partial_match = True
                                logger.debug(f"小区名称部分匹配: {celname} 在 {alarm_cgi} 中")
                        
                        # 检查BBU名称
                        if not partial_match and bbu_name:
                            if bbu_name in alarm_cgi:
                                partial_match = True
                                logger.debug(f"BBU名称匹配: {bbu_name} 在 {alarm_cgi} 中")
                        
                        # 检查站点名称
                        if not partial_match and site_name:
                            if site_name in alarm_cgi:
                                partial_match = True
                                logger.debug(f"站点名称匹配: {site_name} 在 {alarm_cgi} 中")
                        
                        # 检查线路名称
                        if not partial_match and line_name:
                            if line_name in alarm_cgi:
                                partial_match = True
                                logger.debug(f"线路名称匹配: {line_name} 在 {alarm_cgi} 中")
                        
                        # 检查CGI的部分匹配（去掉分隔符后匹配）
                        if not partial_match:
                            # 移除CGI中的分隔符
                            cgi_no_dash = cgi.replace('-', '')
                            alarm_cgi_no_dash = alarm_cgi.replace('-', '')
                            # 检查是否有部分匹配
                            if len(cgi_no_dash) > 6 and cgi_no_dash in alarm_cgi_no_dash:
                                partial_match = True
                                logger.debug(f"CGI部分匹配: {cgi} 在 {alarm_cgi} 中")
                        
                        if partial_match:
                            # 匹配所有告警（不严格检查CPID）
                            matched_alarms = []
                            for alarm in alarms:
                                # 宽松匹配：如果有CPID则检查，否则直接匹配
                                alarm_cpid = alarm.get('extracted_cpid', '')
                                cpid_match = (not alarm_cpid or not cell_cpid_str or alarm_cpid == cell_cpid_str)

                                # 检查rru_id是否匹配（如果告警有matched_rru_id的话）
                                matched_rru_id = alarm.get('matched_rru_id', '')
                                rru_match = (not matched_rru_id or matched_rru_id == cell_rru_id)

                                if cpid_match and rru_match:
                                    matched_alarms.append(alarm)

                            if matched_alarms:
                                has_alarm = True
                                alarm_count = len(matched_alarms)
                                alarm_details = matched_alarms
                                logger.debug(f"部分匹配到告警: {alarm_cgi}, 告警数量={alarm_count}")
                                break
                
                # 3. 尝试网元ID匹配（从CGI中提取网元ID）
                if not has_alarm:
                    # 从CGI中提取网元ID（假设CGI格式为：460-00-网元ID-小区ID）
                    cgi_parts = cgi.split('-')
                    if len(cgi_parts) >= 3:
                        ne_id = cgi_parts[2]
                        # 遍历所有告警，尝试网元ID匹配
                        for alarm_cgi, alarms in alarm_data.items():
                            if ne_id in alarm_cgi:
                                matched_alarms = []
                                for alarm in alarms:
                                    # 检查是否是超级小区CP退服告警
                                    is_super_cell_cp_alarm = any(keyword in alarm.get('alarm_name', '') for keyword in ['超级小区CP退服', '超级小区CP退出服务'])
                                    # 检查是否是网元链路断告警
                                    is_ne_link_alarm = '网元链路断' in alarm.get('alarm_name', '')

                                    if is_super_cell_cp_alarm:
                                        # 超级小区CP退服告警需要检查CPID匹配
                                        alarm_cpid = alarm.get('extracted_cpid', '')
                                        if not alarm_cpid or not cell_cpid_str or alarm_cpid == cell_cpid_str:
                                            matched_alarms.append(alarm)
                                    elif is_ne_link_alarm:
                                        # 网元链路断告警匹配所有该网元下的小区，不检查rru_id
                                        matched_alarms.append(alarm)
                                    else:
                                        # 其他告警需要检查rru_id匹配（如果有的话）
                                        matched_rru_id = alarm.get('matched_rru_id', '')
                                        rru_match = (not matched_rru_id or matched_rru_id == cell_rru_id)
                                        if rru_match:
                                            matched_alarms.append(alarm)
                                
                                if matched_alarms:
                                    has_alarm = True
                                    alarm_count = len(matched_alarms)
                                    alarm_details = matched_alarms
                                    logger.debug(f"网元ID匹配到告警: NE_ID={ne_id}, 告警数量={alarm_count}")
                                    break
                
                # 判断健康状态
                status, reason = self._judge_health_status(
                    has_alarm
                )
                
                if status == 'healthy':
                    healthy_count += 1
                
                # 构建小区详情
                cell_detail = {
                    'id': cell.get('id'),
                    'line_name': cell.get('line_name'),
                    'site_name': cell.get('site_name'),
                    'area': cell.get('area'),
                    'site_type': cell.get('site_type'),
                    'bbu_name': cell.get('bbu_name'),
                    'celname': cell.get('celname'),
                    'cgi': cgi,
                    'network_type': network_type,
                    'lng': cell.get('lng'),
                    'lat': cell.get('lat'),
                    'high': cell.get('high'),
                    'ant_dir': cell.get('ant_dir'),
                    'cpId': cell.get('cpId'),
                    'cpId_key': cell.get('cpId_key'),
                    'rru_id_key': cell.get('rru_id_key'),
                    'rru_id': cell.get('rru_id'),
                    'rru_type': cell.get('rru_type'),
                    'status': status,
                    'reason': reason,
                    'has_alarm': has_alarm,
                    'alarm_count': alarm_count,
                    'alarm_details': alarm_details,
                    'check_time': check_time
                }
                
                checked_cells.append(cell_detail)
            
            # 计算统计数据
            total_count = len(checked_cells)
            unhealthy_count = total_count - healthy_count
            healthy_rate = round(healthy_count / total_count * 100, 2) if total_count > 0 else 0
            
            # 返回结果
            return {
                'line_name': line_name,
                'check_time': check_time,
                'total_cells': total_count,
                'healthy_cells': healthy_count,
                'unhealthy_cells': unhealthy_count,
                'healthy_rate': healthy_rate,
                'cells': checked_cells
            }
            
        except Exception as e:
            logger.error(f"高铁线路健康检查失败: {e}", exc_info=True)
            return {
                'error': str(e),
                'check_time': datetime.now()
            }
    
    def get_hsr_lines(self) -> List[str]:
        """获取所有高铁线路名称
        
        Returns:
            高铁线路名称列表
        """
        try:
            sql = """
                SELECT DISTINCT line_name
                FROM hsr_info
                WHERE line_name IS NOT NULL AND line_name != ''
                ORDER BY line_name
            """
            rows = self.mysql.fetch_all(sql)
            return [row.get('line_name', '') for row in rows if row.get('line_name', '')]
        except Exception as e:
            logger.error(f"获取高铁线路失败: {e}")
            return []
    
    def extract_hsr_health_check_table(self) -> Dict[str, Any]:
        """提取高铁发射点健康检查表
        
        Returns:
            健康检查表数据，包含：
            - summary: 总体统计信息
            - site_summary: 按发射点统计的信息
            - line_summary: 按线路统计的信息
            - detailed_table: 详细的小区健康检查表
        """
        try:
            # 1. 获取所有高铁小区的健康状态
            health_result = self.check_hsr_health()
            
            if 'error' in health_result:
                return {
                    'error': health_result['error'],
                    'check_time': health_result['check_time']
                }
            
            # 2. 按发射点统计
            site_summary = {}
            line_summary = {}
            detailed_table = []
            
            for cell in health_result['cells']:
                site_name = cell.get('site_name', '未知')
                line_name = cell.get('line_name', '未知')
                
                # 构建详细表格行
                table_row = {
                    '线路名称': line_name,
                    '发射点名称': site_name,
                    '小区名称': cell.get('celname', ''),
                    'CGI': cell.get('cgi', ''),
                    '网络类型': cell.get('network_type', ''),
                    '健康状态': '健康' if cell.get('status') == 'healthy' else '不健康',
                    '状态原因': cell.get('reason', ''),
                    '是否有性能数据': '是' if cell.get('has_performance') else '否',
                    '流量(GB)': round(cell.get('traffic', 0.0), 3),
                    '是否有告警': '是' if cell.get('has_alarm') else '否',
                    '告警数量': cell.get('alarm_count', 0),
                    '告警详情': '; '.join([f"{alarm.get('alarm_name')}({alarm.get('alarm_level')})" for alarm in cell.get('alarm_details', [])])[:200],
                    '检查时间': cell.get('check_time', '').strftime('%Y-%m-%d %H:%M:%S') if hasattr(cell.get('check_time'), 'strftime') else str(cell.get('check_time', ''))
                }
                detailed_table.append(table_row)
                
                # 按发射点统计
                if site_name not in site_summary:
                    site_summary[site_name] = {
                        'line_name': line_name,
                        'total_cells': 0,
                        'healthy_cells': 0,
                        'unhealthy_cells': 0,
                        'cells': []
                    }
                site_summary[site_name]['total_cells'] += 1
                if cell.get('status') == 'healthy':
                    site_summary[site_name]['healthy_cells'] += 1
                else:
                    site_summary[site_name]['unhealthy_cells'] += 1
                site_summary[site_name]['cells'].append(cell)
                
                # 按线路统计
                if line_name not in line_summary:
                    line_summary[line_name] = {
                        'total_cells': 0,
                        'healthy_cells': 0,
                        'unhealthy_cells': 0,
                        'sites': set()
                    }
                line_summary[line_name]['total_cells'] += 1
                if cell.get('status') == 'healthy':
                    line_summary[line_name]['healthy_cells'] += 1
                else:
                    line_summary[line_name]['unhealthy_cells'] += 1
                line_summary[line_name]['sites'].add(site_name)
            
            # 计算统计数据
            for site_name, data in site_summary.items():
                total = data['total_cells']
                data['healthy_rate'] = round(data['healthy_cells'] / total * 100, 2) if total > 0 else 0
            
            for line_name, data in line_summary.items():
                total = data['total_cells']
                data['healthy_rate'] = round(data['healthy_cells'] / total * 100, 2) if total > 0 else 0
                data['site_count'] = len(data['sites'])
                del data['sites']  # 移除sites集合，只保留计数
            
            # 3. 构建返回结果
            return {
                'check_time': health_result['check_time'],
                'summary': {
                    'total_cells': health_result['total_cells'],
                    'healthy_cells': health_result['healthy_cells'],
                    'unhealthy_cells': health_result['unhealthy_cells'],
                    'healthy_rate': health_result['healthy_rate'],
                    'site_count': len(site_summary),
                    'line_count': len(line_summary)
                },
                'site_summary': site_summary,
                'line_summary': line_summary,
                'detailed_table': detailed_table,
                'table_headers': list(detailed_table[0].keys()) if detailed_table else []
            }
            
        except Exception as e:
            logger.error(f"提取高铁发射点健康检查表失败: {e}", exc_info=True)
            return {
                'error': str(e),
                'check_time': datetime.now()
            }
