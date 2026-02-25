# 告警监控功能使用指南

## 快速开始

### 1. 测试告警服务（可选）

```bash
python test_alarm_service.py
```

如果MySQL连接正常，会显示告警统计信息。

### 2. 插入测试数据（可选）

如果数据库中没有告警数据，可以运行以下脚本插入测试数据：

```bash
python temp/scripts/insert_alarm_test_data.py
```

这将创建：
- 6条当前告警（紧急2条、重要2条、一般2条）
- 4条历史告警（用于测试去重功能）

### 3. 启动应用

```bash
python app.py
```

### 4. 访问告警监控页面

打开浏览器访问：
```
http://127.0.0.1:5000/alarm
```

## 功能说明

### 当前告警
- 自动显示最近半小时的告警
- 告警按级别用不同颜色标识
- 支持导出为Excel

### 历史告警
- 支持自定义时间范围查询
- 数据自动去重
- 支持分页浏览
- 支持导出为Excel

### 告警统计
页面顶部显示4个统计卡片：
- 当前告警总数
- 紧急告警数量
- 重要告警数量
- 今日告警总数

## 数据库配置

系统会自动从 `config.json` 文件中读取MySQL配置。

当前配置示例：
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

**注意**: 测试脚本会自动读取config.json中的配置，无需手动修改。

## 详细文档

- [完整功能说明](temp/docs/ALARM_MONITORING_GUIDE.md)
- [快速启动指南](temp/docs/ALARM_QUICKSTART.md)
- [功能实现总结](temp/docs/ALARM_FEATURE_SUMMARY.md)

## 常见问题

**Q: 页面显示"告警服务未初始化"？**
A: 检查MySQL配置是否正确，确保数据库服务正常运行。

**Q: 查询不到数据？**
A: 运行 `python temp/scripts/insert_alarm_test_data.py` 插入测试数据。

**Q: 如何创建cur_alarm表？**
A: 可以使用 `temp/scripts/create_alarm_test_data.sql` 中的SQL语句。

## 文件说明

```
├── services/alarm_service.py          # 告警服务类
├── templates/alarm.html               # 告警页面模板
├── test_alarm_service.py              # 测试脚本
├── README_ALARM.md                    # 本文档
└── temp/
    ├── docs/                          # 详细文档
    │   ├── ALARM_MONITORING_GUIDE.md
    │   ├── ALARM_QUICKSTART.md
    │   └── ALARM_FEATURE_SUMMARY.md
    └── scripts/                       # 辅助脚本
        ├── insert_alarm_test_data.py
        └── create_alarm_test_data.sql
```

## 技术支持

如有问题，请查看：
1. 应用日志文件
2. 浏览器控制台
3. MySQL错误日志
