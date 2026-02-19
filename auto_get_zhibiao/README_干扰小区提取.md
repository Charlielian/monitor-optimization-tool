# 干扰小区数据提取工具使用说明

## 📋 功能概述

本工具用于自动登录大数据平台，进入即席查询模块，提取4G/5G干扰小区数据。

## 🚀 快速开始

### 方式一：使用快速提取脚本（推荐）

```bash
python quick_extract_interference.py
```

按照提示输入：
1. 网络类型（5G/4G）
2. 查询天数（默认7天）
3. 城市名称（默认"阳江"）

### 方式二：使用完整功能脚本

```bash
python get_interference_cells.py
```

## 📦 依赖环境

### 必需的Python包
```bash
pip install pandas openpyxl requests lxml pycryptodome pytesseract pillow
```

### Tesseract OCR
用于图形验证码识别，需要安装：
- Windows: 下载安装包 https://github.com/UB-Mannheim/tesseract/wiki
- macOS: `brew install tesseract`
- Linux: `apt-get install tesseract-ocr`

## 🔧 配置说明

### 1. 账号配置

默认使用 `Login.py` 中配置的账号：
```python
uname_gol = 'dwpengmin'
password_gol = 'YJdwpm_258'
```

如需使用其他账号，可以在代码中指定：
```python
extractor = InterferenceCellExtractor(
    username='your_username',
    password='your_password'
)
```

### 2. 查询参数配置

在 `get_interference_cells.py` 的 `main()` 函数中修改：

```python
df_5g = extractor.get_interference_data(
    network_type='5G',        # 网络类型: '4G' 或 '5G'
    start_date='2025-01-13',  # 开始日期
    end_date='2025-01-19',    # 结束日期
    city='阳江',               # 城市名称
    only_interfered=True      # 是否只提取干扰小区
)
```

## 📊 输出数据说明

### 5G干扰小区数据字段

| 字段名 | 说明 |
|--------|------|
| 数据时间 | starttime |
| 结束时间 | endtime |
| CGI | 小区全局标识 |
| 小区名 | cell_name |
| 频段 | freq |
| 微网格标识 | micro_grid |
| 全频段均值 | averagevalue |
| D1均值 | averagevalued1 |
| D2均值 | averagevalued2 |
| 是否干扰小区 | is_interfere_5g |

### 4G干扰小区数据字段

| 字段名 | 说明 |
|--------|------|
| 数据时间 | starttime |
| 结束时间 | endtime |
| CGI | 小区全局标识 |
| 小区名 | cell_name |
| 频段 | freq |
| 微网格标识 | micro_grid |
| 系统带宽 | bandwidth |
| 平均干扰电平 | averagevalue |
| 是否干扰小区 | is_interfere |

## 💡 使用示例

### 示例1：提取最近7天的5G干扰小区

```python
from get_interference_cells import InterferenceCellExtractor

extractor = InterferenceCellExtractor()
extractor.login()
extractor.init_jxcx()

df = extractor.get_interference_data(
    network_type='5G',
    days=7,
    city='阳江',
    only_interfered=True
)

extractor.save_to_excel(df, filename='5G干扰小区_最近7天.xlsx')
```

### 示例2：提取指定日期范围的4G干扰小区

```python
from datetime import datetime

df = extractor.get_interference_data(
    network_type='4G',
    start_date='2025-01-01',
    end_date='2025-01-31',
    city='阳江',
    only_interfered=True
)
```

### 示例3：提取所有小区（包括非干扰小区）

```python
df = extractor.get_interference_data(
    network_type='5G',
    start_date='2025-01-13',
    end_date='2025-01-19',
    city='阳江',
    only_interfered=False  # 提取所有小区
)
```

## 🔐 登录流程说明

1. **Cookie复用**：优先尝试使用本地保存的cookie
2. **图形验证码**：自动OCR识别（前5次），失败后需手动输入
3. **短信验证码**：需要手动输入短信验证码
4. **Session保持**：登录成功后自动保存session

## 📁 输出文件位置

默认保存路径：`WNCOP-20250303-debug/data/out/`

文件命名格式：`{网络类型}_干扰小区_{时间戳}.xlsx`

例如：`5G_干扰小区_20250114_153045.xlsx`

## ⚠️ 注意事项

1. **首次登录**需要输入短信验证码，后续可使用cookie自动登录
2. **图形验证码**识别可能失败，失败后需手动输入
3. **查询大量数据**时可能需要较长时间，请耐心等待
4. **网络连接**需要能够访问 `nqi.gmcc.net:20443`
5. **数据时效性**：平台数据通常有1-2天延迟

## 🐛 常见问题

### Q1: 登录失败怎么办？
- 检查网络连接
- 确认账号密码正确
- 尝试删除 `data/cookies/` 目录下的cookie文件重新登录

### Q2: 图形验证码识别失败？
- 前5次自动识别失败后会保存验证码图片到 `data/验证码/` 目录
- 手动查看图片并输入验证码

### Q3: 查询不到数据？
- 检查日期范围是否正确
- 确认城市名称是否正确
- 检查平台是否有该时间段的数据

### Q4: 短信验证码收不到？
- 检查手机号是否正确
- 联系管理员确认账号状态
- 尝试重新触发短信发送

## 📞 技术支持

如遇到问题，请检查：
1. `WNCOP-20250303-debug/feature/login/log.log` - 登录日志
2. `WNCOP-20250303-debug/log.log` - 主程序日志

## 🔄 更新日志

### v1.0 (2025-01-14)
- ✨ 初始版本
- ✅ 支持4G/5G干扰小区数据提取
- ✅ 支持自动登录和cookie复用
- ✅ 支持图形验证码自动识别
- ✅ 支持数据导出为Excel格式

## 📝 代码结构

```
.
├── get_interference_cells.py      # 完整功能脚本（面向对象）
├── quick_extract_interference.py  # 快速提取脚本（简化版）
├── README_干扰小区提取.md          # 使用说明文档
└── WNCOP-20250303-debug/
    ├── feature/
    │   ├── login/
    │   │   └── Login.py           # 登录模块
    │   └── get_data/
    │       └── JXCX/
    │           ├── entry.py       # 即席查询入口
    │           └── payload/
    │               ├── ganrao_NR.py   # 5G干扰查询模板
    │               ├── ganrao_LTE.py  # 4G干扰查询模板
    │               └── set_where.py   # 查询条件设置
    └── data/
        ├── cookies/               # Cookie存储目录
        ├── 验证码/                 # 验证码图片目录
        └── out/                   # 输出文件目录
```

## 🎯 核心功能模块

### 1. 登录模块 (`Login.py`)
- RSA加密账号密码
- 图形验证码OCR识别
- 短信验证码验证
- Cookie管理

### 2. 即席查询模块 (`entry.py`)
- 进入即席查询系统
- 获取查询结果行数
- 执行查询并返回数据
- 中英文字段映射

### 3. Payload模板 (`ganrao_*.py`)
- 预定义查询参数
- 字段定义和映射
- 查询条件模板

### 4. 数据提取器 (`InterferenceCellExtractor`)
- 封装完整提取流程
- 支持灵活参数配置
- 自动数据过滤和保存
