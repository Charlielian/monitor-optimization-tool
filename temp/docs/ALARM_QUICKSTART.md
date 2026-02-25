# 告警监控功能快速启动指南

## 快速开始

### 1. 确认MySQL配置

检查 `config.json` 文件中的MySQL配置（系统会自动读取）：

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

### 2. 测试告警服务

运行测试脚本验证功能：

```bash
python test_alarm_service.py
```

预期输出：
```
============================================================
测试告警服务
============================================================

1. 初始化MySQL客户端...
✓ MySQL连接成功

2. 初始化告警服务...
✓ 告警服务初始化成功

3. 获取告警统计...
✓ 告警统计:
  - 当前告警总数: X
  - 紧急告警: X
  - 重要告警: X
  - 一般告警: X
  - 今日告警总数: X

4. 获取当前告警...
✓ 查询到 X 条当前告警

5. 获取历史告警...
✓ 查询到 X 条历史告警（去重后）

============================================================
✓ 所有测试通过！
============================================================
```

### 3. 启动应用

```bash
python app.py
```

### 4. 访问告警监控页面

打开浏览器访问：
```
http://127.0.0.1:5000/alarm
```

## 功能演示

### 当前告警
1. 页面默认显示"当前告警"标签
2. 自动显示最近半小时的告警数据
3. 告警按级别用不同颜色标识：
   - 🔴 紧急（红色）
   - 🟡 重要（黄色）
   - 🔵 一般（蓝色）

### 历史告警
1. 切换到"历史告警"标签
2. 选择时间范围（默认最近7天）
3. 点击"查询"按钮
4. 数据已自动去重
5. 支持分页浏览

### 数据导出
- 点击"导出Excel"按钮
- 自动下载包含所有告警数据的Excel文件
- 文件名包含时间戳

## 常见问题

### Q1: 页面显示"告警服务未初始化"
**A**: MySQL连接失败，请检查：
- MySQL服务是否运行
- config.json中的配置是否正确
- 数据库是否存在

### Q2: 查询不到数据
**A**: 请检查：
- 数据库中是否有cur_alarm表
- 表中是否有数据
- 时间范围是否正确

### Q3: 导出功能不工作
**A**: 请检查：
- 是否有数据可导出
- 浏览器是否允许下载
- 磁盘空间是否充足

## 数据表结构参考

如果`cur_alarm`表不存在，可以参考以下结构创建：

```sql
CREATE TABLE `cur_alarm` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `alarm_id` VARCHAR(100),
  `alarm_name` VARCHAR(200),
  `alarm_level` VARCHAR(50),
  `alarm_type` VARCHAR(100),
  `alarm_source` VARCHAR(100),
  `alarm_time` DATETIME,
  `alarm_status` VARCHAR(50),
  `alarm_desc` TEXT,
  `cell_id` VARCHAR(100),
  `cell_name` VARCHAR(200),
  `network_type` VARCHAR(10),
  `import_time` DATETIME,
  `import_filename` VARCHAR(200),
  `import_batch` VARCHAR(100),
  INDEX `idx_alarm_time` (`alarm_time`),
  INDEX `idx_import_time` (`import_time`),
  INDEX `idx_cell_id` (`cell_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 下一步

- 查看完整文档：[ALARM_MONITORING_GUIDE.md](ALARM_MONITORING_GUIDE.md)
- 了解更多功能和API接口
- 根据需求进行定制化开发

## 技术支持

如有问题，请查看：
1. 应用日志文件
2. 浏览器控制台
3. MySQL错误日志
