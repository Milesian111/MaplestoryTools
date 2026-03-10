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

# 配置文件（角色数量 + 泰涅布利斯）：exe 下存于 exe 同目录，脚本下存于 Daily 目录
def _config_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

CONFIG_FILE = _config_dir() / "sweep_role_count.txt"


def _load_config():
    """从配置文件读取 (角色数量, 是否扫荡泰涅布利斯)。角色数量无效或不存在则 53，泰涅布利斯默认 False。"""
    role_count, tenebris = 53, False
    try:
        if CONFIG_FILE.exists():
            lines = CONFIG_FILE.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                n = int(lines[0].strip())
                if 1 <= n <= 999:
                    role_count = n
            if len(lines) >= 2:
                tenebris = lines[1].strip() == "1"
    except (ValueError, OSError):
        pass
    return role_count, tenebris


def _save_config(role_count, tenebris):
    """将角色数量和泰涅布利斯选项写入同一配置文件。"""
    try:
        CONFIG_FILE.write_text(
            str(role_count) + "\n" + ("1" if tenebris else "0"),
            encoding="utf-8",
        )
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
        self._total_roles, self._tenebris_enabled = _load_config()

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
        self.btn_roles.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_tenebris = ttk.Button(btn_frame, text="泰涅布利斯", command=self._toggle_tenebris)
        self.btn_tenebris.pack(side=tk.LEFT)

        # 泰涅布利斯选项面板（点击泰涅布利斯按钮后才显示，与 MonsterCard 选择魔方一致）
        self._tenebris_visible = False
        self._tenebris_var = tk.BooleanVar(value=self._tenebris_enabled)

        def _on_tenebris_change(*args):
            self._tenebris_enabled = self._tenebris_var.get()
            _save_config(self._total_roles, self._tenebris_enabled)

        self._tenebris_var.trace_add("write", _on_tenebris_change)

        self._tenebris_frame = ttk.LabelFrame(main, text="泰涅布利斯", padding=12)
        # 不 pack，由 _toggle_tenebris 控制显示
        ttk.Label(self._tenebris_frame, text="是否扫荡泰涅布利斯（需要皇家VIP）？", font=("", 10)).pack(anchor=tk.W)
        rb_frame = ttk.Frame(self._tenebris_frame)
        rb_frame.pack(anchor=tk.W, pady=(8, 12))
        ttk.Radiobutton(rb_frame, text="是", variable=self._tenebris_var, value=True).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Radiobutton(rb_frame, text="否", variable=self._tenebris_var, value=False).pack(side=tk.LEFT)
        ttk.Button(self._tenebris_frame, text="确定", command=self._hide_tenebris).pack(anchor=tk.W)

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

    def _toggle_tenebris(self):
        """点击泰涅布利斯按钮：若未显示则在下方面板显示问题和选项，若已显示则收起。"""
        if self._tenebris_visible:
            self._hide_tenebris()
            return
        self._show_tenebris()

    def _show_tenebris(self):
        """在下方面板显示泰涅布利斯选项（替换注意事项）。"""
        if self._tenebris_visible:
            return
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
            self.btn_log.config(text="查看日志")
            self.root.geometry(WIN_SIZE_NORMAL)
        self._notice_frame.pack_forget()
        self._tenebris_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self._tenebris_visible = True

    def _hide_tenebris(self):
        """收起泰涅布利斯面板，恢复显示注意事项。"""
        if not self._tenebris_visible:
            return
        self._tenebris_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self._tenebris_visible = False

    def _toggle_log(self):
        if self._log_visible:
            self._log_frame.pack_forget()
            if self._tenebris_visible:
                self._tenebris_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            else:
                self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
            self._log_visible = False
        else:
            self._notice_frame.pack_forget()
            self._tenebris_frame.pack_forget()
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
            _save_config(self._total_roles, self._tenebris_enabled)
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

    def _run_worker(self):
        """按配置执行扫荡；若勾选泰涅布利斯，则每个角色在进入主扫荡前先执行一次泰涅布利斯流程。"""
        run_sweep_loop(
            self.stop_event,
            self._status_callback,
            self._log_callback,
            self._total_roles,
            tenebris_enabled=self._tenebris_enabled,
        )

    def start(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.stop_event.clear()
        self.status_var.set("运行中…")
        self._set_running(True)
        self.root.after(0, self._log_clear)
        self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
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
