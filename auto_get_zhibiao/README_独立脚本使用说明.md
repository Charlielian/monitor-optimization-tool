# 独立干扰小区提取脚本使用说明

## 📋 简介

`standalone_interference_extractor.py` 是一个**完全独立**的干扰小区数据提取脚本，所有依赖模块已内嵌，无需依赖外部项目目录结构。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests pandas openpyxl lxml pycryptodome pytesseract pillow
```

### 2. 安装 Tesseract OCR（可选，用于自动识别验证码）

- **Windows**: 下载安装 https://github.com/UB-Mannheim/tesseract/wiki
- **macOS**: `brew install tesseract`
- **Linux**: `apt-get install tesseract-ocr`

### 3. 运行脚本

```bash
python standalone_interference_extractor.py
```

按照提示输入参数即可。

## 📝 配置说明

### 修改默认账号

在脚本开头的配置区域修改：

```python
# 登录账号配置（请修改为你的账号）
DEFAULT_USERNAME = 'your_username'
DEFAULT_PASSWORD = 'your_password'
```

### 修改输出目录

```python
# 输出目录配置
OUTPUT_DIR = './interference_data_output'  # 数据输出目录
COOKIE_DIR = './cookies'                   # Cookie保存目录
CAPTCHA_DIR = './captcha_images'           # 验证码图片目录
```

## 💡 使用方式

### 方式一：交互式运行（推荐）

直接运行脚本，按提示输入参数：

```bash
python standalone_interference_extractor.py
```

交互流程：
1. 选择网络类型（5G/4G/同时提取）
2. 输入查询天数（默认7天）
3. 输入城市名称（默认"阳江"）
4. 选择是否只提取干扰小区（默认是）
5. 输入短信验证码（首次登录）

### 方式二：在代码中调用

```python
from standalone_interference_extractor import quick_extract

# 快速提取5G干扰小区数据
df, filepath = quick_extract(
    network_type='5G',
    days=7,
    city='阳江'
)

if df is not None:
    print(f"提取成功，数据已保存到: {filepath}")
    print(df.head())
```

### 方式三：使用提取器类

```python
from standalone_interference_extractor import InterferenceCellExtractor
from datetime import datetime

# 创建提取器
extractor = InterferenceCellExtractor(
    username='your_username',  # 可选，不填使用默认账号
    password='your_password'
)

# 登录
if extractor.login():
    # 初始化即席查询
    if extractor.init_jxcx():
        # 提取数据
        df = extractor.extract_data(
            network_type='5G',
            start_date='2025-01-13',
            end_date='2025-01-19',
            city='阳江',
            only_interfered=True
        )
        
        # 保存数据
        if not df.empty:
            extractor.save_to_excel(df, network_type='5G')
```

## 📊 输出数据

### 输出文件

- **位置**: `./interference_data_output/`
- **格式**: Excel (.xlsx)
- **命名**: `{网络类型}_干扰小区_{时间戳}.xlsx`
- **示例**: `5G_干扰小区_20250114_153045.xlsx`

### 5G干扰小区字段

| 字段名 | 说明 |
|--------|------|
| 数据时间 | 数据采集时间 |
| 结束时间 | 数据结束时间 |
| CGI | 小区全局标识 |
| 小区名 | 小区名称 |
| 频段 | 频段信息 |
| 微网格标识 | 微网格ID |
| 全频段均值 | 全频段干扰均值 |
| D1均值 | D1频段干扰均值 |
| D2均值 | D2频段干扰均值 |
| 是否干扰小区 | 是/否 |

### 4G干扰小区字段

| 字段名 | 说明 |
|--------|------|
| 数据时间 | 数据采集时间 |
| 结束时间 | 数据结束时间 |
| CGI | 小区全局标识 |
| 小区名 | 小区名称 |
| 频段 | 频段信息 |
| 微网格标识 | 微网格ID |
| 系统带宽 | 系统带宽 |
| 平均干扰电平 | 平均干扰电平 |
| 是否干扰小区 | 是/否 |

## 🔐 登录流程

1. **Cookie复用**: 优先使用保存的cookie（位于 `./cookies/` 目录）
2. **图形验证码**: 
   - 前5次自动OCR识别
   - 失败后保存图片到 `./captcha_images/` 目录，需手动输入
3. **短信验证码**: 首次登录需要输入短信验证码
4. **Session保持**: 登录成功后自动保存cookie，下次可直接使用

## ⚠️ 注意事项

1. **首次运行**需要输入短信验证码
2. **图形验证码**识别可能失败，失败后需手动输入
3. **网络要求**：需要能访问 `nqi.gmcc.net:20443`
4. **数据延迟**：平台数据通常有1-2天延迟
5. **查询限制**：单次查询不建议超过30天数据

## 🐛 常见问题

### Q1: 提示"模块未找到"错误？

确保已安装所有依赖：
```bash
pip install requests pandas openpyxl lxml pycryptodome pytesseract pillow
```

### Q2: 验证码识别失败？

- 检查是否安装了 Tesseract OCR
- 或者直接查看 `./captcha_images/` 目录下的验证码图片手动输入

### Q3: 登录失败？

- 检查账号密码是否正确
- 删除 `./cookies/` 目录下的cookie文件重试
- 检查网络连接

### Q4: 查询不到数据？

- 确认日期范围是否正确
- 确认城市名称是否正确（如"阳江"）
- 检查平台是否有该时间段的数据

### Q5: 短信验证码收不到？

- 检查手机号是否正确
- 联系管理员确认账号状态
- 等待30秒后重试

## 📁 目录结构

运行后会自动创建以下目录：

```
.
├── standalone_interference_extractor.py  # 主脚本
├── interference_data_output/             # 数据输出目录
│   ├── 5G_干扰小区_20250114_153045.xlsx
│   └── 4G_干扰小区_20250114_153050.xlsx
├── cookies/                              # Cookie保存目录
│   └── dwpengmin.pkl
└── captcha_images/                       # 验证码图片目录
    ├── captcha_0_0.jpg
    └── captcha_0_1.jpg
```

## 🔄 更新日志

### v1.0 (2025-01-14)
- ✨ 初始版本
- ✅ 完全独立，无需外部依赖
- ✅ 支持4G/5G干扰小区数据提取
- ✅ 支持自动登录和cookie复用
- ✅ 支持图形验证码自动识别
- ✅ 支持交互式和编程式调用

## 📞 技术支持

如遇到问题，请检查：
1. 网络连接是否正常
2. 依赖包是否完整安装
3. 账号密码是否正确
4. 平台是否可访问

## 🎯 核心特性

- ✅ **完全独立**: 所有模块已内嵌，无需外部项目
- ✅ **自动登录**: 支持cookie复用，减少登录次数
- ✅ **智能识别**: 图形验证码自动OCR识别
- ✅ **灵活查询**: 支持自定义时间范围和城市
- ✅ **数据过滤**: 可选择只提取干扰小区
- ✅ **多种调用**: 支持交互式、函数式、类式调用
- ✅ **错误处理**: 完善的异常处理和提示信息

## 📖 代码示例

### 示例1: 提取最近7天的5G干扰小区

```python
from standalone_interference_extractor import quick_extract

df, filepath = quick_extract(network_type='5G', days=7, city='阳江')
```

### 示例2: 提取指定日期范围的4G干扰小区

```python
from standalone_interference_extractor import InterferenceCellExtractor

extractor = InterferenceCellExtractor()
extractor.login()
extractor.init_jxcx()

df = extractor.extract_data(
    network_type='4G',
    start_date='2025-01-01',
    end_date='2025-01-31',
    city='阳江',
    only_interfered=True
)

extractor.save_to_excel(df, filename='4G干扰小区_1月.xlsx')
```

### 示例3: 批量提取多个城市数据

```python
from standalone_interference_extractor import InterferenceCellExtractor

cities = ['阳江', '广州', '深圳']
extractor = InterferenceCellExtractor()
extractor.login()
extractor.init_jxcx()

for city in cities:
    df = extractor.extract_data(
        network_type='5G',
        days=7,
        city=city,
        only_interfered=True
    )
    extractor.save_to_excel(df, filename=f'5G干扰小区_{city}.xlsx')
```
