"""
Main Business Routes Blueprint

This module contains the main business routes:
- dashboard: 全网监控首页
- cell: 指标查询
- monitor: 保障监控
- scenarios: 场景管理

Requirements: 8.3
"""

import logging
import time
from datetime import datetime
from typing import List

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    jsonify,
)

from auth import create_page_decorator, login_required, api_login_required
from services.cache import cache_5m


# Create the main blueprint with no URL prefix to maintain existing URL patterns
main_bp = Blueprint('main', __name__)


def get_services():
    """
    Get service instances from app config.
    
    Returns:
        tuple: (service, scenario_service, cfg, auth_enabled)
    """
    service = current_app.config.get('service')
    scenario_service = current_app.config.get('scenario_service')
    cfg = current_app.config.get('app_config')
    auth_enabled = current_app.config.get('auth_enabled', True)
    return service, scenario_service, cfg, auth_enabled


def _paginate(data: List[dict], page: int, page_size: int = 20) -> dict:
    """
    Paginate a list of data.
    
    Args:
        data: List of items to paginate
        page: Current page number (1-indexed)
        page_size: Number of items per page
    
    Returns:
        Dictionary with paginated data and metadata
    """
    total = len(data)
    pages = (total + page_size - 1) // page_size if total else 0
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return {
        "data": data[start_idx:end_idx],
        "page": page,
        "pages": pages,
        "total": total,
    }


@main_bp.route("/")
@login_required
def dashboard():
    """全网监控首页：只做全网流量/接通率/Top小区，不含指标查询。"""
    from config import Config
    from constants import (
        DEFAULT_PAGE_SIZE,
        TOP_CELLS_DEFAULT_LIMIT,
        DEFAULT_AUTO_REFRESH_INTERVAL,
    )
    from utils.validators import validate_time_range, validate_granularity
    
    route_start = time.time()
    
    # Get services from app config
    service = current_app.config.get('service')
    scenario_service = current_app.config.get('scenario_service')
    
    # Check if services are available
    if not service or not scenario_service:
        flash("数据库服务未连接，请检查配置或联系管理员", "danger")
        return render_template("error.html", message="数据库服务未连接")
    
    # Load config
    cfg = Config()
    
    # Parameter validation
    param_start = time.time()
    range_key = validate_time_range(request.args.get("range", ""))
    networks: List[str] = request.args.getlist("networks") or cfg.ui_config["default_networks"]
    auto = request.args.get("auto", "0") == "1"
    auto_interval = int(request.args.get("auto_interval", DEFAULT_AUTO_REFRESH_INTERVAL))
    granularity = validate_granularity(request.args.get("granularity", ""))
    logging.debug(f"  ├─ 参数解析: {(time.time() - param_start) * 1000:.2f}ms")
    
    # Process date parameter (for daily traffic and voice)
    date_str = request.args.get("date", "")
    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            logging.warning(f"解析日期参数失败: {date_str}, 错误: {e}")

    # Get latest time
    latest_start = time.time()
    latest = scenario_service.latest_time()
    latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
    latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
    logging.debug(f"  ├─ 获取最新时间: {(time.time() - latest_start) * 1000:.2f}ms")

    # Parse time range
    range_start = time.time()
    start, end = service.resolve_range(range_key, reference_time=latest_ts)
    logging.debug(f"  ├─ 解析时间范围: {(time.time() - range_start) * 1000:.2f}ms")

    # Create stable cache key (using sorted string)
    networks_key = ','.join(sorted(networks))

    # Query traffic data
    traffic_start = time.time()
    traffic = cache_5m.get(
        f"traffic:{range_key}:{networks_key}:{granularity}:{end}",
        lambda: service.traffic_series(networks, start, end, granularity),
    )
    logging.debug(f"  ├─ 查询流量数据: {(time.time() - traffic_start) * 1000:.2f}ms")

    # Query connectivity data
    connect_start = time.time()
    connect_series = cache_5m.get(
        f"connect:{range_key}:{networks_key}:{granularity}:{end}",
        lambda: service.connectivity_series(networks, start, end, granularity),
    )
    logging.debug(f"  ├─ 查询接通率数据: {(time.time() - connect_start) * 1000:.2f}ms")
    
    # Query RRC data
    rrc_start = time.time()
    rrc_series = cache_5m.get(
        f"rrc:{range_key}:{networks_key}:{granularity}:{end}",
        lambda: service.rrc_series(networks, start, end, granularity),
    )
    logging.debug(f"  ├─ 查询RRC数据: {(time.time() - rrc_start) * 1000:.2f}ms")
    
    # Query voice data
    voice_start = time.time()
    voice_series = cache_5m.get(
        f"voice:{range_key}:{networks_key}:{granularity}:{end}",
        lambda: service.voice_series(networks, start, end, granularity),
    )
    logging.debug(f"  ├─ 查询话务量数据: {(time.time() - voice_start) * 1000:.2f}ms")
    
    # Top utilization (by latest period)
    top_start = time.time()
    top4_raw = service.top_utilization("4G", limit=TOP_CELLS_DEFAULT_LIMIT, granularity=granularity)
    top5_raw = service.top_utilization("5G", limit=TOP_CELLS_DEFAULT_LIMIT, granularity=granularity)
    logging.debug(f"  ├─ 查询Top利用率: {(time.time() - top_start) * 1000:.2f}ms")
    
    page4 = int(request.args.get("page4", 1))
    page5 = int(request.args.get("page5", 1))

    top4 = _paginate(top4_raw, page4, DEFAULT_PAGE_SIZE)
    top5 = _paginate(top5_raw, page5, DEFAULT_PAGE_SIZE)
    
    # Query daily traffic and voice
    daily_start = time.time()
    daily_stats = service.daily_traffic_and_voice(target_date)
    daily_stats_by_region = service.daily_traffic_and_voice_by_region(target_date)
    logging.debug(f"  ├─ 查询日统计数据: {(time.time() - daily_start) * 1000:.2f}ms")
    
    logging.info(f"  └─ dashboard 数据查询总耗时: {(time.time() - route_start) * 1000:.2f}ms")

    return render_template(
        "dashboard.html",
        range_key=range_key,
        networks=networks,
        traffic=traffic,
        top4=top4,
        top5=top5,
        page4=page4,
        page5=page5,
        connect_series=connect_series,
        rrc_series=rrc_series,
        voice_series=voice_series,
        end_time=end,
        auto=auto,
        auto_interval=auto_interval,
        latest_ts=latest,
        granularity=granularity,
        daily_stats=daily_stats,
        daily_stats_by_region=daily_stats_by_region,
        selected_date=date_str or daily_stats["date"],
    )


@main_bp.route("/cell")
@login_required
def cell():
    """指标查询单独页面。"""
    from constants import MAX_CELL_QUERY_LIMIT
    from utils.validators import validate_and_parse_cgis, validate_granularity, validate_network_type
    from utils.time_parser import parse_time_range, format_datetime_for_input
    
    # Get services from app config
    service = current_app.config.get('service')
    scenario_service = current_app.config.get('scenario_service')
    
    # Check if services are available
    if not service or not scenario_service:
        flash("数据库服务未连接，请检查配置或联系管理员", "danger")
        return render_template("error.html", message="数据库服务未连接")
    
    # Parameter acquisition and validation
    cell_cgi = request.args.get("cell_cgi", "").strip()
    cell_network = request.args.get("cell_network", "").strip()  # 支持空值表示混查
    granularity = validate_granularity(request.args.get("granularity", ""))
    query_type = request.args.get("query_type", "cell").strip()
    scenario_ids = request.args.getlist("scenario_ids")
    
    # 自动刷新参数
    auto = request.args.get("auto", "0") == "1"
    auto_interval = int(request.args.get("auto_interval", 60))
    if auto_interval < 30:
        auto_interval = 30
    
    # 获取场景列表
    scenarios = scenario_service.list_scenarios()
    selected_scenario_ids = []
    for sid in scenario_ids:
        if sid and sid.isdigit():
            selected_scenario_ids.append(int(sid))
    
    # 从场景中获取小区列表（如果选择了场景）
    scenario_cells = []
    all_scenario_cgis = []
    for scenario_id in selected_scenario_ids:
        scenario_cells.extend(scenario_service.list_cells(scenario_id))
    # 从场景小区中提取CGI
    all_scenario_cgis = [cell.get('cgi') or cell.get('cell_id') for cell in scenario_cells if cell.get('cgi') or cell.get('cell_id')]
    if all_scenario_cgis:
        cell_cgi = ','.join(all_scenario_cgis)
    
    # CGI validation
    cgi_list, warning = validate_and_parse_cgis(cell_cgi, MAX_CELL_QUERY_LIMIT)
    if warning and not selected_scenario_ids:
        flash(warning, "warning")
    
    # Time parsing
    latest = scenario_service.latest_time()
    latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
    latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
    
    # 根据粒度设置默认时间范围
    if granularity == "1d":
        default_hours = 168  # 天级默认7天
        max_days = 90  # 天级最多90天
    else:
        default_hours = 6  # 小时级默认6小时
        max_days = 30  # 小时级最多30天
    
    start, end = parse_time_range(
        request.args.get("start_time", ""),
        request.args.get("end_time", ""),
        latest_ts=latest_ts,
        default_hours=default_hours,
        max_days=max_days
    )
    
    # Query data
    cell_data = []
    auto_detected_network = None
    
    if cgi_list:
        # 如果是汇总查询
        if query_type == "summary":
            # 如果未指定制式，自动识别（混查模式）
            if not cell_network or cell_network == "混查":
                # 自动识别CGI并分别汇总
                cgi_4g = []
                cgi_5g = []
                for cgi in cgi_list:
                    if not cgi:
                        continue
                    parts = cgi.split('-')
                    if len(parts) >= 4:
                        enb_gnb = parts[2]
                        if len(enb_gnb) == 6:
                            cgi_4g.append(cgi)
                        elif len(enb_gnb) == 8:
                            cgi_5g.append(cgi)
                
                # 分别汇总4G和5G数据
                summary_4g = []
                summary_5g = []
                
                if cgi_4g:
                    summary_4g = service.cell_timeseries_summary(cgi_4g, "4G", start, end, granularity)
                if cgi_5g:
                    summary_5g = service.cell_timeseries_summary(cgi_5g, "5G", start, end, granularity)
                
                # 合并结果
                cell_data = summary_4g + summary_5g
                # 按时间排序
                cell_data.sort(key=lambda x: x.get('start_time', ''))
                
                if not cell_data:
                    flash("未查询到任何小区的指标数据，请确认CGI格式是否正确。", "warning")
            else:
                # 指定制式汇总查询
                cell_network = validate_network_type(cell_network)
                cell_data = service.cell_timeseries_summary(
                    cgi_list, cell_network, start, end, granularity
                )
                
                if not cell_data:
                    flash("未查询到该小区的指标数据，请确认CGI与制式是否正确。", "warning")
        else:
            # 小区查询（原逻辑）
            # 如果未指定制式，自动识别（混查模式）
            if not cell_network or cell_network == "混查":
                # 自动识别CGI并分别查询
                cell_data, auto_detected_network = service.cell_timeseries_mixed(
                    cgi_list, start, end, granularity
                )
                if not cell_data:
                    flash("未查询到任何小区的指标数据，请确认CGI格式是否正确。", "warning")
            else:
                # 指定制式查询
                cell_network = validate_network_type(cell_network)
                cell_data = service.cell_timeseries_bulk(
                    cgi_list, cell_network, start, end, granularity
                )
                # Fill in CGI/cell ID info for each record
                for row in cell_data:
                    if 'cgi' not in row or not row.get('cgi'):
                        row['cgi'] = row.get('cell_id')
                    if 'cell_id' not in row or not row.get('cell_id'):
                        row['cell_id'] = row.get('cgi')
                    row['network_type'] = cell_network
                
                if not cell_data:
                    flash("未查询到该小区的指标数据，请确认CGI与制式是否正确。", "warning")

    return render_template(
        "cell.html",
        cell_cgi=cell_cgi,
        cell_network=cell_network or "混查",
        start_time=format_datetime_for_input(start),
        end_time=format_datetime_for_input(end),
        cell_data=cell_data,
        granularity=granularity,
        auto_detected_network=auto_detected_network,
        auto=auto,
        auto_interval=auto_interval,
        query_type=query_type,
        scenarios=scenarios,
        selected_scenario_ids=selected_scenario_ids
    )


@main_bp.route("/monitor", methods=["GET", "POST"])
@login_required
def monitor():
    """保障监控页面"""
    from constants import (
        DEFAULT_THRESHOLD_4G,
        DEFAULT_THRESHOLD_5G,
        DEFAULT_AUTO_REFRESH_INTERVAL,
        DEFAULT_PAGE_SIZE,
    )
    from utils.time_parser import parse_time_range
    
    # Get services from app config
    scenario_service = current_app.config.get('scenario_service')
    
    # Check if services are available
    if not scenario_service:
        flash("数据库服务未连接，请检查配置或联系管理员", "danger")
        return render_template("error.html", message="数据库服务未连接")
    
    scenarios = scenario_service.list_scenarios()
    selected = request.values.getlist("scenario_id", type=int)
    threshold_4g = float(request.values.get("thr4g", DEFAULT_THRESHOLD_4G))
    threshold_5g = float(request.values.get("thr5g", DEFAULT_THRESHOLD_5G))
    auto = request.values.get("auto", "0") == "1"
    auto_interval = int(request.values.get("auto_interval", DEFAULT_AUTO_REFRESH_INTERVAL))
    
    # Time parsing (using unified utility function)
    latest = scenario_service.latest_time()
    latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
    latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
    
    start, end = parse_time_range(
        request.values.get("start_time", ""),
        request.values.get("end_time", ""),
        latest_ts=latest_ts,
        default_hours=6,
        max_days=30
    )
    
    metrics = scenario_service.scenario_metrics(selected, threshold_4g, threshold_5g)
    trend_4g = scenario_service.traffic_trend(selected, start, end, "4G")
    trend_5g = scenario_service.traffic_trend(selected, start, end, "5G")
    connect_trend_4g = scenario_service.connect_rate_trend(selected, start, end, "4G")
    connect_trend_5g = scenario_service.connect_rate_trend(selected, start, end, "5G")
    util_trend_4g = scenario_service.util_trend(selected, start, end, "4G")
    util_trend_5g = scenario_service.util_trend(selected, start, end, "5G")
    util_snapshot = scenario_service.util_snapshot(selected)
    page_4g = int(request.args.get("page_4g", 1))
    page_5g = int(request.args.get("page_5g", 1))
    filter_text = request.args.get("filter", "")
    cell_metrics = scenario_service.scenario_cell_metrics(
        selected, page_4g=page_4g, page_5g=page_5g, page_size=DEFAULT_PAGE_SIZE, filter_text=filter_text
    )
    # 获取无性能+无流量小区列表
    no_data_cells = scenario_service.get_no_data_cells(selected)

    return render_template(
        "monitor.html",
        scenarios=scenarios,
        selected=selected,
        threshold_4g=threshold_4g,
        threshold_5g=threshold_5g,
        metrics=metrics,
        trend_4g=trend_4g,
        trend_5g=trend_5g,
        connect_trend_4g=connect_trend_4g,
        connect_trend_5g=connect_trend_5g,
        util_trend_4g=util_trend_4g,
        util_trend_5g=util_trend_5g,
        util_snapshot=util_snapshot,
        cell_metrics=cell_metrics,
        no_data_cells=no_data_cells,
        page_4g=page_4g,
        page_5g=page_5g,
        filter_text=filter_text,
        auto=auto,
        auto_interval=auto_interval,
        monitoring_active=bool(selected),
        start_time=request.values.get("start_time", ""),
        end_time=request.values.get("end_time", ""),
    )


@main_bp.route("/api/monitor/refresh", methods=["GET"])
@api_login_required
def api_monitor_refresh():
    """API: 监控数据局部刷新（返回JSON）"""
    from constants import (
        DEFAULT_THRESHOLD_4G,
        DEFAULT_THRESHOLD_5G,
        DEFAULT_PAGE_SIZE,
    )
    from utils.time_parser import parse_time_range
    
    scenario_service = current_app.config.get('scenario_service')
    
    if not scenario_service:
        return jsonify({"error": "数据库服务未连接"}), 500
    
    selected = request.args.getlist("scenario_id", type=int)
    threshold_4g = float(request.args.get("thr4g", DEFAULT_THRESHOLD_4G))
    threshold_5g = float(request.args.get("thr5g", DEFAULT_THRESHOLD_5G))
    page_4g = int(request.args.get("page_4g", 1))
    page_5g = int(request.args.get("page_5g", 1))
    filter_text = request.args.get("filter", "")
    
    # Time parsing
    latest = scenario_service.latest_time()
    latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
    latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
    
    start, end = parse_time_range(
        request.args.get("start_time", ""),
        request.args.get("end_time", ""),
        latest_ts=latest_ts,
        default_hours=6,
        max_days=30
    )
    
    # 获取所有数据
    metrics = scenario_service.scenario_metrics(selected, threshold_4g, threshold_5g)
    trend_4g = scenario_service.traffic_trend(selected, start, end, "4G")
    trend_5g = scenario_service.traffic_trend(selected, start, end, "5G")
    connect_trend_4g = scenario_service.connect_rate_trend(selected, start, end, "4G")
    connect_trend_5g = scenario_service.connect_rate_trend(selected, start, end, "5G")
    util_trend_4g = scenario_service.util_trend(selected, start, end, "4G")
    util_trend_5g = scenario_service.util_trend(selected, start, end, "5G")
    cell_metrics = scenario_service.scenario_cell_metrics(
        selected, page_4g=page_4g, page_5g=page_5g, page_size=DEFAULT_PAGE_SIZE, filter_text=filter_text
    )
    # 获取无性能+无流量小区列表
    no_data_cells = scenario_service.get_no_data_cells(selected)
    
    # 格式化时间戳为字符串
    def format_ts(ts):
        if ts is None:
            return "暂无数据"
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)
    
    # 格式化metrics中的时间
    for m in metrics:
        m["ts"] = format_ts(m.get("ts"))
    
    # 格式化cell_metrics中的时间
    for network in ["4G", "5G"]:
        for cell in cell_metrics.get(network, {}).get("data", []):
            cell["start_time"] = format_ts(cell.get("start_time"))
    
    # 格式化no_data_cells中的时间
    for cell in no_data_cells:
        cell["start_time"] = format_ts(cell.get("start_time"))
    
    return jsonify({
        "success": True,
        "data": {
            "metrics": metrics,
            "trend_4g": trend_4g,
            "trend_5g": trend_5g,
            "connect_trend_4g": connect_trend_4g,
            "connect_trend_5g": connect_trend_5g,
            "util_trend_4g": util_trend_4g,
            "util_trend_5g": util_trend_5g,
            "cell_metrics": cell_metrics,
            "no_data_cells": no_data_cells,
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@main_bp.route("/api/cell/query", methods=["GET"])
@api_login_required
def api_cell_query():
    """API: 指标查询（返回HTML片段用于局部更新）"""
    from constants import MAX_CELL_QUERY_LIMIT
    from utils.validators import validate_and_parse_cgis, validate_granularity, validate_network_type
    from utils.time_parser import parse_time_range
    
    service = current_app.config.get('service')
    scenario_service = current_app.config.get('scenario_service')
    
    if not service or not scenario_service:
        return jsonify({"success": False, "error": "数据库服务未连接"}), 500
    
    # 获取参数
    cell_cgi = request.args.get("cell_cgi", "").strip()
    cell_network = request.args.get("cell_network", "").strip()
    granularity = validate_granularity(request.args.get("granularity", ""))
    query_type = request.args.get("query_type", "cell").strip()
    query_method = request.args.get("query_method", "cgi").strip()
    scenario_ids = request.args.getlist("scenario_ids")
    
    logging.info(f"🔍 小区查询API - CGI: {cell_cgi[:50] if len(cell_cgi) > 50 else cell_cgi}, 制式: {cell_network}, 粒度: {granularity}, 查询类型: {query_type}, 查询方式: {query_method}, 场景数: {len(scenario_ids)}")
    
    # 从场景中获取小区列表（如果选择了场景）
    selected_scenario_ids = []
    all_scenario_cells = []
    for sid in scenario_ids:
        if sid and sid.isdigit():
            selected_scenario_ids.append(int(sid))
    
    # 按网络类型分组的小区CGI
    cgi_4g = []
    cgi_5g = []
    
    if selected_scenario_ids:
        for scenario_id in selected_scenario_ids:
            scenario_cells = scenario_service.list_cells(scenario_id)
            all_scenario_cells.extend(scenario_cells)
        
        # 从场景小区中提取CGI，按网络类型分组
        all_scenario_cgis = []
        for cell in all_scenario_cells:
            cgi = cell.get('cgi') or cell.get('cell_id')
            if not cgi:
                continue
            
            all_scenario_cgis.append(cgi)
            # 确保即使network_type字段为空，也能正确处理小区数据
            network_type = cell.get('network_type', '4G')
            # 尝试从CGI格式推断网络类型
            if network_type not in ['4G', '5G']:
                # CGI格式: 460-00-enb-lcrid 或 460-00-gnb-lcrid
                parts = cgi.split('-')
                if len(parts) >= 4:
                    enb_gnb = parts[2]
                    if len(enb_gnb) == 6:
                        network_type = '4G'
                    elif len(enb_gnb) == 8:
                        network_type = '5G'
                else:
                    # 默认按4G处理
                    network_type = '4G'
            
            if network_type == '4G':
                cgi_4g.append(cgi)
            elif network_type == '5G':
                cgi_5g.append(cgi)
        
        if all_scenario_cgis:
            cell_cgi = ','.join(all_scenario_cgis)
    
    # CGI validation
    cgi_list, warning = validate_and_parse_cgis(cell_cgi, MAX_CELL_QUERY_LIMIT)
    
    if not cgi_list and not selected_scenario_ids:
        return jsonify({"success": False, "error": "请输入有效的小区CGI"}), 400
    
    # Time parsing
    latest = scenario_service.latest_time()
    latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
    latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
    
    # 根据粒度设置默认时间范围
    if granularity == "1d":
        default_hours = 168
        max_days = 90
    else:
        default_hours = 6
        max_days = 30
    
    start, end = parse_time_range(
        request.args.get("start_time", ""),
        request.args.get("end_time", ""),
        latest_ts=latest_ts,
        default_hours=default_hours,
        max_days=max_days
    )
    
    # Query data
    cell_data = []
    auto_detected_network = None
    
    # 如果是汇总查询
    if query_type == "summary":
        # 如果未指定制式，自动识别（混查模式）
        if not cell_network or cell_network == "混查":
            # 如果从场景获取了按网络类型分组的CGI，使用分组数据
            if selected_scenario_ids:
                # 分别按场景汇总4G和5G数据
                all_summary_data = []
                
                # 按场景分组处理
                for scenario_id in selected_scenario_ids:
                    scenario_cells = scenario_service.list_cells(scenario_id)
                    scenario_name = scenario_service.get_scenario_name(scenario_id)
                    
                    # 按网络类型分组
                    scenario_cgi_4g = []
                    scenario_cgi_5g = []
                    for cell in scenario_cells:
                        cgi = cell.get('cgi') or cell.get('cell_id')
                        if not cgi:
                            continue
                        
                        # 确保即使network_type字段为空，也能正确处理小区数据
                        network_type = cell.get('network_type', '4G')
                        # 尝试从CGI格式推断网络类型
                        if network_type not in ['4G', '5G']:
                            # CGI格式: 460-00-enb-lcrid 或 460-00-gnb-lcrid
                            parts = cgi.split('-')
                            if len(parts) >= 4:
                                enb_gnb = parts[2]
                                if len(enb_gnb) == 6:
                                    network_type = '4G'
                                elif len(enb_gnb) == 8:
                                    network_type = '5G'
                            else:
                                # 默认按4G处理
                                network_type = '4G'
                        
                        if network_type == '4G':
                            scenario_cgi_4g.append(cgi)
                        elif network_type == '5G':
                            scenario_cgi_5g.append(cgi)
                    
                    # 汇总4G数据
                    if scenario_cgi_4g:
                        summary_4g = service.cell_timeseries_summary(scenario_cgi_4g, "4G", start, end, granularity)
                        # 添加场景信息
                        for row in summary_4g:
                            row['scenario'] = scenario_name
                            all_summary_data.append(row)
                    
                    # 汇总5G数据
                    if scenario_cgi_5g:
                        summary_5g = service.cell_timeseries_summary(scenario_cgi_5g, "5G", start, end, granularity)
                        # 添加场景信息
                        for row in summary_5g:
                            row['scenario'] = scenario_name
                            all_summary_data.append(row)
                
                # 按时间和场景排序
                all_summary_data.sort(key=lambda x: (x.get('start_time', ''), x.get('scenario', '')))
                cell_data = all_summary_data
            else:
                # 否则按CGI格式自动识别
                cgi_4g = []
                cgi_5g = []
                for cgi in cgi_list:
                    if not cgi:
                        continue
                    parts = cgi.split('-')
                    if len(parts) >= 4:
                        enb_gnb = parts[2]
                        if len(enb_gnb) == 6:
                            cgi_4g.append(cgi)
                        elif len(enb_gnb) == 8:
                            cgi_5g.append(cgi)
                
                # 分别汇总4G和5G数据
                summary_4g = []
                summary_5g = []
                
                if cgi_4g:
                    summary_4g = service.cell_timeseries_summary(cgi_4g, "4G", start, end, granularity)
                if cgi_5g:
                    summary_5g = service.cell_timeseries_summary(cgi_5g, "5G", start, end, granularity)
                
                # 合并结果
                cell_data = summary_4g + summary_5g
                # 按时间排序
                cell_data.sort(key=lambda x: x.get('start_time', ''))
        else:
            # 指定制式汇总查询
            cell_network = validate_network_type(cell_network)
            cell_data = service.cell_timeseries_summary(
                cgi_list, cell_network, start, end, granularity
            )
    else:
        # 小区查询（原逻辑）
        # 如果未指定制式，自动识别（混查模式）
        if not cell_network or cell_network == "混查":
            # 如果从场景获取了按网络类型分组的CGI，使用分组数据
            if selected_scenario_ids:
                # 分别查询4G和5G数据
                data_4g = []
                data_5g = []
                
                # 确保即使cgi_4g和cgi_5g都为空，也能正确处理查询
                # 重新按网络类型分组小区，确保即使network_type字段为空也能正确处理
                scenario_cgi_4g = []
                scenario_cgi_5g = []
                
                for cell in all_scenario_cells:
                    cgi = cell.get('cgi') or cell.get('cell_id')
                    if not cgi:
                        continue
                    
                    # 确保即使network_type字段为空，也能正确处理小区数据
                    network_type = cell.get('network_type', '4G')
                    # 尝试从CGI格式推断网络类型
                    if network_type not in ['4G', '5G']:
                        # CGI格式: 460-00-enb-lcrid 或 460-00-gnb-lcrid
                        parts = cgi.split('-')
                        if len(parts) >= 4:
                            enb_gnb = parts[2]
                            if len(enb_gnb) == 6:
                                network_type = '4G'
                            elif len(enb_gnb) == 8:
                                network_type = '5G'
                        else:
                            # 默认按4G处理
                            network_type = '4G'
                    
                    if network_type == '4G':
                        scenario_cgi_4g.append(cgi)
                    elif network_type == '5G':
                        scenario_cgi_5g.append(cgi)
                
                if scenario_cgi_4g:
                    data_4g = service.cell_timeseries_bulk(scenario_cgi_4g, "4G", start, end, granularity)
                    for row in data_4g:
                        if 'cgi' not in row or not row.get('cgi'):
                            row['cgi'] = row.get('cell_id')
                        if 'cell_id' not in row or not row.get('cell_id'):
                            row['cell_id'] = row.get('cgi')
                        row['network_type'] = "4G"
                
                if scenario_cgi_5g:
                    data_5g = service.cell_timeseries_bulk(scenario_cgi_5g, "5G", start, end, granularity)
                    for row in data_5g:
                        if 'cgi' not in row or not row.get('cgi'):
                            row['cgi'] = row.get('cell_id')
                        if 'cell_id' not in row or not row.get('cell_id'):
                            row['cell_id'] = row.get('cgi')
                        row['network_type'] = "5G"
                
                # 合并结果
                cell_data = data_4g + data_5g
                # 按时间和小区ID排序
                cell_data.sort(key=lambda x: (x.get('start_time', ''), x.get('cell_id', '')))
                
                # 设置自动检测的网络类型
                auto_detected = {}
                if scenario_cgi_4g:
                    auto_detected["4G"] = scenario_cgi_4g
                if scenario_cgi_5g:
                    auto_detected["5G"] = scenario_cgi_5g
                auto_detected_network = auto_detected
            else:
                # 否则按CGI格式自动识别
                cell_data, auto_detected_network = service.cell_timeseries_mixed(
                    cgi_list, start, end, granularity
                )
        else:
            cell_network = validate_network_type(cell_network)
            cell_data = service.cell_timeseries_bulk(
                cgi_list, cell_network, start, end, granularity
            )
            for row in cell_data:
                if 'cgi' not in row or not row.get('cgi'):
                    row['cgi'] = row.get('cell_id')
                if 'cell_id' not in row or not row.get('cell_id'):
                    row['cell_id'] = row.get('cgi')
                row['network_type'] = cell_network
    
    # 渲染结果HTML片段
    html = render_template(
        'cell_results.html',
        cell_cgi=cell_cgi,
        cell_network=cell_network or "混查",
        cell_data=cell_data,
        auto_detected_network=auto_detected_network,
        granularity=granularity,
        start_time=request.args.get("start_time", ""),
        end_time=request.args.get("end_time", ""),
        query_type=query_type
    )
    
    return jsonify({
        "success": True,
        "html": html,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@main_bp.route("/api/cell/refresh", methods=["GET"])
@api_login_required
def api_cell_refresh():
    """API: 指标查询局部刷新（返回JSON）"""
    from constants import MAX_CELL_QUERY_LIMIT
    from utils.validators import validate_and_parse_cgis, validate_granularity, validate_network_type
    from utils.time_parser import parse_time_range
    
    service = current_app.config.get('service')
    scenario_service = current_app.config.get('scenario_service')
    
    if not service or not scenario_service:
        return jsonify({"success": False, "error": "数据库服务未连接"}), 500
    
    # 获取参数
    cell_cgi = request.args.get("cell_cgi", "").strip()
    cell_network = request.args.get("cell_network", "").strip()
    granularity = validate_granularity(request.args.get("granularity", ""))
    query_type = request.args.get("query_type", "cell").strip()
    scenario_ids = request.args.getlist("scenario_ids")
    
    # 从场景中获取小区列表（如果选择了场景）
    selected_scenario_ids = []
    all_scenario_cells = []
    for sid in scenario_ids:
        if sid and sid.isdigit():
            selected_scenario_ids.append(int(sid))
    
    # 按网络类型分组的小区CGI
    cgi_4g = []
    cgi_5g = []
    
    if selected_scenario_ids:
        for scenario_id in selected_scenario_ids:
            scenario_cells = scenario_service.list_cells(scenario_id)
            all_scenario_cells.extend(scenario_cells)
        
        # 从场景小区中提取CGI，按网络类型分组
        all_scenario_cgis = []
        for cell in all_scenario_cells:
            cgi = cell.get('cgi') or cell.get('cell_id')
            if not cgi:
                continue
            
            all_scenario_cgis.append(cgi)
            # 确保即使network_type字段为空，也能正确处理小区数据
            network_type = cell.get('network_type', '4G')
            # 尝试从CGI格式推断网络类型
            if network_type not in ['4G', '5G']:
                # CGI格式: 460-00-enb-lcrid 或 460-00-gnb-lcrid
                parts = cgi.split('-')
                if len(parts) >= 4:
                    enb_gnb = parts[2]
                    if len(enb_gnb) == 6:
                        network_type = '4G'
                    elif len(enb_gnb) == 8:
                        network_type = '5G'
                else:
                    # 默认按4G处理
                    network_type = '4G'
            
            if network_type == '4G':
                cgi_4g.append(cgi)
            elif network_type == '5G':
                cgi_5g.append(cgi)
        
        if all_scenario_cgis:
            cell_cgi = ','.join(all_scenario_cgis)
    
    # CGI validation
    cgi_list, warning = validate_and_parse_cgis(cell_cgi, MAX_CELL_QUERY_LIMIT)
    
    if not cgi_list and not selected_scenario_ids:
        return jsonify({"success": False, "error": "请输入有效的小区CGI"}), 400
    
    # Time parsing
    latest = scenario_service.latest_time()
    latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
    latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
    
    # 根据粒度设置默认时间范围
    if granularity == "1d":
        default_hours = 168
        max_days = 90
    else:
        default_hours = 6
        max_days = 30
    
    start, end = parse_time_range(
        request.args.get("start_time", ""),
        request.args.get("end_time", ""),
        latest_ts=latest_ts,
        default_hours=default_hours,
        max_days=max_days
    )
    
    # Query data
    cell_data = []
    auto_detected_network = None
    
    # 如果是汇总查询
    if query_type == "summary":
        # 如果未指定制式，自动识别（混查模式）
        if not cell_network or cell_network == "混查":
            # 如果从场景获取了按网络类型分组的CGI，使用分组数据
            if selected_scenario_ids:
                # 分别按场景汇总4G和5G数据
                all_summary_data = []
                
                # 按场景分组处理
                for scenario_id in selected_scenario_ids:
                    scenario_cells = scenario_service.list_cells(scenario_id)
                    scenario_name = scenario_service.get_scenario_name(scenario_id)
                    
                    # 按网络类型分组
                    scenario_cgi_4g = []
                    scenario_cgi_5g = []
                    for cell in scenario_cells:
                        cgi = cell.get('cgi') or cell.get('cell_id')
                        if not cgi:
                            continue
                        
                        # 确保即使network_type字段为空，也能正确处理小区数据
                        network_type = cell.get('network_type', '4G')
                        # 尝试从CGI格式推断网络类型
                        if network_type not in ['4G', '5G']:
                            # CGI格式: 460-00-enb-lcrid 或 460-00-gnb-lcrid
                            parts = cgi.split('-')
                            if len(parts) >= 4:
                                enb_gnb = parts[2]
                                if len(enb_gnb) == 6:
                                    network_type = '4G'
                                elif len(enb_gnb) == 8:
                                    network_type = '5G'
                            else:
                                # 默认按4G处理
                                network_type = '4G'
                        
                        if network_type == '4G':
                            scenario_cgi_4g.append(cgi)
                        elif network_type == '5G':
                            scenario_cgi_5g.append(cgi)
                    
                    # 汇总4G数据
                    if scenario_cgi_4g:
                        summary_4g = service.cell_timeseries_summary(scenario_cgi_4g, "4G", start, end, granularity)
                        # 添加场景信息
                        for row in summary_4g:
                            row['scenario'] = scenario_name
                            all_summary_data.append(row)
                    
                    # 汇总5G数据
                    if scenario_cgi_5g:
                        summary_5g = service.cell_timeseries_summary(scenario_cgi_5g, "5G", start, end, granularity)
                        # 添加场景信息
                        for row in summary_5g:
                            row['scenario'] = scenario_name
                            all_summary_data.append(row)
                
                # 按时间和场景排序
                all_summary_data.sort(key=lambda x: (x.get('start_time', ''), x.get('scenario', '')))
                cell_data = all_summary_data
            else:
                # 否则按CGI格式自动识别
                cgi_4g = []
                cgi_5g = []
                for cgi in cgi_list:
                    if not cgi:
                        continue
                    parts = cgi.split('-')
                    if len(parts) >= 4:
                        enb_gnb = parts[2]
                        if len(enb_gnb) == 6:
                            cgi_4g.append(cgi)
                        elif len(enb_gnb) == 8:
                            cgi_5g.append(cgi)
                
                # 分别汇总4G和5G数据
                summary_4g = []
                summary_5g = []
                
                if cgi_4g:
                    summary_4g = service.cell_timeseries_summary(cgi_4g, "4G", start, end, granularity)
                if cgi_5g:
                    summary_5g = service.cell_timeseries_summary(cgi_5g, "5G", start, end, granularity)
                
                # 合并结果
                cell_data = summary_4g + summary_5g
                # 按时间排序
                cell_data.sort(key=lambda x: x.get('start_time', ''))
        else:
            # 指定制式汇总查询
            cell_network = validate_network_type(cell_network)
            cell_data = service.cell_timeseries_summary(
                cgi_list, cell_network, start, end, granularity
            )
    else:
        # 小区查询（原逻辑）
        # 如果未指定制式，自动识别（混查模式）
        if not cell_network or cell_network == "混查":
            # 如果从场景获取了按网络类型分组的CGI，使用分组数据
            if selected_scenario_ids:
                # 分别查询4G和5G数据
                data_4g = []
                data_5g = []
                
                # 确保即使cgi_4g和cgi_5g都为空，也能正确处理查询
                # 重新按网络类型分组小区，确保即使network_type字段为空也能正确处理
                scenario_cgi_4g = []
                scenario_cgi_5g = []
                
                for cell in all_scenario_cells:
                    cgi = cell.get('cgi') or cell.get('cell_id')
                    if not cgi:
                        continue
                    
                    # 确保即使network_type字段为空，也能正确处理小区数据
                    network_type = cell.get('network_type', '4G')
                    # 尝试从CGI格式推断网络类型
                    if network_type not in ['4G', '5G']:
                        # CGI格式: 460-00-enb-lcrid 或 460-00-gnb-lcrid
                        parts = cgi.split('-')
                        if len(parts) >= 4:
                            enb_gnb = parts[2]
                            if len(enb_gnb) == 6:
                                network_type = '4G'
                            elif len(enb_gnb) == 8:
                                network_type = '5G'
                        else:
                            # 默认按4G处理
                            network_type = '4G'
                    
                    if network_type == '4G':
                        scenario_cgi_4g.append(cgi)
                    elif network_type == '5G':
                        scenario_cgi_5g.append(cgi)
                
                if scenario_cgi_4g:
                    data_4g = service.cell_timeseries_bulk(scenario_cgi_4g, "4G", start, end, granularity)
                    for row in data_4g:
                        if 'cgi' not in row or not row.get('cgi'):
                            row['cgi'] = row.get('cell_id')
                        if 'cell_id' not in row or not row.get('cell_id'):
                            row['cell_id'] = row.get('cgi')
                        row['network_type'] = "4G"
                
                if scenario_cgi_5g:
                    data_5g = service.cell_timeseries_bulk(scenario_cgi_5g, "5G", start, end, granularity)
                    for row in data_5g:
                        if 'cgi' not in row or not row.get('cgi'):
                            row['cgi'] = row.get('cell_id')
                        if 'cell_id' not in row or not row.get('cell_id'):
                            row['cell_id'] = row.get('cgi')
                        row['network_type'] = "5G"
                
                # 合并结果
                cell_data = data_4g + data_5g
                # 按时间和小区ID排序
                cell_data.sort(key=lambda x: (x.get('start_time', ''), x.get('cell_id', '')))
                
                # 设置自动检测的网络类型
                auto_detected = {}
                if scenario_cgi_4g:
                    auto_detected["4G"] = scenario_cgi_4g
                if scenario_cgi_5g:
                    auto_detected["5G"] = scenario_cgi_5g
                auto_detected_network = auto_detected
            else:
                # 否则按CGI格式自动识别
                cell_data, auto_detected_network = service.cell_timeseries_mixed(
                    cgi_list, start, end, granularity
                )
        else:
            cell_network = validate_network_type(cell_network)
            cell_data = service.cell_timeseries_bulk(
                cgi_list, cell_network, start, end, granularity
            )
            for row in cell_data:
                if 'cgi' not in row or not row.get('cgi'):
                    row['cgi'] = row.get('cell_id')
                if 'cell_id' not in row or not row.get('cell_id'):
                    row['cell_id'] = row.get('cgi')
                row['network_type'] = cell_network
    
    # 格式化时间戳为字符串
    def format_ts(ts):
        if ts is None:
            return ""
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)
    
    # 格式化cell_data中的时间
    for row in cell_data:
        row["start_time"] = format_ts(row.get("start_time"))
    
    return jsonify({
        "success": True,
        "data": {
            "cell_data": cell_data,
            "auto_detected_network": auto_detected_network,
            "warning": warning
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@main_bp.route("/api/performance/log", methods=["POST"])
@api_login_required
def api_log_performance():
    """接收前端性能数据"""
    try:
        data = request.get_json()
        metrics = data.get("metrics", {})
        nav_type = data.get("navType", "未知")
        url = data.get("url", "")
        
        # Record performance data
        total = metrics.get("total", 0)
        white_screen = metrics.get("whiteScreen", 0)
        first_screen = metrics.get("firstScreen", 0)
        
        if total > 3000:
            logging.warning(f"🐌 前端性能较慢 - URL: {url}, 总耗时: {total}ms, 白屏: {white_screen}ms, 首屏: {first_screen}ms")
        else:
            logging.info(f"⚡ 前端性能 - URL: {url}, 总耗时: {total}ms, 白屏: {white_screen}ms, 首屏: {first_screen}ms")
        
        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"记录前端性能数据失败: {e}")
        return jsonify({"success": False})


@main_bp.route("/api/scenarios/cells", methods=["POST"])
@api_login_required
def api_add_cell():
    """API: 添加单个小区（AJAX）"""
    scenario_service = current_app.config.get('scenario_service')
    
    try:
        data = request.get_json() or request.form.to_dict()
        action = data.get("action")
        scenario_id = int(data.get("scenario_id", 0))
        
        if action == "add_cell":
            cell_id = data.get("cell_id", "").strip()
            cell_name = data.get("cell_name", "").strip()
            cgi = data.get("cgi", "").strip()
            network_type = data.get("network_type", "4G")
            
            if not scenario_id or not cell_id:
                return jsonify({"success": False, "message": "场景ID和小区ID不能为空"})
            
            inserted = scenario_service.add_cells(
                scenario_id,
                [{
                    "cell_id": cell_id,
                    "cell_name": cell_name,
                    "cgi": cgi or cell_id,
                    "network_type": network_type,
                }]
            )
            
            if inserted > 0:
                # Return updated cell list
                cells = scenario_service.list_cells(scenario_id)
                return jsonify({
                    "success": True,
                    "message": f"成功添加小区：{cell_id}",
                    "cells": cells,
                    "total": len(cells)
                })
            else:
                return jsonify({"success": False, "message": "小区已存在或添加失败"})
                
        elif action == "remove_cell":
            cell_id = data.get("cell_id", "")
            network_type = data.get("network_type", "4G")
            
            if not scenario_id or not cell_id:
                return jsonify({"success": False, "message": "场景ID和小区ID不能为空"})
            
            scenario_service.remove_cell(scenario_id, cell_id, network_type)
            
            # Return updated cell list
            cells = scenario_service.list_cells(scenario_id)
            return jsonify({
                "success": True,
                "message": f"成功移除小区：{cell_id}",
                "cells": cells,
                "total": len(cells)
            })
        else:
            return jsonify({"success": False, "message": "未知操作"})
            
    except Exception as e:
        logging.error(f"API操作失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"操作失败：{str(e)}"})


@main_bp.route("/scenarios", methods=["GET", "POST"])
@login_required
def scenarios():
    """场景管理页面"""
    scenario_service = current_app.config.get('scenario_service')
    
    # Check if services are available
    if not scenario_service:
        flash("数据库服务未连接，请检查配置或联系管理员", "danger")
        return render_template("error.html", message="数据库服务未连接")
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            name = request.form.get("name", "").strip()
            desc = request.form.get("desc", "").strip()
            if name:
                scenario_service.create_scenario(name, desc)
        elif action == "delete":
            sid = int(request.form.get("scenario_id", "0"))
            scenario_service.delete_scenario(sid)
        elif action == "add_cell":
            sid = int(request.form.get("scenario_id", "0"))
            cell_id = request.form.get("cell_id", "").strip()
            cell_name = request.form.get("cell_name", "").strip()
            cgi = request.form.get("cgi", "").strip()
            net = request.form.get("network_type", "4G")
            if sid and cell_id:
                scenario_service.add_cells(
                    sid,
                    [
                        {
                            "cell_id": cell_id,
                            "cell_name": cell_name,
                            "cgi": cgi or cell_id,
                            "network_type": net,
                        }
                    ],
                )
        elif action == "remove_cell":
            sid = int(request.form.get("scenario_id", "0"))
            cell_id = request.form.get("cell_id", "")
            net = request.form.get("network_type", "4G")
            if sid and cell_id:
                scenario_service.remove_cell(sid, cell_id, net)
        elif action == "import_cells":
            sid = int(request.form.get("scenario_id", "0"))
            if sid and "file" in request.files:
                file = request.files["file"]
                if file.filename:
                    try:
                        import pandas as pd
                        # Read Excel file
                        df = pd.read_excel(file)
                        # Validate required columns
                        required_cols = ["cell_id", "network_type"]
                        if not all(col in df.columns for col in required_cols):
                            flash("Excel文件缺少必需的列：cell_id, network_type", "danger")
                        else:
                            # Convert to list of dictionaries
                            cells = []
                            for _, row in df.iterrows():
                                cell_id = str(row.get("cell_id", "")).strip()
                                if not cell_id:
                                    continue
                                network_type = str(row.get("network_type", "4G")).strip().upper()
                                if network_type not in ["4G", "5G"]:
                                    network_type = "4G"  # Default value
                                # Get CGI, use cell_id as default if empty (consistent with single import logic)
                                cgi = str(row.get("cgi", "")).strip() if pd.notna(row.get("cgi")) else ""
                                cells.append({
                                    "cell_id": cell_id,
                                    "cell_name": str(row.get("cell_name", "")).strip() if pd.notna(row.get("cell_name")) else "",
                                    "cgi": cgi or cell_id,  # Use cell_id as default if CGI is empty
                                    "network_type": network_type,
                                })
                            # Filter empty values
                            cells = [c for c in cells if c["cell_id"]]
                            if cells:
                                inserted = scenario_service.add_cells(sid, cells)
                                flash(f"成功导入 {inserted} 个小区（共 {len(cells)} 条记录）", "success")
                            else:
                                flash("Excel文件中没有有效的小区数据", "warning")
                    except Exception as e:
                        flash(f"导入失败：{str(e)}", "danger")
        scenario_id_param = request.form.get("scenario_id", request.args.get("scenario_id", ""))
        return redirect(url_for("main.scenarios", scenario_id=scenario_id_param) if scenario_id_param else url_for("main.scenarios"))

    scenario_list = scenario_service.list_scenarios()
    selected_id = int(request.args.get("scenario_id", scenario_list[0]["id"] if scenario_list else 0))
    cells = scenario_service.list_cells(selected_id) if selected_id else []
    return render_template(
        "scenarios.html",
        scenarios=scenario_list,
        selected_id=selected_id,
        cells=cells,
    )


# ==================== 响应式测试路由 ====================

@main_bp.route("/test/responsive")
@login_required
def test_responsive():
    """响应式设计测试页面"""
    return render_template("responsive_test.html", title="响应式设计测试")


@main_bp.route("/test/mobile")
@login_required
def test_mobile():
    """移动端测试和诊断页面"""
    return render_template("mobile_test.html", title="移动端测试")


@main_bp.route("/test/widescreen")
@login_required
def test_widescreen():
    """宽屏优化测试页面"""
    return render_template("widescreen_test.html", title="宽屏优化测试")


@main_bp.route("/test/css")
@login_required
def test_css():
    """CSS加载测试页面"""
    return render_template("css_test.html", title="CSS加载测试")


@main_bp.route("/api/traffic/region", methods=["GET"])
@api_login_required
def api_region_traffic():
    """API: 按区域和网络类型分组的流量时间序列数据"""
    from utils.validators import validate_time_range, validate_granularity
    
    service = current_app.config.get('service')
    
    if not service:
        return jsonify({"success": False, "error": "数据库服务未连接"}), 500
    
    # 获取参数
    range_key = validate_time_range(request.args.get("range", ""))
    networks = request.args.getlist("networks") or ["4G", "5G"]
    granularity = validate_granularity(request.args.get("granularity", ""))
    
    # 解析时间范围
    latest = current_app.config.get('scenario_service').latest_time()
    latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
    latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
    
    start, end = service.resolve_range(range_key, reference_time=latest_ts)
    
    # 查询数据（使用 fast 模式，在数据库侧按区域聚合，显著减少返回行数）
    data = service.region_traffic_series(networks, start, end, granularity, fast=True)
    
    # 格式化时间戳为字符串
    def format_ts(ts):
        if ts is None:
            return ""
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)
    
    # 格式化数据中的时间
    for item in data:
        item["start_time"] = format_ts(item.get("start_time"))
    
    return jsonify({
        "success": True,
        "data": data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
