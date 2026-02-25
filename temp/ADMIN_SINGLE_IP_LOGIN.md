# 管理员单IP登录功能说明

## 功能概述

为了增强系统安全性，管理员账号现在实施**单IP登录限制**：同一时间只允许管理员从一个IP地址登录。如果管理员从新的IP地址登录，系统会自动踢出旧的session。

## 功能特性

### 1. 管理员单IP限制
- 管理员账号同一时间只能从一个IP地址登录
- 如果从新IP登录，旧session会被自动踢出
- 系统会记录管理员的登录IP并在每次请求时验证

### 2. 普通用户不受限制
- 普通用户（role: user）不受IP限制
- 可以从多个设备/IP同时登录

### 3. 多管理员独立管理
- 如果系统有多个管理员账号，每个管理员的IP独立管理
- 不同管理员之间互不影响

### 4. 自动清理
- 管理员退出登录时，系统会自动清除IP记录
- 允许管理员从新的IP重新登录

## 实现细节

### 1. IP获取
系统从以下来源获取客户端IP：
```python
client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
```
- 优先使用 `X-Forwarded-For` 头（适用于反向代理场景）
- 如果没有，使用 `request.remote_addr`

### 2. IP验证流程

#### 登录时：
1. 验证用户名和密码
2. 获取客户端IP
3. 如果是管理员：
   - 检查是否已有登录IP记录
   - 如果有且不匹配，清除旧记录（踢出旧session）
   - 记录新的登录IP
4. 创建新session

#### 访问管理员页面时：
1. 检查是否已登录
2. 检查是否有管理员权限
3. 获取当前请求IP
4. 对比session中记录的登录IP
5. 如果不匹配，清除session并要求重新登录

### 3. 代码修改

#### auth.py
```python
class AuthManager:
    def __init__(self, users_config: dict):
        self.users = users_config
        self.logger = logging.getLogger(__name__)
        # 管理员登录IP记录
        self.admin_login_ips = {}
    
    def check_admin_ip(self, username: str, current_ip: str) -> bool:
        """检查管理员IP是否匹配"""
        # 实现逻辑...
    
    def record_admin_login(self, username: str, ip_address: str):
        """记录管理员登录IP"""
        # 实现逻辑...
    
    def clear_admin_login(self, username: str):
        """清除管理员登录IP记录"""
        # 实现逻辑...
```

#### app.py - 登录路由
```python
@app.route("/login", methods=["GET", "POST"])
def login():
    # 获取客户端IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # 如果是管理员，检查IP限制
    if user_role == "admin":
        if not auth_manager.check_admin_ip(username, client_ip):
            auth_manager.clear_admin_login(username)
    
    # 记录登录IP到session
    session["login_ip"] = client_ip
    
    # 记录管理员登录IP
    if user_role == "admin":
        auth_manager.record_admin_login(username, client_ip)
```

#### auth.py - admin_required装饰器
```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查管理员IP是否匹配
        login_ip = session.get("login_ip")
        current_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        if login_ip and login_ip != current_ip:
            session.clear()
            flash("检测到异地登录，已退出当前会话", "warning")
            return redirect(url_for("login"))
        
        return f(*args, **kwargs)
    return decorated_function
```

## 使用场景

### 场景1：正常使用
1. 管理员从办公室电脑（IP: 192.168.1.100）登录
2. 正常使用系统功能
3. 退出登录

### 场景2：异地登录
1. 管理员从办公室电脑（IP: 192.168.1.100）登录
2. 忘记退出，回家后从家里电脑（IP: 192.168.1.200）登录
3. 系统检测到新IP，自动踢出办公室的session
4. 家里电脑成功登录
5. 办公室电脑下次访问时会被要求重新登录

### 场景3：安全防护
1. 管理员从办公室电脑（IP: 192.168.1.100）登录
2. 攻击者从其他地方（IP: 10.0.0.1）尝试使用管理员账号登录
3. 如果攻击者知道密码，会踢出办公室的session
4. 办公室管理员会立即发现异常（被踢出）
5. 管理员可以及时修改密码

## 日志记录

系统会记录以下事件：
- 管理员登录IP记录
- 管理员IP不匹配警告
- 管理员IP清除记录

示例日志：
```
2025-12-29 10:00:00 - INFO - 管理员 admin 登录IP已记录: 192.168.1.100
2025-12-29 11:00:00 - WARNING - 管理员 admin 尝试从新IP登录: 192.168.1.200，旧IP: 192.168.1.100
2025-12-29 11:00:01 - WARNING - 管理员 admin IP不匹配，已踢出: 登录IP=192.168.1.100, 当前IP=192.168.1.200
2025-12-29 12:00:00 - INFO - 管理员 admin 登录IP已清除
```

## 测试

运行测试脚本验证功能：
```bash
python test_admin_single_ip.py
```

测试覆盖：
- ✓ 管理员首次登录
- ✓ 管理员从相同IP访问
- ✓ 管理员从新IP登录（被拒绝）
- ✓ 清除旧IP后允许新IP登录
- ✓ 普通用户不受IP限制
- ✓ 多个管理员独立管理

## 注意事项

### 1. 反向代理配置
如果使用Nginx等反向代理，需要正确配置 `X-Forwarded-For` 头：

```nginx
location / {
    proxy_pass http://127.0.0.1:5010;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 2. 动态IP环境
如果管理员使用动态IP（如家庭宽带），可能会因为IP变化而被踢出。这种情况下：
- 可以考虑放宽限制（如同一网段）
- 或者建议管理员使用固定IP/VPN

### 3. 内存存储
当前IP记录存储在内存中（`admin_login_ips` 字典），应用重启后会丢失。如果需要持久化，可以：
- 存储到Redis
- 存储到数据库
- 存储到文件

### 4. 多实例部署
如果应用部署多个实例（负载均衡），需要使用共享存储（如Redis）来同步IP记录。

## 配置

当前配置在 `config.json` 中：
```json
{
    "auth_config": {
        "enable_auth": true,
        "session_lifetime_hours": 24,
        "users": {
            "admin": {
                "password_hash": "...",
                "role": "admin",
                "name": "系统管理员"
            }
        }
    }
}
```

## 相关文件

- `auth.py` - 认证管理器，包含IP检查逻辑
- `app.py` - Flask应用，登录和登出路由
- `test_admin_single_ip.py` - 功能测试脚本
- `config.json` - 用户配置

## 更新日志

**2025-12-29**
- ✓ 实现管理员单IP登录限制
- ✓ 添加IP记录和验证逻辑
- ✓ 更新登录和登出流程
- ✓ 添加admin_required装饰器IP检查
- ✓ 创建测试脚本
- ✓ 所有测试通过
