/**
 * 图表性能优化工具
 * 提供数据降采样、懒加载等功能
 */

(function(window) {
  'use strict';

  const ChartOptimizer = {
    /**
     * 数据降采样 - 减少数据点数量
     * @param {Array} data - 原始数据数组
     * @param {Number} maxPoints - 最大数据点数量
     * @returns {Array} 降采样后的数据
     */
    downsampleData(data, maxPoints = 100) {
      if (!data || data.length <= maxPoints) {
        return data;
      }

      const step = Math.ceil(data.length / maxPoints);
      return data.filter((_, index) => index % step === 0);
    },

    /**
     * 时间序列数据降采样（保留首尾和关键点）
     * @param {Array} data - 原始数据数组 [{x, y}, ...]
     * @param {Number} maxPoints - 最大数据点数量
     * @returns {Array} 降采样后的数据
     */
    downsampleTimeSeries(data, maxPoints = 100) {
      if (!data || data.length <= maxPoints) {
        return data;
      }

      const result = [];
      const step = Math.floor(data.length / maxPoints);

      // 始终保留第一个点
      result.push(data[0]);

      // 采样中间点
      for (let i = step; i < data.length - step; i += step) {
        // 在每个区间内找最大值和最小值（保留峰值）
        let maxVal = data[i];
        let minVal = data[i];
        
        for (let j = i; j < i + step && j < data.length; j++) {
          if (data[j].y > maxVal.y) maxVal = data[j];
          if (data[j].y < minVal.y) minVal = data[j];
        }
        
        // 添加最大值和最小值
        if (maxVal !== minVal) {
          result.push(minVal);
          result.push(maxVal);
        } else {
          result.push(maxVal);
        }
      }

      // 始终保留最后一个点
      result.push(data[data.length - 1]);

      return result;
    },

    /**
     * 优化 Chart.js 配置
     * @param {Object} config - Chart.js 配置对象
     * @returns {Object} 优化后的配置
     */
    optimizeChartConfig(config) {
      // 默认优化选项
      const optimizations = {
        animation: {
          duration: 0  // 禁用动画以提升性能
        },
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false
        },
        plugins: {
          decimation: {
            enabled: true,
            algorithm: 'lttb',  // Largest-Triangle-Three-Buckets 算法
            samples: 100
          },
          legend: {
            display: true
          },
          tooltip: {
            enabled: true,
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          x: {
            ticks: {
              maxTicksLimit: 10  // 限制X轴标签数量
            }
          },
          y: {
            ticks: {
              maxTicksLimit: 8  // 限制Y轴标签数量
            }
          }
        }
      };

      // 深度合并配置
      return this.deepMerge(config, optimizations);
    },

    /**
     * 深度合并对象
     */
    deepMerge(target, source) {
      const output = Object.assign({}, target);
      if (this.isObject(target) && this.isObject(source)) {
        Object.keys(source).forEach(key => {
          if (this.isObject(source[key])) {
            if (!(key in target)) {
              Object.assign(output, { [key]: source[key] });
            } else {
              output[key] = this.deepMerge(target[key], source[key]);
            }
          } else {
            Object.assign(output, { [key]: source[key] });
          }
        });
      }
      return output;
    },

    isObject(item) {
      return item && typeof item === 'object' && !Array.isArray(item);
    },

    /**
     * 图表懒加载
     * 使用 Intersection Observer 实现图表懒加载
     * @param {String} selector - 图表容器选择器
     * @param {Function} renderCallback - 渲染回调函数
     */
    lazyLoadCharts(selector, renderCallback) {
      if (!('IntersectionObserver' in window)) {
        // 不支持 IntersectionObserver，直接渲染所有图表
        document.querySelectorAll(selector).forEach(el => {
          renderCallback(el);
        });
        return;
      }

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            renderCallback(entry.target);
            observer.unobserve(entry.target);
          }
        });
      }, {
        rootMargin: '50px'  // 提前50px开始加载
      });

      document.querySelectorAll(selector).forEach(el => {
        observer.observe(el);
      });
    },

    /**
     * 批量渲染图表（分批渲染，避免阻塞）
     * @param {Array} charts - 图表配置数组
     * @param {Number} batchSize - 每批渲染数量
     */
    batchRenderCharts(charts, batchSize = 2) {
      let index = 0;

      const renderBatch = () => {
        const batch = charts.slice(index, index + batchSize);
        
        batch.forEach(chartConfig => {
          try {
            new Chart(chartConfig.ctx, chartConfig.config);
          } catch (error) {
            console.error('图表渲染失败:', error);
          }
        });

        index += batchSize;

        if (index < charts.length) {
          // 使用 requestIdleCallback 或 setTimeout 延迟下一批
          if ('requestIdleCallback' in window) {
            requestIdleCallback(renderBatch);
          } else {
            setTimeout(renderBatch, 0);
          }
        }
      };

      renderBatch();
    },

    /**
     * 表格数据分页
     * @param {Array} data - 原始数据
     * @param {Number} page - 当前页码
     * @param {Number} pageSize - 每页大小
     * @returns {Object} 分页结果
     */
    paginateData(data, page = 1, pageSize = 20) {
      const total = data.length;
      const totalPages = Math.ceil(total / pageSize);
      const start = (page - 1) * pageSize;
      const end = start + pageSize;

      return {
        data: data.slice(start, end),
        page: page,
        pageSize: pageSize,
        total: total,
        totalPages: totalPages,
        hasNext: page < totalPages,
        hasPrev: page > 1
      };
    },

    /**
     * 防抖函数
     * @param {Function} func - 要防抖的函数
     * @param {Number} wait - 等待时间（毫秒）
     * @returns {Function} 防抖后的函数
     */
    debounce(func, wait = 300) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    /**
     * 节流函数
     * @param {Function} func - 要节流的函数
     * @param {Number} limit - 时间限制（毫秒）
     * @returns {Function} 节流后的函数
     */
    throttle(func, limit = 300) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    }
  };

  // 导出到全局
  window.ChartOptimizer = ChartOptimizer;

  console.log('✓ 图表优化工具已加载');

})(window);
