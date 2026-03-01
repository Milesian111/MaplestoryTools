"""
Daily 扫荡 GUI：打包为 exe 的入口。
提供图形界面：开始(F11)/结束(F12)、查看日志、修改角色数量。
角色数量会保存到配置文件，下次启动自动读取。
"""
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, simpledialog

if getattr(sys, "frozen", False):
    base = sys._MEIPASS
    if base not in sys.path:
        sys.path.insert(0, base)

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

from sweep import run_sweep_loop

# 角色数量配置文件：exe 下存于 exe 同目录，脚本下存于 Daily 目录
def _config_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

ROLE_COUNT_FILE = _config_dir() / "sweep_role_count.txt"

def _load_role_count():
    """从配置文件读取角色数量，无效或不存在则返回 53。"""
    try:
        if ROLE_COUNT_FILE.exists():
            n = int(ROLE_COUNT_FILE.read_text(encoding="utf-8").strip())
            if 1 <= n <= 999:
                return n
    except (ValueError, OSError):
        pass
    return 53

def _save_role_count(n):
    """将角色数量写入配置文件。"""
    try:
        ROLE_COUNT_FILE.write_text(str(n), encoding="utf-8")
    except OSError:
        pass

WIN_SIZE_NORMAL = "520x260"
WIN_SIZE_WITH_LOG = "520x480"

NOTICE_TEXT = """注意事项：
1.请将冒冒窗口调至1366*768及以下
2.请将冒冒窗口置于屏幕左上角（可用快捷键win + ←实现快速置于左上角）
3.如有多个屏幕，请将冒冒窗口置于主屏左上角
4.默认53个角色，可手动修改，修改后生成配置文件，不要删除
5.290级以上角色请手动领7岛原初！
6.如果鼠标只移动，不点击，请尝试管理员权限打开本工具
7.本软件不得用于商业用途,仅做学习交流
8.未经允许，不得将本工具外传，不然你马没了^_^"""


class SweepApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("好扫货")
        self.root.geometry(WIN_SIZE_NORMAL)
        self.root.resizable(True, True)
        self.root.minsize(480, 180)

        self.stop_event = threading.Event()
        self.worker_thread = None
        self._log_visible = False
        self._total_roles = _load_role_count()  # 主循环次数，从配置读取，默认 53

        self._build_ui()
        self._bind_keys()
        self._register_global_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        hint = "就绪（F11 开始 / F12 结束）"
        if not HAS_KEYBOARD:
            hint += " [未安装 keyboard，仅窗口内有效]"
        self.status_var = tk.StringVar(value=hint)
        ttk.Label(main, textvariable=self.status_var, font=("", 10)).pack(pady=(0, 12))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        self.btn_start = ttk.Button(btn_frame, text="开始(F11)", command=self.start)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ttk.Button(btn_frame, text="结束(F12)", command=self.stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_log = ttk.Button(btn_frame, text="查看日志", command=self._toggle_log)
        self.btn_log.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_roles = ttk.Button(btn_frame, text="修改角色数量", command=self._change_total_roles)
        self.btn_roles.pack(side=tk.LEFT)

        # 注意事项（与 MonsterCard 一致，部分词红色）
        self._notice_frame = ttk.Frame(main)
        self._notice_text = tk.Text(
            self._notice_frame,
            height=10,
            width=58,
            wrap=tk.WORD,
            font=("", 10),
            spacing1=2,
            spacing2=5,
            spacing3=2,
            bd=0,
            highlightthickness=0,
        )
        self._notice_text.tag_configure("red", foreground="red")
        self._notice_text.insert(tk.END, NOTICE_TEXT.strip())
        for phrase in ("关闭强化动画", "管理员权限", "不得用于商业用途", "不得将本工具外传", "马没了^_^","290级以上角色请手动领7岛原初！"):
            start = self._notice_text.search(phrase, "1.0", tk.END)
            if start:
                end = f"{start}+{len(phrase)}c"
                self._notice_text.tag_add("red", start, end)
        self._notice_text.config(state=tk.DISABLED)
        self._notice_text.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # 日志区域（默认隐藏）
        self._log_frame = ttk.LabelFrame(main, text="运行日志", padding=4)
        self._log_text = tk.Text(
            self._log_frame,
            height=14,
            width=58,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        log_scroll = ttk.Scrollbar(self._log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _toggle_log(self):
        if self._log_visible:
            self._log_frame.pack_forget()
            self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
            self._log_visible = False
        else:
            self._notice_frame.pack_forget()
            self._log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_WITH_LOG)
            self.btn_log.config(text="隐藏日志")
            self._log_visible = True

    def _change_total_roles(self):
        n = simpledialog.askinteger(
            "修改角色数量",
            f"请输入角色数量（1-999），当前为 {self._total_roles}：",
            initialvalue=self._total_roles,
            minvalue=1,
            maxvalue=999,
            parent=self.root,
        )
        if n is not None:
            self._total_roles = n
            _save_role_count(n)
            messagebox.showinfo("修改角色数量", f"已设置为 {self._total_roles} 个角色，已保存。", parent=self.root)

    def _log_append(self, msg):
        def _do():
            self._log_text.config(state=tk.NORMAL)
            self._log_text.insert(tk.END, msg + "\n")
            self._log_text.see(tk.END)
            self._log_text.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _bind_keys(self):
        self.root.bind("<F11>", lambda e: self.start())
        self.root.bind("<F12>", lambda e: self.stop())

    def _register_global_hotkeys(self):
        if not HAS_KEYBOARD:
            return
        def on_f11():
            self.root.after(0, self.start)
        def on_f12():
            self.root.after(0, self.stop)
        try:
            keyboard.add_hotkey("f11", on_f11, suppress=False)
            keyboard.add_hotkey("f12", on_f12, suppress=False)
        except Exception as e:
            self.status_var.set(self.status_var.get() + f" 热键注册失败: {e}")

    def _on_close(self):
        if HAS_KEYBOARD:
            try:
                keyboard.remove_hotkey("f11")
                keyboard.remove_hotkey("f12")
            except Exception:
                try:
                    keyboard.unhook_all_hotkeys()
                except Exception:
                    pass
        self.root.destroy()

    def _set_running(self, running):
        if running:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        else:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

    def _status_callback(self, msg):
        def _update():
            self.status_var.set(msg)
            self._set_running(False)
        self.root.after(0, _update)

    def _log_callback(self, msg):
        self.root.after(0, lambda m=msg: self._log_append(m))

    def start(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.stop_event.clear()
        self.status_var.set("运行中…")
        self._set_running(True)
        self.root.after(0, self._log_clear)
        self.worker_thread = threading.Thread(
            target=run_sweep_loop,
            args=(self.stop_event, self._status_callback, self._log_callback, self._total_roles),
            daemon=True,
        )
        self.worker_thread.start()

    def _log_clear(self):
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete(1.0, tk.END)
        self._log_text.config(state=tk.DISABLED)

    def stop(self):
        self.stop_event.set()
        self.status_var.set("正在停止…")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = SweepApp()
    app.run()
