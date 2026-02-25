"""MySQL 数据库连接和查询封装"""
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DatabaseError
import logging

logger = logging.getLogger(__name__)


class MySQLClient:
    """MySQL 客户端封装，使用 SQLAlchemy"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """初始化 MySQL 连接
        
        Args:
            config: MySQL 配置字典，包含 host, port, database, user, password
        """
        self.config = config
        self.url = self._build_url(config)
        self.engine: Optional[Engine] = None
        self._connect()

    @staticmethod
    def _build_url(config: Dict[str, Any]) -> str:
        """根据配置构建 MySQL 连接 URL
        
        Args:
            config: 配置字典
            
        Returns:
            MySQL 连接 URL
        """
        host = config.get("host", "localhost")
        port = config.get("port", 3306)
        database = config.get("database", "")
        user = config.get("user", "root")
        password = config.get("password", "")
        
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    def _connect(self) -> None:
        """建立数据库连接"""
        try:
            self.engine = create_engine(
                self.url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # 自动检测连接是否有效
                pool_recycle=3600,   # 1小时回收连接
                echo=False
            )
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"MySQL 连接成功: {self.url.split('@')[-1]}")
        except (OperationalError, DatabaseError) as e:
            logger.error(f"MySQL 连接失败: {e}")
            raise

    def reconnect(self) -> bool:
        """尝试重新连接数据库
        
        Returns:
            bool: 重连是否成功
        """
        try:
            # 关闭现有连接
            if self.engine:
                try:
                    self.engine.dispose()
                except Exception as e:
                    logger.debug(f"关闭旧连接时出错: {e}")
                self.engine = None
            
            # 重新连接
            self._connect()
            logger.info("✓ MySQL 重连成功")
            return True
        except (OperationalError, DatabaseError) as e:
            logger.debug(f"MySQL 重连失败: {e}")
            return False

    def fetch_all(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询并返回所有结果

        Args:
            sql: SQL 查询语句
            params: 查询参数（元组或字典）

        Returns:
            查询结果列表，每行为一个字典
        """
        import time
        query_start = time.time()

        if not self.engine:
            raise RuntimeError("MySQL 引擎未初始化")

        try:
            with self.engine.connect() as conn:
                if params:
                    # 如果是元组，使用正则表达式安全地替换参数占位符
                    if isinstance(params, tuple):
                        # 验证参数数量
                        param_count = sql.count('%s')
                        if param_count != len(params):
                            raise ValueError(f"参数数量不匹配: SQL需要{param_count}个参数，提供了{len(params)}个")

                        # 创建命名参数字典
                        param_dict = {f'param_{i}': param for i, param in enumerate(params)}
                        # 使用正则表达式替换%s，避免误替换字符串中的%s
                        import re
                        counter = 0
                        def replacer(match):
                            nonlocal counter
                            result = f':param_{counter}'
                            counter += 1
                            return result
                        sql_with_named_params = re.sub(r'%s', replacer, sql)
                        result = conn.execute(text(sql_with_named_params), param_dict)
                    else:
                        result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                
                # 将结果转换为字典列表
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                
                query_elapsed = (time.time() - query_start) * 1000
                if query_elapsed > 2000:
                    logger.warning(f"      ├─ 🔴 MySQL查询超慢: {query_elapsed:.2f}ms, 返回 {len(rows)} 行")
                    logger.warning(f"      └─ SQL: {sql[:200]}...")
                elif query_elapsed > 1000:
                    logger.warning(f"      ├─ 🟡 MySQL查询慢: {query_elapsed:.2f}ms, 返回 {len(rows)} 行")
                elif query_elapsed > 500:
                    logger.info(f"      ├─ MySQL查询: {query_elapsed:.2f}ms, 返回 {len(rows)} 行")
                else:
                    logger.debug(f"      ├─ MySQL查询: {query_elapsed:.2f}ms, 返回 {len(rows)} 行")
                
                return rows
        except (OperationalError, DatabaseError, ValueError) as e:
            query_elapsed = (time.time() - query_start) * 1000
            logger.error(f"MySQL 查询失败 (耗时 {query_elapsed:.2f}ms): {e}\nSQL: {sql}", exc_info=True)
            # 返回空列表以保持应用程序继续运行（容错设计）
            # 调用方应检查日志以诊断问题
            return []

    def fetch_one(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """执行查询并返回单行结果

        Args:
            sql: SQL 查询语句
            params: 查询参数（元组或字典）

        Returns:
            查询结果字典，如果没有结果则返回 None
        """
        import time
        query_start = time.time()

        if not self.engine:
            raise RuntimeError("MySQL 引擎未初始化")

        try:
            with self.engine.connect() as conn:
                if params:
                    # 如果是元组，使用正则表达式安全地替换参数占位符
                    if isinstance(params, tuple):
                        # 验证参数数量
                        param_count = sql.count('%s')
                        if param_count != len(params):
                            raise ValueError(f"参数数量不匹配: SQL需要{param_count}个参数，提供了{len(params)}个")

                        # 创建命名参数字典
                        param_dict = {f'param_{i}': param for i, param in enumerate(params)}
                        # 使用正则表达式替换%s
                        import re
                        counter = 0
                        def replacer(match):
                            nonlocal counter
                            result = f':param_{counter}'
                            counter += 1
                            return result
                        sql_with_named_params = re.sub(r'%s', replacer, sql)
                        result = conn.execute(text(sql_with_named_params), param_dict)
                    else:
                        result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                
                row = result.fetchone()
                query_elapsed = (time.time() - query_start) * 1000
                
                if query_elapsed > 1000:
                    logger.warning(f"      ├─ 🟡 MySQL查询慢: {query_elapsed:.2f}ms")
                elif query_elapsed > 500:
                    logger.info(f"      ├─ MySQL查询: {query_elapsed:.2f}ms")
                else:
                    logger.debug(f"      ├─ MySQL查询: {query_elapsed:.2f}ms")
                
                if row:
                    columns = result.keys()
                    return dict(zip(columns, row))
                return None
        except (OperationalError, DatabaseError, ValueError) as e:
            query_elapsed = (time.time() - query_start) * 1000
            logger.error(f"MySQL 查询失败 (耗时 {query_elapsed:.2f}ms): {e}\nSQL: {sql}", exc_info=True)
            # 返回None以保持应用程序继续运行（容错设计）
            # 调用方应检查日志以诊断问题
            return None
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        """执行 INSERT/UPDATE/DELETE 操作
        
        Args:
            sql: SQL 语句
            params: 查询参数（元组或字典）
            
        Returns:
            受影响的行数
        """
        import time
        query_start = time.time()
        
        if not self.engine:
            raise RuntimeError("MySQL 引擎未初始化")
        
        try:
            with self.engine.connect() as conn:
                if params:
                    # 如果是元组，转换为字典格式
                    if isinstance(params, tuple):
                        # 为参数创建占位符字典
                        param_dict = {f'param_{i}': param for i, param in enumerate(params)}
                        # 替换SQL中的%s为:param_0, :param_1等
                        sql_with_named_params = sql
                        for i in range(len(params)):
                            sql_with_named_params = sql_with_named_params.replace('%s', f':param_{i}', 1)
                        result = conn.execute(text(sql_with_named_params), param_dict)
                    else:
                        result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                
                # 提交事务
                conn.commit()
                
                affected_rows = result.rowcount
                query_elapsed = (time.time() - query_start) * 1000
                
                if query_elapsed > 1000:
                    logger.warning(f"      ├─ 🟡 MySQL执行慢: {query_elapsed:.2f}ms, 影响 {affected_rows} 行")
                else:
                    logger.info(f"      ├─ MySQL执行: {query_elapsed:.2f}ms, 影响 {affected_rows} 行")
                
                return affected_rows
        except (OperationalError, DatabaseError, ValueError) as e:
            query_elapsed = (time.time() - query_start) * 1000
            logger.error(f"MySQL 执行失败 (耗时 {query_elapsed:.2f}ms): {e}\nSQL: {sql}")
            raise

    def close(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            logger.info("MySQL 连接已关闭")


__all__ = ["MySQLClient"]
