"""
计划任务调度服务
支持定时执行 Python 脚本和系统命令
"""
import logging
import subprocess
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from collections import deque

logger = logging.getLogger(__name__)


class SchedulerService:
    """计划任务调度服务"""
    
    def __init__(self, config_file: str = "scheduler_config.json"):
        """初始化调度器
        
        Args:
            config_file: 任务配置文件路径
        """
        self.config_file = config_file
        self.scheduler = None
        self.job_logs = deque(maxlen=1000)  # 保存最近1000条执行日志
        self._init_scheduler()
        self._load_jobs()
    
    def _init_scheduler(self):
        """初始化 APScheduler"""
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=5)
        }
        job_defaults = {
            'coalesce': True,  # 合并错过的任务
            'max_instances': 1,  # 同一任务最多同时运行1个实例
            'misfire_grace_time': 300  # 错过任务的宽限时间（秒）
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )
        self.scheduler.start()
        logger.info("✓ 计划任务调度器已启动")
    
    def _load_jobs(self):
        """从配置文件加载任务"""
        if not os.path.exists(self.config_file):
            logger.info(f"配置文件不存在，创建默认配置: {self.config_file}")
            self._save_config([])
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
            
            for job_config in jobs:
                if job_config.get('enabled', True):
                    self._add_job_from_config(job_config)
            
            logger.info(f"✓ 已加载 {len(jobs)} 个计划任务")
        except Exception as e:
            logger.error(f"加载任务配置失败: {e}")
    
    def _add_job_from_config(self, job_config: Dict[str, Any]):
        """从配置添加任务到调度器"""
        try:
            job_id = job_config['id']
            job_type = job_config['type']
            schedule_type = job_config['schedule_type']
            schedule_config = job_config['schedule_config']
            
            # 创建触发器
            trigger = self._create_trigger(schedule_type, schedule_config)
            
            # 添加任务
            if job_type == 'python':
                self.scheduler.add_job(
                    func=self._execute_python_script,
                    trigger=trigger,
                    id=job_id,
                    args=[job_config],
                    name=job_config.get('name', job_id),
                    replace_existing=True
                )
            elif job_type == 'command':
                self.scheduler.add_job(
                    func=self._execute_command,
                    trigger=trigger,
                    id=job_id,
                    args=[job_config],
                    name=job_config.get('name', job_id),
                    replace_existing=True
                )
            
            logger.info(f"✓ 任务已添加: {job_config.get('name', job_id)}")
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
    
    def _create_trigger(self, schedule_type: str, config: Dict[str, Any]):
        """创建调度触发器
        
        Args:
            schedule_type: 调度类型 (cron, interval, date)
            config: 调度配置
        """
        if schedule_type == 'cron':
            # Cron 表达式调度
            return CronTrigger(
                year=config.get('year'),
                month=config.get('month'),
                day=config.get('day'),
                week=config.get('week'),
                day_of_week=config.get('day_of_week'),
                hour=config.get('hour'),
                minute=config.get('minute'),
                second=config.get('second', 0),
                timezone='Asia/Shanghai'
            )
        elif schedule_type == 'interval':
            # 间隔调度
            return IntervalTrigger(
                weeks=config.get('weeks', 0),
                days=config.get('days', 0),
                hours=config.get('hours', 0),
                minutes=config.get('minutes', 0),
                seconds=config.get('seconds', 0),
                timezone='Asia/Shanghai'
            )
        elif schedule_type == 'date':
            # 一次性调度
            run_date = datetime.fromisoformat(config['run_date'])
            return DateTrigger(run_date=run_date, timezone='Asia/Shanghai')
        else:
            raise ValueError(f"不支持的调度类型: {schedule_type}")
    
    def _execute_python_script(self, job_config: Dict[str, Any]):
        """执行 Python 脚本"""
        script_path = job_config['script_path']
        args = job_config.get('args', [])
        working_dir = job_config.get('working_dir', os.getcwd())
        
        start_time = datetime.now()
        log_entry = {
            'job_id': job_config['id'],
            'job_name': job_config.get('name', job_config['id']),
            'type': 'python',
            'start_time': start_time.isoformat(),
            'script_path': script_path,
            'status': 'running'
        }
        
        try:
            # 执行 Python 脚本
            cmd = ['python', script_path] + args
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=job_config.get('timeout', 3600)  # 默认超时1小时
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            log_entry.update({
                'end_time': end_time.isoformat(),
                'duration': duration,
                'status': 'success' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'stdout': result.stdout[-1000:] if result.stdout else '',  # 保留最后1000字符
                'stderr': result.stderr[-1000:] if result.stderr else ''
            })
            
            if result.returncode == 0:
                logger.info(f"✓ 任务执行成功: {job_config.get('name')} (耗时: {duration:.2f}s)")
            else:
                logger.error(f"✗ 任务执行失败: {job_config.get('name')} (返回码: {result.returncode})")
        
        except subprocess.TimeoutExpired:
            log_entry.update({
                'end_time': datetime.now().isoformat(),
                'status': 'timeout',
                'error': '任务执行超时'
            })
            logger.error(f"✗ 任务执行超时: {job_config.get('name')}")
        
        except Exception as e:
            log_entry.update({
                'end_time': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            })
            logger.error(f"✗ 任务执行异常: {job_config.get('name')} - {e}")
        
        self.job_logs.append(log_entry)
    
    def _execute_command(self, job_config: Dict[str, Any]):
        """执行系统命令"""
        command = job_config['command']
        working_dir = job_config.get('working_dir', os.getcwd())
        
        start_time = datetime.now()
        log_entry = {
            'job_id': job_config['id'],
            'job_name': job_config.get('name', job_config['id']),
            'type': 'command',
            'start_time': start_time.isoformat(),
            'command': command,
            'status': 'running'
        }
        
        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=job_config.get('timeout', 3600)
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            log_entry.update({
                'end_time': end_time.isoformat(),
                'duration': duration,
                'status': 'success' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'stdout': result.stdout[-1000:] if result.stdout else '',
                'stderr': result.stderr[-1000:] if result.stderr else ''
            })
            
            if result.returncode == 0:
                logger.info(f"✓ 命令执行成功: {job_config.get('name')} (耗时: {duration:.2f}s)")
            else:
                logger.error(f"✗ 命令执行失败: {job_config.get('name')} (返回码: {result.returncode})")
        
        except subprocess.TimeoutExpired:
            log_entry.update({
                'end_time': datetime.now().isoformat(),
                'status': 'timeout',
                'error': '命令执行超时'
            })
            logger.error(f"✗ 命令执行超时: {job_config.get('name')}")
        
        except Exception as e:
            log_entry.update({
                'end_time': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            })
            logger.error(f"✗ 命令执行异常: {job_config.get('name')} - {e}")
        
        self.job_logs.append(log_entry)
    
    def add_job(self, job_config: Dict[str, Any]) -> bool:
        """添加新任务"""
        try:
            # 加载现有配置
            jobs = self._load_config()
            
            # 检查 ID 是否已存在
            if any(job['id'] == job_config['id'] for job in jobs):
                raise ValueError(f"任务 ID 已存在: {job_config['id']}")
            
            # 添加到配置
            jobs.append(job_config)
            self._save_config(jobs)
            
            # 添加到调度器
            if job_config.get('enabled', True):
                self._add_job_from_config(job_config)
            
            return True
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return False
    
    def update_job(self, job_id: str, job_config: Dict[str, Any]) -> bool:
        """更新任务"""
        try:
            jobs = self._load_config()
            
            # 查找并更新任务
            found = False
            for i, job in enumerate(jobs):
                if job['id'] == job_id:
                    jobs[i] = job_config
                    found = True
                    break
            
            if not found:
                raise ValueError(f"任务不存在: {job_id}")
            
            self._save_config(jobs)
            
            # 移除旧任务
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # 添加新任务
            if job_config.get('enabled', True):
                self._add_job_from_config(job_config)
            
            return True
        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """删除任务"""
        try:
            jobs = self._load_config()
            jobs = [job for job in jobs if job['id'] != job_id]
            self._save_config(jobs)
            
            # 从调度器移除
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            return True
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务配置"""
        jobs = self._load_config()
        for job in jobs:
            if job['id'] == job_id:
                # 添加运行时信息
                scheduler_job = self.scheduler.get_job(job_id)
                if scheduler_job:
                    job['next_run_time'] = scheduler_job.next_run_time.isoformat() if scheduler_job.next_run_time else None
                return job
        return None
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        jobs = self._load_config()
        
        # 添加运行时信息
        for job in jobs:
            scheduler_job = self.scheduler.get_job(job['id'])
            if scheduler_job:
                job['next_run_time'] = scheduler_job.next_run_time.isoformat() if scheduler_job.next_run_time else None
            else:
                job['next_run_time'] = None
        
        return jobs
    
    def run_job_now(self, job_id: str) -> bool:
        """立即执行任务"""
        try:
            job_config = self.get_job(job_id)
            if not job_config:
                raise ValueError(f"任务不存在: {job_id}")
            
            if job_config['type'] == 'python':
                self._execute_python_script(job_config)
            elif job_config['type'] == 'command':
                self._execute_command(job_config)
            
            return True
        except Exception as e:
            logger.error(f"立即执行任务失败: {e}")
            return False
    
    def get_job_logs(self, job_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取任务执行日志"""
        logs = list(self.job_logs)
        
        if job_id:
            logs = [log for log in logs if log['job_id'] == job_id]
        
        # 按时间倒序
        logs.sort(key=lambda x: x['start_time'], reverse=True)
        
        return logs[:limit]
    
    def _load_config(self) -> List[Dict[str, Any]]:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            return []
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_config(self, jobs: List[Dict[str, Any]]):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("计划任务调度器已关闭")


__all__ = ['SchedulerService']
