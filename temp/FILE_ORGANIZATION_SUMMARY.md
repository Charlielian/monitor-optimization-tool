# 文件整理总结

## 整理时间
2025-12-29

## 整理目的
保持项目根目录整洁，只保留关键运行脚本和配置文件，将测试脚本和说明文档移至 temp 目录。

## 根目录保留的文件

### Python 脚本（关键运行文件）
- `app.py` - Flask 主应用程序
- `auth.py` - 用户认证模块
- `config.py` - 配置加载模块
- `constants.py` - 常量定义
- `flask_service.py` - Flask 服务启动脚本
- `generate_password_hash.py` - 密码哈希生成工具

### 配置文件
- `config.json` - 主配置文件（包含数据库、认证等配置）
- `config.example.json` - 配置文件示例
- `service_config.json` - 服务配置
- `requirements.txt` - Python 依赖包列表

### 文档
- `README.md` - 项目主说明文档
- `QUICKSTART.md` - 快速开始指南

### 其他
- `query` - 查询脚本

### 目录结构
- `db/` - 数据库相关
- `services/` - 业务服务层
- `templates/` - HTML 模板
- `static/` - 静态资源
- `utils/` - 工具函数
- `logs/` - 日志文件
- `temp/` - 临时文件和文档
- `venv/` - Python 虚拟环境

## 移至 temp 目录的文件

### 测试脚本（5个）
1. `test_auth.py` - 认证系统测试
2. `test_admin_single_ip.py` - 管理员单IP登录测试
3. `test_user_management.py` - 用户管理测试
4. `test_export_latest_metrics.py` - 导出功能测试
5. `test_mysql_connection.py` - MySQL 连接测试

### 说明文档（24个）
1. `AUTH_SYSTEM_GUIDE.md` - 认证系统指南
2. `USER_MANAGEMENT_GUIDE.md` - 用户管理指南
3. `CONFIG_GUIDE.md` - 配置指南
4. `EXPORT_GUIDE.md` - 导出指南
5. `QUICKSTART_AUTH.md` - 认证快速开始
6. `AUTH_IMPLEMENTATION_SUMMARY.md` - 认证实现总结
7. `ADMIN_FEATURES_SUMMARY.md` - 管理员功能总结
8. `ADMIN_SINGLE_IP_LOGIN.md` - 单IP登录功能
9. `CELL_WITHOUT_DATA_FEATURE.md` - 无数据小区功能
10. `EXCEL_EXPORT_FEATURES.md` - Excel 导出功能
11. `TASK4_NO_TRAFFIC_NO_PERFORMANCE_SUMMARY.md` - 无流量/无性能统计
12. `CHANGELOG_20251229.md` - 更新日志
13. `UPDATE_SUMMARY.md` - 更新总结
14. `UPDATE_NO_PERFORMANCE_INCLUDES_NO_DATA.md` - 无性能统计更新
15. `CHANGES_SUMMARY.md` - 变更总结
16. `FINAL_SUMMARY.md` - 最终总结
17. `DEPLOYMENT_SUMMARY.md` - 部署总结
18. `INSTALL_MYSQL.md` - MySQL 安装
19. `MYSQL_INTEGRATION.md` - MySQL 集成
20. `WINDOWS_SERVICE_INSTALL.md` - Windows 服务安装
21. `START_CHECKLIST.md` - 启动检查清单
22. `CELL_QUERY_UPDATE.md` - 小区查询更新
23. `CGI_MATCHING_SUMMARY.md` - CGI 匹配总结
24. `TEST_CELL_WITHOUT_DATA.md` - 无数据小区测试

## 整理效果

### 整理前
- 根目录文件：40+ 个文件
- 包含大量测试脚本和说明文档
- 不易找到关键运行文件

### 整理后
- 根目录文件：13 个关键文件
- 结构清晰，一目了然
- 测试和文档集中在 temp 目录

## 使用建议

1. **日常开发**：只需关注根目录的关键文件
2. **查看文档**：需要时到 temp 目录查找
3. **运行测试**：从 temp 目录运行测试脚本
4. **部署生产**：可以不包含 temp 目录

## 文件访问

如需查看 temp 目录中的文档，请参考：
- `temp/README_TEMP.md` - temp 目录详细说明
