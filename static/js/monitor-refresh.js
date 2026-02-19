/**
 * 监控页面局部刷新功能
 */

// 图表实例存储
let chartInstances = {
  trendFlow: null,
  trendConnect: null,
  trendUtil: null
};

// 刷新状态
let refreshTimer = null;
let refreshCountdown = 0;

// 通用图表绘制函数
function drawChart(canvasId, data, yLabel, valueKey, maxY = null) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  
  if (typeof Chart === 'undefined') {
    console.error('Chart.js 未加载');
    return null;
  }
  
  if (!data || data.length === 0) {
    return null;
  }
  
  const labels = [...new Set(data.map(r => r.start_time))].sort();
  const scenarios = [...new Set(data.map(r => r.scenario))];
  const palette = ["#0d6efd","#dc3545","#198754","#6f42c1","#fd7e14","#20c997","#ffc107"];
  
  const datasets = scenarios.map((s, idx) => {
    const vals = labels.map(ts => {
      const row = data.find(r => r.scenario === s && r.start_time === ts);
      return row ? Number(row[valueKey] || 0) : 0;
    });
    return {
      label: s,
      data: vals,
      borderColor: palette[idx % palette.length],
      backgroundColor: palette[idx % palette.length] + "20",
      borderWidth: 2,
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
    };
  });
  
  // 计算数据范围以自适应Y轴
  const allValues = datasets.flatMap(ds => ds.data);
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  
  // 为接通率和利用率设置合理的Y轴范围
  let yMin, yMax;
  if (valueKey === 'connect_rate' || yLabel.includes('接通率') || yLabel.includes('利用率')) {
    // 接通率和利用率：根据实际数据动态调整Y轴范围
    // Y轴最大值 = 数据最大值 + 5%（但不超过100%）
    yMax = Math.min(100, Math.ceil(maxValue * 1.05));
    
    // 智能调整Y轴最小值，根据数据范围使用不同的调整单位
    if (maxValue > 95) {
      // 数据>95%时：以2%为单位调整
      yMin = Math.max(0, Math.floor(minValue / 2) * 2 - 2);
    } else if (maxValue > 80) {
      // 数据>80%时：以5%为单位调整
      yMin = Math.max(0, Math.floor(minValue / 5) * 5 - 5);
    } else {
      // 其他情况：以10%为单位调整
      yMin = Math.max(0, Math.floor(minValue / 10) * 10 - 10);
    }
  } else {
    // 其他指标从0开始
    yMin = 0;
    yMax = maxY;
  }
  
  // 销毁旧图表
  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }
  
  const chart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      animation: { duration: 500 },
      scales: {
        y: {
          min: yMin,
          max: yMax,
          title: { display: true, text: yLabel, font: { size: 13, weight: 'bold' } },
          grid: { color: 'rgba(0, 0, 0, 0.06)' }
        },
        x: {
          title: { display: true, text: "时间", font: { size: 13, weight: 'bold' } },
          grid: { display: false },
          ticks: { 
            maxRotation: 45,
            callback: function(value, index, ticks) {
              const label = this.getLabelForValue(value);
              // 确保时间格式为 YYYY-MM-DD HH:mm:ss
              if (label && label.length === 16) {
                return label + ':00';
              }
              return label;
            }
          }
        }
      },
      plugins: {
        legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 15 } },
        tooltip: { backgroundColor: 'rgba(0, 0, 0, 0.85)', padding: 12, cornerRadius: 8 }
      }
    }
  });
  
  chartInstances[canvasId] = chart;
  return chart;
}

// 流量单位自适应
function getTrafficLabel(data) {
  if (!data || data.length === 0) return "流量(GB)";
  const maxTraffic = Math.max(...data.map(r => Number(r.total_traffic || 0)), 0);
  return maxTraffic >= 1024 ? "流量(TB)" : "流量(GB)";
}

function getTrafficFactor(data) {
  if (!data || data.length === 0) return 1;
  const maxTraffic = Math.max(...data.map(r => Number(r.total_traffic || 0)), 0);
  return maxTraffic >= 1024 ? 1/1024 : 1;
}

// 绘制流量趋势图（自适应Y轴）
function drawFlowChart(t4g, t5g) {
  const trend4gFactor = getTrafficFactor(t4g);
  const trend5gFactor = getTrafficFactor(t5g);
  const trend4gAdjusted = (t4g || []).map(r => ({ ...r, total_traffic: (r.total_traffic || 0) * trend4gFactor, scenario: `${r.scenario} (4G)` }));
  const trend5gAdjusted = (t5g || []).map(r => ({ ...r, total_traffic: (r.total_traffic || 0) * trend5gFactor, scenario: `${r.scenario} (5G)` }));
  const trendFlowAll = [...trend4gAdjusted, ...trend5gAdjusted];
  const flowLabel = getTrafficLabel(t5g) === "流量(TB)" || getTrafficLabel(t4g) === "流量(TB)" ? "流量(TB)" : "流量(GB)";
  
  // 使用自适应Y轴绘制流量图表
  drawFlowChartAdaptive("trendFlow", trendFlowAll, flowLabel, "total_traffic");
}

// 流量图表专用绘制函数（自适应Y轴）
function drawFlowChartAdaptive(canvasId, data, yLabel, valueKey) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined' || !data || data.length === 0) return;
  
  const labels = [...new Set(data.map(r => r.start_time))].sort();
  const scenarios = [...new Set(data.map(r => r.scenario))];
  const palette = ["#0d6efd","#dc3545","#198754","#6f42c1","#fd7e14","#20c997","#ffc107"];
  
  const datasets = scenarios.map((s, idx) => {
    const vals = labels.map(ts => {
      const row = data.find(r => r.scenario === s && r.start_time === ts);
      return row ? Number(row[valueKey] || 0) : 0;
    });
    return {
      label: s,
      data: vals,
      borderColor: palette[idx % palette.length],
      backgroundColor: palette[idx % palette.length] + "20",
      borderWidth: 2,
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
    };
  });
  
  // 计算数据范围以自适应Y轴，突出流量波动
  const allValues = datasets.flatMap(ds => ds.data).filter(v => v > 0);
  if (allValues.length === 0) return;
  
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  const range = maxValue - minValue;
  
  // 流量图表自适应策略：
  // 如果波动范围小于最大值的30%，则不从0开始，以突出波动
  let yMin, yMax;
  if (range < maxValue * 0.3 && minValue > 0) {
    // 设置Y轴最小值为最小值的80%（留出20%空间）
    yMin = Math.max(0, minValue * 0.8);
    // Y轴最大值为最大值的110%（留出10%空间）
    yMax = maxValue * 1.1;
  } else {
    // 波动较大时，从0开始
    yMin = 0;
    yMax = maxValue * 1.1;
  }
  
  // 销毁旧图表
  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }
  
  chartInstances[canvasId] = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      animation: { duration: 500 },
      scales: {
        y: {
          min: yMin,
          max: yMax,
          title: { display: true, text: yLabel, font: { size: 13, weight: 'bold' } },
          grid: { color: 'rgba(0, 0, 0, 0.06)' },
          ticks: {
            callback: function(value) {
              // 格式化显示，保留2位小数
              return value.toFixed(2);
            }
          }
        },
        x: {
          title: { display: true, text: "时间", font: { size: 13, weight: 'bold' } },
          grid: { display: false },
          ticks: { 
            maxRotation: 45,
            callback: function(value, index, ticks) {
              const label = this.getLabelForValue(value);
              // 确保时间格式为 YYYY-MM-DD HH:mm:ss
              if (label && label.length === 16) {
                return label + ':00';
              }
              return label;
            }
          }
        }
      },
      plugins: {
        legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 15 } },
        tooltip: { 
          backgroundColor: 'rgba(0, 0, 0, 0.85)', 
          padding: 12, 
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              label += context.parsed.y.toFixed(2);
              return label;
            }
          }
        }
      }
    }
  });
}

// 绘制接通率趋势图
function drawConnectChart(c4g, c5g) {
  const connectAll = [
    ...(c4g || []).map(r => ({ ...r, scenario: `${r.scenario} (4G)` })),
    ...(c5g || []).map(r => ({ ...r, scenario: `${r.scenario} (5G)` })),
  ];
  drawChart("trendConnect", connectAll, "无线接通率(%)", "connect_rate", 100);
}

// 绘制利用率趋势图
function drawUtilChart(canvasId, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined' || !data || data.length === 0) return;
  
  const labels = [...new Set(data.map(r => r.start_time))].sort();
  const scenarios = [...new Set(data.map(r => `${r.scenario} (${r.network})`))];
  const palette = ["#0d6efd","#dc3545","#198754","#6f42c1","#fd7e14","#20c997","#ffc107"];
  const datasets = [];
  
  scenarios.forEach((s, idx) => {
    const ul = labels.map(ts => { const row = data.find(r => `${r.scenario} (${r.network})` === s && r.start_time === ts); return row ? Number(row.ul_prb || 0) : 0; });
    const dl = labels.map(ts => { const row = data.find(r => `${r.scenario} (${r.network})` === s && r.start_time === ts); return row ? Number(row.dl_prb || 0) : 0; });
    datasets.push({ label: `${s} 上行PRB`, data: ul, borderColor: palette[(idx*2) % palette.length], backgroundColor: palette[(idx*2) % palette.length] + "20", borderWidth: 2, tension: 0.3, pointRadius: 3 });
    datasets.push({ label: `${s} 下行PRB`, data: dl, borderColor: palette[(idx*2+1) % palette.length], backgroundColor: palette[(idx*2+1) % palette.length] + "20", borderWidth: 2, tension: 0.3, pointRadius: 3 });
  });
  
  // 计算数据范围以自适应Y轴，突出波动性
  const allValues = datasets.flatMap(ds => ds.data);
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  
  // 利用率：根据实际数据动态调整Y轴范围
  // Y轴最大值 = 数据最大值 + 5%（但不超过100%）
  const yMax = Math.min(100, Math.ceil(maxValue * 1.05));
  
  // 智能调整Y轴最小值，根据数据范围使用不同的调整单位
  let yMin;
  if (maxValue > 95) {
    // 数据>95%时：以2%为单位调整
    yMin = Math.max(0, Math.floor(minValue / 2) * 2 - 2);
  } else if (maxValue > 80) {
    // 数据>80%时：以5%为单位调整
    yMin = Math.max(0, Math.floor(minValue / 5) * 5 - 5);
  } else {
    // 其他情况：以10%为单位调整
    yMin = Math.max(0, Math.floor(minValue / 10) * 10 - 10);
  }
  
  if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
  chartInstances[canvasId] = new Chart(ctx, {
    type: "line", data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      animation: { duration: 500 },
      scales: {
        y: { min: yMin, max: yMax, title: { display: true, text: "PRB利用率(%)", font: { size: 13, weight: 'bold' } }, grid: { color: 'rgba(0, 0, 0, 0.06)' } },
        x: { 
          title: { display: true, text: "时间", font: { size: 13, weight: 'bold' } }, 
          grid: { display: false }, 
          ticks: { 
            maxRotation: 45,
            callback: function(value, index, ticks) {
              const label = this.getLabelForValue(value);
              // 确保时间格式为 YYYY-MM-DD HH:mm:ss
              if (label && label.length === 16) {
                return label + ':00';
              }
              return label;
            }
          } 
        }
      },
      plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 15 } }, tooltip: { backgroundColor: 'rgba(0, 0, 0, 0.85)', padding: 12, cornerRadius: 8 } }
    }
  });
}

// 更新场景指标汇总表格
function updateMetricsTable(metrics) {
  const tbody = document.querySelector('#scenarioMetricsSection tbody');
  if (!tbody) return;
  
  if (!metrics || metrics.length === 0) {
    tbody.innerHTML = `<tr><td colspan="13" class="text-center text-muted py-5"><i class="bi bi-inbox display-1 mb-3 d-block"></i><h5 class="text-muted">暂无数据</h5></td></tr>`;
    return;
  }
  
  let html = '';
  metrics.forEach(row => {
    const networkBadge = row.network === '4G' ? 'bg-primary' : 'bg-danger';
    const trafficValue = row['流量值'] || row['流量(GB)'] || 0;
    const trafficUnit = row['流量单位'] || 'GB';
    html += `<tr>
      <td class="text-center">${row.scenario}</td>
      <td class="text-center"><span class="badge ${networkBadge}">${row.network}</span></td>
      <td class="text-center"><small>${row.ts}</small></td>
      <td class="text-center"><span class="badge bg-info">${parseFloat(trafficValue).toFixed(2)} ${trafficUnit}</span></td>
      <td class="text-center">${parseFloat(row['上行PRB利用率(%)'] || 0).toFixed(2)}</td>
      <td class="text-center">${parseFloat(row['下行PRB利用率(%)'] || 0).toFixed(2)}</td>
      <td class="text-center">${parseFloat(row['无线接通率(%)'] || 0).toFixed(2)}</td>
      <td class="text-center">${row['最大用户数'] || 0}</td>
      <td class="text-center">${row['超阈值小区数'] > 0 ? `<span class="badge bg-warning text-dark">${row['超阈值小区数']}</span>` : '<span class="text-muted">0</span>'}</td>
      <td class="text-center">${(row['干扰小区数'] || 0) > 0 ? `<span class="badge bg-danger">${row['干扰小区数']}</span>` : '<span class="text-muted">0</span>'}</td>
      <td class="text-center">${(row['无流量小区数'] || 0) > 0 ? `<span class="badge bg-secondary">${row['无流量小区数']}</span>` : '<span class="text-muted">0</span>'}</td>
      <td class="text-center">${(row['无性能小区数'] || 0) > 0 ? `<span class="badge bg-dark">${row['无性能小区数']}</span>` : '<span class="text-muted">0</span>'}</td>
      <td class="text-center">${row['总小区数'] || 0}</td>
    </tr>`;
  });
  tbody.innerHTML = html;
}

// 更新小区详细指标表格
function updateCellTable(network, cellData) {
  const sectionId = network === '4G' ? 'cell4GSection' : 'cell5GSection';
  const tbody = document.querySelector(`#${sectionId} tbody`);
  if (!tbody || !cellData) return;
  
  const data = cellData.data || [];
  if (data.length === 0) { tbody.innerHTML = `<tr><td colspan="11" class="text-center text-muted py-4">暂无数据</td></tr>`; return; }
  
  const getPrbBadge = (val) => val >= 80 ? 'bg-danger' : val >= 60 ? 'bg-warning' : 'bg-success';
  const getPrbText = (val) => val >= 80 ? 'text-danger' : val >= 60 ? 'text-warning' : 'text-success';
  
  let html = '';
  data.forEach(cell => {
    const hasData = cell.has_data !== false;
    const rowClass = !hasData ? 'class="table-warning" style="opacity: 0.7;"' : '';
    html += `<tr ${rowClass}>
      <td class="text-center">${cell.scenario || ''}</td>
      <td class="text-center"><div class="text-truncate" style="max-width: 200px;">${cell.cellname || cell.cell_id || ''}${!hasData ? ' <span class="badge bg-warning text-dark ms-1">无数据</span>' : ''}</div></td>
      <td class="text-center"><code class="text-secondary">${cell.cgi || ''}</code></td>
      <td class="text-center"><small>${cell.start_time || '-'}</small></td>
      <td class="text-center">${hasData ? parseFloat(cell.interference || 0).toFixed(2) : '-'}</td>
      <td class="text-center">${hasData ? `<span class="badge bg-info">${parseFloat(cell.traffic_value || cell.traffic_gb || 0).toFixed(2)} ${cell.traffic_unit || 'GB'}</span>` : '-'}</td>
      <td class="text-center">${hasData ? `<span class="badge ${getPrbBadge(cell.ul_prb_util || 0)}">${parseFloat(cell.ul_prb_util || 0).toFixed(2)}%</span>` : '-'}</td>
      <td class="text-center">${hasData ? `<span class="badge ${getPrbBadge(cell.dl_prb_util || 0)}">${parseFloat(cell.dl_prb_util || 0).toFixed(2)}%</span>` : '-'}</td>
      <td class="text-center">${hasData ? `<strong class="${getPrbText(cell.max_prb_util || 0)}">${parseFloat(cell.max_prb_util || 0).toFixed(2)}%</strong>` : '-'}</td>
      <td class="text-center">${hasData ? parseFloat(cell.connect_rate || 0).toFixed(2) + '%' : '-'}</td>
      <td class="text-center">${hasData ? (cell.rrc_users || 0) : '-'}</td>
    </tr>`;
  });
  tbody.innerHTML = html;
}

// 执行局部刷新
async function refreshMonitorData(config) {
  if (!config.selectedScenarios || config.selectedScenarios.length === 0) return;
  
  const params = new URLSearchParams();
  config.selectedScenarios.forEach(id => params.append('scenario_id', id));
  params.append('thr4g', config.threshold4g);
  params.append('thr5g', config.threshold5g);
  params.append('page_4g', config.page4g);
  params.append('page_5g', config.page5g);
  
  try {
    const response = await fetch(`/api/monitor/refresh?${params.toString()}`);
    const result = await response.json();
    
    if (result.success && result.data) {
      const data = result.data;
      
      // 更新场景指标汇总
      updateMetricsTable(data.metrics);
      
      // 更新图表
      if (config.hasCharts) {
        drawFlowChart(data.trend_4g || [], data.trend_5g || []);
        drawConnectChart(data.connect_trend_4g || [], data.connect_trend_5g || []);
        drawUtilChart("trendUtil", [...(data.util_trend_4g || []).map(r => ({ ...r, network: "4G" })), ...(data.util_trend_5g || []).map(r => ({ ...r, network: "5G" }))]);
      }
      
      // 更新小区详细指标
      if (data.cell_metrics) {
        updateCellTable('4G', data.cell_metrics['4G']);
        updateCellTable('5G', data.cell_metrics['5G']);
      }
      
      console.log(`✅ 数据刷新成功 - ${result.timestamp}`);
    }
  } catch (error) {
    console.error('❌ 数据刷新失败:', error);
  }
}

// 更新倒计时显示
function updateCountdownDisplay() {
  const countdownEl = document.getElementById('refreshCountdown');
  const wrapperEl = document.getElementById('refreshCountdownWrapper');
  if (countdownEl) {
    countdownEl.textContent = refreshCountdown;
    console.log(`⏱️ 自动刷新倒计时: ${refreshCountdown}s`);
  }
  if (wrapperEl) {
    wrapperEl.style.display = '';
  }
}

// 启动自动刷新
function startAutoRefresh(config) {
  if (refreshTimer) clearInterval(refreshTimer);
  
  refreshCountdown = config.refreshInterval;
  console.log(`🔄 自动刷新已启动，间隔 ${config.refreshInterval} 秒`);
  
  // 显示倒计时容器
  const wrapperEl = document.getElementById('refreshCountdownWrapper');
  if (wrapperEl) {
    wrapperEl.style.display = '';
  }
  
  // 立即更新一次显示
  updateCountdownDisplay();
  
  refreshTimer = setInterval(() => {
    refreshCountdown--;
    updateCountdownDisplay();
    if (refreshCountdown <= 0) {
      console.log('🔄 执行自动刷新...');
      refreshMonitorData(config);
      refreshCountdown = config.refreshInterval;
    }
  }, 1000);
}

// 停止自动刷新
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
    // 隐藏倒计时显示
    const wrapperEl = document.getElementById('refreshCountdownWrapper');
    if (wrapperEl) {
      wrapperEl.style.display = 'none';
    }
    console.log('⏹️ 自动刷新已停止');
  }
}

// 初始化监控刷新
function initMonitorRefresh(config) {
  // 初始绘制图表
  if (config.hasCharts && config.initialData) {
    drawFlowChart(config.initialData.trend4g, config.initialData.trend5g);
    drawConnectChart(config.initialData.connectTrend4g, config.initialData.connectTrend5g);
    const utilAll = [
      ...(config.initialData.utilTrend4g || []).map(r => ({ ...r, network: "4G" })),
      ...(config.initialData.utilTrend5g || []).map(r => ({ ...r, network: "5G" })),
    ];
    drawUtilChart("trendUtil", utilAll);
  }
  
  // 启动自动刷新
  if (config.autoRefresh) {
    startAutoRefresh(config);
  }
}

// 导出函数供全局使用
window.MonitorRefresh = {
  init: initMonitorRefresh,
  refresh: refreshMonitorData,
  start: startAutoRefresh,
  stop: stopAutoRefresh,
  drawFlowChart,
  drawConnectChart,
  drawUtilChart
};
