#!/usr/bin/env python3
"""
为高铁小区生成15分钟粒度的昨日及今日数据

功能：
1. 从hsr_info表获取所有高铁小区信息
2. 为每个小区生成15分钟粒度的昨日及今日数据
3. 将生成的数据插入到cell_4g_metrics和cell_5g_metrics表中
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import threading

from config import Config
from db.mysql import MySQLClient
from db.pg import PostgresClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataGenerator:
    """数据生成器"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.cfg = Config()
        self.mysql_client = None
        self.pg_client = None
        self.setup_connections()
    
    def setup_connections(self):
        """设置数据库连接"""
        # MySQL连接（用于获取hsr_info表数据）
        try:
            self.mysql_client = MySQLClient(self.cfg.mysql_config)
            if self.mysql_client.test_connection():
                logger.info("MySQL连接成功")
            else:
                logger.error("MySQL连接失败")
                self.mysql_client = None
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
        
        # PostgreSQL连接（用于插入数据）
        try:
            self.pg_client = PostgresClient(self.cfg.pgsql_config)
            if self.pg_client.test_connection():
                logger.info("PostgreSQL连接成功")
            else:
                logger.warning("PostgreSQL连接测试失败，但将尝试在执行SQL时连接")
        except Exception as e:
            logger.error(f"PostgreSQL连接失败: {e}")
            self.pg_client = None
    
    def get_hsr_cells(self) -> List[Dict[str, Any]]:
        """从hsr_info表获取所有高铁小区信息"""
        cells = []
        if not self.mysql_client:
            logger.error("MySQL客户端未初始化，无法获取小区信息")
            return cells
        
        try:
            sql = """
                SELECT 
                    id, 
                    line_name, 
                    Transmitting_Point_Name as site_name, 
                    celname, 
                    CGI, 
                    zhishi as network_type
                FROM hsr_info
                ORDER BY line_name, site_name, celname
            """
            cells = self.mysql_client.fetch_all(sql)
            # 去重，避免重复处理同一个CGI
            unique_cells = []
            seen_cgis = set()
            for cell in cells:
                cgi = cell.get('CGI', '')
                if cgi and cgi not in seen_cgis:
                    seen_cgis.add(cgi)
                    unique_cells.append(cell)
            logger.info(f"成功获取 {len(unique_cells)} 个去重后的高铁小区")
            return unique_cells
        except Exception as e:
            logger.error(f"获取小区信息失败: {e}")
            return cells
    
    def generate_15min_data(self, cell: Dict[str, Any]):
        """为单个小区生成15分钟粒度的昨日及今日数据"""
        if not self.pg_client:
            logger.error("PostgreSQL客户端未初始化，无法插入数据")
            return
        
        cgi = cell.get('CGI', '')
        network_type = cell.get('network_type', '')
        celname = cell.get('celname', '')
        
        if not cgi:
            logger.warning(f"小区 {celname} 缺少CGI，跳过")
            return
        
        # 根据网络类型选择表名
        if network_type == '4G':
            self._generate_4g_data(cgi, celname)
        elif network_type == '5G':
            self._generate_5g_data(cgi, celname)
        else:
            logger.warning(f"小区 {cgi} 网络类型未知: {network_type}，跳过")
    
    def _generate_4g_data(self, cgi: str, celname: str):
        """生成4G小区的15分钟粒度数据"""
        try:
            # 生成昨日数据
            yesterday = datetime.now().date() - timedelta(days=1)
            self._generate_4g_data_for_date(cgi, celname, yesterday)
            
            # 生成今日数据
            today = datetime.now().date()
            self._generate_4g_data_for_date(cgi, celname, today)
            
            logger.info(f"成功为4G小区 {cgi} ({celname}) 生成15分钟粒度数据")
        except Exception as e:
            logger.error(f"生成4G数据失败: {e}")
    
    def _generate_4g_data_for_date(self, cgi: str, celname: str, date: datetime.date):
        """为指定日期生成4G小区的15分钟粒度数据"""
        # 为每个15分钟间隔生成数据
        for hour in range(24):
            for quarter in range(4):
                # 计算开始时间
                start_time = datetime(date.year, date.month, date.day, hour, quarter * 15, 0, 0)
                
                # 生成随机但合理的性能数据
                pdcp_upoctul = 100000000 + (hour * 4 + quarter) * 10000000  # 上行流量
                pdcp_upoctdl = 200000000 + (hour * 4 + quarter) * 20000000  # 下行流量
                rrc_att_conn_estab = 100 + (hour * 4 + quarter) * 10  # RRC连接建立尝试次数
                rrc_succ_conn_estab = rrc_att_conn_estab * 0.95  # RRC连接建立成功次数
                erab_nbr_att_estab = 90 + (hour * 4 + quarter) * 9  # ERAB建立尝试次数
                erab_nbr_succ_estab = erab_nbr_att_estab * 0.96  # ERAB建立成功次数
                rru_pusch_prb_assn = 20 + (hour * 4 + quarter)  # PUSCH PRB分配数
                rru_pusch_prb_tot = 100  # PUSCH PRB总数
                rru_pdsch_prb_assn = 30 + (hour * 4 + quarter) * 2  # PDSCH PRB分配数
                rru_pdsch_prb_tot = 100  # PDSCH PRB总数
                
                # 计算衍生指标
                total_traffic_gb = (pdcp_upoctul + pdcp_upoctdl) / 1000000000.0  # 总流量(GB)
                rrc_success_rate = rrc_succ_conn_estab / rrc_att_conn_estab if rrc_att_conn_estab > 0 else 0  # RRC连接成功率
                erab_success_rate = erab_nbr_succ_estab / erab_nbr_att_estab if erab_nbr_att_estab > 0 else 0  # ERAB建立成功率
                dl_prb_utilization = rru_pdsch_prb_assn / rru_pdsch_prb_tot * 100  # 下行PRB利用率
                ul_prb_utilization = rru_pusch_prb_assn / rru_pusch_prb_tot * 100  # 上行PRB利用率
                
                # 插入数据
                sql = """
                    INSERT INTO cell_4g_metrics 
                    (start_time, cell_id, cgi, cellname, 
                     "PDCP_UpOctUl", "PDCP_UpOctDl", 
                     "RRC_AttConnEstab", "RRC_SuccConnEstab", 
                     "ERAB_NbrAttEstab", "ERAB_NbrSuccEstab", 
                     "RRU_PuschPrbAssn", "RRU_PuschPrbTot", 
                     "RRU_PdschPrbAssn", "RRU_PdschPrbTot", 
                     total_traffic_gb, rrc_success_rate, erab_success_rate, 
                     dl_prb_utilization, ul_prb_utilization)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (start_time, cell_id) DO NOTHING
                """
                params = (
                    start_time, cgi, cgi, celname,
                    pdcp_upoctul, pdcp_upoctdl,
                    rrc_att_conn_estab, rrc_succ_conn_estab,
                    erab_nbr_att_estab, erab_nbr_succ_estab,
                    rru_pusch_prb_assn, rru_pusch_prb_tot,
                    rru_pdsch_prb_assn, rru_pdsch_prb_tot,
                    total_traffic_gb, rrc_success_rate, erab_success_rate,
                    dl_prb_utilization, ul_prb_utilization
                )
                try:
                    self.pg_client.execute(sql, params)
                    # 添加小延迟，减少连接池压力
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"处理4G 15分钟数据失败: {e}")
    
    def _generate_5g_data(self, cgi: str, celname: str):
        """生成5G小区的15分钟粒度数据"""
        try:
            # 生成昨日数据
            yesterday = datetime.now().date() - timedelta(days=1)
            self._generate_5g_data_for_date(cgi, celname, yesterday)
            
            # 生成今日数据
            today = datetime.now().date()
            self._generate_5g_data_for_date(cgi, celname, today)
            
            logger.info(f"成功为5G小区 {cgi} ({celname}) 生成15分钟粒度数据")
        except Exception as e:
            logger.error(f"生成5G数据失败: {e}")
    
    def _generate_5g_data_for_date(self, cgi: str, celname: str, date: datetime.date):
        """为指定日期生成5G小区的15分钟粒度数据"""
        # 为每个15分钟间隔生成数据
        for hour in range(24):
            for quarter in range(4):
                # 计算开始时间
                start_time = datetime(date.year, date.month, date.day, hour, quarter * 15, 0, 0)
                
                # 生成随机但合理的性能数据
                rlc_upoctul = 150000000 + (hour * 4 + quarter) * 15000000  # 上行流量
                rlc_upoctdl = 300000000 + (hour * 4 + quarter) * 30000000  # 下行流量
                rru_puschprbassn = 20 + (hour * 4 + quarter)  # PUSCH PRB分配数
                rru_puschprbtot = 100  # PUSCH PRB总数
                rru_pdschprbassn = 40 + (hour * 4 + quarter) * 2  # PDSCH PRB分配数
                rru_pdschprbtot = 100  # PDSCH PRB总数
                rrc_att_conn_estab = 120 + (hour * 4 + quarter) * 12  # RRC连接建立尝试次数
                rrc_succ_conn_estab = rrc_att_conn_estab * 0.96  # RRC连接建立成功次数
                erab_nbr_att_estab = 100 + (hour * 4 + quarter) * 10  # ERAB建立尝试次数
                erab_nbr_succ_estab = erab_nbr_att_estab * 0.97  # ERAB建立成功次数
                
                # 计算衍生指标
                total_traffic_gb = (rlc_upoctul + rlc_upoctdl) / 1000000000.0  # 总流量(GB)
                rrc_success_rate = rrc_succ_conn_estab / rrc_att_conn_estab if rrc_att_conn_estab > 0 else 0  # RRC连接成功率
                erab_success_rate = erab_nbr_succ_estab / erab_nbr_att_estab if erab_nbr_att_estab > 0 else 0  # ERAB建立成功率
                dl_prb_utilization = rru_pdschprbassn / rru_pdschprbtot * 100  # 下行PRB利用率
                ul_prb_utilization = rru_puschprbassn / rru_puschprbtot * 100  # 上行PRB利用率
                
                # 插入数据
                sql = """
                    INSERT INTO cell_5g_metrics 
                    (start_time, "Ncgi", 
                     "RLC_UpOctUl", "RLC_UpOctDl", 
                     "RRC_AttConnEstab", "RRC_SuccConnEstab", 
                     "RRU_PuschPrbAssn", "RRU_PuschPrbTot", 
                     "RRU_PdschPrbAssn", "RRU_PdschPrbTot")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (start_time, "Ncgi") DO NOTHING
                """
                params = (
                    start_time, cgi,
                    rlc_upoctul, rlc_upoctdl,
                    rrc_att_conn_estab, rrc_succ_conn_estab,
                    rru_puschprbassn, rru_puschprbtot,
                    rru_pdschprbassn, rru_pdschprbtot
                )
                try:
                    self.pg_client.execute(sql, params)
                    # 添加小延迟，减少连接池压力
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"处理5G 15分钟数据失败: {e}")
    
    def close_connections(self):
        """关闭数据库连接"""
        if self.mysql_client:
            logger.info("MySQL客户端已初始化，连接由连接池管理")
        
        if self.pg_client:
            logger.info("PostgreSQL客户端已初始化，连接由连接池管理")


def main():
    """主函数"""
    generator = DataGenerator()
    
    try:
        # 获取所有高铁小区
        cells = generator.get_hsr_cells()
        if not cells:
            logger.error("未获取到小区信息，无法生成数据")
            return
        
        # 使用多线程并行处理小区数据
        threads = []
        max_threads = 10  # 限制最大线程数，避免数据库连接过多
        thread_count = 0
        
        for cell in cells:
            # 等待线程数达到上限时，等待一些线程完成
            while thread_count >= max_threads:
                for t in threads:
                    if not t.is_alive():
                        threads.remove(t)
                        thread_count -= 1
                if thread_count < max_threads:
                    break
                # 短暂睡眠，避免忙等
                time.sleep(0.1)
            
            # 创建并启动线程
            thread = threading.Thread(
                target=generator.generate_15min_data,
                args=(cell,)
            )
            threads.append(thread)
            thread.start()
            thread_count += 1
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        logger.info("完成生成所有小区的15分钟粒度数据")
            
    finally:
        generator.close_connections()
        logger.info("数据生成任务完成")


if __name__ == "__main__":
    main()
