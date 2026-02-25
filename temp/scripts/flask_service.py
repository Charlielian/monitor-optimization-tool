"""
Flask应用Windows服务包装器
使用pywin32将Flask应用部署为Windows服务

安装服务：
    python flask_service.py install

启动服务：
    python flask_service.py start
    
停止服务：
    python flask_service.py stop
    
卸载服务：
    python flask_service.py remove

或者使用：
    python flask_service.py --startup=auto install  # 设置开机自启动
"""

import os
import sys
import time
import logging
import threading
import json
from pathlib import Path

# 确保当前目录是脚本所在目录
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe文件
    application_path = os.path.dirname(sys.executable)
else:
    # 如果是Python脚本
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)
sys.path.insert(0, application_path)

# 服务配置文件路径
SERVICE_CONFIG_FILE = os.path.join(application_path, 'service_config.json')

# 读取服务配置
def load_service_config():
    """加载服务配置"""
    default_config = {
        'host': '0.0.0.0',
        'port': 5000,
        'debug': False,
        'log_level': 'INFO',
        'waitress': {
            'threads': 8,
            'connection_limit': 100,
            'request_timeout': 30,
            'channel_timeout': 60
        }
    }
    
    if os.path.exists(SERVICE_CONFIG_FILE):
        try:
            with open(SERVICE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            # 合并配置，用户配置优先级更高
            default_config.update(user_config)
        except Exception as e:
            print(f"警告：无法读取配置文件 {SERVICE_CONFIG_FILE}，使用默认配置: {str(e)}")
    
    return default_config

# 保存服务配置
def save_service_config(config):
    """保存服务配置"""
    try:
        with open(SERVICE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"警告：无法保存配置文件 {SERVICE_CONFIG_FILE}: {str(e)}")

# 加载配置
config = load_service_config()

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    # 尝试导入waitress
    try:
        from waitress import serve
    except ImportError:
        print("警告：waitress未安装，将使用Flask开发服务器")
        print("建议运行: pip install waitress")
        waitress_available = False
    else:
        waitress_available = True
except ImportError:
    print("错误：需要安装pywin32")
    print("请运行: pip install pywin32")
    sys.exit(1)

# 导入Flask应用
from app import create_app


class FlaskService(win32serviceutil.ServiceFramework):
    """Flask应用Windows服务类"""
    
    _svc_name_ = "FlaskMonitoringApp"
    _svc_display_name_ = "保障指标监控系统 (Flask)"
    _svc_description_ = "保障指标监控系统 - Flask Web应用服务"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.app = None
        self.server_thread = None
        self.is_alive = True
        self.waitress_server = None
        
        # 设置日志
        log_file = os.path.join(application_path, 'logs', 'service.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, config['log_level'].upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_file,
            encoding='utf-8'
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"服务配置加载完成: {config}")
    
    def SvcStop(self):
        """停止服务"""
        self.logger.info("正在停止服务...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_alive = False
        
        # 停止waitress服务器
        if self.waitress_server:
            self.logger.info("正在停止waitress服务器...")
            try:
                self.waitress_server.close()
                self.waitress_server = None
            except Exception as e:
                self.logger.error(f"停止waitress服务器时出错: {str(e)}", exc_info=True)
        
        # 设置事件信号，唤醒主线程
        win32event.SetEvent(self.hWaitStop)
        
        # 给线程一些时间来完成当前请求
        if self.server_thread and self.server_thread.is_alive():
            self.logger.info("等待Flask应用线程停止...")
            time.sleep(3)
        
        self.logger.info("服务已停止")
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
    
    def SvcDoRun(self):
        """运行服务主循环"""
        try:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.logger.info(f"服务 {self._svc_name_} 正在启动...")
            
            # 创建Flask应用
            self.logger.info("正在创建Flask应用...")
            self.app = create_app()
            
            # 在单独线程中运行Flask应用
            self.logger.info("正在启动Flask服务器...")
            self.server_thread = threading.Thread(
                target=self._run_flask,
                daemon=True
            )
            self.server_thread.start()
            
            self.logger.info(f"服务已启动，Flask应用将在 {config['host']}:{config['port']} 上运行")
            
            # 等待停止信号
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
        except Exception as e:
            self.logger.error(f"服务运行出错: {str(e)}", exc_info=True)
            servicemanager.LogErrorMsg(f"服务运行出错: {str(e)}")
            # 服务出错，设置事件信号以退出
            win32event.SetEvent(self.hWaitStop)
        finally:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, '')
            )
            self.logger.info("服务已退出")
    
    def _run_flask(self):
        """在单独线程中运行Flask应用"""
        try:
            host = config['host']
            port = config['port']
            debug = config['debug']
            
            self.logger.info(f"使用配置: host={host}, port={port}, debug={debug}")
            
            if waitress_available and not debug:
                # 使用waitress WSGI服务器（生产环境推荐）
                self.logger.info(f"使用waitress运行Flask应用，配置: {config['waitress']}")
                # 启动waitress服务器
                self.waitress_server = serve(
                    self.app,
                    host=host,
                    port=port,
                    threads=config['waitress']['threads'],
                    connection_limit=config['waitress']['connection_limit'],
                    channel_timeout=config['waitress']['channel_timeout']
                )
            else:
                # 使用Flask开发服务器（仅用于开发或调试）
                self.logger.warning("使用Flask开发服务器，不适用于生产环境")
                self.app.run(
                    host=host,
                    port=port,
                    debug=debug,
                    use_reloader=False,  # 服务模式下禁用自动重载
                    threaded=True
                )
        except Exception as e:
            self.logger.error(f"Flask应用运行出错: {str(e)}", exc_info=True)
            servicemanager.LogErrorMsg(f"Flask应用运行出错: {str(e)}")
            # 应用出错，设置事件信号以停止服务
            win32event.SetEvent(self.hWaitStop)
            raise


def main():
    """主函数 - 处理服务安装、启动、停止等操作"""
    if len(sys.argv) == 1:
        # 如果没有参数，显示帮助信息
        print(__doc__)
        print("\n可用命令:")
        print("  install    - 安装服务")
        print("  remove     - 卸载服务")
        print("  start      - 启动服务")
        print("  stop       - 停止服务")
        print("  restart    - 重启服务")
        print("  debug      - 以调试模式运行（非服务模式）")
        print("  config     - 显示当前服务配置")
        print("\n示例:")
        print("  python flask_service.py install")
        print("  python flask_service.py --startup=auto install  # 开机自启动")
        print("  python flask_service.py start")
        print("  python flask_service.py debug  # 调试模式")
        sys.exit(0)
    
    # 处理debug模式（非服务模式运行）
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        print("以调试模式运行Flask应用（非服务模式）...")
        print("按 Ctrl+C 停止")
        app = create_app()
        host = config['host']
        port = config['port']
        print(f"访问地址: http://{host}:{port}")
        try:
            app.run(host=host, port=port, debug=True)
        except KeyboardInterrupt:
            print("\n应用已停止")
        sys.exit(0)
    
    # 处理config命令
    if len(sys.argv) > 1 and sys.argv[1] == 'config':
        print("当前服务配置:")
        print(json.dumps(config, ensure_ascii=False, indent=2))
        print(f"\n配置文件路径: {SERVICE_CONFIG_FILE}")
        sys.exit(0)
    
    # 处理其他服务操作（install, start, stop, remove等）
    try:
        win32serviceutil.HandleCommandLine(FlaskService)
    except Exception as e:
        print(f"错误: {str(e)}")
        print("\n提示:")
        print("1. 确保已安装pywin32: pip install pywin32")
        print("2. 建议安装waitress以获得更好的性能: pip install waitress")
        print("3. 如果安装服务失败，请以管理员身份运行命令提示符")
        print("4. 检查服务是否已存在: sc query FlaskMonitoringApp")
        print("5. 查看服务日志: logs/service.log")
        sys.exit(1)


if __name__ == '__main__':
    main()
