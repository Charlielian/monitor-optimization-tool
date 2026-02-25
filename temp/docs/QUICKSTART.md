# 快速启动指南

## 一键安装和启动

### 1. 安装依赖

```bash
# 确保在项目目录
cd /Users/charlie-macmini/Documents/python/优化工具/网页监控/网页监控_flask

# 激活虚拟环境（如果有）
source venv/bin/activate

# 安装/更新依赖
pip install -r requirements.txt
```

### 2. 验证配置

检查 `config.json` 是否包含以下配置：

```json
{
  "pgsql_config": {
    "host": "192.168.31.51",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "103001"
  },
  "mysql_config": {
    "host": "192.168.31.175",
    "port": 3306,
    "database": "optimization_toolbox",
    "user": "root",
    "password": "103001"
  }
}
```

### 3. 测试连接（可选）

```bash
# 测试 MySQL 连接和工参表
python test_mysql_connection.py
```

### 4. 启动应用

```bash
python app.py
```

### 5. 访问应用

打开浏览器访问：
```
http://localhost:5000
```

---

## 功能验证清单

### ✅ 话务量显示
1. 访问首页"全网监控"
2. 查看"4G/5G总流量及话务量"卡片
3. 确认话务量单位显示正确：
   - 小于 10000 显示为 "XXX.XX Erl"
   - 大于等于 10000 显示为 "X.XX 万Erl"

### ✅ 区域统计
1. 在同一卡片中查看"各区域流量及话务量统计"
2. 确认五个区域都有数据：
   - 江城区
   - 阳东县
   - 南区
   - 阳西县
   - 阳春市

### ✅ 日期选择
1. 使用日期选择器选择不同日期
2. 点击"查询"按钮
3. 确认数据更新正确

### ✅ 最新全量小区指标导出
1. 点击页面右上角"下载最新全量小区指标"按钮
2. 确认文件名格式：`最新全量小区指标_YYYYMMDD_HHMMSS.xlsx`
3. 打开 Excel 文件，确认：
   - 列名为中文
   - 包含小区名字段
   - 表头有蓝色背景样式
   - 首行已冻结
   - 数值格式正确（保留2位小数）
   - 列宽自动调整

---

## 常见问题

### Q1: MySQL 连接失败怎么办？

**A:** 应用会自动回退到基于小区名的分类，不影响使用。检查：
- MySQL 服务是否运行
- 网络连接是否正常
- 配置信息是否正确

### Q2: 看不到话务量数据？

**A:** 检查：
- 数据库中是否有日级表数据（`cell_4g_metrics_day`, `cell_5g_metrics_day`）
- 选择的日期是否有数据
- 查看日志文件 `logs/monitoring_app.log`

### Q3: 区域分类不准确？

**A:** 可能原因：
- 工参表数据不完整
- CGI 字段缺失
- 需要更新工参表数据

解决方法：
- 运行 `python test_mysql_connection.py` 查看加载的 CGI 数量
- 检查工参表中的 `cgi`, `area_compy`, `celname` 字段

---

## 日志查看

### 实时查看日志

```bash
tail -f logs/monitoring_app.log
```

### 查找关键信息

```bash
# 查看 MySQL 相关日志
grep -i mysql logs/monitoring_app.log

# 查看工参服务日志
grep -i "工参" logs/monitoring_app.log

# 查看错误日志
grep -i error logs/monitoring_app.log
```

---

## 性能说明

### 启动时间
- 首次启动：3-5 秒（加载工参表）
- 后续启动：2-3 秒

### 内存占用
- 基础应用：~50 MB
- 工参表缓存：~2-5 MB（取决于记录数）

### 响应时间
- 首页加载：< 1 秒
- 区域统计查询：< 2 秒

---

## 停止应用

在终端按 `Ctrl+C` 停止应用。

---

## 下一步

- 📖 阅读 `MYSQL_INTEGRATION.md` 了解工参表集成详情
- 📖 阅读 `INSTALL_MYSQL.md` 了解详细配置
- 📖 阅读 `CHANGES_SUMMARY.md` 了解所有更新内容

---

## 技术支持

如遇问题，请检查：
1. 日志文件：`logs/monitoring_app.log`
2. 测试脚本：`python test_mysql_connection.py`
3. 配置文件：`config.json`

---

**祝使用愉快！** 🎉
