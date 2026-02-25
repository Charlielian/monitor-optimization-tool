# 静态资源下载说明

## 问题说明

本应用依赖以下外部资源：
- Bootstrap 5.3.3 (CSS 和 JS)
- Chart.js 4.4.4

在无网络环境下，这些资源无法从 CDN 加载，会导致页面样式异常和图表无法显示。

## 解决方案

### 方法1：使用下载脚本（推荐）

在有网络的环境下，运行以下任一脚本：

**使用 Python 脚本：**
```bash
python3 download_static_resources.py
```

**使用 Shell 脚本：**
```bash
bash download_static_resources.sh
```

脚本会自动下载以下文件到 `static` 目录：
- `static/css/bootstrap.min.css`
- `static/js/bootstrap.bundle.min.js`
- `static/js/chart.umd.min.js`

### 方法2：手动下载

如果脚本无法运行，可以手动下载以下文件：

1. **Bootstrap CSS**
   - URL: https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css
   - 保存到: `static/css/bootstrap.min.css`

2. **Bootstrap JS**
   - URL: https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js
   - 保存到: `static/js/bootstrap.bundle.min.js`

3. **Chart.js**
   - URL: https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js
   - 保存到: `static/js/chart.umd.min.js`

### 验证

下载完成后，重启 Flask 应用，页面应该能正常显示。如果资源未正确加载，页面顶部会显示警告信息。

## 目录结构

下载完成后，`static` 目录结构应该是：

```
static/
├── css/
│   ├── bootstrap.min.css
│   └── style.css
└── js/
    ├── bootstrap.bundle.min.js
    └── chart.umd.min.js
```

