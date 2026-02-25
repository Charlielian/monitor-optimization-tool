#!/usr/bin/env python3
"""
性能分析工具
分析日志文件中的请求时延，识别慢请求和性能瓶颈
"""

import re
import sys
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class PerformanceAnalyzer:
    """性能日志分析器"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.requests = []
        self.slow_requests = []
        self.db_queries = []
        
    def parse_log(self):
        """解析日志文件"""
        print(f"正在分析日志文件: {self.log_file}")
        print("=" * 80)
        
        # 请求日志模式
        request_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?'
            r'([🔴🟡🟢⚡])\s+(GET|POST|PUT|DELETE)\s+(\S+)\s+\|\s+'
            r'状态:\s+(\d+)\s+\|\s+'
            r'耗时:\s+([\d.]+)ms\s+\|\s+'
            r'大小:\s+([\d.]+)KB'
        )
        
        # 数据库查询模式
        db_pattern = re.compile(
            r'([🔴🟡])\s+(MySQL|PostgreSQL)查询(超慢|慢)?:\s+([\d.]+)ms(?:,\s+返回\s+(\d+)\s+行)?'
        )
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # 解析请求日志
                    match = request_pattern.search(line)
                    if match:
                        timestamp, emoji, method, path, status, elapsed, size = match.groups()
                        elapsed_ms = float(elapsed)
                        size_kb = float(size)
                        
                        request_info = {
                            'timestamp': timestamp,
                            'emoji': emoji,
                            'method': method,
                            'path': path,
                            'status': int(status),
                            'elapsed_ms': elapsed_ms,
                            'size_kb': size_kb
                        }
                        
                        self.requests.append(request_info)
                        
                        # 记录慢请求（>1秒）
                        if elapsed_ms > 1000:
                            self.slow_requests.append(request_info)
                    
                    # 解析数据库查询日志
                    db_match = db_pattern.search(line)
                    if db_match:
                        emoji, db_type, slow_type, elapsed, rows = db_match.groups()
                        self.db_queries.append({
                            'db_type': db_type,
                            'elapsed_ms': float(elapsed),
                            'rows': int(rows) if rows else 0,
                            'slow_type': slow_type or 'normal'
                        })
        
        except FileNotFoundError:
            print(f"❌ 错误: 找不到日志文件 {self.log_file}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 错误: 解析日志文件失败 - {e}")
            sys.exit(1)
    
    def analyze(self):
        """分析性能数据"""
        if not self.requests:
            print("⚠️  未找到请求日志数据")
            return
        
        print(f"\n📊 总体统计")
        print("=" * 80)
        print(f"总请求数: {len(self.requests)}")
        print(f"慢请求数 (>1s): {len(self.slow_requests)} ({len(self.slow_requests)/len(self.requests)*100:.1f}%)")
        
        # 计算平均响应时间
        total_time = sum(r['elapsed_ms'] for r in self.requests)
        avg_time = total_time / len(self.requests)
        print(f"平均响应时间: {avg_time:.2f}ms")
        
        # 计算中位数
        sorted_times = sorted(r['elapsed_ms'] for r in self.requests)
        median_time = sorted_times[len(sorted_times) // 2]
        print(f"中位数响应时间: {median_time:.2f}ms")
        
        # 计算95分位数
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]
        print(f"95分位数响应时间: {p95_time:.2f}ms")
        
        # 最慢的请求
        slowest = max(self.requests, key=lambda x: x['elapsed_ms'])
        print(f"最慢请求: {slowest['method']} {slowest['path']} - {slowest['elapsed_ms']:.2f}ms")
        
        # 按路径统计
        print(f"\n📍 按路径统计 (Top 10 最慢)")
        print("=" * 80)
        path_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'max_time': 0})
        
        for req in self.requests:
            path = req['path']
            path_stats[path]['count'] += 1
            path_stats[path]['total_time'] += req['elapsed_ms']
            path_stats[path]['max_time'] = max(path_stats[path]['max_time'], req['elapsed_ms'])
        
        # 计算平均时间并排序
        path_avg = []
        for path, stats in path_stats.items():
            avg = stats['total_time'] / stats['count']
            path_avg.append((path, avg, stats['max_time'], stats['count']))
        
        path_avg.sort(key=lambda x: x[1], reverse=True)
        
        for i, (path, avg, max_time, count) in enumerate(path_avg[:10], 1):
            print(f"{i:2}. {path:50} | 平均: {avg:7.2f}ms | 最大: {max_time:7.2f}ms | 次数: {count:4}")
        
        # 按方法统计
        print(f"\n🔧 按HTTP方法统计")
        print("=" * 80)
        method_stats = defaultdict(lambda: {'count': 0, 'total_time': 0})
        
        for req in self.requests:
            method = req['method']
            method_stats[method]['count'] += 1
            method_stats[method]['total_time'] += req['elapsed_ms']
        
        for method, stats in sorted(method_stats.items()):
            avg = stats['total_time'] / stats['count']
            print(f"{method:6} | 请求数: {stats['count']:5} | 平均耗时: {avg:7.2f}ms")
        
        # 状态码统计
        print(f"\n📈 HTTP状态码分布")
        print("=" * 80)
        status_counter = Counter(r['status'] for r in self.requests)
        for status, count in sorted(status_counter.items()):
            percentage = count / len(self.requests) * 100
            print(f"{status}: {count:5} ({percentage:5.1f}%)")
        
        # 慢请求详情
        if self.slow_requests:
            print(f"\n🐌 慢请求详情 (>1秒, Top 20)")
            print("=" * 80)
            slow_sorted = sorted(self.slow_requests, key=lambda x: x['elapsed_ms'], reverse=True)
            
            for i, req in enumerate(slow_sorted[:20], 1):
                print(f"{i:2}. [{req['timestamp']}] {req['method']:6} {req['path']:50} | {req['elapsed_ms']:7.2f}ms | {req['status']}")
        
        # 数据库查询统计
        if self.db_queries:
            print(f"\n💾 数据库查询统计")
            print("=" * 80)
            print(f"总查询数: {len(self.db_queries)}")
            
            mysql_queries = [q for q in self.db_queries if q['db_type'] == 'MySQL']
            pg_queries = [q for q in self.db_queries if q['db_type'] == 'PostgreSQL']
            
            if mysql_queries:
                avg_mysql = sum(q['elapsed_ms'] for q in mysql_queries) / len(mysql_queries)
                slow_mysql = len([q for q in mysql_queries if q['elapsed_ms'] > 1000])
                print(f"MySQL查询: {len(mysql_queries)} 次 | 平均: {avg_mysql:.2f}ms | 慢查询: {slow_mysql}")
            
            if pg_queries:
                avg_pg = sum(q['elapsed_ms'] for q in pg_queries) / len(pg_queries)
                slow_pg = len([q for q in pg_queries if q['elapsed_ms'] > 1000])
                print(f"PostgreSQL查询: {len(pg_queries)} 次 | 平均: {avg_pg:.2f}ms | 慢查询: {slow_pg}")
        
        # 性能建议
        print(f"\n💡 性能优化建议")
        print("=" * 80)
        
        if len(self.slow_requests) / len(self.requests) > 0.1:
            print("⚠️  慢请求比例较高 (>10%)，建议优化以下方面：")
            print("   1. 检查数据库查询是否有索引")
            print("   2. 考虑添加缓存机制")
            print("   3. 优化数据处理逻辑")
        
        if avg_time > 500:
            print("⚠️  平均响应时间较慢 (>500ms)，建议：")
            print("   1. 分析慢请求路径，针对性优化")
            print("   2. 考虑使用异步处理")
            print("   3. 优化数据库连接池配置")
        
        if self.db_queries:
            slow_db = [q for q in self.db_queries if q['elapsed_ms'] > 1000]
            if len(slow_db) > len(self.db_queries) * 0.1:
                print("⚠️  数据库慢查询较多，建议：")
                print("   1. 添加必要的索引")
                print("   2. 优化SQL查询语句")
                print("   3. 考虑分页查询大数据集")
        
        if not self.slow_requests and avg_time < 200:
            print("✅ 性能表现良好！继续保持。")


def main():
    """主函数"""
    # 默认日志文件路径
    default_log = "logs/monitoring_app.log"
    
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        log_file = default_log
    
    if not Path(log_file).exists():
        print(f"❌ 错误: 日志文件不存在: {log_file}")
        print(f"\n使用方法: python {sys.argv[0]} [日志文件路径]")
        print(f"默认路径: {default_log}")
        sys.exit(1)
    
    analyzer = PerformanceAnalyzer(log_file)
    analyzer.parse_log()
    analyzer.analyze()
    
    print("\n" + "=" * 80)
    print("分析完成！")


if __name__ == "__main__":
    main()
