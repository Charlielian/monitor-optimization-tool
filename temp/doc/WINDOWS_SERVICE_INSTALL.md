# Flask项目Windows服务安装指南

本文档详细介绍如何将Flask项目部署为Windows服务，适用于生产环境。

## 1. 环境要求

| 环境项 | 要求 | 备注 |
|-------|------|------|
| 操作系统 | Windows Server 2012+ 或 Windows 10+ | 建议使用Windows Server |
| Python版本 | Python 3.8+ | 推荐3.10+ |
| 权限 | 管理员权限 | 用于安装和管理服务 |
| 数据库 | PostgreSQL | 已部署并可访问 |

## 2. 项目准备

### 2.1 项目结构

确保项目包含以下关键文件：
- `app.py` - Flask应用入口
- `config.py` - 配置加载器
- `config.json` - 配置文件
- `flask_service.py` - Windows服务包装器
- `requirements.txt` - 项目依赖

### 2.2 配置文件

#### 2.2.1 数据库配置 (`config.json`)

修改数据库连接信息：

```json
{
    "pgsql_config": {
        "host": "192.168.31.51",
        "port": 5432,
        "database": "postgres",
        "user": "postgres",
        "password": "103001"
    }
}
```

#### 2.2.2 服务配置 (`service_config.json`)

配置服务运行参数：

```json
{
    "host": "0.0.0.0",
    "port": 5001,
    "debug": false,
    "log_level": "INFO",
    "waitress": {
        "threads": 8,
        "connection_limit": 100,
        "channel_timeout": 60
    }
}
```

## 3. 依赖安装

以管理员身份运行命令提示符，执行以下命令：

```powershell
# 进入项目目录
cd C:\tmp\网页监控_flask 2

# 安装项目依赖
pip install -r requirements.txt pywin32 waitress psycopg2-binary
```

### 依赖说明

| 依赖包 | 用途 |
|-------|------|
| `pywin32` | 创建和管理Windows服务 |
| `waitress` | 生产级WSGI服务器 |
| `psycopg2-binary` | PostgreSQL数据库驱动 |
| `requirements.txt` | 项目其他依赖（Flask、pandas等） |

## 4. 服务安装

### 4.1 安装服务

```powershell
python flask_service.py install
```

**预期输出：**
```
Installing service FlaskMonitoringApp
Changing service configuration
Service updated
```

### 4.2 启动服务

```powershell
python flask_service.py start
```

**预期输出：**
```
Starting service FlaskMonitoringApp
```

### 4.3 验证服务状态

```powershell
Get-Service -Name FlaskMonitoringApp
```

**预期输出：**
```
Status   Name               DisplayName
------   ----               -----------
Running  FlaskMonitoringApp 保障指标监控系统 (Flask)
```

## 5. 服务管理命令

### 5.1 停止服务

```powershell
python flask_service.py stop
```

### 5.2 重启服务

```powershell
python flask_service.py restart
```

### 5.3 卸载服务

```powershell
python flask_service.py remove
```

### 5.4 查看服务配置

```powershell
python flask_service.py config
```

### 5.5 调试模式运行

```powershell
python flask_service.py debug
```

## 6. 服务信息

| 服务属性 | 值 |
|---------|-----|
| 服务名称 | FlaskMonitoringApp |
| 显示名称 | 保障指标监控系统 (Flask) |
| 描述 | 保障指标监控系统 - Flask Web应用服务 |
| 默认端口 | 5001 |
| 日志路径 | `logs/service.log` |
| 访问地址 | http://localhost:5001 |

## 7. 故障排除

### 7.1 服务安装失败

**问题**：`错误: 无法打开服务控制管理器`

**解决方案**：
- 以**管理员身份**运行命令提示符
- 检查命令是否正确

### 7.2 服务启动失败

**问题**：服务状态显示`Stopped`

**解决方案**：
1. 查看服务日志：
   ```powershell
   Get-Content logs/service.log -Tail 100
   ```

2. 常见错误及解决方法：

   | 错误信息 | 原因 | 解决方案 |
   |---------|------|----------|
   | `Connection refused` | 数据库连接失败 | 检查数据库是否运行，连接参数是否正确 |
   | `Unknown adjustment 'request_timeout'` | Waitress配置错误 | 修改`flask_service.py`，移除`request_timeout`参数 |
   | `KeyError: 'request_timeout'` | 配置参数缺失 | 修改`flask_service.py`，移除对不存在参数的引用 |

### 7.3 数据库连接失败

**解决方案**：
- 验证数据库服务是否运行：`net start postgresql-x64-17`（根据版本调整）
- 检查`config.json`中的数据库配置是否正确
- 测试数据库连接：
  ```powershell
  python -c "import psycopg2; psycopg2.connect(host='192.168.31.51', port=5432, database='postgres', user='postgres', password='103001')"
  ```

### 7.4 端口被占用

**解决方案**：
- 查看端口占用情况：
  ```powershell
  netstat -ano | findstr :5001
  ```
- 结束占用端口的进程：
  ```powershell
  taskkill /PID <进程ID> /F
  ```
- 修改`service_config.json`中的端口配置

## 8. 访问验证

### 8.1 本地访问

在浏览器中访问：
```
http://localhost:5001
```

### 8.2 命令行验证

使用curl命令测试：
```powershell
curl http://localhost:5001
```

**预期输出**：返回HTML页面内容

## 9. 服务自动启动设置

### 9.1 安装时设置自动启动

```powershell
python flask_service.py --startup=auto install
```

### 9.2 修改现有服务的启动类型

```powershell
sc config FlaskMonitoringApp start= auto
```

## 10. 日志管理

### 10.1 查看服务日志

```powershell
# 查看最新日志
Get-Content logs/service.log -Tail 50

# 实时监控日志
Get-Content logs/service.log -Wait
```

### 10.2 日志配置

日志配置在`service_config.json`中：

```json
{
    "log_level": "INFO"
}
```

支持的日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL

## 11. 常见管理操作

### 11.1 查看服务列表

```powershell
Get-Service | Where-Object {$_.DisplayName -like "*Flask*"}
```

### 11.2 查看服务详情

```powershell
sc qc FlaskMonitoringApp
```

### 11.3 手动启动/停止服务

1. 打开**服务管理器**（services.msc）
2. 找到"保障指标监控系统 (Flask)"服务
3. 右键点击，选择"启动"或"停止"

## 12. 卸载服务

### 12.1 停止服务

```powershell
python flask_service.py stop
```

### 12.2 卸载服务

```powershell
python flask_service.py remove
```

## 13. 升级服务

### 13.1 停止服务

```powershell
python flask_service.py stop
```

### 13.2 更新代码

替换项目文件（保留配置文件）

### 13.3 重启服务

```powershell
python flask_service.py start
```

## 14. 最佳实践

1. **定期备份**：定期备份配置文件和数据库
2. **监控日志**：设置日志监控，及时发现问题
3. **更新依赖**：定期更新项目依赖，修复安全漏洞
4. **配置防火墙**：开放必要端口，限制访问来源
5. **使用HTTPS**：生产环境建议配置HTTPS

## 15. 附录

### 15.1 服务相关文件

| 文件路径 | 用途 |
|---------|------|
| `flask_service.py` | Windows服务包装器 |
| `service_config.json` | 服务运行配置 |
| `config.json` | 应用配置 |
| `logs/service.log` | 服务日志 |

### 15.2 服务命令速查表

| 操作 | 命令 |
|------|------|
| 安装服务 | `python flask_service.py install` |
| 启动服务 | `python flask_service.py start` |
| 停止服务 | `python flask_service.py stop` |
| 重启服务 | `python flask_service.py restart` |
| 卸载服务 | `python flask_service.py remove` |
| 查看配置 | `python flask_service.py config` |
| 调试模式 | `python flask_service.py debug` |

---

**文档更新时间**：2025-12-29
**适用版本**：Flask 3.0+
**作者**：自动生成
