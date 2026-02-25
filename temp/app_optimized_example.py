"""
app.py 优化示例
展示如何使用新的工具模块优化路由代码
"""

from flask import Flask, request, render_template, flash
from datetime import datetime

# 导入常量
from constants import (
    MAX_CELL_QUERY_LIMIT,
    DEFAULT_PAGE_SIZE,
    DEFAULT_THRESHOLD_4G,
    DEFAULT_THRESHOLD_5G,
    GRANULARITY_15MIN,
    DEFAULT_AUTO_REFRESH_INTERVAL,
)

# 导入工具函数
from utils.formatters import format_traffic_with_unit
from utils.time_parser import parse_time_range, format_datetime_for_input
from utils.validators import (
    validate_and_parse_cgis,
    validate_granularity,
    validate_network_type,
    validate_time_range,
)

# 假设已有的服务
# from services.metrics_service import MetricsService
# from services.scenario_service import ScenarioService


def create_optimized_app():
    """创建优化后的Flask应用示例"""
    app = Flask(__name__)
    
    # 假设服务已初始化
    # service = MetricsService(pg_client)
    # scenario_service = ScenarioService(pg_client)
    
    @app.route("/cell_optimized")
    def cell_optimized():
        """
        优化后的小区指标查询路由
        对比原来的代码，减少了大量重复逻辑
        """
        # 1. 参数获取和验证（使用验证器）
        cell_cgi = request.args.get("cell_cgi", "").strip()
        cell_network = validate_network_type(request.args.get("cell_network", ""))
        granularity = validate_granularity(request.args.get("granularity", ""))
        
        # 2. CGI验证（统一的验证逻辑）
        cgi_list, warning = validate_and_parse_cgis(cell_cgi, MAX_CELL_QUERY_LIMIT)
        if warning:
            flash(warning, "warning")
        
        # 3. 时间解析（统一的解析逻辑，带验证）
        # latest = scenario_service.latest_time()
        # latest_ts = max((ts for ts in [latest.get("4g"), latest.get("5g")] if ts), default=None)
        latest_ts = datetime.now()  # 示例
        
        start, end = parse_time_range(
            request.args.get("start_time", ""),
            request.args.get("end_time", ""),
            latest_ts=latest_ts,
            default_hours=6,
            max_days=30
        )
        
        # 4. 查询数据
        cell_data = []
        if cgi_list:
            # cell_data = service.cell_timeseries_bulk(cgi_list, cell_network, start, end, granularity)
            
            # 数据补齐
            for row in cell_data:
                if 'cgi' not in row or not row.get('cgi'):
                    row['cgi'] = row.get('cell_id')
                if 'cell_id' not in row or not row.get('cell_id'):
                    row['cell_id'] = row.get('cgi')
            
            if not cell_data:
                flash("未查询到该小区的指标数据，请确认CGI与制式是否正确。", "warning")
        
        # 5. 返回渲染（使用格式化函数）
        return render_template(
            "cell.html",
            cell_cgi=cell_cgi,
            cell_network=cell_network,
            start_time=format_datetime_for_input(start),
            end_time=format_datetime_for_input(end),
            cell_data=cell_data,
            granularity=granularity,
        )
    
    @app.route("/monitor_optimized", methods=["GET", "POST"])
    def monitor_optimized():
        """
        优化后的保障监控路由
        使用常量替代硬编码值
        """
        # scenarios = scenario_service.list_scenarios()
        scenarios = []  # 示例
        
        # 使用常量替代硬编码
        selected = request.values.getlist("scenario_id", type=int)
        threshold_4g = float(request.values.get("thr4g", DEFAULT_THRESHOLD_4G))
        threshold_5g = float(request.values.get("thr5g", DEFAULT_THRESHOLD_5G))
        auto = request.values.get("auto", "0") == "1"
        auto_interval = int(request.values.get("auto_interval", DEFAULT_AUTO_REFRESH_INTERVAL))
        
        # 时间解析（统一逻辑）
        # latest = scenario_service.latest_time()
        # latest_ts = max((ts for ts in [latest.get("4g"), latest.get("5g")] if ts), default=None)
        latest_ts = datetime.now()  # 示例
        
        start, end = parse_time_range(
            request.values.get("start_time", ""),
            request.values.get("end_time", ""),
            latest_ts=latest_ts,
            default_hours=6
        )
        
        # 查询数据
        # metrics = scenario_service.scenario_metrics(selected, threshold_4g, threshold_5g)
        # trend_4g = scenario_service.traffic_trend(selected, start, end, "4G")
        # ...
        
        # 分页（使用常量）
        page_4g = int(request.args.get("page_4g", 1))
        page_5g = int(request.args.get("page_5g", 1))
        # cell_metrics = scenario_service.scenario_cell_metrics(
        #     selected, page_4g=page_4g, page_5g=page_5g, page_size=DEFAULT_PAGE_SIZE
        # )
        
        return render_template(
            "monitor.html",
            scenarios=scenarios,
            selected=selected,
            threshold_4g=threshold_4g,
            threshold_5g=threshold_5g,
            # metrics=metrics,
            # trend_4g=trend_4g,
            # ...
            page_4g=page_4g,
            page_5g=page_5g,
            auto=auto,
            auto_interval=auto_interval,
            monitoring_active=bool(selected),
            start_time=format_datetime_for_input(start),
            end_time=format_datetime_for_input(end),
        )
    
    @app.route("/dashboard_optimized")
    def dashboard_optimized():
        """
        优化后的全网监控路由
        使用验证器和常量
        """
        # 参数验证
        range_key = validate_time_range(request.args.get("range", ""))
        networks = request.args.getlist("networks")
        if not networks:
            networks = ["4G", "5G"]  # 默认值
        
        auto = request.args.get("auto", "0") == "1"
        auto_interval = int(request.args.get("auto_interval", DEFAULT_AUTO_REFRESH_INTERVAL))
        granularity = validate_granularity(request.args.get("granularity", ""))
        
        # 日期参数
        date_str = request.args.get("date", "")
        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                pass
        
        # 查询数据
        # latest = scenario_service.latest_time()
        # latest_ts = max((ts for ts in [latest.get("4g"), latest.get("5g")] if ts), default=None)
        # start, end = service.resolve_range(range_key, reference_time=latest_ts)
        # ...
        
        # 分页（使用常量）
        page4 = int(request.args.get("page4", 1))
        page5 = int(request.args.get("page5", 1))
        
        return render_template(
            "dashboard.html",
            range_key=range_key,
            networks=networks,
            # traffic=traffic,
            # top4=top4,
            # top5=top5,
            page4=page4,
            page5=page5,
            auto=auto,
            auto_interval=auto_interval,
            granularity=granularity,
            # ...
        )
    
    @app.route("/admin/cache_stats")
    def cache_stats():
        """
        缓存统计端点（新增）
        用于监控缓存性能
        """
        from services.cache import get_all_cache_stats
        from flask import jsonify
        
        stats = get_all_cache_stats()
        return jsonify(stats)
    
    return app


# 代码对比示例
def comparison_example():
    """
    代码对比：优化前 vs 优化后
    """
    
    # ========== 优化前 ==========
    def old_way():
        # CGI验证 - 重复代码
        cell_cgi = request.args.get("cell_cgi", "").strip()
        cgi_list = [c.strip() for c in cell_cgi.split(',') if c.strip()]
        if len(cgi_list) > 200:
            flash(f"最多只能查询200个小区，当前输入了{len(cgi_list)}个，已自动截取前200个", "warning")
            cgi_list = cgi_list[:200]
        
        # 时间解析 - 重复代码
        start_time_str = request.args.get("start_time", "")
        end_time_str = request.args.get("end_time", "")
        end = datetime.now()
        start = end - timedelta(hours=6)
        if end_time_str:
            try:
                if 'T' in end_time_str:
                    end = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                else:
                    end = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except Exception as e:
                pass
        # ... 更多重复代码
        
        # 硬编码值
        page_size = 20
        threshold = 50
        max_cells = 200
    
    # ========== 优化后 ==========
    def new_way():
        # CGI验证 - 一行代码
        cgi_list, warning = validate_and_parse_cgis(
            request.args.get("cell_cgi", "").strip()
        )
        if warning:
            flash(warning, "warning")
        
        # 时间解析 - 一行代码
        start, end = parse_time_range(
            request.args.get("start_time", ""),
            request.args.get("end_time", ""),
            latest_ts=latest_ts
        )
        
        # 使用常量
        page_size = DEFAULT_PAGE_SIZE
        threshold = DEFAULT_THRESHOLD_4G
        max_cells = MAX_CELL_QUERY_LIMIT


if __name__ == "__main__":
    # 这只是示例代码，不要直接运行
    print("这是优化示例代码，请参考 MIGRATION_GUIDE.md 进行实际迁移")
    print("\n优化要点：")
    print("1. 使用常量替代硬编码值")
    print("2. 使用工具函数消除重复代码")
    print("3. 统一验证和解析逻辑")
    print("4. 添加缓存监控端点")
