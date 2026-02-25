# 告警监控配置说明

## 配置文件

告警监控功能使用 `config.json` 中的 `mysql_config` 配置连接数据库。

### 当前配置

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

## 自动读取配置

所有相关脚本都会自动从 `config.json` 读取配置，无需手动修改：

### 1. 主应用 (app.py)
```python
cfg = Config()  # 自动读取config.json
mysql_client = MySQLClient(cfg.mysql_config)
alarm_service = AlarmService(mysql_client)
```

### 2. 测试脚本 (test_alarm_service.py)
```python
# 从config.json读取MySQL配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    mysql_config = config['mysql_config']
```

### 3. 数据插入脚本 (temp/scripts/insert_alarm_test_data.py)
```python
# 从config.json读取MySQL配置
config_path = os.path.join(os.path.dirname(__file__), '../../config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
    mysql_config = config['mysql_config']
```

## 使用说明

### 1. 确认配置
检查 `config.json` 中的 `mysql_config` 是否正确。

### 2. 测试连接
```bash
python test_alarm_service.py
```

如果配置正确，会显示：
```
✓ MySQL连接成功
✓ 告警服务初始化成功
```

### 3. 插入测试数据
```bash
python temp/scripts/insert_alarm_test_data.py
```

### 4. 启动应用
```bash
python app.py
```

### 5. 访问页面
```
http://127.0.0.1:5000/alarm
```

## 配置修改

如果需要修改数据库配置，只需编辑 `config.json` 文件：

```json
{
  "mysql_config": {
    "host": "你的数据库地址",
    "port": 3306,
    "database": "optimization_toolbox",
    "user": "你的用户名",
    "password": "你的密码"
  }
}
```

修改后，重启应用即可生效。

## 注意事项

1. **配置文件位置**: `config.json` 必须在项目根目录
2. **数据库名称**: 必须是 `optimization_toolbox`
3. **数据表名称**: 必须是 `cur_alarm`
4. **字符集**: 建议使用 `utf8mb4`
5. **权限**: 确保MySQL用户有读写权限

## 故障排查

### 问题1: 找不到config.json
**错误**: `FileNotFoundError: config.json`
**解决**: 确保在项目根目录运行脚本

### 问题2: MySQL连接失败
**错误**: `MySQL 连接失败`
**解决**: 
- 检查MySQL服务是否运行
- 检查host、port是否正确
- 检查用户名密码是否正确
- 检查网络连接

### 问题3: 数据库不存在
**错误**: `Unknown database 'optimization_toolbox'`
**解决**: 创建数据库
```sql
CREATE DATABASE optimization_toolbox CHARACTER SET utf8mb4;
```

### 问题4: 表不存在
**错误**: `Table 'cur_alarm' doesn't exist`
**解决**: 运行SQL脚本创建表
```bash
mysql -h 192.168.31.175 -u root -p optimization_toolbox < temp/scripts/create_alarm_test_data.sql
```

## 配置验证清单

- [ ] config.json文件存在
- [ ] mysql_config配置正确
- [ ] MySQL服务运行正常
- [ ] 数据库optimization_toolbox存在
- [ ] 表cur_alarm存在
- [ ] 用户有读写权限
- [ ] 网络连接正常

## 相关文档

- [快速使用指南](README_ALARM.md)
- [完整功能说明](temp/docs/ALARM_MONITORING_GUIDE.md)
- [快速启动指南](temp/docs/ALARM_QUICKSTART.md)
