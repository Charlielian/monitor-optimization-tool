/**
 * 全局 AJAX 工具库
 * 提供统一的 AJAX 请求处理、Toast 提示、表单处理等功能
 */

(function(window) {
  'use strict';

  // Toast 提示管理器
  const ToastManager = {
    container: null,
    
    // 初始化 Toast 容器
    init() {
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.className = 'toast-container position-fixed top-0 end-0 p-3';
        this.container.style.zIndex = '9999';
        document.body.appendChild(this.container);
      }
    },
    
    // 显示 Toast
    show(message, type = 'info', duration = 3000) {
      this.init();
      
      const toastId = 'toast-' + Date.now();
      const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'danger': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
      }[type] || 'bg-info';
      
      const icon = {
        'success': 'check-circle',
        'error': 'x-circle',
        'danger': 'x-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
      }[type] || 'info-circle';
      
      const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
          <div class="d-flex">
            <div class="toast-body">
              <i class="bi bi-${icon} me-2"></i>
              ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        </div>
      `;
      
      this.container.insertAdjacentHTML('beforeend', toastHTML);
      
      const toastElement = document.getElementById(toastId);
      const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration
      });
      toast.show();
      
      toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
      });
    },
    
    success(message, duration) {
      this.show(message, 'success', duration);
    },
    
    error(message, duration) {
      this.show(message, 'error', duration);
    },
    
    warning(message, duration) {
      this.show(message, 'warning', duration);
    },
    
    info(message, duration) {
      this.show(message, 'info', duration);
    }
  };

  // AJAX 请求管理器
  const AjaxManager = {
    // 发送 GET 请求
    get(url, options = {}) {
      return this.request(url, { ...options, method: 'GET' });
    },
    
    // 发送 POST 请求
    post(url, data, options = {}) {
      return this.request(url, { 
        ...options, 
        method: 'POST',
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });
    },
    
    // 发送 PUT 请求
    put(url, data, options = {}) {
      return this.request(url, { 
        ...options, 
        method: 'PUT',
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });
    },
    
    // 发送 DELETE 请求
    delete(url, options = {}) {
      return this.request(url, { ...options, method: 'DELETE' });
    },
    
    // 通用请求方法
    request(url, options = {}) {
      const showLoading = options.showLoading !== false;
      const showToast = options.showToast !== false;
      
      if (showLoading) {
        LoadingManager.show();
      }
      
      return fetch(url, options)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
          return response.json();
        })
        .then(data => {
          if (showLoading) {
            LoadingManager.hide();
          }
          
          if (showToast && data.message) {
            if (data.success) {
              ToastManager.success(data.message);
            } else {
              ToastManager.error(data.message);
            }
          }
          
          return data;
        })
        .catch(error => {
          if (showLoading) {
            LoadingManager.hide();
          }
          
          if (showToast) {
            ToastManager.error(error.message || '网络错误，请重试');
          }
          
          throw error;
        });
    }
  };

  // 加载动画管理器
  const LoadingManager = {
    overlay: null,
    count: 0,
    
    show(message = '加载中...') {
      this.count++;
      
      if (!this.overlay) {
        this.overlay = document.createElement('div');
        this.overlay.className = 'loading-overlay';
        this.overlay.innerHTML = `
          <div class="loading-spinner">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <div class="loading-text mt-3">${message}</div>
          </div>
        `;
        
        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
          .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9998;
          }
          .loading-spinner {
            background: white;
            padding: 2rem;
            border-radius: 0.5rem;
            text-align: center;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
          }
          .loading-text {
            color: #333;
            font-weight: 500;
          }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(this.overlay);
      }
    },
    
    hide() {
      this.count = Math.max(0, this.count - 1);
      
      if (this.count === 0 && this.overlay) {
        this.overlay.remove();
        this.overlay = null;
      }
    }
  };

  // 表单处理器
  const FormHandler = {
    // 将表单转换为 AJAX 提交
    ajaxify(form, options = {}) {
      if (typeof form === 'string') {
        form = document.querySelector(form);
      }
      
      if (!form) return;
      
      form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = {};
        formData.forEach((value, key) => {
          data[key] = value;
        });
        
        const url = options.url || this.action || window.location.href;
        const method = options.method || this.method || 'POST';
        
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalHTML = submitBtn ? submitBtn.innerHTML : '';
        
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>处理中...';
        }
        
        AjaxManager.request(url, {
          method: method,
          body: JSON.stringify(data),
          headers: {
            'Content-Type': 'application/json'
          },
          showLoading: options.showLoading !== false,
          showToast: options.showToast !== false
        })
        .then(result => {
          if (options.onSuccess) {
            options.onSuccess(result, form);
          }
          
          if (options.resetForm !== false && result.success) {
            form.reset();
          }
        })
        .catch(error => {
          if (options.onError) {
            options.onError(error, form);
          }
        })
        .finally(() => {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHTML;
          }
        });
      });
    },
    
    // 批量处理表单
    ajaxifyAll(selector, options = {}) {
      document.querySelectorAll(selector).forEach(form => {
        this.ajaxify(form, options);
      });
    }
  };

  // 确认对话框
  const ConfirmDialog = {
    show(message, options = {}) {
      return new Promise((resolve) => {
        const result = confirm(message);
        resolve(result);
      });
    },
    
    // 带回调的确认
    ask(message, onConfirm, onCancel) {
      if (confirm(message)) {
        if (onConfirm) onConfirm();
      } else {
        if (onCancel) onCancel();
      }
    }
  };

  // 工具函数
  const Utils = {
    // 防抖
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
    
    // 节流
    throttle(func, limit = 300) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },
    
    // 格式化日期
    formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
      if (typeof date === 'string') {
        date = new Date(date);
      }
      
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      
      return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
    },
    
    // 转义 HTML
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  };

  // 导出到全局
  window.AjaxUtils = {
    toast: ToastManager,
    ajax: AjaxManager,
    loading: LoadingManager,
    form: FormHandler,
    confirm: ConfirmDialog,
    utils: Utils
  };

  // 简写别名
  window.toast = ToastManager;
  window.ajax = AjaxManager;

})(window);
