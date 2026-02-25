"""
API v1 Blueprint
提供版本化的API端点
"""
from flask import Blueprint, jsonify, request
from auth import api_login_required
import logging

logger = logging.getLogger(__name__)

# 创建API v1蓝图
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


@api_v1.route('/health', methods=['GET'])
def health_check():
    """API健康检查端点（无需登录）"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "api_version": "v1"
    }), 200


@api_v1.route('/performance/log', methods=['POST'])
@api_login_required
def log_performance():
    """接收前端性能数据"""
    try:
        data = request.get_json()
        metrics = data.get("metrics", {})
        nav_type = data.get("navType", "未知")
        url = data.get("url", "")

        # 记录性能数据
        total = metrics.get("total", 0)
        white_screen = metrics.get("whiteScreen", 0)
        first_screen = metrics.get("firstScreen", 0)

        if total > 3000:
            logger.warning(f"🐌 前端性能较慢 - URL: {url}, 总耗时: {total}ms, 白屏: {white_screen}ms, 首屏: {first_screen}ms")
        else:
            logger.info(f"⚡ 前端性能 - URL: {url}, 总耗时: {total}ms, 白屏: {white_screen}ms, 首屏: {first_screen}ms")

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"记录前端性能数据失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
