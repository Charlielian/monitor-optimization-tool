# 更新总结

## 本次更新内容

### 1. 话务量字段优化 ✅

**修改文件：**
- `services/metrics_service.py`
- `templates/dashboard.html`

**主要变更：**

#### 后端 SQL 查询修改
- **4G话务量**：从 `SUM("ERAB_NbrMeanEstab_1") / 4 / 10000` 改为 `SUM("ERAB_NbrMeanEstab_1") / 4`
- **5G话务量**：从 `SUM("Flow_NbrMeanEstab_5QI1") / 4 / 10000` 改为 `SUM("Flow_NbrMeanEstab_5QI1") / 4`

#### 智能单位转换
- 话务量 >= 10000 Erl → 自动转换为"万Erl"
- 话务量 < 10000 Erl → 保持"Erl"单位
- 新增 `voice_unit` 字段存储当前单位

#### 前端显示优化
- 动态显示单位：`{{ voice_erl }} {{ voice_unit }}`
- 支持 4G/5G 总话务量和各区域话务量

**效果示例：**
- 小值：`1234.56 Erl`
- 大值：`1.23 万Erl`

---

### 2. MySQL 工参表集成 ✅

**新增文件：**
- `db/mysql.py` - MySQL 客户端封装
- `services/engineering_params_service.py` - 工参表服务
- `test_mysql_connection.py` - 测试脚本
- `MYSQL_INTEGRATION.md` - 功能说明文档
- `INSTALL_MYSQL.md` - 安装指南

**修改文件：**
- `requirements.txt` - 添加 pymysql 和 sqlalchemy
- `config.json` - 添加 MySQL 配置（改为 key-value 格式）
- `config.py` - 加载 MySQL 配置
- `app.py` - 初始化 MySQL 客户端和工参服务
- `services/metrics_service.py` - 集成工参服务的区域分类

**主要功能：**

#### 三级区域分类优先级

1. **工参表 CGI 映射**（最高优先级）
   - 从 `engineering_params` 表查询 CGI 对应的区域

2. **area_compy 字段分类**
   ```
   阳西分公司 → 阳西县
   阳春分公司 → 阳春市
   阳东分公司 → 阳东县
   南区分公司 → 南区
   江城分公司 → 江城区
   ```

3. **小区名（celname）分类**
   ```
   阳江阳西 / yangjiangyangxi → 阳西县
   阳江阳春 / yangjiangyangchun → 阳春市
   阳江阳东 / yangjiangyangdong → 阳东县
   阳江南区 / yangjiangnanqu → 南区
   阳江江城 / yangjiangjiangcheng → 江城区
   ```

4. **默认分类**：江城区

#### 性能优化
- 启动时一次性加载工参表到内存
- 使用字典缓存，查询时间复杂度 O(1)
- 支持手动刷新缓存

#### 容错机制
- MySQL 连接失败时自动回退到小区名分类
- 不影响主要功能运行
- 错误记录到日志

---

### 3. 最新全量小区指标导出优化 ✅

**修改文件：**
- `services/metrics_service.py` - 添加 cellname 字段
- `app.py` - 改为 Excel 格式，添加中文列名映射和样式

**新增文件：**
- `test_export_latest_metrics.py` - 测试脚本
- `EXPORT_GUIDE.md` - 导出功能说明

**主要变更：**

#### 添加小区名字段
- 4G: 查询 `cellname` 字段
- 5G: 查询 `userlabel AS cellname` 字段

#### 改为 Excel 格式
- 从 CSV 格式改为 Excel (xlsx) 格式
- 添加表头样式（蓝色背景，白色粗体文字）
- 自动调整列宽
- 冻结首行
- 设置数值格式（保留2位小数）

#### 中文列名映射
```
network          → 网络类型
cellname         → 小区名
cell_id          → 小区ID
cgi              → CGI
start_time       → 时间
total_traffic_gb → 总流量(GB)
ul_prb_utilization → 上行PRB利用率(%)
dl_prb_utilization → 下行PRB利用率(%)
wireless_connect_rate → 无线接通率(%)
rrc_users        → 最大RRC连接数
```

#### 文件命名优化
- 旧格式：`latest_metrics.csv`
- 新格式：`最新全量小区指标_20251229_143025.xlsx`

#### Excel 特性
- 工作表名称：最新全量小区指标
- 表头样式：蓝色背景 (#4472C4)
- 首行冻结：方便滚动查看
- 列宽自动调整：最大50字符
- 数值格式：0.00（保留2位小数）

---

## 配置说明

### config.json 新增配置

```json
{
  "mysql_config": {
    "host": "192.168.31.175",
    "port": 3306,
    "database": "optimization_toolbox",
    "user": "root",
    "password": "103001"
  }
}
```

### 依赖包更新

```bash
pip install -r requirements.txt
```

新增依赖：
- `pymysql>=1.1.0`
- `sqlalchemy>=2.0.0`

---

## 测试方法

### 1. 测试 MySQL 连接

```bash
python test_mysql_connection.py
```

### 2. 启动应用

```bash
python app.py
```

### 3. 访问页面

```
http://localhost:5000/
```

查看"4G/5G总流量及话务量"卡片中的：
- 话务量单位是否正确显示
- 各区域统计是否准确

---

## 影响范围

### 话务量优化影响
- ✅ 全网监控 - 4G/5G 总话务量显示
- ✅ 全网监控 - 各区域话务量显示

### 工参表集成影响
- ✅ 全网监控 - 各区域流量及话务量统计
- ✅ 日级数据查询 - 按区域统计

---

## 数据流程

```
PostgreSQL (指标数据)
    ↓
查询 cellname, cgi, 流量, 话务量
    ↓
MySQL (工参表) - 根据 CGI 查询区域
    ↓
区域分类（三级优先级）
    ↓
话务量单位转换（>= 10000 → 万Erl）
    ↓
按区域聚合统计
    ↓
前端动态显示
```

---

## 兼容性说明

### 向后兼容
- ✅ MySQL 连接失败时自动回退
- ✅ 工参表不存在时使用默认分类
- ✅ 不影响现有功能

### 数据库要求
- PostgreSQL: 保持不变
- MySQL: 可选，建议配置以提高区域分类准确性

---

## 后续优化建议

1. **工参表数据质量**
   - 确保 CGI、area_compy、celname 字段完整
   - 定期更新工参表数据

2. **性能监控**
   - 监控工参表加载时间
   - 监控内存占用情况

3. **功能扩展**
   - 添加工参表刷新接口
   - 添加区域分类统计报表
   - 支持自定义区域分类规则

4. **安全加固**
   - 使用环境变量存储数据库密码
   - 限制数据库用户权限
   - 添加连接加密

---

## 文档索引

- `MYSQL_INTEGRATION.md` - MySQL 集成功能说明
- `INSTALL_MYSQL.md` - 安装和配置指南
- `README.md` - 项目主文档
- `CHANGES_SUMMARY.md` - 本文档

---

## 版本信息

- **更新日期**: 2025-12-29
- **版本**: v2.1
- **主要变更**: 
  1. 话务量优化
  2. MySQL 工参表集成
  3. 最新全量小区指标导出优化（中文列名）
