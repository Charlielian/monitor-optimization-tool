"""
告警网格匹配服务
将中兴和诺基亚告警与小区配置关联，统计网格故障数量
"""
import logging
import os
import pandas as pd
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AlarmGridMatcher:
    """告警网格匹配器 - 将告警关联到网格"""
    
    # 影响性能的告警类型定义
    PERFORMANCE_AFFECTING_ALARMS_ZTE = {
        '网元链路断', '输入电源断', '光口链路故障', '天馈驻波比异常',
        'RRU链路断', '光模块接收光功率异常', 'Ng断链', 'LTE小区退出服务',
        'S1断链告警', '小区关断告警', '超级小区CP退服', '小区关断',
        'DU小区退服', '基站退出服务', '超级小区CP退出服务'
    }
    
    PERFORMANCE_AFFECTING_ALARMS_NOKIA = {
        'RRU故障', '网元断链', '小区退服'
    }
    
    def __init__(self, mysql_client, pg_client=None):
        """
        初始化告警网格匹配器
        
        Args:
            mysql_client: MySQL客户端（用于读取告警和映射表）
            pg_client: PostgreSQL客户端（未使用，保留兼容性）
        """
        self.mysql = mysql_client
        self.pg = pg_client
        
        # 配置文件路径
        self.config_base_path = "小区配置"
        
        # 缓存数据
        self._cell_mapping_cache = None
        self._lte_config_cache = None
        self._nr_config_cache = None
        self._fdd_config_cache = None
        self._cache_time = None
        self._cache_ttl = 300  # 缓存5分钟
        
        # 告警查询时间范围配置
        self.default_query_hours = 1  # 默认查询时间范围（小时）
        self.max_adaptive_hours = 24  # 最大自适应扩展时间范围（小时）
    
    def configure_time_range(self, default_hours: int = None, max_hours: int = None):
        """
        配置告警查询时间范围
        
        Args:
            default_hours: 默认查询时间范围（小时），如果为None则保持当前值
            max_hours: 最大自适应扩展时间范围（小时），如果为None则保持当前值
        """
        if default_hours is not None:
            self.default_query_hours = default_hours
            logger.info(f"设置默认查询时间范围为 {default_hours} 小时")
        
        if max_hours is not None:
            self.max_adaptive_hours = max_hours
            logger.info(f"设置最大自适应扩展时间范围为 {max_hours} 小时")
    
    def _load_cell_mapping(self) -> List[Dict[str, Any]]:
        """加载小区映射表（从MySQL）"""
        try:
            sql = """
                SELECT cgi, celname, grid_id, grid_name
                FROM cell_mapping
                WHERE cgi IS NOT NULL
            """
            return self.mysql.fetch_all(sql) or []
        except Exception as e:
            logger.error(f"加载cell_mapping失败: {e}")
            return []
    
    def _load_csv_config(self, folder: str, pattern: str) -> List[Dict[str, Any]]:
        """
        加载CSV配置文件（加载文件夹中的所有CSV文件）
        
        Args:
            folder: 文件夹名称（LTE/NR/FDD）
            pattern: 文件名模式（用于过滤文件）
        
        Returns:
            配置记录列表
        """
        try:
            folder_path = os.path.join(self.config_base_path, folder)
            if not os.path.exists(folder_path):
                logger.warning(f"配置文件夹不存在: {folder_path}")
                return []
            
            # 查找所有匹配的CSV文件
            csv_files = [f for f in os.listdir(folder_path) 
                        if f.endswith('.csv') and pattern in f]
            if not csv_files:
                logger.warning(f"未找到CSV文件: {folder_path} (pattern: {pattern})")
                return []
            
            # 按文件名排序（最新的在前）
            csv_files.sort(reverse=True)
            
            # 加载所有CSV文件并合并
            all_records = []
            for csv_filename in csv_files:
                csv_file = os.path.join(folder_path, csv_filename)
                try:
                    logger.info(f"加载配置文件: {csv_file}")
                    df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
                    records = df.to_dict('records')
                    all_records.extend(records)
                    logger.info(f"  └─ 加载 {len(records)} 条记录")
                except Exception as e:
                    logger.error(f"  └─ 加载失败: {e}")
                    continue
            
            logger.info(f"✓ {folder} 配置加载完成: 共 {len(all_records)} 条记录（来自 {len(csv_files)} 个文件）")
            return all_records
            
        except Exception as e:
            logger.error(f"加载{folder}配置失败: {e}")
            return []
    
    def _load_excel_config(self, folder: str) -> List[Dict[str, Any]]:
        """
        加载Excel配置文件（加载文件夹中的所有Excel文件）
        
        Args:
            folder: 文件夹名称（FDD）
        
        Returns:
            配置记录列表
        """
        try:
            folder_path = os.path.join(self.config_base_path, folder)
            if not os.path.exists(folder_path):
                logger.warning(f"配置文件夹不存在: {folder_path}")
                return []
            
            # 查找所有Excel文件
            excel_files = [f for f in os.listdir(folder_path) 
                          if f.endswith('.xlsx') or f.endswith('.xls')]
            if not excel_files:
                logger.warning(f"未找到Excel文件: {folder_path}")
                return []
            
            # 按文件名排序
            excel_files.sort()
            
            # 加载所有Excel文件并合并
            all_records = []
            for excel_filename in excel_files:
                excel_file = os.path.join(folder_path, excel_filename)
                try:
                    logger.info(f"加载配置文件: {excel_file}")
                    df = pd.read_excel(excel_file)
                    records = df.to_dict('records')
                    all_records.extend(records)
                    logger.info(f"  └─ 加载 {len(records)} 条记录")
                except Exception as e:
                    logger.error(f"  └─ 加载失败: {e}")
                    continue
            
            logger.info(f"✓ {folder} 配置加载完成: 共 {len(all_records)} 条记录（来自 {len(excel_files)} 个文件）")
            return all_records
            
        except Exception as e:
            logger.error(f"加载{folder}配置失败: {e}")
            return []
    
    def _load_lte_config(self) -> List[Dict[str, Any]]:
        """加载LTE配置（从CSV文件）"""
        return self._load_csv_config('LTE', 'LTE_ITBBU_CellInfo')
    
    def _load_nr_config(self) -> List[Dict[str, Any]]:
        """加载NR配置（从CSV文件）"""
        records = self._load_csv_config('NR', 'NR_CellInfo')
        
        # 构造CGI字段（如果不存在）
        for record in records:
            if 'cgi' not in record or pd.isna(record.get('cgi')):
                gnb_id = record.get('gNBId') or record.get('gnb_id')
                cell_id = record.get('cellLocalId') or record.get('cell_local_id')
                if gnb_id and cell_id:
                    record['cgi'] = f"460-00-{gnb_id}-{cell_id}"
            
            # 统一字段名
            if 'gNBId' in record:
                record['gnb_id'] = record['gNBId']
            if 'cellLocalId' in record:
                record['cell_local_id'] = record['cellLocalId']
            if 'CellName' in record:
                record['cell_name'] = record['CellName']
        
        return records
    
    def _load_fdd_config(self) -> List[Dict[str, Any]]:
        """加载FDD配置（从Excel文件）"""
        return self._load_excel_config('FDD')
    
    def _refresh_cache(self):
        """刷新缓存数据"""
        now = datetime.now()
        if self._cache_time and (now - self._cache_time).total_seconds() < self._cache_ttl:
            return
        
        logger.info("刷新告警匹配缓存数据...")
        self._cell_mapping_cache = self._load_cell_mapping()
        self._lte_config_cache = self._load_lte_config()
        self._nr_config_cache = self._load_nr_config()
        self._fdd_config_cache = self._load_fdd_config()
        self._cache_time = now
        logger.info(f"缓存刷新完成: mapping={len(self._cell_mapping_cache)}, "
                   f"lte={len(self._lte_config_cache)}, "
                   f"nr={len(self._nr_config_cache)}, "
                   f"fdd={len(self._fdd_config_cache)}")
    
    def match_zte_alarm(self, alarm: Dict[str, Any]) -> Set[str]:
        """
        匹配中兴告警到CGI
        
        Args:
            alarm: 告警记录，包含字段：
                - alarm_object_type: 告警对象类型 (CELL/ITBBU/SDR/PHUB/BBU/RU)
                - alarm_object_name: 告警对象名称
                - alarm_object_id: 告警对象ID
                - ne_id: 网元ID
                - ne_name: 网元名称
        
        Returns:
            匹配到的CGI集合
        """
        self._refresh_cache()
        
        cgis = set()
        alarm_type = alarm.get('alarm_object_type', '').upper()
        alarm_object_name = alarm.get('alarm_object_name', '')
        alarm_object_id = alarm.get('alarm_object_id', '')
        ne_id = alarm.get('ne_id', '')
        ne_name = alarm.get('ne_name', '')
        
        # DEBUG模式下记录告警关键字段
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"匹配中兴告警: type={alarm_type}, name={alarm_object_name}, "
                        f"id={alarm_object_id}, ne_id={ne_id}")
        
        if alarm_type == 'CELL':
            # CELL级告警匹配
            logger.debug(f"  CELL级告警: 匹配小区")
            cgis = self._match_cell_alarm(alarm)
        elif alarm_type in ['ITBBU', 'SDR', 'PHUB', 'BBU']:
            # 基站级告警匹配
            logger.debug(f"  {alarm_type}级告警: 匹配基站下所有小区")
            cgis = self._match_station_alarm(alarm)
        elif alarm_type == 'RU':
            # RU级告警匹配
            logger.debug(f"  RU级告警: 匹配RU关联的小区")
            cgis = self._match_ru_alarm(alarm)
        else:
            # 未知告警类型
            if alarm_type:
                logger.debug(f"  未知告警类型: {alarm_type}，不进行匹配")
            else:
                logger.debug(f"  告警缺少alarm_object_type字段，无法匹配")
        
        # 记录匹配结果
        if cgis:
            logger.debug(f"  中兴告警匹配成功: 匹配到 {len(cgis)} 个CGI")
            if logger.isEnabledFor(logging.DEBUG) and len(cgis) <= 5:
                logger.debug(f"  匹配的CGI: {', '.join(list(cgis)[:5])}")
        else:
            # 记录未匹配的原因
            if not alarm_type:
                logger.debug(f"  未匹配原因: 缺少告警类型字段")
            elif alarm_type not in ['CELL', 'ITBBU', 'SDR', 'PHUB', 'BBU', 'RU']:
                logger.debug(f"  未匹配原因: 告警类型'{alarm_type}'不在匹配规则中")
            elif alarm_type == 'CELL' and not alarm_object_name and not (ne_id and alarm_object_id):
                logger.debug(f"  未匹配原因: CELL告警缺少alarm_object_name或(ne_id+alarm_object_id)")
            elif alarm_type in ['ITBBU', 'SDR', 'PHUB', 'BBU'] and not ne_id:
                logger.debug(f"  未匹配原因: {alarm_type}告警缺少ne_id字段")
            elif alarm_type == 'RU' and not alarm_object_id:
                logger.debug(f"  未匹配原因: RU告警缺少alarm_object_id字段")
            else:
                logger.debug(f"  未匹配原因: CGI不在映射表或配置文件中")
        
        return cgis
    
    def _match_cell_alarm(self, alarm: Dict[str, Any]) -> Set[str]:
        """匹配CELL级告警"""
        cgis = set()
        alarm_object_name = alarm.get('alarm_object_name', '')
        ne_id = alarm.get('ne_id', '')
        alarm_object_id = alarm.get('alarm_object_id', '')
        
        # 方法1：通过小区名称匹配
        if alarm_object_name:
            # 在映射表中查找
            for cell in self._cell_mapping_cache:
                if cell.get('celname') == alarm_object_name:
                    cgis.add(cell['cgi'])
            
            # 在配置文件中查找
            for config in self._lte_config_cache + self._nr_config_cache + self._fdd_config_cache:
                cell_name = config.get('CellName') or config.get('cell_name')
                if cell_name == alarm_object_name:
                    cgi = config.get('cgi')
                    if cgi and not pd.isna(cgi):
                        cgis.add(str(cgi))
        
        # 方法2：通过CGI构造匹配
        if ne_id and alarm_object_id:
            constructed_cgi = f"460-00-{ne_id}-{alarm_object_id}"
            # 检查是否存在
            for cell in self._cell_mapping_cache:
                if cell['cgi'] == constructed_cgi:
                    cgis.add(constructed_cgi)
                    break
            
            # 在配置中检查
            for config in self._lte_config_cache + self._nr_config_cache + self._fdd_config_cache:
                cgi = config.get('cgi')
                if cgi and str(cgi) == constructed_cgi:
                    cgis.add(constructed_cgi)
                    break
        
        return cgis
    
    def _match_station_alarm(self, alarm: Dict[str, Any]) -> Set[str]:
        """匹配基站级告警"""
        cgis = set()
        ne_id = alarm.get('ne_id', '')
        
        if not ne_id:
            return cgis
        
        # 在映射表中查找该基站下的所有小区
        for cell in self._cell_mapping_cache:
            cgi = cell['cgi']
            parts = cgi.split('-')
            if len(parts) >= 3 and parts[2] == str(ne_id):
                cgis.add(cgi)
        
        # 在LTE配置中查找
        for config in self._lte_config_cache:
            enb_id = config.get('eNBId') or config.get('enb_id')
            if str(enb_id) == str(ne_id):
                cgi = config.get('cgi')
                if cgi and not pd.isna(cgi):
                    cgis.add(str(cgi))
        
        # 在NR配置中查找
        for config in self._nr_config_cache:
            gnb_id = config.get('gNBId') or config.get('gnb_id')
            if str(gnb_id) == str(ne_id):
                cgi = config.get('cgi')
                if cgi and not pd.isna(cgi):
                    cgis.add(str(cgi))
        
        # 在FDD配置中查找
        for config in self._fdd_config_cache:
            enb_id = config.get('eNBId') or config.get('enb_id')
            if str(enb_id) == str(ne_id):
                cgi = config.get('cgi')
                if cgi and not pd.isna(cgi):
                    cgis.add(str(cgi))
        
        return cgis
    
    def _match_ru_alarm(self, alarm: Dict[str, Any]) -> Set[str]:
        """匹配RU级告警"""
        cgis = set()
        ne_id = alarm.get('ne_id', '')
        ne_name = alarm.get('ne_name', '')
        ru_id = alarm.get('alarm_object_id', '')
        
        if not ru_id:
            return cgis
        
        # RU匹配字符串
        ru_pattern = f"ReplaceableUnit={ru_id}"
        
        # 在所有配置中查找
        for config in self._lte_config_cache + self._nr_config_cache + self._fdd_config_cache:
            # 网元匹配
            ne_matched = False
            if ne_id:
                config_ne_id = (config.get('eNBId') or config.get('enb_id') or 
                               config.get('gNBId') or config.get('gnb_id'))
                if str(config_ne_id) == str(ne_id):
                    ne_matched = True
            elif ne_name:
                config_ne_name = config.get('NE_Name') or config.get('ne_name', '')
                if ne_name in str(config_ne_name):
                    ne_matched = True
            
            if not ne_matched:
                continue
            
            # RU匹配
            ru_fields = [
                config.get('refReplaceableUnit_Aau', ''),
                config.get('refReplaceableUnit_IrRru', ''),
                config.get('refReplaceableUnit_rru', ''),
                config.get('refReplaceableUnit_Prru', ''),
                config.get('refReplaceableUnit_Aau_main', ''),
                config.get('refReplaceableUnit_IrRru_main', ''),
                config.get('refReplaceableUnit_rru_main', ''),
                config.get('refReplaceableUnit_Prru_main', '')
            ]
            
            for field_value in ru_fields:
                if field_value and ru_pattern in str(field_value):
                    cgi = config.get('cgi')
                    if cgi and not pd.isna(cgi):
                        cgis.add(str(cgi))
                    break
        
        return cgis
    
    def match_nokia_alarm(self, alarm: Dict[str, Any]) -> Set[str]:
        """
        匹配诺基亚告警到CGI
        
        Args:
            alarm: 告警记录，包含字段：
                - ne_id: 基站ID (由SQL别名提供)
                - cgi: 小区全局标识
                - alarm_name: 告警类型名称 (由SQL别名提供)
                - 故障中文名: 告警类型名称 (兼容字段)
        
        Returns:
            匹配到的CGI集合
        """
        self._refresh_cache()
        
        cgis = set()
        # 优先使用标准字段名（由SQL别名提供）
        fault_name = alarm.get('alarm_name', '') or alarm.get('故障中文名', '')
        ne_id = alarm.get('ne_id')
        cgi_field = alarm.get('cgi')
        
        # DEBUG模式下记录告警关键字段
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"匹配诺基亚告警: fault_name={fault_name}, ne_id={ne_id}, cgi={cgi_field}")
        
        if fault_name == '小区退服':
            # 直接使用CGI字段（标准字段名）
            if cgi_field:
                cgis.add(str(cgi_field))
                logger.debug(f"  小区退服告警: 直接使用CGI={cgi_field}")
            else:
                logger.debug(f"  小区退服告警: 缺少CGI字段，无法匹配")
        elif fault_name in ['RRU故障', '网元断链']:
            # 通过ne_id关联该基站下所有小区（标准字段名）
            if ne_id:
                logger.debug(f"  {fault_name}告警: 查找基站{ne_id}下的所有小区")
                
                # 在映射表中查找
                mapping_count = 0
                for cell in self._cell_mapping_cache:
                    cgi = cell['cgi']
                    parts = cgi.split('-')
                    if len(parts) >= 3 and parts[2] == str(ne_id):
                        cgis.add(cgi)
                        mapping_count += 1
                
                # 在配置中查找
                config_count = 0
                for config in self._lte_config_cache + self._nr_config_cache + self._fdd_config_cache:
                    config_ne_id = (config.get('eNBId') or config.get('enb_id') or 
                                   config.get('gNBId') or config.get('gnb_id'))
                    if str(config_ne_id) == str(ne_id):
                        cgi = config.get('cgi')
                        if cgi and not pd.isna(cgi):
                            cgis.add(str(cgi))
                            config_count += 1
                
                logger.debug(f"  找到 {mapping_count} 个映射表小区, {config_count} 个配置文件小区")
            else:
                logger.debug(f"  {fault_name}告警: 缺少ne_id字段，无法匹配")
        else:
            # 未知告警类型
            if fault_name:
                logger.debug(f"  未知告警类型: {fault_name}，不进行匹配")
            else:
                logger.debug(f"  告警缺少fault_name字段，无法匹配")
        
        # 记录匹配结果
        if cgis:
            logger.debug(f"  诺基亚告警匹配成功: 匹配到 {len(cgis)} 个CGI")
            if logger.isEnabledFor(logging.DEBUG) and len(cgis) <= 5:
                logger.debug(f"  匹配的CGI: {', '.join(list(cgis)[:5])}")
        else:
            # 记录未匹配的原因
            if not fault_name:
                logger.debug(f"  未匹配原因: 缺少告警名称字段")
            elif fault_name not in ['小区退服', 'RRU故障', '网元断链']:
                logger.debug(f"  未匹配原因: 告警类型'{fault_name}'不在匹配规则中")
            elif fault_name == '小区退服' and not cgi_field:
                logger.debug(f"  未匹配原因: 小区退服告警缺少CGI字段")
            elif fault_name in ['RRU故障', '网元断链'] and not ne_id:
                logger.debug(f"  未匹配原因: {fault_name}告警缺少ne_id字段")
            else:
                logger.debug(f"  未匹配原因: CGI不在映射表或配置文件中")
        
        return cgis
    
    def _get_alarms_adaptive(self, table_name: str, start_time: datetime, 
                             max_hours: int = None) -> List[Dict[str, Any]]:
        """
        自适应时间范围查询告警
        
        如果默认时间范围内无数据，自动扩大到最新数据时间
        
        Args:
            table_name: 表名 (cur_alarm 或 cur_alarm_nokia)
            start_time: 初始查询起始时间
            max_hours: 最大扩展小时数（如果为None，使用配置的max_adaptive_hours）
            
        Returns:
            告警列表
        """
        # 使用配置的最大扩展时间范围
        if max_hours is None:
            max_hours = self.max_adaptive_hours
        
        # 先尝试默认时间范围
        if table_name == 'cur_alarm':
            result = self._get_zte_alarms(start_time)
        else:
            result = self._get_nokia_alarms(start_time)
        
        if not result or len(result) == 0:
            # 查询最新数据时间
            try:
                check_sql = f"SELECT MAX(import_time) as latest FROM {table_name}"
                check_result = self.mysql.fetch_one(check_sql)
                
                if check_result and check_result['latest']:
                    latest_time = check_result['latest']
                    
                    # 如果最新数据早于查询范围，扩大范围
                    if latest_time < start_time:
                        time_diff_hours = (start_time - latest_time).total_seconds() / 3600
                        
                        if time_diff_hours <= max_hours:
                            logger.info(f"扩大{table_name}查询范围到 {time_diff_hours:.1f} 小时前")
                            new_start_time = latest_time - timedelta(hours=1)
                            
                            # 重新查询
                            if table_name == 'cur_alarm':
                                result = self._get_zte_alarms(new_start_time)
                            else:
                                result = self._get_nokia_alarms(new_start_time)
                            
                            logger.info(f"扩大范围后获取到 {len(result or [])} 条告警")
                        else:
                            logger.warning(f"最新数据时间过旧（{time_diff_hours:.1f}小时前），超过最大范围{max_hours}小时")
            except Exception as e:
                logger.error(f"自适应查询失败: {e}")
        
        return result or []
    
    def get_grid_fault_stats(self, performance_only: bool = False) -> Dict[str, int]:
        """
        获取网格故障统计
        
        Args:
            performance_only: 是否只统计影响性能的告警
        
        Returns:
            网格ID -> 故障小区数量的字典
        """
        if not self.mysql:
            logger.warning("MySQL未连接，无法获取告警数据")
            return {}
        
        self._refresh_cache()
        
        # 获取当前告警（使用配置的默认时间范围）
        now = datetime.now()
        start_time = now - timedelta(hours=self.default_query_hours)
        
        # 使用自适应查询获取中兴告警
        zte_alarms = self._get_alarms_adaptive('cur_alarm', start_time)
        logger.info(f"获取到 {len(zte_alarms)} 条中兴告警")
        
        # 使用自适应查询获取诺基亚告警
        nokia_alarms = self._get_alarms_adaptive('cur_alarm_nokia', start_time)
        logger.info(f"获取到 {len(nokia_alarms)} 条诺基亚告警")
        
        # 如果只统计影响性能的告警，进行过滤
        if performance_only:
            zte_alarms = [
                alarm for alarm in zte_alarms
                if alarm.get('alarm_name', '') in self.PERFORMANCE_AFFECTING_ALARMS_ZTE
            ]
            nokia_alarms = [
                alarm for alarm in nokia_alarms
                if alarm.get('alarm_name', '') in self.PERFORMANCE_AFFECTING_ALARMS_NOKIA
            ]
            logger.info(f"过滤后: {len(zte_alarms)} 条中兴影响性能告警, {len(nokia_alarms)} 条诺基亚影响性能告警")
        
        # 匹配告警到CGI
        fault_cgis = set()
        
        # 匹配中兴告警
        for alarm in zte_alarms:
            cgis = self.match_zte_alarm(alarm)
            fault_cgis.update(cgis)
        
        # 匹配诺基亚告警
        for alarm in nokia_alarms:
            cgis = self.match_nokia_alarm(alarm)
            fault_cgis.update(cgis)
        
        logger.info(f"匹配到 {len(fault_cgis)} 个故障小区")
        
        # 统计每个网格的故障小区数
        grid_faults = {}
        for cgi in fault_cgis:
            # 在映射表中查找网格
            for cell in self._cell_mapping_cache:
                if cell['cgi'] == cgi and cell.get('grid_id'):
                    grid_id = cell['grid_id']
                    grid_faults[grid_id] = grid_faults.get(grid_id, 0) + 1
                    break
        
        logger.info(f"统计到 {len(grid_faults)} 个网格有故障")
        return grid_faults
    
    def _get_zte_alarms(self, start_time: datetime) -> List[Dict[str, Any]]:
        """
        获取中兴告警（从MySQL）
        
        Args:
            start_time: 查询起始时间
            
        Returns:
            中兴告警列表，如果查询失败则返回空列表
        """
        try:
            sql = """
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
            
            now = datetime.now()
            logger.info(f"查询中兴告警，时间范围: {start_time} 至 {now}")
            logger.debug(f"执行SQL: {sql.strip()} with start_time={start_time}")
            
            result = self.mysql.fetch_all(sql, (start_time,))
            
            if result and len(result) > 0:
                logger.info(f"获取到 {len(result)} 条中兴告警")
                
                # DEBUG模式下记录样本数据
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"中兴告警样本: {result[0]}")
            else:
                # 查询返回0条，进行诊断
                logger.warning(f"查询中兴告警返回0条记录")
                
                # 检查表中是否有数据
                try:
                    check_sql = "SELECT COUNT(*) as count, MAX(import_time) as latest FROM cur_alarm"
                    check_result = self.mysql.fetch_one(check_sql)
                    
                    if check_result:
                        total_count = check_result['count']
                        latest_time = check_result['latest']
                        
                        logger.warning(f"  中兴告警表总记录数: {total_count}")
                        logger.warning(f"  最新数据时间: {latest_time}")
                        logger.warning(f"  查询起始时间: {start_time}")
                        
                        if total_count == 0:
                            logger.warning(f"  ⚠️ 告警表为空，无任何数据")
                        elif latest_time and latest_time < start_time:
                            time_diff = (start_time - latest_time).total_seconds() / 3600
                            logger.warning(f"  ⚠️ 最新数据时间早于查询范围 {time_diff:.1f} 小时")
                            logger.warning(f"  建议：检查数据更新是否正常，或扩大查询时间范围")
                        else:
                            logger.warning(f"  ⚠️ 表中有数据但不在查询时间范围内")
                except Exception as diag_e:
                    logger.error(f"诊断查询失败: {diag_e}")
            
            return result or []
            
        except Exception as e:
            logger.warning(f"获取中兴告警失败: {e}")
            return []
    
    def _get_nokia_alarms(self, start_time: datetime) -> List[Dict[str, Any]]:
        """
        获取诺基亚告警（从MySQL）
        
        诺基亚表字段映射：
        - enb_id → ne_id (基站ID)
        - cgi → cgi (小区全局标识)
        - fault_name_cn → alarm_name (告警名称)
        
        注意：此方法与 NokiaAlarmService 使用相同的字段映射规则
        
        Args:
            start_time: 查询起始时间
            
        Returns:
            诺基亚告警列表，如果表不存在或查询失败则返回空列表
        """
        try:
            # 使用正确的列名查询诺基亚告警表
            # 字段别名保持接口一致性
            sql = """
                SELECT 
                    enb_id as ne_id,
                    cgi,
                    fault_name_cn as alarm_name,
                    fault_name_cn as 故障中文名,
                    import_time
                FROM cur_alarm_nokia
                WHERE import_time >= %s
            """
            
            now = datetime.now()
            logger.info(f"查询诺基亚告警，时间范围: {start_time} 至 {now}")
            logger.debug(f"执行SQL: {sql.strip()} with start_time={start_time}")
            
            result = self.mysql.fetch_all(sql, (start_time,))
            
            if result and len(result) > 0:
                # 成功时记录INFO级别日志，包含告警数量
                logger.info(f"获取到 {len(result)} 条诺基亚告警")
                
                # DEBUG模式下记录样本数据
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"诺基亚告警样本: {result[0]}")
            else:
                # 查询返回0条，进行诊断
                logger.warning(f"查询诺基亚告警返回0条记录")
                
                # 检查表中是否有数据
                try:
                    check_sql = "SELECT COUNT(*) as count, MAX(import_time) as latest FROM cur_alarm_nokia"
                    check_result = self.mysql.fetch_one(check_sql)
                    
                    if check_result:
                        total_count = check_result['count']
                        latest_time = check_result['latest']
                        
                        logger.warning(f"  诺基亚告警表总记录数: {total_count}")
                        logger.warning(f"  最新数据时间: {latest_time}")
                        logger.warning(f"  查询起始时间: {start_time}")
                        
                        if total_count == 0:
                            logger.warning(f"  ⚠️ 告警表为空，无任何数据")
                        elif latest_time and latest_time < start_time:
                            time_diff = (start_time - latest_time).total_seconds() / 3600
                            logger.warning(f"  ⚠️ 最新数据时间早于查询范围 {time_diff:.1f} 小时")
                            logger.warning(f"  建议：检查数据更新是否正常，或扩大查询时间范围")
                        else:
                            logger.warning(f"  ⚠️ 表中有数据但不在查询时间范围内")
                except Exception as diag_e:
                    logger.error(f"诊断查询失败: {diag_e}")
            
            # 确保返回空列表而不是None
            return result or []
            
        except Exception as e:
            # 表不存在或字段不匹配时优雅降级，不影响中兴告警处理
            logger.error(f"MySQL 查询诺基亚告警失败: {e}")
            logger.debug(f"诺基亚告警表不可用（如果只有中兴告警，这是正常的）")
            
            # 确保返回空列表而不是None
            return []
    
    def diagnose_alarm_data(self) -> Dict[str, Any]:
        """
        诊断告警数据状态
        
        检查告警表是否有数据，最新数据时间是多少，帮助定位为何查询返回0条记录
        
        Returns:
            诊断信息字典，包含：
            - zte_table_exists: 中兴告警表是否存在
            - nokia_table_exists: 诺基亚告警表是否存在
            - zte_total_count: 中兴告警表总记录数
            - nokia_total_count: 诺基亚告警表总记录数
            - zte_latest_time: 中兴告警最新import_time
            - nokia_latest_time: 诺基亚告警最新import_time
            - time_diff_hours: 最新数据距离现在的小时数
        """
        result = {
            'zte_table_exists': False,
            'nokia_table_exists': False,
            'zte_total_count': 0,
            'nokia_total_count': 0,
            'zte_latest_time': None,
            'nokia_latest_time': None
        }
        
        if not self.mysql:
            logger.warning("MySQL未连接，无法诊断告警数据")
            return result
        
        # 检查中兴告警表
        try:
            sql = "SELECT COUNT(*) as count, MAX(import_time) as latest FROM cur_alarm"
            zte_info = self.mysql.fetch_one(sql)
            if zte_info:
                result['zte_table_exists'] = True
                result['zte_total_count'] = zte_info['count']
                result['zte_latest_time'] = zte_info['latest']
                logger.info(f"中兴告警表: 总数={zte_info['count']}, 最新时间={zte_info['latest']}")
        except Exception as e:
            logger.error(f"检查中兴告警表失败: {e}")
        
        # 检查诺基亚告警表
        try:
            sql = "SELECT COUNT(*) as count, MAX(import_time) as latest FROM cur_alarm_nokia"
            nokia_info = self.mysql.fetch_one(sql)
            if nokia_info:
                result['nokia_table_exists'] = True
                result['nokia_total_count'] = nokia_info['count']
                result['nokia_latest_time'] = nokia_info['latest']
                logger.info(f"诺基亚告警表: 总数={nokia_info['count']}, 最新时间={nokia_info['latest']}")
        except Exception as e:
            logger.error(f"检查诺基亚告警表失败: {e}")
        
        # 计算时间差
        now = datetime.now()
        if result['zte_latest_time']:
            time_diff = (now - result['zte_latest_time']).total_seconds() / 3600
            result['zte_time_diff_hours'] = round(time_diff, 2)
        
        if result['nokia_latest_time']:
            time_diff = (now - result['nokia_latest_time']).total_seconds() / 3600
            result['nokia_time_diff_hours'] = round(time_diff, 2)
        
        return result
    
    def get_grid_fault_details(self, grid_id: str) -> List[Dict[str, Any]]:
        """
        获取指定网格的故障小区详情
        
        Args:
            grid_id: 网格ID
        
        Returns:
            故障小区列表，包含CGI、小区名、告警名称等
        """
        if not self.mysql:
            return []
        
        self._refresh_cache()
        
        # 获取当前告警（使用配置的默认时间范围）
        now = datetime.now()
        start_time = now - timedelta(hours=self.default_query_hours)
        
        # 使用自适应查询
        zte_alarms = self._get_alarms_adaptive('cur_alarm', start_time)
        nokia_alarms = self._get_alarms_adaptive('cur_alarm_nokia', start_time)
        
        # 匹配告警到CGI，并记录告警名称
        cgi_alarms = {}  # CGI -> 告警名称列表
        
        for alarm in zte_alarms:
            cgis = self.match_zte_alarm(alarm)
            alarm_name = alarm.get('alarm_name', '未知告警')
            for cgi in cgis:
                if cgi not in cgi_alarms:
                    cgi_alarms[cgi] = []
                cgi_alarms[cgi].append(alarm_name)
        
        for alarm in nokia_alarms:
            cgis = self.match_nokia_alarm(alarm)
            alarm_name = alarm.get('alarm_name', '未知告警')
            for cgi in cgis:
                if cgi not in cgi_alarms:
                    cgi_alarms[cgi] = []
                cgi_alarms[cgi].append(alarm_name)
        
        # 筛选该网格的故障小区
        fault_cells = []
        for cell in self._cell_mapping_cache:
            if cell.get('grid_id') == grid_id and cell['cgi'] in cgi_alarms:
                fault_cells.append({
                    'cgi': cell['cgi'],
                    'celname': cell.get('celname', ''),
                    'grid_id': cell['grid_id'],
                    'grid_name': cell.get('grid_name', ''),
                    'alarms': '; '.join(cgi_alarms[cell['cgi']])
                })
        
        return fault_cells

    def get_fault_cells_details(self, performance_only: bool = False) -> List[Dict[str, Any]]:
        """
        获取所有故障小区的详细信息（包含告警信息）
        
        Args:
            performance_only: 是否只统计影响性能的告警
        
        Returns:
            故障小区列表，每个小区包含：cgi, celname, grid_id, grid_name, alarm_names, alarm_count
        """
        if not self.mysql:
            logger.warning("MySQL未连接，无法获取告警数据")
            return []
        
        self._refresh_cache()
        
        # 获取当前告警（使用配置的默认时间范围）
        now = datetime.now()
        start_time = now - timedelta(hours=self.default_query_hours)
        
        # 使用自适应查询获取中兴告警
        zte_alarms = self._get_alarms_adaptive('cur_alarm', start_time)
        logger.info(f"获取到 {len(zte_alarms)} 条中兴告警")
        
        # 使用自适应查询获取诺基亚告警
        nokia_alarms = self._get_alarms_adaptive('cur_alarm_nokia', start_time)
        logger.info(f"获取到 {len(nokia_alarms)} 条诺基亚告警")
        
        # 如果只统计影响性能的告警，进行过滤
        if performance_only:
            zte_alarms = [
                alarm for alarm in zte_alarms
                if alarm.get('alarm_name', '') in self.PERFORMANCE_AFFECTING_ALARMS_ZTE
            ]
            nokia_alarms = [
                alarm for alarm in nokia_alarms
                if alarm.get('alarm_name', '') in self.PERFORMANCE_AFFECTING_ALARMS_NOKIA
            ]
            logger.info(f"过滤后: {len(zte_alarms)} 条中兴影响性能告警, {len(nokia_alarms)} 条诺基亚影响性能告警")
        
        # 匹配告警到CGI，并记录告警名称
        cgi_alarms = {}  # CGI -> 告警名称列表
        
        # 匹配中兴告警
        for alarm in zte_alarms:
            cgis = self.match_zte_alarm(alarm)
            alarm_name = alarm.get('alarm_name', '未知告警')
            for cgi in cgis:
                if cgi not in cgi_alarms:
                    cgi_alarms[cgi] = []
                cgi_alarms[cgi].append(alarm_name)
        
        # 匹配诺基亚告警
        for alarm in nokia_alarms:
            cgis = self.match_nokia_alarm(alarm)
            alarm_name = alarm.get('alarm_name', '未知告警')
            for cgi in cgis:
                if cgi not in cgi_alarms:
                    cgi_alarms[cgi] = []
                cgi_alarms[cgi].append(alarm_name)
        
        logger.info(f"匹配到 {len(cgi_alarms)} 个故障小区")
        
        # 获取网格信息（包括网格名称和标签）
        grid_info_map = {}
        try:
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
            logger.info(f"获取到 {len(grid_info_map)} 个网格信息")
        except Exception as e:
            logger.warning(f"获取网格信息失败: {e}")
        
        # 构建故障小区详细信息列表
        fault_cells = []
        for cgi, alarm_list in cgi_alarms.items():
            # 在映射表中查找小区信息
            cell_info = None
            for cell in self._cell_mapping_cache:
                if cell['cgi'] == cgi:
                    cell_info = cell
                    break
            
            if cell_info and cell_info.get('grid_id'):
                grid_id = cell_info['grid_id']
                # 从grid_info_map获取网格名称和标签
                grid_info = grid_info_map.get(grid_id, {})
                
                # 去重告警名称
                unique_alarms = list(set(alarm_list))
                fault_cells.append({
                    'cgi': cgi,
                    'celname': cell_info.get('celname', ''),
                    'grid_id': grid_id,
                    'grid_name': grid_info.get('grid_name', cell_info.get('grid_name', '')),
                    'grid_pp': grid_info.get('grid_pp', ''),
                    'alarm_names': '; '.join(unique_alarms),
                    'alarm_count': len(alarm_list)
                })
        
        logger.info(f"返回 {len(fault_cells)} 个故障小区详细信息")
        return fault_cells
