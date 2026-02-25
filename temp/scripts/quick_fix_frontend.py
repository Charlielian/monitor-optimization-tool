#!/usr/bin/env python3
"""
前端性能快速修复脚本
自动应用关键优化
"""

import os
import re
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def backup_file(filepath):
    """备份文件"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.backup"
        import shutil
        shutil.copy2(filepath, backup_path)
        logging.info(f"✓ 已备份: {filepath}")
        return True
    return False

def add_chart_optimizer_to_base():
    """在 base.html 中添加图表优化工具"""
    logging.info("\n" + "=" * 60)
    logging.info("步骤 1: 添加图表优化工具到 base.html")
    logging.info("=" * 60)
    
    base_file = 'templates/base.html'
    
    if not os.path.exists(base_file):
        logging.error(f"✗ 找不到 {base_file}")
        return False
    
    backup_file(base_file)
    
    with open(base_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已添加
    if 'chart-optimizer.js' in content:
        logging.info("✓ 图表优化工具已存在")
        return True
    
    # 在 performance-monitor.js 之前添加
    if 'performance-monitor.js' in content:
        content = content.replace(
            '<script src="{{ url_for(\'static\', filename=\'js/performance-monitor.js\') }}" defer></script>',
            '<script src="{{ url_for(\'static\', filename=\'js/chart-optimizer.js\') }}" defer></script>\n    <script src="{{ url_for(\'static\', filename=\'js/performance-monitor.js\') }}" defer></script>'
        )
        
        with open(base_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info("✓ 图表优化工具已添加")
        return True
    else:
        logging.error("✗ 找不到 performance-monitor.js 引用")
        return False

def add_downsample_to_service():
    """在 metrics_service.py 中添加降采样函数"""
    logging.info("\n" + "=" * 60)
    logging.info("步骤 2: 添加数据降采样函数")
    logging.info("=" * 60)
    
    service_file = 'services/metrics_service.py'
    
    if not os.path.exists(service_file):
        logging.error(f"✗ 找不到 {service_file}")
        return False
    
    backup_file(service_file)
    
    with open(service_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已添加
    if 'def downsample_data' in content:
        logging.info("✓ 降采样函数已存在")
        return True
    
    # 在类定义后添加降采样函数
    downsample_code = '''
    @staticmethod
    def downsample_data(data, max_points=100):
        """
        数据降采样 - 减少前端渲染压力
        
        Args:
            data: 原始数据列表
            max_points: 最大数据点数量
        
        Returns:
            降采样后的数据
        """
        if not data or len(data) <= max_points:
            return data
        
        step = max(1, len(data) // max_points)
        return data[::step]
'''
    
    # 找到类定义
    class_match = re.search(r'class\s+MetricsService.*?:', content)
    if class_match:
        insert_pos = class_match.end()
        content = content[:insert_pos] + downsample_code + content[insert_pos:]
        
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info("✓ 降采样函数已添加")
        logging.info("  请手动在各个查询方法中调用 downsample_data()")
        return True
    else:
        logging.error("✗ 找不到 MetricsService 类定义")
        return False

def create_optimized_dashboard_template():
    """创建优化后的 dashboard 模板示例"""
    logging.info("\n" + "=" * 60)
    logging.info("步骤 3: 创建优化模板示例")
    logging.info("=" * 60)
    
    example_file = 'templates/dashboard_optimized_example.html'
    
    example_content = '''{% extends "base.html" %}
{% block content %}
<!-- 原有内容 -->
{% endblock %}

{% block scripts %}
<script>
// 等待依赖加载
function waitForDependencies(callback) {
  if (typeof Chart !== 'undefined' && typeof ChartOptimizer !== 'undefined') {
    callback();
  } else {
    setTimeout(() => waitForDependencies(callback), 100);
  }
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
  waitForDependencies(function() {
    console.log('✓ 依赖加载完成，开始渲染图表');
    
    // 示例：渲染流量图表
    renderTrafficChart();
    
    // 示例：渲染接通率图表（延迟渲染）
    setTimeout(() => renderConnectChart(), 200);
    
    // 示例：渲染RRC图表（延迟渲染）
    setTimeout(() => renderRRCChart(), 400);
  });
});

function renderTrafficChart() {
  const ctx = document.getElementById('trafficChart');
  if (!ctx) return;
  
  // 获取原始数据
  const rawData = {{ traffic | tojson }};
  
  // 降采样（如果数据量大）
  const optimizedData = ChartOptimizer.downsampleTimeSeries(rawData, 100);
  
  // 优化配置
  const config = ChartOptimizer.optimizeChartConfig({
    type: 'line',
    data: {
      labels: optimizedData.map(d => d.time),
      datasets: [{
        label: '流量',
        data: optimizedData.map(d => d.value),
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1
      }]
    },
    options: {
      animation: false,  // 禁用动画
      responsive: true,
      maintainAspectRatio: false
    }
  });
  
  // 创建图表
  new Chart(ctx.getContext('2d'), config);
  console.log('✓ 流量图表渲染完成');
}

function renderConnectChart() {
  // 类似的优化逻辑
  console.log('✓ 接通率图表渲染完成');
}

function renderRRCChart() {
  // 类似的优化逻辑
  console.log('✓ RRC图表渲染完成');
}
</script>
{% endblock %}
'''
    
    with open(example_file, 'w', encoding='utf-8') as f:
        f.write(example_content)
    
    logging.info(f"✓ 优化模板示例已创建: {example_file}")
    logging.info("  请参考此示例优化其他模板")
    return True

def download_bootstrap_icons():
    """下载 Bootstrap Icons"""
    logging.info("\n" + "=" * 60)
    logging.info("步骤 4: 下载 Bootstrap Icons（离线支持）")
    logging.info("=" * 60)
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, 'download_bootstrap_icons.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("✓ Bootstrap Icons 下载成功")
            return True
        else:
            logging.warning("⚠️ Bootstrap Icons 下载失败")
            logging.warning("  请手动运行: python download_bootstrap_icons.py")
            return False
    except Exception as e:
        logging.warning(f"⚠️ Bootstrap Icons 下载失败: {e}")
        logging.warning("  请手动运行: python download_bootstrap_icons.py")
        return False

def print_manual_steps():
    """打印需要手动完成的步骤"""
    logging.info("\n" + "=" * 60)
    logging.info("需要手动完成的步骤")
    logging.info("=" * 60)
    
    print("""
📋 手动步骤清单:

1. 在 services/metrics_service.py 中应用降采样
   在每个时间序列查询方法的返回前添加:
   
   result = self.downsample_data(result, 100)
   
   需要修改的方法:
   - traffic_series()
   - connectivity_series()
   - rrc_series()
   - cell_metrics()

2. 在所有模板中禁用图表动画
   查找所有 new Chart() 调用，确保配置中有:
   
   options: {
     animation: false
   }

3. 参考 templates/dashboard_optimized_example.html
   优化其他页面模板，使用:
   - ChartOptimizer.downsampleTimeSeries()
   - ChartOptimizer.optimizeChartConfig()
   - 分批渲染图表（使用 setTimeout）

4. 重启应用并测试
   python app.py

5. 清除浏览器缓存并测试性能
   运行: python analyze_performance.py logs/monitoring_app.log
    """)

def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║         前端性能快速修复脚本                              ║
║         Frontend Performance Quick Fix                   ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    logging.info("当前问题: 前端首屏时间 48-66秒")
    logging.info("优化目标: 降至 5-8秒")
    logging.info("")
    
    response = input("是否继续执行自动修复? (y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    success_count = 0
    total_steps = 4
    
    # 执行自动化步骤
    if add_chart_optimizer_to_base():
        success_count += 1
    
    if add_downsample_to_service():
        success_count += 1
    
    if create_optimized_dashboard_template():
        success_count += 1
    
    if download_bootstrap_icons():
        success_count += 1
    
    # 打印手动步骤
    print_manual_steps()
    
    # 总结
    logging.info("\n" + "=" * 60)
    logging.info("自动修复完成")
    logging.info("=" * 60)
    logging.info(f"完成 {success_count}/{total_steps} 个自动化步骤")
    
    if success_count == total_steps:
        logging.info("🎉 所有自动化步骤执行成功!")
    else:
        logging.warning(f"⚠️ 部分步骤失败 ({total_steps - success_count} 个)")
    
    logging.info("\n请完成上述手动步骤，然后重启应用测试效果。")
    
    return 0 if success_count == total_steps else 1

if __name__ == "__main__":
    sys.exit(main())
