import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import threading
import time
import pyautogui
import win32gui
import win32clipboard
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw, ImageFont
import sys
import os


class SquadAutoTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Squad战术小队工具 v2.0")
        self.root.geometry("400x350")
        self.root.resizable(False, False)
        self.root.configure(bg="#2c3e50")

        # 设置Windows任务栏图标
        if os.name == 'nt':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('SquadTool.2.0')

        self.running = False
        self.interval = 0.05  # 默认50ms
        self.squad_name = "TANK"

        self.tray_icon = None
        self.setup_ui()
        self.create_tray_icon()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        # 预加载剪贴板内容
        self._prepare_clipboard()

    def setup_ui(self):
        """创建现代化UI界面"""
        style = ttk.Style()
        style.theme_use('clam')

        # 自定义样式
        style.configure('TFrame', background='#2c3e50')
        style.configure('TLabel', background='#2c3e50', foreground='#ecf0f1', font=('微软雅黑', 10))
        style.configure('TButton', font=('微软雅黑', 9), padding=6)
        style.configure('TRadiobutton', background='#2c3e50', foreground='#ecf0f1')
        style.configure('TEntry', fieldbackground='#34495e', foreground='#ecf0f1')

        # 主框架
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="SQUAD 战术小队抢车工具", font=('微软雅黑', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # 小队名称输入
        ttk.Label(main_frame, text="小队名称:").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_squad = ttk.Entry(main_frame, width=20)
        self.entry_squad.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.entry_squad.insert(0, self.squad_name)
        self.entry_squad.bind("<KeyRelease>", self._update_clipboard)

        # 间隔选择
        ttk.Label(main_frame, text="发送间隔:").grid(row=2, column=0, sticky="w", pady=5)

        self.interval_frame = ttk.Frame(main_frame)
        self.interval_frame.grid(row=2, column=1, sticky="w")

        self.interval_var = tk.StringVar(value="50ms")
        intervals = [("超快 (10ms)", 0.01), ("快速 (50ms)", 0.05), ("标准 (100ms)", 0.1)]

        for text, val in intervals:
            rb = ttk.Radiobutton(
                self.interval_frame,
                text=text,
                value=val,
                variable=self.interval_var,
                command=lambda v=val: self.set_interval(v)
            )
            rb.pack(anchor="w", pady=2)

        # 状态显示
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=('微软雅黑', 9))
        status_label.grid(row=3, column=0, columnspan=2, pady=15)

        # 热键提示
        hotkey_frame = ttk.Frame(main_frame, style='TFrame')
        hotkey_frame.grid(row=4, column=0, columnspan=2, pady=10)

        ttk.Label(hotkey_frame, text="热键控制: F9 启动/停止", font=('微软雅黑', 9)).pack()
        ttk.Label(hotkey_frame, text="当前模式: 极速粘贴模式", font=('微软雅黑', 9)).pack()

        # 版权信息
        ttk.Label(main_frame, text="© 2025 Squad抢车工具 by 鱼见Uomi | v2.0", font=('微软雅黑', 8)).grid(row=5, column=0, columnspan=2,
                                                                                         pady=(20, 0))

    def _update_clipboard(self, event=None):
        """更新剪贴板内容"""
        self.squad_name = self.entry_squad.get().strip()
        self._prepare_clipboard()

    def _prepare_clipboard(self):
        """准备剪贴板内容"""
        cmd = f"createsquad {self.squad_name} 1"
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(cmd)
            win32clipboard.CloseClipboard()
        except:
            pass

    def set_interval(self, interval):
        self.interval = interval

    def create_tray_icon(self):
        """创建系统托盘图标"""

        def create_image():
            # 创建更精美的托盘图标
            image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            dc = ImageDraw.Draw(image)

            # 绘制渐变背景
            for i in range(64):
                dc.line([(i, 0), (i, 64)], fill=(40, 116, 166, int(255 * (i / 64))))

            # 添加文字
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            dc.text((12, 15), "S", font=font, fill=(255, 255, 255, 255))
            return image

        menu = Menu(
            MenuItem('显示主界面', self.show_window),
            MenuItem('退出', self.quit_app)
        )
        self.tray_icon = Icon(
            "squad_tool",
            create_image(),
            "Squad战术小队工具",
            menu
        )
        threading.Thread(
            target=self.tray_icon.run,
            daemon=True
        ).start()

    def register_hotkey(self):
        keyboard.add_hotkey('F9', self.toggle_operation)
        self.status_var.set("就绪状态 (F9控制)")

    def toggle_operation(self):
        if not self.running:
            self.squad_name = self.entry_squad.get().strip()
            if not self.squad_name:
                messagebox.showerror("错误", "请输入有效的小队名称！")
                return

            self.running = True
            threading.Thread(
                target=self.execute_loop,
                daemon=True
            ).start()
            self.status_var.set(f"运行中: {self.squad_name}")
        else:
            self.running = False
            self.status_var.set("已停止")

    def execute_loop(self):
        """极速粘贴模式"""
        while self.running:
            if self.is_game_focused():
                # 打开控制台
                pyautogui.press('`')
                time.sleep(0.01)

                # 粘贴命令
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.01)

                # 发送命令
                pyautogui.press('enter')

            time.sleep(self.interval)

    def is_game_focused(self, window_title="Squad"):
        try:
            return window_title in win32gui.GetWindowText(
                win32gui.GetForegroundWindow()
            )
        except:
            return False

    def show_window(self, *args):
        self.root.after(0, self.root.deiconify)

    def hide_to_tray(self):
        self.root.withdraw()

    def quit_app(self, *args):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        sys.exit()


if __name__ == "__main__":
    app = SquadAutoTool()
    app.register_hotkey()
    app.root.mainloop()