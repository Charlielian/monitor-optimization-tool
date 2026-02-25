# -*- coding: utf-8 -*-
"""
干扰小区数据提取工具 - GUI版本
基于 tkinter 的图形界面，简单易用
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys
from datetime import datetime, timedelta
import queue
import logging

# 导入独立提取器模块
try:
    import standalone_interference_extractor as sie
except ImportError:
    messagebox.showerror("错误", "找不到 standalone_interference_extractor.py 文件！\n请确保该文件在同一目录下。")
    sys.exit(1)


class InterferenceExtractorGUI:
    """干扰小区提取工具GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("干扰小区数据提取工具")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 设置窗口图标（可选）
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # 数据队列，用于线程间通信
        self.log_queue = queue.Queue()
        self.extractor = None
        self.is_logged_in = False
        
        # 初始化日志系统
        self.setup_logging()
        
        # 创建界面
        self.create_widgets()
        
        # 启动日志更新
        self.update_log()
        
        # 加载配置
        self.load_config()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # 1. 登录配置区域
        self.create_login_section(main_frame)
        
        # 2. 查询参数区域
        self.create_query_section(main_frame)
        
        # 3. 操作按钮区域
        self.create_button_section(main_frame)
        
        # 4. 进度条
        self.create_progress_section(main_frame)
        
        # 5. 日志显示区域
        self.create_log_section(main_frame)
        
        # 6. 状态栏
        self.create_status_bar(main_frame)
    
    def create_login_section(self, parent):
        """创建登录配置区域"""
        login_frame = ttk.LabelFrame(parent, text="登录配置", padding="10")
        login_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        login_frame.columnconfigure(1, weight=1)
        
        # 用户名
        ttk.Label(login_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.username_var = tk.StringVar(value=sie.DEFAULT_USERNAME)
        ttk.Entry(login_frame, textvariable=self.username_var, width=30).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # 密码
        ttk.Label(login_frame, text="密码:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.password_var = tk.StringVar(value=sie.DEFAULT_PASSWORD)
        ttk.Entry(login_frame, textvariable=self.password_var, show="*", width=30).grid(
            row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # 登录状态
        self.login_status_var = tk.StringVar(value="未登录")
        status_label = ttk.Label(login_frame, textvariable=self.login_status_var, 
                                foreground="red", font=("Arial", 10, "bold"))
        status_label.grid(row=0, column=2, rowspan=2, padx=10)
    
    def create_query_section(self, parent):
        """创建查询参数区域"""
        query_frame = ttk.LabelFrame(parent, text="查询参数", padding="10")
        query_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        query_frame.columnconfigure(1, weight=1)
        query_frame.columnconfigure(3, weight=1)
        
        # 网络类型
        ttk.Label(query_frame, text="网络类型:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.network_type_var = tk.StringVar(value="5G")
        network_combo = ttk.Combobox(query_frame, textvariable=self.network_type_var, 
                                     values=["5G", "4G", "5G和4G"], state="readonly", width=15)
        network_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 城市
        ttk.Label(query_frame, text="城市:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.city_var = tk.StringVar(value="阳江")
        ttk.Entry(query_frame, textvariable=self.city_var, width=15).grid(
            row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 查询天数
        ttk.Label(query_frame, text="查询天数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.days_var = tk.IntVar(value=7)
        days_spinbox = ttk.Spinbox(query_frame, from_=1, to=30, textvariable=self.days_var, width=15)
        days_spinbox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 只提取干扰小区
        self.only_interfered_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(query_frame, text="只提取干扰小区", 
                       variable=self.only_interfered_var).grid(
            row=1, column=2, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 日期范围显示
        self.date_range_var = tk.StringVar()
        self.update_date_range()
        ttk.Label(query_frame, textvariable=self.date_range_var, 
                 foreground="blue").grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        
        # 绑定天数变化事件
        self.days_var.trace('w', lambda *args: self.update_date_range())
    
    def update_date_range(self):
        """更新日期范围显示"""
        try:
            days = self.days_var.get()
            end_date = datetime.now() - timedelta(days=1)
            start_date = end_date - timedelta(days=days-1)
            date_range = f"查询日期范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
            self.date_range_var.set(date_range)
        except:
            pass
    
    def setup_logging(self):
        """初始化日志系统"""
        # 创建日志目录
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 生成日志文件名（按日期）
        log_filename = datetime.now().strftime("gui_log_%Y%m%d_%H%M%S.log")
        self.log_file_path = os.path.join(log_dir, log_filename)
        
        # 配置日志记录器
        self.logger = logging.getLogger('InterferenceExtractorGUI')
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                     datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
        # 记录启动信息
        self.logger.info("=" * 60)
        self.logger.info("干扰小区数据提取工具 GUI 启动")
        self.logger.info(f"日志文件: {self.log_file_path}")
        self.logger.info("=" * 60)
    
    def create_button_section(self, parent):
        """创建操作按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 登录按钮
        self.login_btn = ttk.Button(button_frame, text="登录", command=self.login, width=15)
        self.login_btn.pack(side=tk.LEFT, padx=5)
        
        # 开始提取按钮
        self.extract_btn = ttk.Button(button_frame, text="开始提取", command=self.start_extract, 
                                      width=15, state=tk.DISABLED)
        self.extract_btn.pack(side=tk.LEFT, padx=5)
        
        # 停止按钮
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_extract, 
                                   width=15, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 打开输出目录按钮
        self.open_dir_btn = ttk.Button(button_frame, text="打开输出目录", 
                                       command=self.open_output_dir, width=15)
        self.open_dir_btn.pack(side=tk.LEFT, padx=5)
        
        # 打开日志文件按钮
        self.open_log_btn = ttk.Button(button_frame, text="打开日志文件", 
                                       command=self.open_log_file, width=15)
        self.open_log_btn.pack(side=tk.LEFT, padx=5)
        
        # 清空日志按钮
        self.clear_log_btn = ttk.Button(button_frame, text="清空日志", 
                                        command=self.clear_log, width=15)
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)
    
    def create_progress_section(self, parent):
        """创建进度条区域"""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        self.progress_label_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.progress_label_var).grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=2)
    
    def create_log_section(self, parent):
        """创建日志显示区域"""
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="5")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                  height=15, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置文本标签颜色
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")

    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 添加日志文件路径显示
        self.log_file_var = tk.StringVar(value="")
        log_file_label = ttk.Label(status_frame, textvariable=self.log_file_var, 
                                   foreground="blue", cursor="hand2")
        log_file_label.pack(side=tk.RIGHT, padx=5)
        log_file_label.bind("<Button-1>", lambda e: self.open_log_file())
    
    def log(self, message, level="INFO"):
        """添加日志到队列并写入文件"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, message, level))
        
        # 同时写入日志文件
        log_level_map = {
            "INFO": logging.INFO,
            "SUCCESS": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        self.logger.log(log_level_map.get(level, logging.INFO), message)
    
    def update_log(self):
        """从队列更新日志显示"""
        try:
            while True:
                timestamp, message, level = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", level)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        
        # 每100ms检查一次
        self.root.after(100, self.update_log)
    
    def clear_log(self):
        """清空日志显示（不清空文件）"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("界面日志已清空（文件日志保留）", "INFO")
    
    def open_log_file(self):
        """打开日志文件"""
        if not os.path.exists(self.log_file_path):
            messagebox.showwarning("警告", "日志文件不存在")
            return
        
        import platform
        system = platform.system()
        
        try:
            if system == "Windows":
                os.startfile(self.log_file_path)
            elif system == "Darwin":  # macOS
                os.system(f'open "{self.log_file_path}"')
            else:  # Linux
                os.system(f'xdg-open "{self.log_file_path}"')
            self.log(f"已打开日志文件: {self.log_file_path}", "SUCCESS")
        except Exception as e:
            self.log(f"打开日志文件失败: {e}", "ERROR")
            messagebox.showerror("错误", f"无法打开日志文件: {self.log_file_path}")
    
    def update_progress(self, value, label=""):
        """更新进度条"""
        self.progress_var.set(value)
        if label:
            self.progress_label_var.set(label)
    
    def update_status(self, message):
        """更新状态栏"""
        self.status_var.set(message)
    
    def open_output_dir(self):
        """打开输出目录"""
        output_dir = os.path.abspath(sie.OUTPUT_DIR)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 根据操作系统打开文件夹
        import platform
        system = platform.system()
        
        try:
            if system == "Windows":
                os.startfile(output_dir)
            elif system == "Darwin":  # macOS
                os.system(f'open "{output_dir}"')
            else:  # Linux
                os.system(f'xdg-open "{output_dir}"')
            self.log(f"已打开输出目录: {output_dir}", "SUCCESS")
        except Exception as e:
            self.log(f"打开目录失败: {e}", "ERROR")
            messagebox.showerror("错误", f"无法打开目录: {output_dir}")
    
    def load_config(self):
        """加载配置"""
        # 可以从配置文件加载，这里使用默认值
        # 更新状态栏显示日志文件路径
        self.log_file_var.set(f"日志: {os.path.basename(self.log_file_path)}")
        pass
    
    def save_config(self):
        """保存配置"""
        # 可以保存到配置文件
        pass

    
    def login(self):
        """执行登录"""
        if self.is_logged_in:
            messagebox.showinfo("提示", "已经登录，无需重复登录")
            return
        
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            messagebox.showwarning("警告", "请输入用户名和密码")
            return
        
        # 禁用登录按钮
        self.login_btn.config(state=tk.DISABLED)
        self.update_status("正在登录...")
        self.log("开始登录...", "INFO")
        
        # 在新线程中执行登录
        thread = threading.Thread(target=self._login_thread, args=(username, password))
        thread.daemon = True
        thread.start()
    
    def _login_thread(self, username, password):
        """登录线程"""
        try:
            # 创建提取器
            self.extractor = sie.InterferenceCellExtractor(username, password)
            
            # 重定向print输出到日志
            original_print = print
            original_input = input
            
            def custom_print(*args, **kwargs):
                message = ' '.join(map(str, args))
                if '✓' in message or '成功' in message:
                    self.log(message, "SUCCESS")
                elif '✗' in message or '失败' in message or '错误' in message:
                    self.log(message, "ERROR")
                elif '⚠' in message or '警告' in message:
                    self.log(message, "WARNING")
                else:
                    self.log(message, "INFO")
            
            def custom_input(prompt=''):
                """自定义input，使用GUI弹窗"""
                self.log(prompt, "WARNING")
                result = self._show_input_dialog(prompt)
                return result if result else ''
            
            # 临时替换print和input
            import builtins
            builtins.print = custom_print
            builtins.input = custom_input
            
            # 执行登录
            self.update_progress(20, "正在连接服务器...")
            success = self.extractor.login()
            
            # 恢复print和input
            builtins.print = original_print
            builtins.input = original_input
            
            if success:
                self.update_progress(50, "登录成功，初始化即席查询...")
                
                # 初始化即席查询
                builtins.print = custom_print
                jxcx_success = self.extractor.init_jxcx()
                builtins.print = original_print
                
                if jxcx_success:
                    self.is_logged_in = True
                    self.update_progress(100, "登录完成")
                    self.log("登录成功！", "SUCCESS")
                    
                    # 更新UI
                    self.root.after(0, self._login_success_ui)
                else:
                    self.log("初始化即席查询失败", "ERROR")
                    self.root.after(0, self._login_failed_ui)
            else:
                self.log("登录失败", "ERROR")
                self.root.after(0, self._login_failed_ui)
                
        except Exception as e:
            self.log(f"登录异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self.root.after(0, self._login_failed_ui)
    
    def _login_success_ui(self):
        """登录成功后更新UI"""
        self.login_status_var.set("已登录")
        self.login_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.NORMAL)
        self.update_status("登录成功，可以开始提取数据")
        messagebox.showinfo("成功", "登录成功！")
    
    def _login_failed_ui(self):
        """登录失败后更新UI"""
        self.login_status_var.set("登录失败")
        self.login_btn.config(state=tk.NORMAL)
        self.update_status("登录失败")
        self.update_progress(0, "登录失败")
        messagebox.showerror("失败", "登录失败，请检查账号密码或网络连接")

    
    def start_extract(self):
        """开始提取数据"""
        if not self.is_logged_in:
            messagebox.showwarning("警告", "请先登录")
            return
        
        # 禁用按钮
        self.extract_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.update_status("正在提取数据...")
        
        # 在新线程中执行提取
        thread = threading.Thread(target=self._extract_thread)
        thread.daemon = True
        thread.start()
    
    def _extract_thread(self):
        """提取数据线程"""
        try:
            network_type = self.network_type_var.get()
            city = self.city_var.get().strip()
            days = self.days_var.get()
            only_interfered = self.only_interfered_var.get()
            
            # 计算日期范围
            end_date = datetime.now() - timedelta(days=1)
            start_date = end_date - timedelta(days=days-1)
            
            # 确定要提取的网络类型
            if network_type == "5G和4G":
                network_types = ['5G', '4G']
            else:
                network_types = [network_type]
            
            total_types = len(network_types)
            
            # 重定向print
            import builtins
            original_print = print
            def custom_print(*args, **kwargs):
                message = ' '.join(map(str, args))
                if '✓' in message or '成功' in message:
                    self.log(message, "SUCCESS")
                elif '✗' in message or '失败' in message or '错误' in message:
                    self.log(message, "ERROR")
                elif '⚠' in message or '警告' in message:
                    self.log(message, "WARNING")
                else:
                    self.log(message, "INFO")
            
            builtins.print = custom_print
            
            # 提取数据
            for idx, net_type in enumerate(network_types):
                progress_base = (idx / total_types) * 100
                progress_step = 100 / total_types
                
                self.update_progress(progress_base, f"正在提取 {net_type} 数据...")
                self.log(f"开始提取 {net_type} 干扰小区数据", "INFO")
                
                df = self.extractor.extract_data(
                    network_type=net_type,
                    start_date=start_date,
                    end_date=end_date,
                    city=city,
                    only_interfered=only_interfered
                )
                
                if not df.empty:
                    self.update_progress(progress_base + progress_step * 0.8, 
                                       f"正在保存 {net_type} 数据...")
                    filepath = self.extractor.save_to_excel(df, network_type=net_type)
                    
                    if filepath:
                        self.log(f"{net_type} 数据提取完成，共 {len(df)} 条记录", "SUCCESS")
                    else:
                        self.log(f"{net_type} 数据保存失败", "ERROR")
                else:
                    self.log(f"{net_type} 未查询到数据", "WARNING")
            
            # 恢复print
            builtins.print = original_print
            
            self.update_progress(100, "数据提取完成")
            self.log("所有数据提取完成！", "SUCCESS")
            self.root.after(0, self._extract_success_ui)
            
        except Exception as e:
            self.log(f"提取数据异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self.root.after(0, self._extract_failed_ui)
    
    def _extract_success_ui(self):
        """提取成功后更新UI"""
        self.extract_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("数据提取完成")
        messagebox.showinfo("成功", "数据提取完成！\n文件已保存到输出目录。")
    
    def _extract_failed_ui(self):
        """提取失败后更新UI"""
        self.extract_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("数据提取失败")
        self.update_progress(0, "提取失败")
        messagebox.showerror("失败", "数据提取失败，请查看日志")
    
    def stop_extract(self):
        """停止提取（暂未实现完整功能）"""
        messagebox.showinfo("提示", "停止功能开发中...")
        self.stop_btn.config(state=tk.DISABLED)
    
    def _show_input_dialog(self, prompt):
        """显示输入对话框（在主线程中执行）"""
        result = {'value': None, 'done': False}
        
        def show_dialog():
            # 创建输入对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("输入验证码")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            
            # 提示信息
            ttk.Label(dialog, text=prompt, wraplength=350, 
                     font=("Arial", 10)).pack(pady=20, padx=20)
            
            # 如果是验证码，显示图片路径提示
            if '验证码' in prompt and 'captcha_images' in prompt:
                img_path = prompt.split('并输入验证码')[0].split('请查看图片 ')[1] if '请查看图片' in prompt else ''
                if img_path:
                    ttk.Label(dialog, text=f"验证码图片位置:\n{img_path}", 
                             foreground="blue", wraplength=350).pack(pady=5)
                    
                    # 添加打开图片按钮
                    def open_image():
                        import platform
                        system = platform.system()
                        try:
                            if system == "Windows":
                                os.startfile(img_path)
                            elif system == "Darwin":
                                os.system(f'open "{img_path}"')
                            else:
                                os.system(f'xdg-open "{img_path}"')
                        except:
                            pass
                    
                    ttk.Button(dialog, text="打开验证码图片", 
                              command=open_image).pack(pady=5)
            
            # 输入框
            input_var = tk.StringVar()
            entry = ttk.Entry(dialog, textvariable=input_var, width=30, font=("Arial", 12))
            entry.pack(pady=10)
            entry.focus_set()
            
            # 按钮框架
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=20)
            
            def on_ok():
                result['value'] = input_var.get()
                result['done'] = True
                dialog.destroy()
            
            def on_cancel():
                result['value'] = ''
                result['done'] = True
                dialog.destroy()
            
            # 确定和取消按钮
            ttk.Button(btn_frame, text="确定", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="取消", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
            
            # 绑定回车键
            entry.bind('<Return>', lambda e: on_ok())
            
            # 等待窗口关闭
            dialog.wait_window()
        
        # 在主线程中显示对话框
        self.root.after(0, show_dialog)
        
        # 等待用户输入
        while not result['done']:
            import time
            time.sleep(0.1)
        
        return result['value']


def main():
    """主函数"""
    root = tk.Tk()
    app = InterferenceExtractorGUI(root)
    
    # 程序退出时记录日志
    def on_closing():
        app.logger.info("=" * 60)
        app.logger.info("干扰小区数据提取工具 GUI 关闭")
        app.logger.info("=" * 60)
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
