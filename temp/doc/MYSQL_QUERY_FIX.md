# MySQL查询参数修复说明

## 问题描述
当前告警页面显示不正常，MySQL查询失败，错误信息：
```
MySQL 查询失败: List argument must consist only of dictionaries
```

## 问题原因
SQLAlchemy的 `text()` 函数需要命名参数（字典格式），但我们传递的是元组格式的参数，并且使用了 `%s` 占位符。

## 错误示例
```python
# 错误的方式
params = (start_time, end_time)
sql = "SELECT * FROM cur_alarm WHERE import_time >= %s AND import_time <= %s"
conn.execute(text(sql), params)  # 这会失败
```

## 解决方案
修改 `db/mysql.py` 中的 `fetch_all()` 和 `fetch_one()` 方法，将元组参数转换为字典格式，并将 `%s` 占位符替换为命名占位符。

### 修复逻辑
1. **检测参数类型**：判断传入的参数是否为元组
2. **转换参数格式**：将元组转换为字典 `{param_0: value0, param_1: value1, ...}`
3. **替换占位符**：将SQL中的 `%s` 替换为 `:param_0`, `:param_1` 等
4. **执行查询**：使用转换后的参数和SQL执行查询

### 修复后的代码
```python
def fetch_all(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    if params:
        if isinstance(params, tuple):
            # 转换为字典格式
            param_dict = {f'param_{i}': param for i, param in enumerate(params)}
            # 替换占位符
            sql_with_named_params = sql
            for i in range(len(params)):
                sql_with_named_params = sql_with_named_params.replace('%s', f':param_{i}', 1)
            result = conn.execute(text(sql_with_named_params), param_dict)
        else:
            result = conn.execute(text(sql), params)
    else:
        result = conn.execute(text(sql))
```

## 转换示例

### 简单查询
```python
# 原始
params = (start_time, end_time)
sql = "SELECT * FROM cur_alarm WHERE import_time >= %s AND import_time <= %s"

# 转换后
param_dict = {'param_0': start_time, 'param_1': end_time}
sql = "SELECT * FROM cur_alarm WHERE import_time >= :param_0 AND import_time <= :param_1"
```

### 复杂查询
```python
# 原始
params = (start_time, end_time, 100, 0)
sql = "SELECT * FROM cur_alarm WHERE import_time BETWEEN %s AND %s LIMIT %s OFFSET %s"

# 转换后
param_dict = {
    'param_0': start_time, 
    'param_1': end_time, 
    'param_2': 100, 
    'param_3': 0
}
sql = "SELECT * FROM cur_alarm WHERE import_time BETWEEN :param_0 AND :param_1 LIMIT :param_2 OFFSET :param_3"
```

## 修复的查询

### 1. 当前告警查询
```sql
SELECT *
FROM cur_alarm
WHERE import_time >= :param_0 AND import_time <= :param_1
ORDER BY import_time DESC
```

### 2. 历史告警统计查询
```sql
SELECT COUNT(*) as total
FROM (
    SELECT DISTINCT 
        alarm_id, alarm_name, alarm_level, alarm_type,
        alarm_source, alarm_time, alarm_status, alarm_desc,
        cell_id, cell_name, network_type
    FROM cur_alarm
    WHERE import_time BETWEEN :param_0 AND :param_1
) as distinct_alarms
```

### 3. 历史告警分页查询
```sql
SELECT DISTINCT 
    alarm_id, alarm_name, alarm_level, alarm_type,
    alarm_source, alarm_time, alarm_status, alarm_desc,
    cell_id, cell_name, network_type
FROM cur_alarm
WHERE import_time BETWEEN :param_0 AND :param_1
ORDER BY alarm_time DESC
LIMIT :param_2 OFFSET :param_3
```

### 4. 告警统计查询
```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN alarm_level = '紧急' THEN 1 ELSE 0 END) as urgent,
    SUM(CASE WHEN alarm_level = '重要' THEN 1 ELSE 0 END) as important,
    SUM(CASE WHEN alarm_level = '一般' THEN 1 ELSE 0 END) as normal
FROM cur_alarm
WHERE import_time >= :param_0
```

## 测试验证

运行测试脚本验证修复：
```bash
python test_mysql_fix.py
```

## 预期效果

修复后，告警页面应该能够：
1. ✅ 正常显示当前告警（最近1小时）
2. ✅ 正常查询历史告警（指定时间范围）
3. ✅ 正确显示告警统计数据
4. ✅ 支持分页功能
5. ✅ 正确处理datetime对象参数

## 注意事项

1. **参数类型**：修复后的代码同时支持元组和字典参数
2. **占位符顺序**：确保 `%s` 替换的顺序与参数顺序一致
3. **SQLAlchemy版本**：此修复适用于SQLAlchemy 1.4+版本
4. **向后兼容**：修复保持了原有的API接口不变

## 相关文件

- `db/mysql.py`：MySQL客户端修复
- `services/alarm_service.py`：告警服务（使用修复后的客户端）
- `test_mysql_fix.py`：测试脚本

## 后续建议

1. 考虑统一使用字典参数格式，避免转换开销
2. 添加参数类型检查和验证
3. 考虑使用SQLAlchemy的ORM模式替代原生SQL
4. 添加查询性能监控和优化