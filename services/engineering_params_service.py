"""工参表服务 - 用于小区区域分类"""
from typing import Dict, Optional
from db.mysql import MySQLClient
import logging

logger = logging.getLogger(__name__)


class EngineeringParamsService:
    """工参表服务，提供基于工参表的区域分类"""

    def __init__(self, mysql_client: MySQLClient) -> None:
        self.mysql = mysql_client
        self._region_cache: Dict[str, str] = {}
        self._load_region_mapping()

    def _load_region_mapping(self) -> None:
        """从工参表加载 CGI 到区域的映射关系"""
        try:
            sql = """
                SELECT cgi, area_compy, celname
                FROM engineering_params
                WHERE cgi IS NOT NULL AND cgi != ''
            """
            rows = self.mysql.fetch_all(sql)
            
            for row in rows:
                cgi = row.get("cgi", "").strip()
                area_compy = row.get("area_compy", "").strip()
                celname = row.get("celname", "").strip()
                
                if not cgi:
                    continue
                
                # 优先级1: 根据 area_compy 字段分类
                region = self._classify_by_area_compy(area_compy)
                
                # 优先级2: 如果 area_compy 未能分类，则根据小区名分类
                if region == "江城区" and celname:
                    region = self._classify_by_celname(celname)
                
                self._region_cache[cgi] = region
            
            logger.info(f"工参表区域映射加载完成，共 {len(self._region_cache)} 条记录")
        except Exception as e:
            logger.error(f"加载工参表区域映射失败: {e}")
            self._region_cache = {}

    @staticmethod
    def _classify_by_area_compy(area_compy: str) -> str:
        """根据 area_compy 字段分类区域
        
        Args:
            area_compy: 区域公司字段
            
        Returns:
            区域名称
        """
        if not area_compy:
            return "江城区"
        
        area_compy_lower = area_compy.lower()
        
        if "阳西分公司" in area_compy:
            return "阳西县"
        elif "阳春分公司" in area_compy:
            return "阳春市"
        elif "阳东分公司" in area_compy:
            return "阳东县"
        elif "南区分公司" in area_compy:
            return "南区"
        elif "江城分公司" in area_compy:
            return "江城区"
        else:
            return "江城区"

    @staticmethod
    def _classify_by_celname(celname: str) -> str:
        """根据小区名分类区域
        
        Args:
            celname: 小区名
            
        Returns:
            区域名称
        """
        if not celname:
            return "江城区"
        
        celname_str = str(celname).strip()
        
        # 中文匹配
        if "阳江阳西" in celname_str:
            return "阳西县"
        elif "阳江阳春" in celname_str:
            return "阳春市"
        elif "阳江阳东" in celname_str:
            return "阳东县"
        elif "阳江南区" in celname_str:
            return "南区"
        elif "阳江江城" in celname_str:
            return "江城区"
        
        # 英文匹配
        celname_lower = celname_str.lower()
        if "yangjiangyangxi" in celname_lower:
            return "阳西县"
        elif "yangjiangyangchun" in celname_lower:
            return "阳春市"
        elif "yangjiangyangdong" in celname_lower:
            return "阳东县"
        elif "yangjiangnanqu" in celname_lower:
            return "南区"
        elif "yangjiangjiangcheng" in celname_lower:
            return "江城区"
        
        return "江城区"

    def get_region_by_cgi(self, cgi: str) -> str:
        """根据 CGI 获取区域
        
        Args:
            cgi: 小区 CGI
            
        Returns:
            区域名称，如果未找到则返回 "江城区"
        """
        if not cgi:
            return "江城区"
        
        cgi_str = str(cgi).strip()
        return self._region_cache.get(cgi_str, "江城区")

    def classify_region_with_fallback(
        self, 
        cgi: Optional[str] = None, 
        cellname: Optional[str] = None, 
        network_type: str = "4G"
    ) -> str:
        """综合分类区域（带回退机制）
        
        优先级：
        1. 工参表 CGI 映射
        2. 小区名分类
        3. 默认江城区
        
        Args:
            cgi: 小区 CGI
            cellname: 小区名
            network_type: 网络类型 "4G" 或 "5G"
            
        Returns:
            区域名称
        """
        # 优先使用工参表映射
        if cgi:
            region = self.get_region_by_cgi(cgi)
            if region != "江城区":  # 如果找到了非默认区域，直接返回
                return region
        
        # 回退到小区名分类
        if cellname:
            return self._classify_by_celname(cellname)
        
        # 最终默认
        return "江城区"

    def reload_mapping(self) -> None:
        """重新加载区域映射（用于数据更新后刷新缓存）"""
        self._region_cache.clear()
        self._load_region_mapping()


__all__ = ["EngineeringParamsService"]
