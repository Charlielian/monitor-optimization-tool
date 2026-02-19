"""告警监控服务"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AlarmService:
    """告警监控服务类 - 支持多厂商配置"""
    
    def __init__(self, mysql_client, 
                 current_table: str = 'cur_alarm',
                 history_table: str = 'his_alarm',
                 vendor_name: str = '中兴'):
        """初始化告警服务
        
        Args:
            mysql_client: MySQL客户端实例
            current_table: 当前告警表名，默认为 'cur_alarm'
            history_table: 历史告警表名，默认为 'his_alarm'
            vendor_name: 厂商名称（用于日志），默认为 '中兴'
        """
        self.mysql = mysql_client
        self.current_table = current_table
        self.history_table = history_table
        self.vendor_name = vendor_name
    
    def _parse_ne_filter(self, ne_id_filter: str, where_conditions: list, params: list) -> None:
        """解析网元ID/站点名称过滤条件
        
        Args:
            ne_id_filter: 过滤字符串，支持：
                         - 网元ID：12345
                         - 多个ID：12345,67890
                         - ID+站点：12345 北京
                         - 纯站点：北京（不含数字）
            where_conditions: WHERE条件列表（会被修改）
            params: 参数列表（会被修改）
        """
        if not ne_id_filter or not ne_id_filter.strip():
            return
        
        # 分割多个条件（用逗号分隔）
        filter_items = [item.strip() for item in ne_id_filter.split(',') if item.strip()]
        
        if not filter_items:
            return
        
        item_conditions = []
        
        for item in filter_items:
            # 检查是否包含空格（网元ID + 站点名称）
            if ' ' in item:
                parts = item.split(None, 1)  # 按第一个空格分割
                ne_id_part = parts[0].strip()
                site_name_part = parts[1].strip() if len(parts) > 1 else ''
                
                if ne_id_part and site_name_part:
                    # 同时匹配网元ID和站点名称
                    item_conditions.append("(ne_id LIKE %s AND site_name LIKE %s)")
                    params.extend([f"%{ne_id_part}%", f"%{site_name_part}%"])
                    logger.info(f"    ├─ 过滤条件: 网元ID={ne_id_part}, 站点名称={site_name_part}")
                elif ne_id_part:
                    # 只有网元ID
                    item_conditions.append("ne_id LIKE %s")
                    params.append(f"%{ne_id_part}%")
                    logger.info(f"    ├─ 过滤网元ID: {ne_id_part}")
            else:
                # 判断是纯站点名称还是网元ID
                # 如果包含数字，认为是网元ID；否则认为是站点名称
                if any(char.isdigit() for char in item):
                    # 包含数字，认为是网元ID
                    item_conditions.append("ne_id LIKE %s")
                    params.append(f"%{item}%")
                    logger.info(f"    ├─ 过滤网元ID: {item}")
                else:
                    # 不包含数字，认为是站点名称
                    item_conditions.append("site_name LIKE %s")
                    params.append(f"%{item}%")
                    logger.info(f"    ├─ 过滤站点名称: {item}")
        
        if item_conditions:
            # 多个条件用OR连接
            where_conditions.append(f"({' OR '.join(item_conditions)})")
    
    def _get_current_alarm_time_range(self) -> tuple:
        """计算当前告警的时间范围
        
        当前告警定义：最近1小时内的告警
        
        Returns:
            (start_time, end_time) 时间范围元组
        """
        now = datetime.now()
        # 当前告警：最近1小时
        start_time = now - timedelta(hours=1)
        end_time = now
        
        return start_time, end_time
    
    def get_current_alarms(self, ne_id_filter: str = None, alarm_name_filter: str = None) -> List[Dict[str, Any]]:
        """获取当前告警数据（最近1小时）
        
        Args:
            ne_id_filter: 网元ID过滤条件，支持：
                         - 多个ID用逗号分隔：12345,67890
                         - 网元ID+站点名称用空格分隔：12345 站点A
            alarm_name_filter: 告警名称过滤条件
        
        Returns:
            当前告警列表
        """
        import time
        method_start = time.time()
        
        try:
            start_time, end_time = self._get_current_alarm_time_range()
            
            logger.info(f"    ├─ 查询当前告警时间范围: {start_time} 至 {end_time}")
            
            # 构建查询条件
            build_start = time.time()
            where_conditions = ["import_time >= %s", "import_time <= %s"]
            params = [start_time, end_time]
            
            # 添加网元ID/站点名称过滤
            self._parse_ne_filter(ne_id_filter, where_conditions, params)
            
            # 添加告警名称过滤
            if alarm_name_filter and alarm_name_filter.strip():
                where_conditions.append("(alarm_code_name LIKE %s OR alarm_title LIKE %s)")
                params.extend([f"%{alarm_name_filter.strip()}%", f"%{alarm_name_filter.strip()}%"])
                logger.info(f"    ├─ 过滤告警名称: {alarm_name_filter.strip()}")
            
            logger.debug(f"    ├─ SQL条件构建: {(time.time() - build_start) * 1000:.2f}ms")
            
            # 查询最近1小时的告警（使用import_time字段）
            # 增加查询字段：ne, ne_name, site_name, alarm_object_name, location, additional_info
            sql = f"""
                SELECT *
                FROM {self.current_table}
                WHERE {' AND '.join(where_conditions)}
                ORDER BY import_time DESC, alarm_level DESC
            """
            
            query_start = time.time()
            alarms = self.mysql.fetch_all(sql, tuple(params))
            query_elapsed = (time.time() - query_start) * 1000
            
            if query_elapsed > 1000:
                logger.warning(f"    ├─ ⚠️ SQL查询慢: {query_elapsed:.2f}ms")
            else:
                logger.info(f"    ├─ SQL查询: {query_elapsed:.2f}ms")
            
            total_elapsed = (time.time() - method_start) * 1000
            logger.info(f"    └─ 查询到 {len(alarms)} 条当前告警数据，总耗时: {total_elapsed:.2f}ms")
            return alarms
            
        except Exception as e:
            logger.error(f"查询当前告警失败: {e}", exc_info=True)
            return []
    
    def get_historical_alarms(self, start_time: Optional[datetime] = None, 
                             end_time: Optional[datetime] = None,
                             page: int = 1, page_size: int = 100,
                             ne_id_filter: str = None, alarm_name_filter: str = None) -> Dict[str, Any]:
        """获取历史告警数据（去重）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            page_size: 每页数量
            ne_id_filter: 网元ID过滤条件，支持多个ID用逗号分隔
            alarm_name_filter: 告警名称过滤条件
            
        Returns:
            包含告警列表和分页信息的字典
        """
        import time
        method_start = time.time()
        
        try:
            # 默认查询最近7天
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time - timedelta(days=7)
            
            logger.info(f"    ├─ 查询历史告警时间范围: {start_time} 至 {end_time}")
            
            # 构建查询条件
            build_start = time.time()
            where_conditions = ["import_time BETWEEN %s AND %s"]
            params = [start_time, end_time]
            
            # 添加网元ID/站点名称过滤
            self._parse_ne_filter(ne_id_filter, where_conditions, params)
            
            # 添加告警名称过滤
            if alarm_name_filter and alarm_name_filter.strip():
                where_conditions.append("(alarm_code_name LIKE %s OR alarm_title LIKE %s)")
                params.extend([f"%{alarm_name_filter.strip()}%", f"%{alarm_name_filter.strip()}%"])
                logger.info(f"    ├─ 过滤告警名称: {alarm_name_filter.strip()}")
            
            where_clause = " AND ".join(where_conditions)
            logger.debug(f"    ├─ SQL条件构建: {(time.time() - build_start) * 1000:.2f}ms")
            
            # 查询历史告警，增加新字段
            count_start = time.time()
            sql_count = f"""
                SELECT COUNT(*) as total
                FROM (
                    SELECT DISTINCT 
                        alarm_id, alarm_code_name, alarm_level, alarm_type,
                        occur_time, alarm_reason, ack_status, 
                        ne_id, ne_type, ne_name, site_name, alarm_object_name, location, additional_info
                    FROM {self.history_table}
                    WHERE {where_clause}
                ) as distinct_alarms
            """
            
            count_result = self.mysql.fetch_one(sql_count, tuple(params))
            total = count_result.get('total', 0) if count_result else 0
            count_elapsed = (time.time() - count_start) * 1000
            
            if count_elapsed > 2000:
                logger.warning(f"    ├─ ⚠️ COUNT查询慢: {count_elapsed:.2f}ms")
            else:
                logger.info(f"    ├─ COUNT查询: {count_elapsed:.2f}ms")
            
            logger.info(f"    ├─ 历史告警总数（去重后）: {total}")
            
            # 计算分页
            offset = (page - 1) * page_size
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            # 查询分页数据，增加新字段
            data_start = time.time()
            params_with_limit = params + [page_size, offset]
            sql = f"""
                SELECT DISTINCT 
                    alarm_id, alarm_code_name, alarm_level, alarm_type,
                    occur_time, alarm_reason, ack_status, 
                    ne_id, ne_type, ne_name, site_name, alarm_object_name, location, additional_info
                FROM {self.history_table}
                WHERE {where_clause}
                ORDER BY occur_time DESC
                LIMIT %s OFFSET %s
            """
            
            alarms = self.mysql.fetch_all(sql, tuple(params_with_limit))
            data_elapsed = (time.time() - data_start) * 1000
            
            if data_elapsed > 2000:
                logger.warning(f"    ├─ ⚠️ 数据查询慢: {data_elapsed:.2f}ms")
            else:
                logger.info(f"    ├─ 数据查询: {data_elapsed:.2f}ms")
            
            total_elapsed = (time.time() - method_start) * 1000
            logger.info(f"    └─ 查询到 {len(alarms)} 条历史告警数据（第{page}页，共{total}条），总耗时: {total_elapsed:.2f}ms")
            
            return {
                'alarms': alarms,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except Exception as e:
            logger.error(f"查询历史告警失败: {e}", exc_info=True)
            return {
                'alarms': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'start_time': start_time,
                'end_time': end_time
            }
    
    def get_alarm_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息
        
        Returns:
            告警统计字典
        """
        import time
        method_start = time.time()
        
        try:
            # 当前告警统计（最近1小时，使用import_time）
            current_start = time.time()
            one_hour_ago = datetime.now() - timedelta(hours=1)
            sql_current = f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN alarm_level = '紧急' THEN 1 ELSE 0 END) as urgent,
                    SUM(CASE WHEN alarm_level = '重要' THEN 1 ELSE 0 END) as important,
                    SUM(CASE WHEN alarm_level = '主要' THEN 1 ELSE 0 END) as major,
                    SUM(CASE WHEN alarm_level = '一般' THEN 1 ELSE 0 END) as normal
                FROM {self.current_table}
                WHERE import_time >= %s
            """
            current_stats = self.mysql.fetch_one(sql_current, (one_hour_ago,)) or {}
            current_elapsed = (time.time() - current_start) * 1000
            
            if current_elapsed > 500:
                logger.warning(f"    ├─ ⚠️ 当前告警统计查询慢: {current_elapsed:.2f}ms")
            else:
                logger.info(f"    ├─ 当前告警统计查询: {current_elapsed:.2f}ms")
            
            # 获取最新告警时间（查询整个表，使用import_time字段）
            latest_time_start = time.time()
            sql_latest = f"""
                SELECT MAX(import_time) as latest_alarm_time
                FROM {self.current_table}
            """
            latest_stats = self.mysql.fetch_one(sql_latest) or {}
            latest_elapsed = (time.time() - latest_time_start) * 1000
            logger.debug(f"    ├─ 最新告警时间查询: {latest_elapsed:.2f}ms")
            
            # 今日告警统计（简化查询，不使用DISTINCT，直接COUNT）
            # 注意：这会包含重复告警，但速度快很多
            today_start = time.time()
            sql_today = f"""
                SELECT COUNT(*) as total
                FROM {self.current_table}
                WHERE DATE(import_time) = CURDATE()
            """
            today_stats = self.mysql.fetch_one(sql_today) or {}
            today_elapsed = (time.time() - today_start) * 1000
            
            if today_elapsed > 500:
                logger.warning(f"    ├─ ⚠️ 今日告警统计查询慢: {today_elapsed:.2f}ms")
            else:
                logger.info(f"    ├─ 今日告警统计查询: {today_elapsed:.2f}ms")
            
            total_elapsed = (time.time() - method_start) * 1000
            logger.info(f"    └─ 告警统计完成，总耗时: {total_elapsed:.2f}ms")
            
            return {
                'current_total': current_stats.get('total', 0),
                'current_urgent': current_stats.get('urgent', 0),
                'current_important': current_stats.get('important', 0),
                'current_major': current_stats.get('major', 0),
                'current_normal': current_stats.get('normal', 0),
                'today_total': today_stats.get('total', 0),
                'latest_alarm_time': latest_stats.get('latest_alarm_time')
            }
            
        except Exception as e:
            logger.error(f"获取告警统计失败: {e}", exc_info=True)
            return {
                'current_total': 0,
                'current_urgent': 0,
                'current_important': 0,
                'current_major': 0,
                'current_normal': 0,
                'today_total': 0,
                'latest_alarm_time': None
            }


__all__ = ['AlarmService', 'NokiaAlarmService']


class NokiaAlarmService:
    """诺基亚设备告警监控服务类
    
    Nokia表字段与中兴表不同，需要单独处理字段映射：
    - alarm_start_time -> occur_time
    - severity -> alarm_level  
    - fault_name_cn -> alarm_code_name
    - enb_id -> ne_id
    - bts_name -> site_name, 网元
    - alarm_status -> ack_status
    - diagnosis_info -> alarm_reason
    - alarm_detail -> additional_info
    """
    
    def __init__(self, mysql_client, 
                 current_table: str = 'cur_alarm_nokia',
                 history_table: str = 'his_alarm_nokia',
                 vendor_name: str = '诺基亚'):
        """初始化诺基亚告警服务"""
        self.mysql = mysql_client
        self.current_table = current_table
        self.history_table = history_table
        self.vendor_name = vendor_name
    
    def _parse_ne_filter(self, ne_id_filter: str, where_conditions: list, params: list) -> None:
        """解析网元ID/站点名称过滤条件（Nokia字段）"""
        if not ne_id_filter or not ne_id_filter.strip():
            return
        
        filter_items = [item.strip() for item in ne_id_filter.split(',') if item.strip()]
        if not filter_items:
            return
        
        item_conditions = []
        for item in filter_items:
            if ' ' in item:
                parts = item.split(None, 1)
                ne_id_part = parts[0].strip()
                site_name_part = parts[1].strip() if len(parts) > 1 else ''
                
                if ne_id_part and site_name_part:
                    item_conditions.append("(enb_id LIKE %s AND bts_name LIKE %s)")
                    params.extend([f"%{ne_id_part}%", f"%{site_name_part}%"])
                    logger.info(f"    ├─ 过滤条件: 网元ID={ne_id_part}, 站点名称={site_name_part}")
                elif ne_id_part:
                    item_conditions.append("enb_id LIKE %s")
                    params.append(f"%{ne_id_part}%")
                    logger.info(f"    ├─ 过滤网元ID: {ne_id_part}")
            else:
                if any(char.isdigit() for char in item):
                    item_conditions.append("enb_id LIKE %s")
                    params.append(f"%{item}%")
                    logger.info(f"    ├─ 过滤网元ID: {item}")
                else:
                    item_conditions.append("bts_name LIKE %s")
                    params.append(f"%{item}%")
                    logger.info(f"    ├─ 过滤站点名称: {item}")
        
        if item_conditions:
            where_conditions.append(f"({' OR '.join(item_conditions)})")
    
    def _get_current_alarm_time_range(self) -> tuple:
        """计算当前告警的时间范围（最近1小时）"""
        now = datetime.now()
        return now - timedelta(hours=1), now
    
    def _map_severity_to_level(self, severity: str) -> str:
        """将Nokia的severity映射为中文告警级别"""
        mapping = {
            'CRITICAL': '紧急',
            'MAJOR': '主要',
            'MINOR': '一般',
            'WARNING': '警告',
        }
        return mapping.get(severity, severity or '一般')
    
    def get_current_alarms(self, ne_id_filter: str = None, alarm_name_filter: str = None) -> List[Dict[str, Any]]:
        """获取当前告警数据（最近1小时）- Nokia字段映射"""
        import time
        method_start = time.time()
        
        try:
            start_time, end_time = self._get_current_alarm_time_range()
            logger.info(f"    ├─ 查询Nokia当前告警时间范围: {start_time} 至 {end_time}")
            
            where_conditions = ["import_time >= %s", "import_time <= %s"]
            params = [start_time, end_time]
            
            self._parse_ne_filter(ne_id_filter, where_conditions, params)
            
            if alarm_name_filter and alarm_name_filter.strip():
                where_conditions.append("(fault_name_cn LIKE %s OR alarm_description LIKE %s)")
                params.extend([f"%{alarm_name_filter.strip()}%", f"%{alarm_name_filter.strip()}%"])
                logger.info(f"    ├─ 过滤告警名称: {alarm_name_filter.strip()}")
            
            # 使用字段别名映射Nokia字段到标准字段
            sql = f"""
                SELECT 
                    id,
                    alarm_start_time as occur_time,
                    severity as alarm_level,
                    fault_name_cn as alarm_code_name,
                    alarm_type,
                    enb_id as ne_id,
                    '' as ne_type,
                    bts_name as site_name,
                    bts_name as `网元`,
                    alarm_object_name,
                    alarm_object as location,
                    alarm_detail as additional_info,
                    alarm_status as ack_status,
                    diagnosis_info as alarm_reason,
                    alarm_description,
                    alarm_code,
                    import_time
                FROM {self.current_table}
                WHERE {' AND '.join(where_conditions)}
                ORDER BY import_time DESC, severity DESC
            """
            
            query_start = time.time()
            alarms = self.mysql.fetch_all(sql, tuple(params))
            query_elapsed = (time.time() - query_start) * 1000
            
            # 转换severity为中文
            for alarm in alarms:
                alarm['alarm_level'] = self._map_severity_to_level(alarm.get('alarm_level'))
            
            if query_elapsed > 1000:
                logger.warning(f"    ├─ ⚠️ SQL查询慢: {query_elapsed:.2f}ms")
            else:
                logger.info(f"    ├─ SQL查询: {query_elapsed:.2f}ms")
            
            total_elapsed = (time.time() - method_start) * 1000
            logger.info(f"    └─ 查询到 {len(alarms)} 条Nokia当前告警数据，总耗时: {total_elapsed:.2f}ms")
            return alarms
            
        except Exception as e:
            logger.error(f"查询Nokia当前告警失败: {e}", exc_info=True)
            return []
    
    def get_historical_alarms(self, start_time: Optional[datetime] = None, 
                             end_time: Optional[datetime] = None,
                             page: int = 1, page_size: int = 100,
                             ne_id_filter: str = None, alarm_name_filter: str = None) -> Dict[str, Any]:
        """获取历史告警数据 - Nokia字段映射"""
        import time
        method_start = time.time()
        
        try:
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time - timedelta(days=7)
            
            logger.info(f"    ├─ 查询Nokia历史告警时间范围: {start_time} 至 {end_time}")
            
            where_conditions = ["import_time BETWEEN %s AND %s"]
            params = [start_time, end_time]
            
            self._parse_ne_filter(ne_id_filter, where_conditions, params)
            
            if alarm_name_filter and alarm_name_filter.strip():
                where_conditions.append("(fault_name_cn LIKE %s OR alarm_description LIKE %s)")
                params.extend([f"%{alarm_name_filter.strip()}%", f"%{alarm_name_filter.strip()}%"])
                logger.info(f"    ├─ 过滤告警名称: {alarm_name_filter.strip()}")
            
            where_clause = " AND ".join(where_conditions)
            
            # 统计总数
            sql_count = f"""
                SELECT COUNT(*) as total FROM {self.history_table}
                WHERE {where_clause}
            """
            count_result = self.mysql.fetch_one(sql_count, tuple(params))
            total = count_result.get('total', 0) if count_result else 0
            
            logger.info(f"    ├─ Nokia历史告警总数: {total}")
            
            offset = (page - 1) * page_size
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            params_with_limit = params + [page_size, offset]
            sql = f"""
                SELECT 
                    id,
                    alarm_start_time as occur_time,
                    severity as alarm_level,
                    fault_name_cn as alarm_code_name,
                    alarm_type,
                    enb_id as ne_id,
                    '' as ne_type,
                    bts_name as site_name,
                    bts_name as `网元`,
                    alarm_object_name,
                    alarm_object as location,
                    alarm_detail as additional_info,
                    alarm_status as ack_status,
                    diagnosis_info as alarm_reason,
                    alarm_description,
                    alarm_code,
                    import_time
                FROM {self.history_table}
                WHERE {where_clause}
                ORDER BY import_time DESC
                LIMIT %s OFFSET %s
            """
            
            alarms = self.mysql.fetch_all(sql, tuple(params_with_limit))
            
            # 转换severity为中文
            for alarm in alarms:
                alarm['alarm_level'] = self._map_severity_to_level(alarm.get('alarm_level'))
            
            total_elapsed = (time.time() - method_start) * 1000
            logger.info(f"    └─ 查询到 {len(alarms)} 条Nokia历史告警数据，总耗时: {total_elapsed:.2f}ms")
            
            return {
                'alarms': alarms,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except Exception as e:
            logger.error(f"查询Nokia历史告警失败: {e}", exc_info=True)
            return {
                'alarms': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'start_time': start_time,
                'end_time': end_time
            }
    
    def get_alarm_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息 - Nokia字段"""
        import time
        method_start = time.time()
        
        try:
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            # Nokia使用severity字段，值为CRITICAL/MAJOR/MINOR等
            sql_current = f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) as urgent,
                    SUM(CASE WHEN severity = 'MAJOR' THEN 1 ELSE 0 END) as major,
                    SUM(CASE WHEN severity = 'MINOR' THEN 1 ELSE 0 END) as normal,
                    SUM(CASE WHEN severity = 'WARNING' THEN 1 ELSE 0 END) as warning
                FROM {self.current_table}
                WHERE import_time >= %s
            """
            current_stats = self.mysql.fetch_one(sql_current, (one_hour_ago,)) or {}
            
            # 获取最新告警时间（查询整个表，使用import_time字段）
            sql_latest = f"""
                SELECT MAX(import_time) as latest_alarm_time
                FROM {self.current_table}
            """
            latest_stats = self.mysql.fetch_one(sql_latest) or {}
            
            sql_today = f"""
                SELECT COUNT(*) as total
                FROM {self.current_table}
                WHERE DATE(import_time) = CURDATE()
            """
            today_stats = self.mysql.fetch_one(sql_today) or {}
            
            total_elapsed = (time.time() - method_start) * 1000
            logger.info(f"    └─ Nokia告警统计完成，总耗时: {total_elapsed:.2f}ms")
            
            return {
                'current_total': current_stats.get('total', 0),
                'current_urgent': current_stats.get('urgent', 0),
                'current_important': 0,  # Nokia没有"重要"级别
                'current_major': current_stats.get('major', 0),
                'current_normal': current_stats.get('normal', 0),
                'today_total': today_stats.get('total', 0),
                'latest_alarm_time': latest_stats.get('latest_alarm_time')
            }
            
        except Exception as e:
            logger.error(f"获取Nokia告警统计失败: {e}", exc_info=True)
            return {
                'current_total': 0,
                'current_urgent': 0,
                'current_important': 0,
                'current_major': 0,
                'current_normal': 0,
                'today_total': 0,
                'latest_alarm_time': None
            }
