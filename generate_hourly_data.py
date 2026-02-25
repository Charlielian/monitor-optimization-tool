#!/usr/bin/env python3
"""
为高铁小区生成2月2日和3日的小时级数据

功能：
1. 从hsr_info表获取所有高铁小区信息
2. 为每个小区生成2月2日和3日的小时级数据
3. 将数据插入到cell_4g_metrics_hour和cell_5g_metrics_hour表中
"""

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 使用项目中的PostgresClient
from db.pg import PostgresClient
from db.mysql import MySQLClient

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
        self.mysql_client = None
        self.pg_client = None
        self.config = self._load_config()
        self.setup_connections()
    
    def _load_config(self) -> Dict[str, Any]:
        """从config.json文件加载配置信息"""
        config = {}
        project_root = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(project_root, "config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info(f"成功加载配置文件: {config_path}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        else:
            logger.warning(f"配置文件不存在: {config_path}")
        
        return config
    
    def setup_connections(self):
        """设置数据库连接"""
        # MySQL连接（用于获取hsr_info表数据）
        try:
            mysql_config = self.config.get("mysql_config", {
                "host": "localhost",
                "port": 3306,
                "database": "optimization_toolbox",
                "user": "root",
                "password": "10300"
            })
            self.mysql_client = MySQLClient(mysql_config)
            logger.info("MySQL连接成功")
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
        
        # PostgreSQL连接（用于插入数据）
        try:
            pg_config = {
                "host": "192.168.31.99",
                "port": 5432,
                "database": "postgres",
                "user": "postgres",
                "password": "103001",
                "connect_timeout": 10,
                "application_name": "generate_hourly_data",
                "pool_min": 5,
                "pool_max": 20
            }
            self.pg_client = PostgresClient(pg_config)
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
            all_cells = self.mysql_client.fetch_all(sql)
            logger.info(f"成功获取 {len(all_cells)} 个高铁小区（未去重）")
            
            # 对CGI进行去重处理
            seen_cgis = set()
            for cell in all_cells:
                cgi = cell.get('CGI', '')
                if cgi and cgi not in seen_cgis:
                    seen_cgis.add(cgi)
                    cells.append(cell)
            
            logger.info(f"去重后剩余 {len(cells)} 个高铁小区")
        except Exception as e:
            logger.error(f"获取小区信息失败: {e}")
        
        return cells
    
    def generate_hourly_data(self, cell: Dict[str, Any], date: datetime):
        """为单个小区生成指定日期的小时级数据"""
        if not self.pg_client:
            logger.error("PostgreSQL客户端未初始化，无法插入数据")
            return
        
        cgi = cell.get('CGI', '')
        network_type = cell.get('network_type', '')
        
        if not cgi:
            logger.warning(f"小区 {cell.get('celname', '')} 缺少CGI，跳过")
            return
        
        # 根据网络类型选择表名
        if network_type == '4G':
            self._generate_4g_data(cgi, date)
        elif network_type == '5G':
            self._generate_5g_data(cgi, date)
        else:
            logger.warning(f"小区 {cgi} 网络类型未知: {network_type}，跳过")
    
    def _generate_4g_data(self, cgi: str, date: datetime):
        """生成4G小区的小时级数据"""
        try:
            import time
            
            # 串行处理每个小时的数据
            for hour in range(24):
                start_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # 生成随机但合理的性能数据
                pdcp_upoctul = 1000000000 + hour * 100000000  # 上行流量
                pdcp_upoctdl = 2000000000 + hour * 200000000  # 下行流量
                dl_prb_utilization = 10.0 + hour * 0.5  # 下行PRB利用率
                ul_prb_utilization = 5.0 + hour * 0.3  # 上行PRB利用率
                
                # 插入数据
                sql = """
                    INSERT INTO cell_4g_metrics_hour 
                    (cgi, cell_id, start_time, 
                     "PDCP_UpOctUl", "PDCP_UpOctDl", 
                     "dl_prb_utilization", "ul_prb_utilization")
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cgi, start_time) DO NOTHING
                """
                params = (
                    cgi, cgi, start_time,
                    pdcp_upoctul, pdcp_upoctdl,
                    dl_prb_utilization, ul_prb_utilization
                )
                try:
                    self.pg_client.execute(sql, params)
                    # 添加小延迟，减少连接池压力
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"处理4G小时 {hour} 失败: {e}")
            
            logger.info(f"成功为4G小区 {cgi} 生成 {date.date()} 的小时级数据")
        except Exception as e:
            logger.error(f"生成4G数据失败: {e}")
    
    def _generate_5g_data(self, cgi: str, date: datetime):
        """生成5G小区的小时级数据"""
        try:
            import time
            
            # 串行处理每个小时的数据
            for hour in range(24):
                start_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # 生成随机但合理的性能数据
                rlc_upoctul = 1500000000 + hour * 150000000  # 上行流量
                rlc_upoctdl = 3000000000 + hour * 300000000  # 下行流量
                rru_puschprbassn = 20 + hour  # PUSCH PRB分配数
                rru_pdschprbassn = 40 + hour * 2  # PDSCH PRB分配数
                rru_puschprbtot = 100  # PUSCH PRB总数
                rru_pdschprbtot = 100  # PDSCH PRB总数
                
                # 插入数据
                sql = """
                    INSERT INTO cell_5g_metrics_hour 
                    ("Ncgi", start_time, 
                     "RLC_UpOctUl", "RLC_UpOctDl", 
                     "RRU_PuschPrbAssn", "RRU_PdschPrbAssn", 
                     "RRU_PuschPrbTot", "RRU_PdschPrbTot")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ("Ncgi", start_time) DO NOTHING
                """
                params = (
                    cgi, start_time,
                    rlc_upoctul, rlc_upoctdl,
                    rru_puschprbassn, rru_pdschprbassn,
                    rru_puschprbtot, rru_pdschprbtot
                )
                try:
                    self.pg_client.execute(sql, params)
                    # 添加小延迟，减少连接池压力
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"处理5G小时 {hour} 失败: {e}")
            
            logger.info(f"成功为5G小区 {cgi} 生成 {date.date()} 的小时级数据")
        except Exception as e:
            logger.error(f"生成5G数据失败: {e}")
    
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
        # 清空hour表数据
        if generator.pg_client:
            logger.info("开始清空cell_4g_metrics_hour表数据")
            generator.pg_client.execute("DELETE FROM cell_4g_metrics_hour")
            logger.info("成功清空cell_4g_metrics_hour表数据")
            
            logger.info("开始清空cell_5g_metrics_hour表数据")
            generator.pg_client.execute("DELETE FROM cell_5g_metrics_hour")
            logger.info("成功清空cell_5g_metrics_hour表数据")
        
        # 获取所有高铁小区
        cells = generator.get_hsr_cells()
        if not cells:
            logger.error("未获取到小区信息，无法生成数据")
            return
        
        # 生成2月2日和3日的数据
        dates = [
            datetime(2026, 2, 2),  # 2月2日
            datetime(2026, 2, 3)   # 2月3日
        ]
        
        for date in dates:
            logger.info(f"开始生成 {date.date()} 的小时级数据")
            
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
                    import time
                    time.sleep(0.1)
                
                # 创建并启动线程
                thread = threading.Thread(
                    target=generator.generate_hourly_data,
                    args=(cell, date)
                )
                threads.append(thread)
                thread.start()
                thread_count += 1
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            logger.info(f"完成生成 {date.date()} 的小时级数据")
            
    finally:
        generator.close_connections()
        logger.info("数据生成任务完成")


if __name__ == "__main__":
    main()
