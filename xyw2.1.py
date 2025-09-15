import tkinter as tk
from tkinter import ttk, messagebox
import requests
import time
from datetime import datetime
import urllib3
import sys
import os
import winreg
from PIL import Image
import pystray
import threading
import json

urllib3.disable_warnings()

VERSION = "2.1"
USERNAME = "" 
PASSWORD = ""
OPERATORS = {
    "中国移动": "@cmcc",
    "中国联通": "@cucc",
    "中国电信": "@ctcc",
    "免费校园网": ""
}
LOGIN_URL = "http://172.16.1.11/drcom/login"
TEST_URL = "http://www.baidu.com"

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, radius=5, bg='#1a73e8', fg='white', font=('Microsoft YaHei UI', 8), **kwargs):
        super().__init__(parent, bg=parent['bg'], highlightthickness=0, **kwargs)
        self.bg = bg
        self.fg = fg
        self.hover_fg = '#1a1a1a'
        self.command = command
        self.radius = radius
        self.font = font
        self.text = text
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
        
        # 添加配置更改事件绑定
        self.bind('<Configure>', self._on_configure)
        
        # 初始绘制
        self._draw()
        
    def _on_configure(self, event):
        # 当控件大小改变时重新绘制
        self._draw()
        
    def _draw(self, hover=False):
        self.delete('all')
        color = '#e5e7eb' if hover else self.bg  # 悬停时背景色略深
        text_color = self.hover_fg if hover else self.fg
        
        self.create_rounded_rect(0, 0, self.winfo_width(), self.winfo_height(), 
                               self.radius, fill=color)
        
        self.create_text(self.winfo_width()/2, self.winfo_height()/2,
                        text=self.text, fill=text_color, font=self.font)
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _on_enter(self, e):
        self._draw(hover=True)
    
    def _on_leave(self, e):
        self._draw(hover=False)
    
    def _on_click(self, e):
        if self.command:
            self.command()

    def configure(self, **kwargs):
        if 'text' in kwargs:
            self.text = kwargs.pop('text')
        super().configure(**kwargs)
        self._draw()

class NetworkLoginGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("校园网自动登录")
        self.root.geometry("450x730")
        
        # 修改配置文件路径到软件目录
        if getattr(sys, 'frozen', False):
            self.config_path = os.path.join(os.path.dirname(sys.executable), 'config.json')
        else:
            self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        
        # 加载保存的配置
        self.load_config()
        
        # 检查是否为静默启动
        if len(sys.argv) > 1 and sys.argv[1] == '--silent':
            self.root.withdraw()  # 隐藏主窗口
            if self.saved_username and self.saved_password:  # 如果有保存的账号信息
                self.root.after(1000, self.auto_start)  # 延迟1秒后自动开始连接

        self.root.configure(bg='white')
        
        # 获取图标文件的路径
        if getattr(sys, 'frozen', False):
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            
        self.icon_path = os.path.join(application_path, 'favicon.ico')
        
        # 创建主框架和GUI组件
        self.main_frame = tk.Frame(self.root, bg='white', padx=24, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 初始化变量
        self.autostart_var = tk.BooleanVar()
        self.save_account_var = tk.BooleanVar(value=True)
        self.is_running = False
        self.log_text = []
        
        # 创建界面元素（先创建所有GUI组件）
        self.create_widgets()
        
        # 设置窗口图标
        try:
            icon = tk.PhotoImage(file=self.icon_path)
            self.root.iconphoto(True, icon)
        except Exception as e:
            self.log(f"设置窗口图标失败: {str(e)}")
        
        # 添加系统托盘支持
        self.create_tray_icon()
        
        # 添加窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 检查是否已设置自启动
        self.check_autostart_status()

        # 如果是 Windows 系统，确保配置文件是隐藏的
        if os.name == 'nt' and os.path.exists(self.config_path):
            import ctypes
            try:
                ctypes.windll.kernel32.SetFileAttributesW(self.config_path, 2)  # 2 表示隐藏属性
            except:
                pass

    def create_widgets(self):
        title_label = tk.Label(self.main_frame, 
                             text="校园网自动登录工具", 
                             font=('Microsoft YaHei UI', 20, 'bold'),
                             bg='white',
                             fg='#2c3e50')
        title_label.pack(pady=(0, 24))

        input_frame = tk.Frame(self.main_frame, bg='white')
        input_frame.pack(fill=tk.X, pady=4)
        
        entry_style = {
            'font': ('Microsoft YaHei UI', 9),
            'relief': 'flat',
            'bg': '#f7f9fc',
            'bd': 0,
            'highlightthickness': 0
        }
        
        label_style = {
            'font': ('Microsoft YaHei UI', 9),
            'bg': 'white',
            'fg': '#000000'
        }

        # 减小输入区域的间距
        tk.Label(input_frame, text="账号", **label_style).pack(anchor='w', pady=(4,2))
        self.username_entry = tk.Entry(input_frame, **entry_style)
        self.username_entry.insert(0, self.saved_username)
        self.username_entry.pack(fill=tk.X, ipady=6)
        self._add_modern_entry_effects(self.username_entry)

        tk.Label(input_frame, text="密码", **label_style).pack(anchor='w', pady=(12,2))
        self.password_entry = tk.Entry(input_frame, show="•", **entry_style)
        self.password_entry.insert(0, self.saved_password)
        self.password_entry.pack(fill=tk.X, ipady=6)
        self._add_modern_entry_effects(self.password_entry)

        tk.Label(input_frame, text="运营商", **label_style).pack(anchor='w', pady=(12,2))
        self.operator_var = tk.StringVar()
        self.operator_combo = ttk.Combobox(input_frame, 
                                         textvariable=self.operator_var,
                                         values=list(OPERATORS.keys()),
                                         font=('Microsoft YaHei UI', 9),
                                         state='readonly')
        self.operator_combo.set(self.saved_operator)
        self.operator_combo.pack(fill=tk.X, ipady=2)

        tk.Label(input_frame, text="检查间隔（秒）", **label_style).pack(anchor='w', pady=(12,2))
        self.interval_var = tk.StringVar(value=self.saved_interval)
        self.interval_entry = tk.Entry(input_frame, 
                                     textvariable=self.interval_var,
                                     **entry_style)
        self.interval_entry.pack(fill=tk.X, ipady=6)
        self._add_modern_entry_effects(self.interval_entry)

        # 在输入框下方添加保存账号选项
        save_frame = tk.Frame(input_frame, bg='white')
        save_frame.pack(fill=tk.X, pady=(8,0))
        
        save_checkbox = tk.Checkbutton(save_frame,
                                     text="保存账号信息",
                                     variable=self.save_account_var,
                                     bg='white',
                                     fg='#000000',
                                     font=('Microsoft YaHei UI', 9))
        save_checkbox.pack(side=tk.LEFT)

        log_frame = tk.Frame(self.main_frame, bg='white')
        log_frame.pack(fill=tk.X, pady=20)
        
        # 移除滚动条相关代码，直接创建文本框
        self.log_area = tk.Text(log_frame, 
                               height=8,
                               font=('Microsoft YaHei UI', 9),
                               bg='#f7f9fc',
                               relief='flat',
                               bd=0,
                               padx=12,
                               pady=12)
        self.log_area.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        self._add_modern_text_effects(self.log_area)

        button_frame = tk.Frame(self.main_frame, bg='white')
        button_frame.pack(pady=12)

        self.toggle_button = RoundedButton(button_frame, 
                                         text="开始自动连接",
                                         command=self.toggle_monitoring,
                                         width=120, height=32,
                                         bg='#1246ff',
                                         fg='#ffffff',  # 使用白色文字
                                         font=('Microsoft YaHei UI', 9))
        self.toggle_button.pack(side=tk.LEFT, padx=6)

        self.settings_button = RoundedButton(button_frame,
                                           text="设置",
                                           command=self.show_settings,
                                           width=120, height=32,
                                           bg='#1246ff',  # 使用协会蓝背景
                                           fg='#ffffff',  # 使用白色文字
                                           font=('Microsoft YaHei UI', 9))
        self.settings_button.pack(side=tk.LEFT, padx=6)

        self.eica_button = RoundedButton(button_frame,
                                       text="嵌入式智控协会",
                                       command=self.open_eica,
                                       width=120, height=32,
                                       bg='#1246ff',  # 使用协会蓝背景
                                       fg='#ffffff',  # 使用白色文字
                                       font=('Microsoft YaHei UI', 9))
        self.eica_button.pack(side=tk.LEFT, padx=6)

        bottom_frame = tk.Frame(self.main_frame, bg='white')
        bottom_frame.pack(fill=tk.X, pady=(16,0))

        author_label = tk.Label(bottom_frame,
                              text="@小东同学",
                              font=('Microsoft YaHei UI', 12),
                              bg='white',
                              fg='#94a3b8')
        author_label.pack(pady=6)

    def _add_modern_entry_effects(self, entry):
        """现代输入框效果"""
        def on_enter(e):
            e.widget.configure(bg='#edf2f7')
            
        def on_leave(e):
            if e.widget != self.root.focus_get():
                e.widget.configure(bg='#f7f9fc')
                
        entry.bind('<Enter>', on_enter)
        entry.bind('<Leave>', on_leave)
        entry.bind('<FocusIn>', lambda e: e.widget.configure(bg='#edf2f7'))
        entry.bind('<FocusOut>', lambda e: e.widget.configure(bg='#f7f9fc'))

    def _add_modern_text_effects(self, text_widget):
        """现代文本框效果"""
        text_widget.configure(font=('Microsoft YaHei UI', 9))
        text_widget.configure(selectbackground='#93c5fd')
        text_widget.configure(selectforeground='black')
        text_widget.configure(spacing1=2)

    def log(self, message):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{current_time}] {message}\n"
        self.log_area.insert(tk.END, log_message)
        self.log_area.see(tk.END)

    def check_connection(self):
        """检查是否能访问百度，并验证返回内容"""
        try:
            start_time = time.time()
            response = requests.get(TEST_URL, timeout=3)  # 设置超时时间为3秒
            response_time = time.time() - start_time
            # 检查是否成功获取内容，并验证返回的内容确实是百度的页面
            if (response.status_code == 200 and 
                len(response.text) > 0 and 
                ('baidu' in response.text.lower() or '百度' in response.text)):
                self.log(f"网络延迟: {response_time:.2f}秒")
                return True
            
            self.log("好像校园网断了！！！尝试重新登录...")
            return False
        except requests.exceptions.Timeout:
            self.log("请求超时（>3秒）")
            return False
        except requests.exceptions.ConnectionError:
            self.log("连接错误")
            return False
        except Exception as e:
            self.log(f"网络请求失败: {str(e)}")
            return False

    def campus_network_login(self):
        """校园网登录"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        operator = OPERATORS[self.operator_combo.get()]
        
        params = {
            'callback': 'dr1003',
            'DDDDD': username + operator if operator else username,
            'upass': password,
            '0MKKey': '123456',
            'R1': '0',
            'R2': '',
            'R3': '0',
            'R6': '0',
            'para': '00',
            'v6ip': '',
            'terminal_type': '1',
            'lang': 'zh-cn',
            'jsVersion': '4.1.3',
            'v': '2282'
        }
        
        try:
            # 先检查是否能访问登录服务器
            try:
                requests.get("http://172.16.1.11", timeout=3)
            except:
                self.log("无法连接到校园网认证服务器")
                return False

            # 尝试登录
            response = requests.get(LOGIN_URL, params=params, verify=False, timeout=5)
                
            # 检查是否包含 "result":1
            if '"result":1' in response.text:
                return True
            elif 'already' in response.text.lower():
                self.log("账号已在线")
                return True
            elif 'password' in response.text.lower():
                self.log("用户名或密码错误")
                return False
            else:
                self.log("登录失败，检查账号密码运行商是否正确！")
                return False
            
        except requests.exceptions.Timeout:
            self.log("登录请求超时")
            return False
        except requests.exceptions.ConnectionError:
            self.log("网络连接错误")
            return False
        except Exception as e:
            self.log(f"登录异常: {str(e)}")
            return False

    def monitoring_loop(self):
        if not self.is_running:
            return

        if not self.check_connection():
            self.retry_login(0)
        else:
            self.log("网络连接正常")
            self.schedule_next_check()

    def retry_login(self, attempt):
        if not self.is_running or attempt >= 3:
            if attempt >= 3:
                self.log("多次登录尝试均失败，请停止自动连接后检查账号密码运行商是否正确！再重新开启自动连接！")
            self.schedule_next_check()
            return
            
        if self.campus_network_login():
            self.log("重新登录成功！")
            self.schedule_next_check()
        else:
            self.log(f"第{attempt+1}次登录尝试失败，等待5秒后重试...")
            self.root.after(5000, lambda: self.retry_login(attempt + 1))

    def schedule_next_check(self):
        """安排下一次检查"""
        if not self.is_running:
            return
            
        try:
            interval = int(self.interval_var.get())
            if interval < 5:  # 检查秒数而不是毫秒
                messagebox.showwarning("提示", "检查间隔不能小于5秒！已自动调整为5秒。")
                interval = 5
                self.interval_var.set("5")
            interval = interval * 1000  # 转换为毫秒
        except ValueError:
            interval = 30000  # 默认30秒
            self.interval_var.set("30")

        self.root.after(interval, self.monitoring_loop)

    def toggle_monitoring(self):
        # 检查账号密码是否已输入
        if not self.username_entry.get() or not self.password_entry.get():
            messagebox.showwarning("提示", "请输入账号和密码！")
            return
            
        if not self.is_running:
            self.is_running = True
            self.toggle_button.configure(text="停止连接")
            self.log("开始自动连接...")
            # 保存配置
            self.save_config()
            self.monitoring_loop()
        else:
            self.is_running = False
            self.toggle_button.configure(text="开始连接")
            self.log("停止自动连接...")

    def open_eica(self):
        """打开EICA网站"""
        import webbrowser
        webbrowser.open('http://www.eica.fun')

    def create_tray_icon(self):
        try:
            image = Image.open(self.icon_path)
            menu = (
                pystray.MenuItem("显示主窗口", lambda: self.root.deiconify()),
                pystray.MenuItem("设置", lambda: (self.root.deiconify(), self.show_settings())),
                pystray.MenuItem("退出", lambda: (setattr(self, 'is_running', False), 
                                              self.icon.stop(), 
                                              self.root.destroy()))
            )
            
            def on_click(icon, button):
                self.root.after(0, self.root.deiconify)
            
            self.icon = pystray.Icon(
                "name",
                image,
                "校园网自动登录",
                menu=menu
            )
            
            self.icon.on_click = lambda icon: self.root.after(0, self.root.deiconify)
            
            threading.Thread(target=self.icon.run, daemon=True).start()
        except Exception as e:
            self.log(f"加载图标文件失败: {str(e)}")

    def on_closing(self):
        """窗口关闭时最小化到系统托盘"""
        self.root.withdraw()  # 只隐藏窗口，不停止托盘图标

    def toggle_autostart(self):
        """切换开机自启动状态"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "CampusNetworkLogin"
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            if self.autostart_var.get():
                # 添加到自启动，增加静默启动参数
                app_path = sys.executable
                if hasattr(sys, '_MEIPASS'):
                    app_path = os.path.abspath(sys.argv[0])
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{app_path}" --silent')
                self.log("已添加到开机自启动")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    self.log("已取消开机自启动")
                except WindowsError:
                    pass
                    
            winreg.CloseKey(key)
        except Exception as e:
            self.log(f"设置开机自启动失败: {str(e)}")
            messagebox.showerror("错误", "设置开机自启动失败")

    def check_autostart_status(self):
        """检查是否已设置开机自启动"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "CampusNetworkLogin"
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, app_name)
                self.autostart_var.set(True)
            except WindowsError:
                self.autostart_var.set(False)
            winreg.CloseKey(key)
        except WindowsError:
            self.autostart_var.set(False)

    def show_settings(self):
        """显示设置窗口"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("300x300")
        settings_window.configure(bg='#f0f2f5')
        
        # 设置窗口为模态
        settings_window.grab_set()
        
        # 居中显示
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (settings_window.winfo_screenheight() // 2) - (height // 2)
        settings_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建设置选项
        frame = tk.Frame(settings_window, bg='#f0f2f5', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 自启动选项
        self.autostart_check = tk.Checkbutton(frame,
                                            text="开机自启动",
                                            variable=self.autostart_var,
                                            command=self.toggle_autostart,
                                            font=('Microsoft YaHei UI', 10),
                                            bg='#f0f2f5',
                                            fg='#5f6368')
        self.autostart_check.pack(pady=10)

        # 添加作者信息
        author_label = tk.Label(frame,
                              text="@小东同学",
                              font=('Microsoft YaHei UI', 8),
                              bg='#f0f2f5',
                              fg='#5f6368')
        author_label.pack(pady=2)

    def load_config(self):
        """加载保存的配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.saved_username = config.get('username', '')
                    self.saved_password = config.get('password', '')
                    self.saved_operator = config.get('operator', '免费校园网')
                    self.saved_interval = config.get('interval', '30')
                    # 检查版本更新提示
                    if config.get('version', '') != VERSION:
                        self.show_update_dialog()
                        config['version'] = VERSION
                        with open(self.config_path, 'w', encoding='utf-8') as f:
                            json.dump(config, f, ensure_ascii=False, indent=2)
            else:
                self.saved_username = USERNAME
                self.saved_password = PASSWORD
                self.saved_operator = "免费校园网"
                self.saved_interval = "30"
                # 新用户首次打开，创建配置文件并显示更新弹窗
                config = {
                    'username': self.saved_username,
                    'password': self.saved_password,
                    'operator': self.saved_operator,
                    'interval': self.saved_interval,
                    'version': VERSION
                }
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                self.show_update_dialog()
        except Exception as e:
            self.saved_username = USERNAME
            self.saved_password = PASSWORD
            self.saved_operator = "免费校园网"
            self.saved_interval = "30"
            self.log(f"加载配置失败: {str(e)}")

    def show_update_dialog(self):
        """显示更新弹窗"""
        update_window = tk.Toplevel(self.root)
        update_window.title(f"更新说明 v{VERSION}")  # 添加版本号
        update_window.geometry("450x450")
        update_window.configure(bg='white')
        
        # 设置窗口为模态
        update_window.grab_set()
        
        # 居中显示
        update_window.update_idletasks()
        width = update_window.winfo_width()
        height = update_window.winfo_height()
        x = (update_window.winfo_screenwidth() // 2) - (width // 2)
        y = (update_window.winfo_screenheight() // 2) - (height // 2)
        update_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建内容框架
        frame = tk.Frame(update_window, bg='white', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title = tk.Label(frame,
                        text=f"欢迎使用校园网自动登录工具 v{VERSION}",
                        font=('Microsoft YaHei UI', 16, 'bold'),
                        bg='white',
                        fg='#1246ff')
        title.pack(pady=(0, 20))
        
        # 更新内容
        update_text = """更新内容：（本次弹窗只显示一次）
1. 全新界面设计，更现代化的UI体验
2. 添加系统托盘功能，最小化后继续运行
3. 支持开机自启动设置
4. 添加配置保存功能
5. 添加开启自启动后静默启动功能
        
使用说明：
• 填写账号密码和运营商信息后点击"开始自动连接"即可
• 保存账号信息后，下次启动会自动使用上次保存的账号信息
• 保存的账号信息在软件对应路径，名为config.json(隐藏文件)

@小东同学
        """
        
        text_widget = tk.Text(frame,
                            wrap=tk.WORD,
                            height=10,
                            font=('Microsoft YaHei UI', 10),
                            bg='white',
                            relief='flat',
                            padx=10,
                            pady=10)
        text_widget.insert('1.0', update_text)
        text_widget.configure(state='disabled')
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 确认按钮
        confirm_button = RoundedButton(frame,
                                     text="我知道了",
                                     command=update_window.destroy,
                                     width=100,
                                     height=32,
                                     bg='#1246ff',
                                     fg='white',
                                     font=('Microsoft YaHei UI', 9))
        confirm_button.pack(pady=(20, 0))

    def save_config(self):
        """保存配置到文件"""
        if not self.save_account_var.get():
            return
            
        try:
            # 如果文件存在，先读取现有配置
            existing_config = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                except:
                    pass

            # 更新配置
            config = {
                'username': self.username_entry.get(),
                'password': self.password_entry.get(),
                'operator': self.operator_combo.get(),
                'interval': self.interval_var.get(),
                'version': VERSION
            }

            # 合并现有配置和新配置
            existing_config.update(config)

            # 使用临时文件方式保存
            import tempfile
            import shutil
            
            # 在同一目录创建临时文件
            temp_dir = os.path.dirname(self.config_path)
            temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir, prefix='config_', suffix='.tmp')
            
            try:
                # 写入临时文件
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                    json.dump(existing_config, temp_file, ensure_ascii=False, indent=2)
                
                # 如果原配置文件存在且是隐藏文件，先取消隐藏
                if os.path.exists(self.config_path) and os.name == 'nt':
                    import ctypes
                    try:
                        attrs = ctypes.windll.kernel32.GetFileAttributesW(self.config_path)
                        if attrs & 2:  # 检查是否为隐藏文件
                            ctypes.windll.kernel32.SetFileAttributesW(self.config_path, attrs & ~2)
                    except:
                        pass
                
                # 替换原文件
                shutil.move(temp_path, self.config_path)
                
                # 设置为隐藏文件
                if os.name == 'nt':
                    import ctypes
                    try:
                        ctypes.windll.kernel32.SetFileAttributesW(self.config_path, 2)
                    except:
                        pass
                    
            except Exception as e:
                # 如果出错，尝试清理临时文件
                try:
                    os.remove(temp_path)
                except:
                    pass
                raise e
            
        except Exception as e:
            self.log(f"保存配置失败: {str(e)}")
            # 如果保存失败，尝试使用用户目录
            try:
                backup_path = os.path.join(os.path.expanduser('~'), 'config.json')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_config, f, ensure_ascii=False, indent=2)
                self.log(f"配置已保存到备用位置: {backup_path}")
            except:
                pass

    def auto_start(self):
        """自动开始连接"""
        if not self.is_running:
            self.toggle_monitoring()  # 开始自动连接

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkLoginGUI(root)
    root.mainloop()
