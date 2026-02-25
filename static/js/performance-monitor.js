/**
 * 前端性能监控
 * 监控页面加载时间、资源加载时间等
 */

(function(window) {
  'use strict';

  const PerformanceMonitor = {
    // 页面加载性能
    logPagePerformance() {
      if (!window.performance || !window.performance.timing) {
        console.warn('浏览器不支持 Performance API');
        return;
      }

      window.addEventListener('load', () => {
        setTimeout(() => {
          const timing = performance.timing;
          const navigation = performance.navigation;

          // 计算各个阶段的耗时
          const metrics = {
            // DNS 查询耗时
            dns: timing.domainLookupEnd - timing.domainLookupStart,
            // TCP 连接耗时
            tcp: timing.connectEnd - timing.connectStart,
            // 请求耗时
            request: timing.responseStart - timing.requestStart,
            // 响应耗时
            response: timing.responseEnd - timing.responseStart,
            // DOM 解析耗时
            domParse: timing.domInteractive - timing.domLoading,
            // DOM 内容加载完成耗时
            domContentLoaded: timing.domContentLoadedEventEnd - timing.domContentLoadedEventStart,
            // 页面完全加载耗时
            pageLoad: timing.loadEventEnd - timing.loadEventStart,
            // 总耗时（从开始导航到页面完全加载）
            total: timing.loadEventEnd - timing.navigationStart,
            // 白屏时间（从开始导航到开始渲染）
            whiteScreen: timing.domLoading - timing.navigationStart,
            // 首屏时间（从开始导航到 DOM 可交互）
            firstScreen: timing.domInteractive - timing.navigationStart,
          };

          // 导航类型
          const navType = ['导航', '重新加载', '前进/后退', '预加载'][navigation.type] || '未知';

          // 输出性能数据
          console.group('📊 页面性能监控');
          console.log(`导航类型: ${navType}`);
          console.log(`DNS 查询: ${metrics.dns}ms`);
          console.log(`TCP 连接: ${metrics.tcp}ms`);
          console.log(`请求耗时: ${metrics.request}ms`);
          console.log(`响应耗时: ${metrics.response}ms`);
          console.log(`DOM 解析: ${metrics.domParse}ms`);
          console.log(`DOM 内容加载: ${metrics.domContentLoaded}ms`);
          console.log(`页面加载: ${metrics.pageLoad}ms`);
          console.log(`⏱️ 白屏时间: ${metrics.whiteScreen}ms`);
          console.log(`⏱️ 首屏时间: ${metrics.firstScreen}ms`);
          console.log(`⏱️ 总耗时: ${metrics.total}ms`);
          console.groupEnd();

          // 性能警告
          if (metrics.total > 3000) {
            console.warn(`⚠️ 页面加载较慢 (${metrics.total}ms)，建议优化`);
          }
          if (metrics.whiteScreen > 1000) {
            console.warn(`⚠️ 白屏时间过长 (${metrics.whiteScreen}ms)，用户体验较差`);
          }

          // 发送性能数据到服务器（可选）
          if (window.AjaxUtils && window.AjaxUtils.ajax) {
            window.AjaxUtils.ajax.post('/api/performance/log', {
              metrics: metrics,
              navType: navType,
              url: window.location.href,
              userAgent: navigator.userAgent
            }, { showLoading: false, showToast: false }).catch(() => {
              // 忽略错误，不影响用户体验
            });
          }
        }, 0);
      });
    },

    // 资源加载性能
    logResourcePerformance() {
      if (!window.performance || !window.performance.getEntriesByType) {
        return;
      }

      window.addEventListener('load', () => {
        setTimeout(() => {
          const resources = performance.getEntriesByType('resource');
          
          // 按类型分组
          const resourcesByType = {};
          let totalSize = 0;
          let totalDuration = 0;

          resources.forEach(resource => {
            const type = this.getResourceType(resource.name);
            if (!resourcesByType[type]) {
              resourcesByType[type] = {
                count: 0,
                duration: 0,
                size: 0
              };
            }

            resourcesByType[type].count++;
            resourcesByType[type].duration += resource.duration;
            
            // 如果有 transferSize，累加大小
            if (resource.transferSize) {
              resourcesByType[type].size += resource.transferSize;
              totalSize += resource.transferSize;
            }
            
            totalDuration += resource.duration;
          });

          console.group('📦 资源加载性能');
          console.log(`总资源数: ${resources.length}`);
          console.log(`总大小: ${(totalSize / 1024).toFixed(2)} KB`);
          console.log(`总耗时: ${totalDuration.toFixed(2)}ms`);
          console.table(resourcesByType);
          console.groupEnd();

          // 找出加载最慢的资源
          const slowResources = resources
            .filter(r => r.duration > 500)
            .sort((a, b) => b.duration - a.duration)
            .slice(0, 5);

          if (slowResources.length > 0) {
            console.group('🐌 加载最慢的资源 (>500ms)');
            slowResources.forEach(r => {
              console.log(`${r.name}: ${r.duration.toFixed(2)}ms`);
            });
            console.groupEnd();
          }
        }, 0);
      });
    },

    // 获取资源类型
    getResourceType(url) {
      if (url.includes('.js')) return 'JavaScript';
      if (url.includes('.css')) return 'CSS';
      if (url.match(/\.(png|jpg|jpeg|gif|svg|webp|ico)/)) return 'Image';
      if (url.match(/\.(woff|woff2|ttf|eot)/)) return 'Font';
      if (url.includes('/api/')) return 'API';
      return 'Other';
    },

    // 监控 AJAX 请求
    monitorAjax() {
      const originalFetch = window.fetch;
      
      window.fetch = function(...args) {
        const startTime = performance.now();
        const url = args[0];
        
        return originalFetch.apply(this, args).then(response => {
          const duration = performance.now() - startTime;
          
          if (duration > 1000) {
            console.warn(`⚠️ AJAX 请求较慢: ${url} (${duration.toFixed(2)}ms)`);
          } else {
            console.log(`✓ AJAX 请求: ${url} (${duration.toFixed(2)}ms)`);
          }
          
          return response;
        });
      };
    },

    // 初始化所有监控
    init() {
      this.logPagePerformance();
      this.logResourcePerformance();
      this.monitorAjax();
      
      console.log('✓ 性能监控已启动');
    }
  };

  // 自动初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      PerformanceMonitor.init();
    });
  } else {
    PerformanceMonitor.init();
  }

  // 导出到全局
  window.PerformanceMonitor = PerformanceMonitor;

})(window);
