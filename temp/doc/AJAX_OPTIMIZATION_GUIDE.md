# AJAX 局部刷新优化指南

## 概述
已创建全局 AJAX 工具库 `static/js/ajax-utils.js`，提供统一的 AJAX 请求处理、Toast 提示、表单处理等功能，避免整页刷新。

## 已完成的优化

### 1. 全局工具库
**文件**: `static/js/ajax-utils.js`

提供以下功能模块：
- **ToastManager**: Toast 提示管理
- **AjaxManager**: AJAX 请求管理
- **LoadingManager**: 加载动画管理
- **FormHandler**: 表单 AJAX 化处理
- **ConfirmDialog**: 确认对话框
- **Utils**: 工具函数（防抖、节流、日期格式化等）

### 2. 后端 API 接口
**文件**: `app.py`

新增 API 路由：
```python
@app.route("/api/scenarios/cells", methods=["POST"])
```

支持操作：
- `add_cell`: 添加单个小区
- `remove_cell`: 移除小区

返回格式：
```json
{
  "success": true/false,
  "message": "操作结果消息",
  "cells": [...],  // 更新后的小区列表
  "total": 10      // 小区总数
}
```

### 3. 前端优化
**文件**: `templates/scenarios.html`

- 添加/移除小区使用 AJAX，无需刷新页面
- 实时更新小区列表和统计数字
- 使用 Toast 提示替代 alert
- 表单提交时显示加载状态

## 使用方法

### 在任何页面使用 Toast 提示

```javascript
// 成功提示
toast.success('操作成功！');

// 错误提示
toast.error('操作失败！');

// 警告提示
toast.warning('请注意！');

// 信息提示
toast.info('提示信息');
```

### 发送 AJAX 请求

```javascript
// GET 请求
ajax.get('/api/endpoint')
  .then(data => {
    console.log(data);
  });

// POST 请求
ajax.post('/api/endpoint', { key: 'value' })
  .then(data => {
    console.log(data);
  });

// 自定义选项
ajax.post('/api/endpoint', data, {
  showLoading: false,  // 不显示加载动画
  showToast: false     // 不自动显示 Toast
});
```

### 表单 AJAX 化

```javascript
// 方法1: 使用 ajaxify
AjaxUtils.form.ajaxify('#myForm', {
  url: '/api/endpoint',
  onSuccess: (result) => {
    console.log('成功', result);
  },
  onError: (error) => {
    console.log('失败', error);
  }
});

// 方法2: 批量处理
AjaxUtils.form.ajaxifyAll('.ajax-form');
```

### 显示/隐藏加载动画

```javascript
// 显示加载动画
AjaxUtils.loading.show('正在处理...');

// 隐藏加载动画
AjaxUtils.loading.hide();
```

## 扩展到其他页面

### 步骤1: 添加 API 接口（后端）

在 `app.py` 中添加新的 API 路由：

```python
@app.route("/api/your-endpoint", methods=["POST"])
@login_required if auth_enabled else lambda f: f
def api_your_function():
    try:
        data = request.get_json() or request.form.to_dict()
        
        # 处理业务逻辑
        result = your_service.do_something(data)
        
        return jsonify({
            "success": True,
            "message": "操作成功",
            "data": result
        })
    except Exception as e:
        logging.error(f"API错误: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"操作失败：{str(e)}"
        })
```

### 步骤2: 修改前端（模板）

在模板的 `{% block scripts %}` 中使用工具库：

```html
{% block scripts %}
<script>
(function() {
  'use strict';
  
  // 使用全局工具库
  const { toast, ajax, form } = window.AjaxUtils;
  
  // 表单 AJAX 化
  form.ajaxify('#yourForm', {
    url: '/api/your-endpoint',
    onSuccess: (result) => {
      // 更新页面内容
      updatePageContent(result.data);
    }
  });
  
  // 或者手动处理
  document.getElementById('yourButton').addEventListener('click', function() {
    ajax.post('/api/your-endpoint', { action: 'do_something' })
      .then(result => {
        if (result.success) {
          toast.success(result.message);
          // 更新页面
        }
      });
  });
  
})();
</script>
{% endblock %}
```

## 示例：优化其他页面

### 示例1: 保障监控页面 - 添加场景

**后端 API**:
```python
@app.route("/api/scenarios/create", methods=["POST"])
def api_create_scenario():
    data = request.get_json()
    name = data.get("name", "").strip()
    desc = data.get("desc", "").strip()
    
    if not name:
        return jsonify({"success": False, "message": "场景名不能为空"})
    
    scenario_service.create_scenario(name, desc)
    scenarios = scenario_service.list_scenarios()
    
    return jsonify({
        "success": True,
        "message": f"场景 {name} 创建成功",
        "scenarios": scenarios
    })
```

**前端**:
```javascript
form.ajaxify('#createScenarioForm', {
  url: '/api/scenarios/create',
  onSuccess: (result) => {
    // 更新场景列表下拉框
    updateScenarioSelect(result.scenarios);
  }
});
```

### 示例2: 小区查询页面 - 实时搜索

**后端 API**:
```python
@app.route("/api/cells/search", methods=["POST"])
def api_search_cells():
    data = request.get_json()
    cgi = data.get("cgi", "")
    network = data.get("network", "4G")
    
    cells = service.search_cells(cgi, network)
    
    return jsonify({
        "success": True,
        "cells": cells,
        "total": len(cells)
    })
```

**前端**:
```javascript
// 使用防抖优化搜索
const searchInput = document.getElementById('cellSearch');
searchInput.addEventListener('input', AjaxUtils.utils.debounce(function() {
  ajax.post('/api/cells/search', {
    cgi: this.value,
    network: document.getElementById('networkSelect').value
  }, { showLoading: false })
  .then(result => {
    updateCellTable(result.cells);
  });
}, 500));
```

## 优势

1. **无需整页刷新**: 操作响应更快，用户体验更好
2. **统一的错误处理**: 自动显示 Toast 提示
3. **代码复用**: 工具库可在所有页面使用
4. **易于维护**: 集中管理 AJAX 逻辑
5. **优雅的加载状态**: 自动显示/隐藏加载动画

## 注意事项

1. **兼容性**: 确保 `static/js/ajax-utils.js` 在 `base.html` 中正确引入
2. **错误处理**: API 接口应返回统一的 JSON 格式
3. **安全性**: 保持 `@login_required` 装饰器
4. **日志记录**: 在 API 接口中添加适当的日志

## 下一步

建议优化的页面：
1. ✅ 场景管理页面（已完成）
2. 保障监控页面 - 场景创建/删除
3. 小区查询页面 - 实时搜索
4. 管理员页面 - 用户管理操作

## 测试

重启 Flask 服务后，访问场景管理页面测试：
1. 添加小区 - 应该无需刷新页面
2. 移除小区 - 应该无需刷新页面
3. 查看 Toast 提示 - 应该显示在右上角
4. 检查浏览器控制台 - 不应有错误

## 文件清单

- `static/js/ajax-utils.js` - 全局 AJAX 工具库（新增）
- `templates/base.html` - 引入工具库（已修改）
- `templates/scenarios.html` - 使用工具库（已修改）
- `app.py` - 添加 API 接口（已修改）
