# 性能优化指南

## 已添加的性能监控

### 1. 后端性能监控

#### 请求级别监控
**位置**: `app.py` - `before_request` 和 `after_request` 中间件

**监控内容**:
- 每个请求的完整耗时
- 请求路径和方法
- 客户端 IP
- HTTP 状态码

**日志格式**:
```
📥 [请求ID] GET /dashboard - IP: 192.168.1.100
🟢 [请求ID] GET /dashboard - 200 - 245.67ms
🟡 [请求ID] GET /monitor - 200 - 856.32ms (较慢)
🔴 [请求ID] GET /export - 200 - 2345.12ms (很慢)
```

**性能阈值**:
- ⚡ < 500ms: 正常（DEBUG 级别）
- 🟢 500ms - 1s: 可接受（INFO 级别）
- 🟡 1s - 2s: 较慢（WARNING 级别）
- 🔴 > 2s: 很慢（ERROR 级别）

#### 路由内部监控
**位置**: `app.py` - dashboard 等主要路由

**监控内容**:
- 参数解析耗时
- 数据库查询耗时
- 缓存命中情况
- 各个数据查询步骤的耗时

**示例日志**:
```
  ├─ 参数解析: 2.34ms
  ├─ 获取最新时间: 45.67ms
  ├─ 解析时间范围: 1.23ms
  ├─ 查询流量数据: 123.45ms
  ├─ 查询接通率数据: 98.76ms
  ├─ 查询RRC数据: 87.65ms
  ├─ 查询Top利用率: 234.56ms
  ├─ 查询日统计数据: 156.78ms
  └─ dashboard 数据查询总耗时: 750.44ms
```

### 2. 前端性能监控

#### 页面加载性能
**位置**: `static/js/performance-monitor.js`

**监控内容**:
- DNS 查询耗时
- TCP 连接耗时
- 请求/响应耗时
- DOM 解析耗时
- 白屏时间
- 首屏时间
- 总加载时间

**查看方式**: 打开浏览器控制台，查看 "📊 页面性能监控" 分组

#### 资源加载性能
**监控内容**:
- JavaScript 文件加载
- CSS 文件加载
- 图片加载
- 字体加载
- API 请求

**查看方式**: 打开浏览器控制台，查看 "📦 资源加载性能" 分组

#### AJAX 请求监控
**监控内容**:
- 每个 AJAX 请求的耗时
- 慢请求警告（>1s）

## 如何使用监控数据

### 1. 查看实时日志

**方式1: 控制台输出**
```bash
# 启动应用时查看控制台
python app.py
```

**方式2: 日志文件**
```bash
# 实时查看日志
tail -f logs/monitoring_app.log

# 查看最近的慢请求
grep "🟡\|🔴" logs/monitoring_app.log | tail -20

# 查看特定路由的性能
grep "GET /dashboard" logs/monitoring_app.log | tail -10
```

### 2. 分析性能瓶颈

#### 后端瓶颈识别

**步骤1**: 找出慢请求
```bash
# 查找超过1秒的请求
grep "🟡\|🔴" logs/monitoring_app.log
```

**步骤2**: 查看详细的步骤耗时
```bash
# 查看特定请求的详细日志
grep "请求ID" logs/monitoring_app.log
```

**步骤3**: 定位具体问题
- 如果 "查询流量数据" 耗时长 → 数据库查询慢，考虑添加索引
- 如果 "获取最新时间" 耗时长 → 缓存未命中，检查缓存配置
- 如果 "查询Top利用率" 耗时长 → SQL 查询复杂，考虑优化查询

#### 前端瓶颈识别

**步骤1**: 打开浏览器控制台（F12）

**步骤2**: 查看性能监控输出
- 白屏时间 > 1s → 服务器响应慢或网络延迟
- DOM 解析 > 500ms → HTML 过大或 JavaScript 阻塞
- 资源加载慢 → 静态资源过大或 CDN 慢

**步骤3**: 查看 Network 面板
- 找出加载最慢的资源
- 检查资源大小和加载顺序

## 常见性能问题及优化方案

### 问题1: 数据库查询慢

**症状**:
```
  ├─ 查询流量数据: 1234.56ms (很慢)
```

**解决方案**:
1. **添加数据库索引**
   ```sql
   -- 为常用查询字段添加索引
   CREATE INDEX idx_cell_4g_start_time ON cell_4g_metrics(start_time);
   CREATE INDEX idx_cell_4g_cgi ON cell_4g_metrics(cgi);
   CREATE INDEX idx_cell_5g_start_time ON cell_5g_metrics(start_time);
   CREATE INDEX idx_cell_5g_ncgi ON cell_5g_metrics("Ncgi");
   ```

2. **优化 SQL 查询**
   - 减少 JOIN 操作
   - 使用 LIMIT 限制结果集
   - 避免 SELECT *

3. **增加缓存时间**
   ```python
   # 将缓存时间从 5 分钟增加到 10 分钟
   cache_10m.get(key, lambda: expensive_query())
   ```

### 问题2: 缓存未命中

**症状**:
```
⚠️ inject_nav 上下文处理器耗时: 234.56ms
```

**解决方案**:
1. **检查缓存配置**
   ```python
   # 确保缓存时间足够长
   cache_5m = SimpleCache(timeout=300)  # 5分钟
   ```

2. **预热缓存**
   ```python
   # 应用启动时预热常用数据
   scenario_service.latest_time()
   ```

### 问题3: 前端资源加载慢

**症状**:
```
🐌 加载最慢的资源 (>500ms)
/static/js/chart.umd.min.js: 1234.56ms
```

**解决方案**:
1. **启用 Gzip 压缩**
   ```python
   # 在 Flask 中启用压缩
   from flask_compress import Compress
   Compress(app)
   ```

2. **使用 CDN**
   ```html
   <!-- 使用 CDN 加速静态资源 -->
   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
   ```

3. **资源懒加载**
   ```javascript
   // 延迟加载非关键资源
   setTimeout(() => {
     loadNonCriticalResources();
   }, 1000);
   ```

### 问题4: 白屏时间长

**症状**:
```
⏱️ 白屏时间: 1234ms
```

**解决方案**:
1. **优化服务器响应时间**
   - 减少数据库查询
   - 使用缓存
   - 优化业务逻辑

2. **使用骨架屏**
   ```html
   <!-- 在内容加载前显示骨架屏 -->
   <div class="skeleton-loader">
     <div class="skeleton-header"></div>
     <div class="skeleton-content"></div>
   </div>
   ```

3. **内联关键 CSS**
   ```html
   <style>
     /* 关键样式内联到 HTML */
     body { margin: 0; font-family: sans-serif; }
   </style>
   ```

### 问题5: 页面刷新慢

**症状**: 每次操作都需要刷新整个页面

**解决方案**: 使用 AJAX 局部刷新（已实现）
- 场景管理页面已优化
- 其他页面可参考 `AJAX_OPTIMIZATION_GUIDE.md`

## 性能优化检查清单

### 后端优化
- [ ] 数据库索引已添加
- [ ] SQL 查询已优化
- [ ] 缓存策略已配置
- [ ] 慢查询已记录
- [ ] API 响应时间 < 500ms

### 前端优化
- [ ] 静态资源已压缩
- [ ] 图片已优化
- [ ] 使用 CDN 加速
- [ ] 关键资源已内联
- [ ] 非关键资源已延迟加载
- [ ] 白屏时间 < 1s
- [ ] 首屏时间 < 2s

### 网络优化
- [ ] 启用 Gzip 压缩
- [ ] 启用浏览器缓存
- [ ] 减少 HTTP 请求数
- [ ] 使用 HTTP/2

## 监控数据分析工具

### 1. 日志分析脚本

创建 `analyze_performance.py`:
```python
import re
from collections import defaultdict

def analyze_logs(log_file):
    """分析性能日志"""
    routes = defaultdict(list)
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            # 匹配请求日志
            match = re.search(r'(GET|POST) (\S+) - \d+ - ([\d.]+)ms', line)
            if match:
                method, path, duration = match.groups()
                routes[f"{method} {path}"].append(float(duration))
    
    # 统计每个路由的性能
    print("路由性能统计:")
    print("-" * 60)
    for route, durations in sorted(routes.items()):
        avg = sum(durations) / len(durations)
        max_dur = max(durations)
        min_dur = min(durations)
        print(f"{route}:")
        print(f"  平均: {avg:.2f}ms, 最大: {max_dur:.2f}ms, 最小: {min_dur:.2f}ms, 请求数: {len(durations)}")

if __name__ == "__main__":
    analyze_logs("logs/monitoring_app.log")
```

### 2. 实时监控命令

```bash
# 监控慢请求
watch -n 1 'tail -20 logs/monitoring_app.log | grep "🟡\|🔴"'

# 统计各路由的请求数
grep -oP 'GET \S+|POST \S+' logs/monitoring_app.log | sort | uniq -c | sort -rn

# 查看最近的错误
grep "ERROR" logs/monitoring_app.log | tail -20
```

## 下一步优化建议

1. **数据库优化**
   - 添加必要的索引
   - 分析慢查询日志
   - 考虑使用连接池

2. **缓存优化**
   - 增加缓存命中率
   - 使用 Redis 替代内存缓存
   - 实现缓存预热

3. **前端优化**
   - 实现代码分割
   - 使用 Service Worker
   - 优化图片加载

4. **架构优化**
   - 考虑使用异步任务队列
   - 实现读写分离
   - 使用负载均衡

## 测试性能优化效果

### 1. 基准测试
```bash
# 使用 ab (Apache Bench) 测试
ab -n 100 -c 10 http://localhost:5000/dashboard

# 使用 wrk 测试
wrk -t4 -c100 -d30s http://localhost:5000/dashboard
```

### 2. 对比优化前后
- 记录优化前的性能数据
- 实施优化措施
- 记录优化后的性能数据
- 计算性能提升百分比

## 总结

通过添加详细的性能监控，现在可以：
1. 实时查看每个请求的耗时
2. 定位性能瓶颈
3. 追踪优化效果
4. 发现潜在问题

重启应用后，查看控制台和日志文件，找出耗时最长的操作，针对性优化。
