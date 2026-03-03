"""
魔方（洗装备）GUI：打包为 exe 的入口。
提供图形界面：开始/结束、查看日志、选择装备、选择属性。
F11/F12 使用全局热键，在任意窗口下都有效（需安装 keyboard：pip install keyboard）。
"""
import threading
import time
import tkinter as tk
from tkinter import ttk

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

WIN_SIZE_NORMAL = "520x250"
WIN_SIZE_WITH_LOG = "520x480"
WIN_SIZE_WITH_EQUIP = "520x320"
WIN_SIZE_WITH_ATTR = "520x280"


def run_cube_loop(stop_event, status_callback, log_callback=None, equipment_type=None):
    """在后台线程中执行魔方主循环（占位：仅用于测试开始/结束与日志）。
    equipment_type: 当前选择的装备类型，如 "200防具饰品"。
    后续可接入 cube 模块的真实找图与点击逻辑。"""
    if log_callback is None:
        log_callback = lambda msg: None
    try:
        n = 0
        while not stop_event.is_set():
            n += 1
            log_callback(f"第{n}轮（装备类型: {equipment_type or '未选择'}）— 主循环逻辑待接入")
            for _ in range(10):
                if stop_event.is_set():
                    break
                time.sleep(0.2)
    except Exception as e:
        log_callback(f"运行出错: {e}")
        status_callback(f"运行出错: {e}")
    else:
        log_callback("已手动停止")
        status_callback("已手动停止")


class CubeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("魔方")
        self.root.geometry(WIN_SIZE_NORMAL)
        self.root.resizable(True, True)
        self.root.minsize(480, 180)

        self.stop_event = threading.Event()
        self.worker_thread = None
        self._log_visible = False
        self._equip_visible = False
        self._attr_visible = False
        # 装备类型（单选）
        self._equip_var = tk.StringVar(value="200防具饰品")
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

        self.btn_equip = ttk.Button(btn_frame, text="选择装备", command=self._toggle_equip)
        self.btn_equip.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_attr = ttk.Button(btn_frame, text="选择属性", command=self._toggle_attr)
        self.btn_attr.pack(side=tk.LEFT)

        # 注意事项（与 MonsterCard 风格一致）
        NOTICE_TEXT = """注意事项：
1.请将冒冒窗口调至1366*768及以下
2.请将冒冒窗口置于屏幕左上角（可用快捷键win + ←实现快速置于左上角）
3.如有多个屏幕，请将冒冒窗口置于主屏左上角
4.请确保关闭强化动画选项
5.如果鼠标只移动，不点击，请尝试管理员权限打开本工具
6.本软件不得用于商业用途,仅做学习交流
7.未经允许，不得将本工具外传，不然你马没了^_^"""
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
        for phrase in ("关闭强化动画", "管理员权限", "不得用于商业用途", "不得将本工具外传", "马没了^_^"):
            start = self._notice_text.search(phrase, "1.0", tk.END)
            if start:
                end = f"{start}+{len(phrase)}c"
                self._notice_text.tag_add("red", start, end)
        self._notice_text.config(state=tk.DISABLED)
        self._notice_text.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # 选择装备区域（与注意事项同位置切换，默认不显示）
        EQUIP_OPTIONS = [
            "200防具饰品",
            "250防具饰品",
            "帽子",
            "手套",
            "200级三大件",
            "140副手",
            "休比德曼",
        ]
        self._equip_frame = ttk.LabelFrame(main, text="选择装备", padding=8)
        for opt in EQUIP_OPTIONS:
            ttk.Radiobutton(self._equip_frame, text=opt, variable=self._equip_var, value=opt).pack(anchor=tk.W, pady=2)
        ttk.Button(self._equip_frame, text="确定", command=self._hide_equip).pack(pady=(8, 0))

        # 选择属性区域（待实现，占位）
        self._attr_frame = ttk.LabelFrame(main, text="选择属性", padding=8)
        ttk.Label(self._attr_frame, text="功能待实现", font=("", 10)).pack(pady=8)
        ttk.Button(self._attr_frame, text="确定", command=self._hide_attr).pack(pady=(4, 0))

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

    def _toggle_equip(self):
        if self._equip_visible:
            self._hide_equip()
            return
        if self._attr_visible:
            self._attr_frame.pack_forget()
            self._attr_visible = False
            self.root.geometry(WIN_SIZE_NORMAL)
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
        self._notice_frame.pack_forget()
        self._equip_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_EQUIP)
        self._equip_visible = True

    def _hide_equip(self):
        if not self._equip_visible:
            return
        self._equip_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_NORMAL)
        self._equip_visible = False

    def _toggle_attr(self):
        if self._attr_visible:
            self._hide_attr()
            return
        if self._equip_visible:
            self._hide_equip()
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
        self._notice_frame.pack_forget()
        self._attr_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_ATTR)
        self._attr_visible = True

    def _hide_attr(self):
        if not self._attr_visible:
            return
        self._attr_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_NORMAL)
        self._attr_visible = False

    def _toggle_log(self):
        if self._log_visible:
            self._log_frame.pack_forget()
            self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
            self._log_visible = False
        else:
            if self._equip_visible:
                self._hide_equip()
            if self._attr_visible:
                self._attr_frame.pack_forget()
                self._attr_visible = False
                self.root.geometry(WIN_SIZE_NORMAL)
            self._notice_frame.pack_forget()
            self._log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_WITH_LOG)
            self.btn_log.config(text="隐藏日志")
            self._log_visible = True

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
        equipment_type = self._equip_var.get()
        self.worker_thread = threading.Thread(
            target=run_cube_loop,
            args=(self.stop_event, self._status_callback, self._log_callback, equipment_type),
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
    app = CubeApp()
    app.run()
