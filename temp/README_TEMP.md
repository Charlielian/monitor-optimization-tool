# temp 目录说明

本目录存放测试脚本、开发文档和历史说明文档。

## 目录结构

### 测试脚本
- `test_auth.py` - 认证系统测试
- `test_admin_single_ip.py` - 管理员单IP登录测试
- `test_user_management.py` - 用户管理测试
- `test_export_latest_metrics.py` - 导出功能测试
- `test_mysql_connection.py` - MySQL 连接测试

### 功能说明文档
- `AUTH_SYSTEM_GUIDE.md` - 认证系统使用指南
- `USER_MANAGEMENT_GUIDE.md` - 用户管理指南
- `CONFIG_GUIDE.md` - 配置文件指南
- `EXPORT_GUIDE.md` - 导出功能指南
- `QUICKSTART_AUTH.md` - 认证系统快速开始

### 功能实现总结
- `AUTH_IMPLEMENTATION_SUMMARY.md` - 认证系统实现总结
- `ADMIN_FEATURES_SUMMARY.md` - 管理员功能总结
- `CELL_WITHOUT_DATA_FEATURE.md` - 无数据小区显示功能
- `EXCEL_EXPORT_FEATURES.md` - Excel 导出功能
- `TASK4_NO_TRAFFIC_NO_PERFORMANCE_SUMMARY.md` - 无流量/无性能小区统计功能

### 更新记录
- `CHANGELOG_20251229.md` - 2025-12-29 更新日志
- `UPDATE_SUMMARY.md` - 更新总结
- `UPDATE_NO_PERFORMANCE_INCLUDES_NO_DATA.md` - 无性能小区统计更新
- `CHANGES_SUMMARY.md` - 变更总结
- `FINAL_SUMMARY.md` - 最终总结

### 部署和安装
- `DEPLOYMENT_SUMMARY.md` - 部署总结
- `INSTALL_MYSQL.md` - MySQL 安装指南
- `MYSQL_INTEGRATION.md` - MySQL 集成说明
- `WINDOWS_SERVICE_INSTALL.md` - Windows 服务安装
- `START_CHECKLIST.md` - 启动检查清单

### 开发记录
- `CELL_QUERY_UPDATE.md` - 小区查询更新
- `CGI_MATCHING_SUMMARY.md` - CGI 匹配总结
- `ADMIN_SINGLE_IP_LOGIN.md` - 管理员单IP登录功能
- `TEST_CELL_WITHOUT_DATA.md` - 无数据小区测试

### 历史文档（中文）
- `使用说明.md`
- `场景管理页面优化说明.md`
- `小区查询页面优化说明.md`
- `保障监控页面优化说明.md`
- `场景数据存储说明.md`
- `功能迁移状态.md`
- `优化完成总结.md`
- `最新优化总结.md`
- `高优先级迁移完成总结.md`

### 其他资源
- `download_static_resources.py` - 静态资源下载脚本
- `download_static_resources.sh` - 静态资源下载脚本（Shell）
- `static_preview.html` - 静态资源预览
- `app_optimized_example.py` - 优化示例代码
- `config_manager.py` - 配置管理器
- `templates.zip` - 模板压缩包

## 注意事项

1. 这些文档主要用于开发参考和历史记录
2. 测试脚本可以用于验证功能
3. 如需查看最新的使用说明，请参考根目录的 `README.md` 和 `QUICKSTART.md`
4. 生产环境不需要这些文件

## 根目录保留的关键文件

根目录只保留以下关键文件：
- `app.py` - 主应用程序
- `auth.py` - 认证模块
- `config.py` - 配置模块
- `constants.py` - 常量定义
- `flask_service.py` - Flask 服务
- `generate_password_hash.py` - 密码哈希生成工具
- `config.json` - 配置文件
- `config.example.json` - 配置示例
- `service_config.json` - 服务配置
- `requirements.txt` - Python 依赖
- `README.md` - 主说明文档
- `QUICKSTART.md` - 快速开始指南
- `query` - 查询脚本
