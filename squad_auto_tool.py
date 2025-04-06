import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import keyboard
import threading
import time
import win32gui
import win32clipboard
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw, ImageFont
import sys
import os
import watchdog.observers
from watchdog.events import FileSystemEventHandler
import logging
import re
from typing import Optional, Dict

# 配置常量
APP_NAME = "Squad战术小队工具"
VERSION = "v2.3"
DEFAULT_SQUAD_NAME = "TANK"
LOG_PATTERNS = {
    "map_loaded": r"Bringing World .* up for play",
    "faction_loaded": r"Success to load FactionSetup .* for team \d+ !",
    "teamstate_valid": r"Loading requirement TeamState Valid finished",
    "loading_screen_hidden": r"Hiding loading screen",
}
LOG_FILE_PATH = os.path.expandvars(r"%LOCALAPPDATA%\SquadGame\Saved\Logs\SquadGame.log")
HOTKEY = "F9"
BG_COLOR = "#2c3e50"
FG_COLOR = "#ecf0f1"
FONT_NAME = "微软雅黑"
TEXT_BG = "#34495e"

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("squad_tool.log")]
)

class ClipboardContext:
    """剪贴板上下文管理器"""
    def __enter__(self):
        win32clipboard.OpenClipboard()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        win32clipboard.CloseClipboard()

class LogMonitor(FileSystemEventHandler):
    """日志文件监控处理器"""
    def __init__(self, callback: callable, patterns: Dict[str, str]):
        super().__init__()
        self.callback = callback
        self.patterns = {name: re.compile(pattern) for name, pattern in patterns.items()}
        self.last_position = 0
        self._stop_event = threading.Event()
        self.last_trigger_time = 0
        self.trigger_cooldown = 5  # 触发冷却时间(秒)

    def on_modified(self, event):
        if self._stop_event.is_set():
            return

        if not event.is_directory and event.src_path.endswith("SquadGame.log"):
            try:
                with open(event.src_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(self.last_position)
                    new_lines = f.readlines()
                    self.last_position = f.tell()

                    current_time = time.time()
                    # 检查最新日志条目
                    for line in reversed(new_lines):
                        for name, pattern in self.patterns.items():
                            if pattern.search(line):
                                # 检查冷却时间
                                if current_time - self.last_trigger_time > self.trigger_cooldown:
                                    self.last_trigger_time = current_time
                                    logging.info(f"检测到{name}事件: %s", line.strip())
                                    self.callback(name, line.strip())
                                break
            except Exception as e:
                logging.error("日志监控错误: %s", str(e))

    def stop(self):
        self._stop_event.set()

class SquadAutoTool:
    """主应用程序类"""
    def __init__(self):
        self.root = self._setup_gui()
        self.running = False
        self.squad_name = DEFAULT_SQUAD_NAME
        self.log_observer: Optional[watchdog.observers.Observer] = None
        self.tray_icon: Optional[Icon] = None
        self.status_var = tk.StringVar(value="准备就绪")
        self.trigger_count = 0
        self.last_trigger_type = ""

        self._init_ui()
        self._init_tray()
        self._prepare_clipboard()
        self._register_hotkey()

    def _setup_gui(self) -> tk.Tk:
        """初始化GUI界面"""
        root = tk.Tk()
        root.title(f"{APP_NAME} {VERSION}")
        root.geometry("600x600")
        root.resizable(False, False)
        root.configure(bg=BG_COLOR)
        self._set_win32_app_id()
        root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        return root

    def _set_win32_app_id(self):
        """设置Windows应用ID"""
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{APP_NAME}.{VERSION}")
            except Exception as e:
                logging.warning("无法设置任务栏图标: %s", str(e))

    def _init_ui(self):
        """初始化用户界面组件"""
        style = ttk.Style()
        style.theme_use("clam")
        self._configure_styles(style)

        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="SQUAD 战术小队精准抢车工具",
            font=(FONT_NAME, 12, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # 控制面板框架
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))

        # 小队名称输入
        ttk.Label(control_frame, text="小队名称:").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_squad = ttk.Entry(control_frame, width=20)
        self.entry_squad.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.entry_squad.insert(0, self.squad_name)
        self.entry_squad.bind("<KeyRelease>", lambda e: self._update_clipboard())

        # 状态显示
        status_label = ttk.Label(control_frame, textvariable=self.status_var, font=(FONT_NAME, 9))
        status_label.grid(row=1, column=0, columnspan=2, pady=15)

        # 热键提示
        hotkey_frame = ttk.Frame(control_frame)
        hotkey_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Label(hotkey_frame, text=f"热键控制: {HOTKEY} 启动/停止", font=(FONT_NAME, 9)).pack()
        ttk.Label(hotkey_frame, text="当前模式: 精准触发模式", font=(FONT_NAME, 9)).pack()

        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding=10)
        log_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=70,
            height=15,
            bg=TEXT_BG,
            fg=FG_COLOR,
            font=(FONT_NAME, 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 添加日志处理器
        self._setup_log_handler()

        # 版权信息
        ttk.Label(
            main_frame,
            text=f"© 2025 Squad抢车工具 by 鱼见Uomi 测试版 | {VERSION}",
            font=(FONT_NAME, 8)
        ).grid(row=4, column=0, columnspan=2, pady=(20, 0))

    def _configure_styles(self, style: ttk.Style):
        """配置UI样式"""
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=(FONT_NAME, 10))
        style.configure("TEntry", fieldbackground=TEXT_BG, foreground=FG_COLOR)
        style.configure("TLabelframe", background=BG_COLOR, foreground=FG_COLOR)

    def _setup_log_handler(self):
        """设置自定义日志处理器"""
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.configure(state="normal")
                self.text_widget.insert(tk.END, msg + "\n")
                self.text_widget.configure(state="disabled")
                self.text_widget.see(tk.END)

        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(text_handler)

    def _init_tray(self):
        """初始化系统托盘图标"""
        def create_image():
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            dc = ImageDraw.Draw(image)
            for i in range(64):
                dc.line([(i, 0), (i, 64)], fill=(40, 116, 166, int(255 * (i / 64))))
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            dc.text((12, 15), "S", font=font, fill=(255, 255, 255, 255))
            return image

        menu = Menu(
            MenuItem("显示主界面", self.show_window),
            MenuItem("退出", self.quit_app)
        )
        self.tray_icon = Icon(
            "squad_tool",
            create_image(),
            f"{APP_NAME} {VERSION}",
            menu
        )
        threading.Thread(
            target=self.tray_icon.run,
            daemon=True
        ).start()

    def _register_hotkey(self):
        """注册热键"""
        try:
            keyboard.add_hotkey(HOTKEY, self.toggle_operation)
            self._update_status("就绪状态 (F9控制)")
            logging.info("热键 %s 已注册", HOTKEY)
        except Exception as e:
            logging.error("热键注册失败: %s", str(e))
            self._update_status("热键注册失败")

    def _update_clipboard(self):
        """更新剪贴板内容"""
        self.squad_name = self.entry_squad.get().strip()
        cmd = f"createsquad {self.squad_name} 1"
        try:
            with ClipboardContext():
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(cmd)
            logging.info("剪贴板已更新: %s", cmd)
        except Exception as e:
            logging.error("剪贴板操作失败: %s", str(e))
            messagebox.showerror("错误", "无法访问剪贴板！")

    def _prepare_clipboard(self):
        """初始化剪贴板内容"""
        cmd = f"createsquad {self.squad_name} 1"
        try:
            with ClipboardContext():
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(cmd)
            logging.info("初始化剪贴板: %s", cmd)
        except Exception as e:
            logging.error("剪贴板初始化失败: %s", str(e))

    def toggle_operation(self):
        """切换操作状态"""
        if not self.running:
            self._validate_and_start()
        else:
            self._stop_operation()

    def _validate_and_start(self):
        """验证输入并启动"""
        self.squad_name = self.entry_squad.get().strip()
        if not self.squad_name:
            messagebox.showerror("错误", "请输入有效的小队名称！")
            return

        self._start_precise_mode()

    def _start_precise_mode(self):
        """启动精准模式"""
        if not os.path.exists(LOG_FILE_PATH):
            messagebox.showerror("错误", f"未找到游戏日志文件:\n{LOG_FILE_PATH}")
            return

        self.running = True
        self.trigger_count = 0
        self._setup_log_monitor()
        self._update_status("精准模式监控中...")
        logging.info("启动精准模式，开始监控日志文件")

    def _setup_log_monitor(self):
        """配置日志监控"""
        try:
            event_handler = LogMonitor(self._execute_precise_operation, LOG_PATTERNS)
            self.log_observer = watchdog.observers.Observer()
            self.log_observer.schedule(
                event_handler,
                path=os.path.dirname(LOG_FILE_PATH),
                recursive=False
            )
            self.log_observer.start()
        except Exception as e:
            self.running = False
            messagebox.showerror("错误", f"无法启动日志监控:\n{str(e)}")
            logging.error("日志监控启动失败: %s", str(e))
            self._update_status("监控启动失败")

    def _execute_precise_operation(self, trigger_type: str, log_line: str):
        """执行精准模式操作"""
        try:
            if self._is_game_focused():
                self.trigger_count += 1
                self.last_trigger_type = trigger_type
                self._send_commands()
                status = f"触发成功 ({trigger_type}) #{self.trigger_count}"
                self._update_status(status)
                logging.info("精准模式触发成功 - 类型: %s, 日志: %s", trigger_type, log_line)
        except Exception as e:
            logging.error("精准模式执行失败: %s", str(e))
            self._update_status("执行出错")

    def _send_commands(self):
        """发送命令序列"""
        import pyautogui  # 延迟导入减少启动时间
        pyautogui.press("`")
        time.sleep(0.01)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.01)
        pyautogui.press("enter")

    def _is_game_focused(self) -> bool:
        """检查游戏窗口是否处于焦点状态"""
        try:
            return "Squad" in win32gui.GetWindowText(win32gui.GetForegroundWindow())
        except Exception as e:
            logging.warning("窗口焦点检测失败: %s", str(e))
            return False

    def _stop_operation(self):
        """停止所有操作"""
        if self.running:
            self.running = False
            self._stop_log_monitor()
            status = f"已停止 (共触发{self.trigger_count}次)" if self.trigger_count > 0 else "已停止"
            self._update_status(status)
            logging.info("操作已停止")

    def _stop_log_monitor(self):
        """停止日志监控"""
        if self.log_observer:
            try:
                self.log_observer.stop()
                self.log_observer.join(timeout=5)
                logging.info("日志监控已停止")
            except Exception as e:
                logging.error("停止日志监控失败: %s", str(e))
            finally:
                self.log_observer = None

    def _update_status(self, message: str):
        """更新状态显示"""
        self.status_var.set(message)
        self.root.update_idletasks()

    def show_window(self, *args):
        """显示主窗口"""
        self.root.after(0, self.root.deiconify)

    def hide_to_tray(self):
        """隐藏到系统托盘"""
        self.root.withdraw()

    def quit_app(self, *args):
        """退出应用程序"""
        self._stop_operation()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        sys.exit()

if __name__ == "__main__":
    try:
        app = SquadAutoTool()
        app.root.mainloop()
    except Exception as e:
        logging.critical("程序崩溃: %s", str(e))
        messagebox.showerror("致命错误", f"程序发生严重错误:\n{str(e)}")
        sys.exit(1)