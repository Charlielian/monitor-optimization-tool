#!/usr/bin/env python3
"""
性能日志分析工具
分析 Flask 应用的性能日志，找出慢请求和性能瓶颈
"""

import re
import sys
from collections import defaultdict
from datetime import datetime


def analyze_logs(log_file="logs/monitoring_app.log"):
    """分析性能日志"""
    
    routes = defaultdict(list)
    slow_requests = []
    errors = []
    
    print("=" * 80)
    print("📊 性能日志分析")
    print("=" * 80)
    print(f"日志文件: {log_file}\n")
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 匹配请求日志: 🟢 [请求ID] GET /path - 200 - 245.67ms
                match = re.search(r'[🟢🟡🔴⚡] \[[\d-]+\] (GET|POST|PUT|DELETE) (\S+) - (\d+) - ([\d.]+)ms', line)
                if match:
                    method, path, status, duration = match.groups()
                    duration = float(duration)
                    route_key = f"{method} {path}"
                    routes[route_key].append(duration)
                    
                    # 记录慢请求（>1秒）
                    if duration > 1000:
                        slow_requests.append({
                            'route': route_key,
                            'duration': duration,
                            'status': status,
                            'line': line.strip()
                        })
                
                # 匹配错误日志
                if 'ERROR' in line or '❌' in line:
                    errors.append(line.strip())
        
        # 统计路由性能
        if routes:
            print("📈 路由性能统计:")
            print("-" * 80)
            print(f"{'路由':<40} {'请求数':>8} {'平均(ms)':>12} {'最大(ms)':>12} {'最小(ms)':>12}")
            print("-" * 80)
            
            # 按平均耗时排序
            sorted_routes = sorted(routes.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
            
            for route, durations in sorted_routes[:20]:  # 只显示前20个
                count = len(durations)
                avg = sum(durations) / count
                max_dur = max(durations)
                min_dur = min(durations)
                
                # 根据平均耗时设置颜色标记
                if avg > 2000:
                    marker = "🔴"
                elif avg > 1000:
                    marker = "🟡"
                elif avg > 500:
                    marker = "🟢"
                else:
                    marker = "⚡"
                
                print(f"{marker} {route:<38} {count:>8} {avg:>12.2f} {max_dur:>12.2f} {min_dur:>12.2f}")
            
            print()
        
        # 显示慢请求
        if slow_requests:
            print("🐌 慢请求列表 (>1秒):")
            print("-" * 80)
            # 按耗时排序
            slow_requests.sort(key=lambda x: x['duration'], reverse=True)
            for req in slow_requests[:10]:  # 只显示前10个
                print(f"  {req['route']}: {req['duration']:.2f}ms (状态: {req['status']})")
            print()
        
        # 显示错误
        if errors:
            print("❌ 错误日志 (最近10条):")
            print("-" * 80)
            for error in errors[-10:]:
                print(f"  {error}")
            print()
        
        # 性能总结
        print("📊 性能总结:")
        print("-" * 80)
        total_requests = sum(len(durations) for durations in routes.values())
        all_durations = [d for durations in routes.values() for d in durations]
        
        if all_durations:
            avg_all = sum(all_durations) / len(all_durations)
            max_all = max(all_durations)
            min_all = min(all_durations)
            
            # 统计各性能等级的请求数
            fast = sum(1 for d in all_durations if d < 500)
            normal = sum(1 for d in all_durations if 500 <= d < 1000)
            slow = sum(1 for d in all_durations if 1000 <= d < 2000)
            very_slow = sum(1 for d in all_durations if d >= 2000)
            
            print(f"总请求数: {total_requests}")
            print(f"平均响应时间: {avg_all:.2f}ms")
            print(f"最快响应: {min_all:.2f}ms")
            print(f"最慢响应: {max_all:.2f}ms")
            print()
            print(f"性能分布:")
            print(f"  ⚡ 快速 (<500ms):     {fast:>6} ({fast/total_requests*100:>5.1f}%)")
            print(f"  🟢 正常 (500-1000ms): {normal:>6} ({normal/total_requests*100:>5.1f}%)")
            print(f"  🟡 较慢 (1-2s):       {slow:>6} ({slow/total_requests*100:>5.1f}%)")
            print(f"  🔴 很慢 (>2s):        {very_slow:>6} ({very_slow/total_requests*100:>5.1f}%)")
            print()
            
            # 性能建议
            if very_slow > 0:
                print("⚠️ 建议: 发现很慢的请求，需要立即优化！")
            elif slow > total_requests * 0.1:
                print("⚠️ 建议: 超过10%的请求较慢，建议优化。")
            elif normal > total_requests * 0.3:
                print("💡 建议: 可以进一步优化以提升性能。")
            else:
                print("✅ 性能良好！")
        
        print("=" * 80)
        
    except FileNotFoundError:
        print(f"❌ 错误: 找不到日志文件 {log_file}")
        print("请确保应用已运行并生成了日志文件。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


def main():
    """主函数"""
    log_file = sys.argv[1] if len(sys.argv) > 1 else "logs/monitoring_app.log"
    analyze_logs(log_file)


if __name__ == "__main__":
    main()
