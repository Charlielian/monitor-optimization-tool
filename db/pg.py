import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor


class PostgresClient:
    """Simple short-lived connection helper for PostgreSQL."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._pool: Optional[pg_pool.ThreadedConnectionPool] = None
        self._init_pool()

    def _init_pool(self) -> None:
        minconn = max(1, int(self.config.get("pool_min", 1)))
        maxconn = max(minconn, int(self.config.get("pool_max", 10)))
        conn_kwargs = {
            "host": self.config["host"],
            "port": self.config["port"],
            "database": self.config["database"],
            "user": self.config["user"],
            "password": self.config["password"],
            "cursor_factory": RealDictCursor,
        }
        if "connect_timeout" in self.config:
            conn_kwargs["connect_timeout"] = int(self.config["connect_timeout"])
        if self.config.get("application_name"):
            conn_kwargs["application_name"] = self.config["application_name"]
        try:
            self._pool = pg_pool.ThreadedConnectionPool(minconn, maxconn, **conn_kwargs)
        except Exception as exc:  # pragma: no cover - external dependency
            self.logger.error("PostgreSQL连接池初始化失败: %s", exc)
            self._pool = None

    def reconnect(self) -> bool:
        """尝试重新连接数据库
        
        Returns:
            bool: 重连是否成功
        """
        try:
            # 关闭现有连接池
            if self._pool is not None:
                try:
                    self._pool.closeall()
                except Exception as e:
                    self.logger.debug(f"关闭旧连接池时出错: {e}")
                self._pool = None
            
            # 重新初始化连接池
            self._init_pool()
            
            # 测试连接
            if self._pool is not None and self.test_connection():
                self.logger.info("✓ PostgreSQL 重连成功")
                return True
            else:
                self.logger.debug("PostgreSQL 重连失败")
                return False
        except Exception as e:
            self.logger.debug(f"PostgreSQL 重连异常: {e}")
            return False

    @contextmanager
    def _get_conn(self):
        conn = None
        pooled = False
        if self._pool is not None:
            conn = self._pool.getconn()
            pooled = True
        else:
            conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
                cursor_factory=RealDictCursor,
                connect_timeout=5,  # 添加5秒连接超时
            )
        try:
            yield conn
        finally:
            if conn is not None:
                try:
                    if not conn.closed:
                        conn.rollback()
                except Exception:
                    pass
                if pooled and self._pool is not None:
                    self._pool.putconn(conn)
                else:
                    conn.close()

    def test_connection(self) -> bool:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception as exc:  # pragma: no cover - external dependency
            self.logger.error("PostgreSQL连接失败: %s", exc)
            return False

    def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        """Run a SELECT-like statement and return a list of dict rows."""
        import time
        query_start = time.time()
        
        with self._get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    rows = cur.fetchall()
                    
                    query_elapsed = (time.time() - query_start) * 1000
                    row_count = len(rows)
                    
                    # 根据耗时记录不同级别的日志
                    if query_elapsed > 2000:
                        self.logger.warning(f"      ├─ 🔴 PostgreSQL查询超慢: {query_elapsed:.2f}ms, 返回 {row_count} 行")
                        self.logger.warning(f"      └─ SQL: {sql[:200]}...")
                    elif query_elapsed > 1000:
                        self.logger.warning(f"      ├─ 🟡 PostgreSQL查询慢: {query_elapsed:.2f}ms, 返回 {row_count} 行")
                    elif query_elapsed > 500:
                        self.logger.info(f"      ├─ PostgreSQL查询: {query_elapsed:.2f}ms, 返回 {row_count} 行")
                    else:
                        self.logger.debug(f"      ├─ PostgreSQL查询: {query_elapsed:.2f}ms, 返回 {row_count} 行")
            except Exception as e:
                query_elapsed = (time.time() - query_start) * 1000
                self.logger.error(f"PostgreSQL 查询失败 (耗时 {query_elapsed:.2f}ms): {e}\nSQL: {sql[:200]}", exc_info=True)
                conn.rollback()
                raise
        return [dict(row) for row in rows]

    def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        import time
        query_start = time.time()
        
        with self._get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    row = cur.fetchone()
                    
                    query_elapsed = (time.time() - query_start) * 1000
                    if query_elapsed > 1000:
                        self.logger.warning(f"      ├─ 🟡 PostgreSQL查询慢: {query_elapsed:.2f}ms")
                    elif query_elapsed > 500:
                        self.logger.info(f"      ├─ PostgreSQL查询: {query_elapsed:.2f}ms")
                    else:
                        self.logger.debug(f"      ├─ PostgreSQL查询: {query_elapsed:.2f}ms")
            except Exception as e:
                query_elapsed = (time.time() - query_start) * 1000
                self.logger.error(f"PostgreSQL 查询失败 (耗时 {query_elapsed:.2f}ms): {e}", exc_info=True)
                conn.rollback()
                raise
        return dict(row) if row else None

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> int:
        """Execute INSERT/UPDATE/DELETE returning affected rows."""
        import time
        query_start = time.time()
        
        with self._get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    conn.commit()
                    rowcount = cur.rowcount
                    
                    query_elapsed = (time.time() - query_start) * 1000
                    if query_elapsed > 1000:
                        self.logger.warning(f"      ├─ 🟡 PostgreSQL执行慢: {query_elapsed:.2f}ms, 影响 {rowcount} 行")
                    elif query_elapsed > 500:
                        self.logger.info(f"      ├─ PostgreSQL执行: {query_elapsed:.2f}ms, 影响 {rowcount} 行")
                    else:
                        self.logger.debug(f"      ├─ PostgreSQL执行: {query_elapsed:.2f}ms, 影响 {rowcount} 行")
                    
                    return rowcount
            except Exception as e:
                query_elapsed = (time.time() - query_start) * 1000
                self.logger.error(f"PostgreSQL 执行失败 (耗时 {query_elapsed:.2f}ms): {e}", exc_info=True)
                conn.rollback()
                raise


__all__ = ["PostgresClient"]
