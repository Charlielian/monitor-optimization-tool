# 导出功能说明

## 最新全量小区指标导出

### 功能概述

从全网监控页面下载最新时刻的全量 4G/5G 小区指标数据，支持中文列名，Excel 格式。

### 访问方式

1. 访问全网监控页面：`http://localhost:5000/`
2. 点击页面右上角的"下载最新全量小区指标"按钮
3. 或直接访问：`http://localhost:5000/export/latest_metrics.xlsx`

### 导出字段说明

| 中文列名 | 英文字段名 | 说明 | 数据来源 |
|---------|-----------|------|---------|
| 网络类型 | network | 4G 或 5G | 固定值 |
| 小区名 | cellname | 小区名称 | 4G: cellname<br>5G: userlabel |
| 小区ID | cell_id | 小区标识 | 4G: cell_id<br>5G: Ncgi |
| CGI | cgi | 小区全局标识 | 4G: cgi<br>5G: Ncgi |
| 时间 | start_time | 数据时间戳 | 最新时刻 |
| 总流量(GB) | total_traffic_gb | 上下行总流量 | 4G: PDCP层<br>5G: RLC层 |
| 上行PRB利用率(%) | ul_prb_utilization | 上行资源利用率 | 百分比 |
| 下行PRB利用率(%) | dl_prb_utilization | 下行资源利用率 | 百分比 |
| 无线接通率(%) | wireless_connect_rate | 无线侧接通成功率 | 百分比 |
| 最大RRC连接数 | rrc_users | RRC最大连接用户数 | 整数 |

### 数据说明

#### 1. 数据来源

- **4G数据**：从 `cell_4g_metrics` 表查询最新时刻数据
- **5G数据**：从 `cell_5g_metrics` 表查询最新时刻数据

#### 2. 时间范围

导出的是数据库中最新时刻的数据：
- 4G: `MAX(start_time)` from `cell_4g_metrics`
- 5G: `MAX(start_time)` from `cell_5g_metrics`

#### 3. 数据格式

- **文件格式**：Excel (xlsx)
- **工作表名称**：最新全量小区指标
- **表头样式**：蓝色背景，白色粗体文字
- **数值精度**：保留2位小数
- **列宽**：自动调整
- **冻结窗格**：首行冻结

#### 4. 文件命名

格式：`最新全量小区指标_YYYYMMDD_HHMMSS.xlsx`

示例：`最新全量小区指标_20251229_143025.xlsx`

### 使用示例

#### 1. 在浏览器中下载

```
访问: http://localhost:5000/
点击: "下载最新全量小区指标" 按钮
```

#### 2. 使用 curl 下载

```bash
curl -o latest_metrics.xlsx "http://localhost:5000/export/latest_metrics.xlsx"
```

#### 3. 使用 Python 下载

```python
import requests

url = "http://localhost:5000/export/latest_metrics.xlsx"
response = requests.get(url)

with open("latest_metrics.xlsx", "wb") as f:
    f.write(response.content)

print("下载完成")
```

### 数据处理示例

#### 1. 使用 pandas 读取

```python
import pandas as pd

# 读取Excel文件
df = pd.read_excel("最新全量小区指标_20251229_143025.xlsx")

# 查看数据
print(df.head())

# 按网络类型分组统计
print(df.groupby("网络类型")["总流量(GB)"].sum())

# 筛选高流量小区
high_traffic = df[df["总流量(GB)"] > 100]
print(high_traffic)
```

#### 2. 使用 Excel 打开

1. 双击 Excel 文件，自动打开
2. 中文列名正常显示
3. 表头有蓝色背景样式
4. 首行已冻结，方便滚动查看
5. 数值格式已设置，保留2位小数
6. 可以使用 Excel 的筛选、排序、透视表等功能

#### 3. 数据分析示例

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_excel("最新全量小区指标_20251229_143025.xlsx")

# 统计各网络类型的小区数量
network_counts = df["网络类型"].value_counts()
print("各网络类型小区数量:")
print(network_counts)

# 统计总流量
total_traffic = df.groupby("网络类型")["总流量(GB)"].sum()
print("\n各网络类型总流量(GB):")
print(total_traffic)

# 找出流量Top10小区
top10 = df.nlargest(10, "总流量(GB)")[["小区名", "网络类型", "总流量(GB)"]]
print("\n流量Top10小区:")
print(top10)

# 绘制流量分布图
plt.figure(figsize=(10, 6))
df.groupby("网络类型")["总流量(GB)"].sum().plot(kind="bar")
plt.title("各网络类型总流量分布")
plt.xlabel("网络类型")
plt.ylabel("总流量(GB)")
plt.tight_layout()
plt.savefig("traffic_distribution.png")
print("\n图表已保存为 traffic_distribution.png")
```

### 常见问题

#### Q1: 下载的文件为空？

**A:** 可能原因：
1. 数据库中没有数据
2. 数据库连接失败
3. 查询时间范围内没有数据

**解决方法：**
```bash
# 运行测试脚本检查
python test_export_latest_metrics.py
```

#### Q2: Excel 打开显示乱码？

**A:** Excel (xlsx) 格式不会出现乱码问题，因为：
1. 使用原生 Excel 格式
2. 中文字符正确编码
3. 直接双击即可打开

#### Q3: 小区名显示为空？

**A:** 可能原因：
1. 数据库中 cellname/userlabel 字段为空
2. 查询语句未包含小区名字段

**解决方法：**
- 检查数据库表结构
- 运行测试脚本查看数据

#### Q4: 如何定时导出？

**A:** 使用 cron 或 Windows 任务计划程序：

Linux/Mac:
```bash
# 每天凌晨1点导出
0 1 * * * curl -o /path/to/latest_metrics_$(date +\%Y\%m\%d).xlsx "http://localhost:5000/export/latest_metrics.xlsx"
```

Windows:
```powershell
# 创建 PowerShell 脚本
$date = Get-Date -Format "yyyyMMdd_HHmmss"
$url = "http://localhost:5000/export/latest_metrics.xlsx"
$output = "D:\exports\latest_metrics_$date.xlsx"
Invoke-WebRequest -Uri $url -OutFile $output
```

### 性能说明

- **查询时间**：通常 < 5 秒（取决于数据量）
- **文件大小**：约 100KB / 1000条记录
- **内存占用**：约 10MB / 10000条记录

### 数据质量检查

运行测试脚本检查数据质量：

```bash
python test_export_latest_metrics.py
```

测试内容：
- ✓ 数据库连接
- ✓ 数据获取
- ✓ 字段完整性
- ✓ 小区名存在性
- ✓ 中文列名映射
- ✓ 数据格式化

### 相关功能

- **保障监控导出**：`/export/monitor_xlsx_full`
- **小区指标查询导出**：`/export/cell_data.xlsx`
- **利用率Top导出**：`/export/top_utilization.xlsx`

### 技术实现

#### 后端实现

```python
# services/metrics_service.py
def latest_full_metrics(self) -> List[Dict[str, Any]]:
    """导出最新时刻全量4G/5G小区指标"""
    # 查询最新时刻
    # 获取4G数据（包含cellname）
    # 获取5G数据（包含userlabel as cellname）
    # 返回合并结果
```

#### 路由实现

```python
# app.py
@app.route("/export/latest_metrics.xlsx")
def export_latest_metrics():
    """导出最新全量小区指标为Excel，使用中文列名"""
    # 获取数据
    # 定义中文列名映射
    # 创建 Excel 工作簿
    # 设置表头样式
    # 写入数据
    # 设置数值格式
    # 自动调整列宽
    # 冻结首行
    # 返回下载
```

### 更新日志

- **2025-12-29**: 
  - ✅ 添加小区名字段（cellname）
  - ✅ 使用中文列名
  - ✅ 改为 Excel (xlsx) 格式
  - ✅ 添加表头样式（蓝色背景）
  - ✅ 自动调整列宽
  - ✅ 冻结首行
  - ✅ 优化文件命名（包含时间戳）
  - ✅ 改进数值格式化
  - ✅ 添加数据验证

---

**提示**：Excel 格式比 CSV 更适合直接查看和分析数据，支持样式、格式化和更好的中文显示。
