"""
计划任务管理路由
仅管理员可访问
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from auth import admin_required
import logging

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/scheduler')


@scheduler_bp.route('/')
@admin_required
def index():
    """计划任务管理页面"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return render_template('error.html', 
                             error_message="计划任务服务未启用",
                             error_code=503), 503
    
    jobs = scheduler_service.get_all_jobs()
    
    return render_template('scheduler/index.html', jobs=jobs)


@scheduler_bp.route('/api/jobs', methods=['GET'])
@admin_required
def get_jobs():
    """获取所有任务（API）"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    jobs = scheduler_service.get_all_jobs()
    return jsonify({'jobs': jobs})


@scheduler_bp.route('/api/jobs/<job_id>', methods=['GET'])
@admin_required
def get_job(job_id):
    """获取单个任务详情"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    job = scheduler_service.get_job(job_id)
    
    if not job:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify({'job': job})


@scheduler_bp.route('/api/jobs', methods=['POST'])
@admin_required
def create_job():
    """创建新任务"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    job_config = request.json
    
    # 验证必填字段
    required_fields = ['id', 'name', 'type', 'schedule_type', 'schedule_config']
    for field in required_fields:
        if field not in job_config:
            return jsonify({'error': f'缺少必填字段: {field}'}), 400
    
    # 验证任务类型
    if job_config['type'] not in ['python', 'command']:
        return jsonify({'error': '任务类型必须是 python 或 command'}), 400
    
    # 验证调度类型
    if job_config['schedule_type'] not in ['cron', 'interval', 'date']:
        return jsonify({'error': '调度类型必须是 cron, interval 或 date'}), 400
    
    # 验证任务内容
    if job_config['type'] == 'python' and 'script_path' not in job_config:
        return jsonify({'error': 'Python 任务必须指定 script_path'}), 400
    
    if job_config['type'] == 'command' and 'command' not in job_config:
        return jsonify({'error': '命令任务必须指定 command'}), 400
    
    success = scheduler_service.add_job(job_config)
    
    if success:
        return jsonify({'message': '任务创建成功', 'job_id': job_config['id']}), 201
    else:
        return jsonify({'error': '任务创建失败'}), 500


@scheduler_bp.route('/api/jobs/<job_id>', methods=['PUT'])
@admin_required
def update_job(job_id):
    """更新任务"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    job_config = request.json
    job_config['id'] = job_id  # 确保 ID 一致
    
    success = scheduler_service.update_job(job_id, job_config)
    
    if success:
        return jsonify({'message': '任务更新成功'})
    else:
        return jsonify({'error': '任务更新失败'}), 500


@scheduler_bp.route('/api/jobs/<job_id>', methods=['DELETE'])
@admin_required
def delete_job(job_id):
    """删除任务"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    success = scheduler_service.delete_job(job_id)
    
    if success:
        return jsonify({'message': '任务删除成功'})
    else:
        return jsonify({'error': '任务删除失败'}), 500


@scheduler_bp.route('/api/jobs/<job_id>/run', methods=['POST'])
@admin_required
def run_job(job_id):
    """立即执行任务"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    success = scheduler_service.run_job_now(job_id)
    
    if success:
        return jsonify({'message': '任务已提交执行'})
    else:
        return jsonify({'error': '任务执行失败'}), 500


@scheduler_bp.route('/api/jobs/<job_id>/logs', methods=['GET'])
@admin_required
def get_job_logs(job_id):
    """获取任务执行日志"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    limit = request.args.get('limit', 50, type=int)
    logs = scheduler_service.get_job_logs(job_id=job_id, limit=limit)
    
    return jsonify({'logs': logs})


@scheduler_bp.route('/api/logs', methods=['GET'])
@admin_required
def get_all_logs():
    """获取所有任务执行日志"""
    scheduler_service = current_app.config.get('scheduler_service')
    
    if not scheduler_service:
        return jsonify({'error': '计划任务服务未启用'}), 503
    
    limit = request.args.get('limit', 100, type=int)
    logs = scheduler_service.get_job_logs(limit=limit)
    
    return jsonify({'logs': logs})


__all__ = ['scheduler_bp']
