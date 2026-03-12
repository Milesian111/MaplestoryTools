"""
卡球任务 GUI：模仿 MonsterCard 界面。
按钮：开始、结束、日志、键位配置。
开始后按「卡球」快捷键即执行 ball.run_sequence()；放球/切球键可配置并传入 run_sequence。
键位配置会保存到配置文件，下次启动自动读取（exe 下存于 exe 同目录，脚本下存于 Farm 目录）。
"""
import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    from pynput import mouse
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

from ball import run_sequence

# 鼠标键内部名 -> 显示名
MOUSE_BUTTON_NAMES = {
    "mouse_middle": "鼠标中键",
    "mouse_side1": "鼠标侧键1",
    "mouse_side2": "鼠标侧键2",
    "mouse_left": "鼠标左键",
    "mouse_right": "鼠标右键",
}
# pynput Button -> 内部名
PYNPUT_TO_BALL = {
    mouse.Button.middle: "mouse_middle",
    mouse.Button.x1: "mouse_side1",
    mouse.Button.x2: "mouse_side2",
    mouse.Button.left: "mouse_left",
    mouse.Button.right: "mouse_right",
} if HAS_PYNPUT else {}

WIN_SIZE_NORMAL = "560x250"
WIN_SIZE_WITH_LOG = "560x480"
WIN_SIZE_WITH_KEYS = "560x350"

# 键位配置文件：exe 下存于 exe 同目录，脚本下存于 Farm 目录（与 Daily 保存角色数量一致）
def _config_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

CONFIG_FILE = _config_dir() / "ball_config.json"

NOTICE_TEXT = """注意事项：
1.请将冒冒窗口调至1366*768及以下
2.请将冒冒窗口置于屏幕左上角（可用快捷键win + ←实现快速置于左上角）
3.如有多个屏幕，请将冒冒窗口置于主屏左上角
4.卡球时间无法做到100%，且每个球的时间可能不一样，需要自己调整
5.间隔时间建议设置3500-4000之间，每次调整20-100为宜
6.本软件不得用于商业用途,仅做学习交流
7.未经允许，不得将本工具外传，不然你马没了^_^"""


def _load_config_static():
    """从配置文件读取配置字典，失败返回 None。"""
    if not CONFIG_FILE.exists():
        return None
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_config_static(data):
    """将配置字典写入配置文件。"""
    try:
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def keysym_to_keyboard(keysym):
    """将 Tk 的 keysym 转为 keyboard 库使用的键名（小写、统一修饰键）。"""
    if not keysym:
        return None
    m = {
        "Control_L": "ctrl", "Control_R": "ctrl",
        "Shift_L": "shift", "Shift_R": "shift",
        "Alt_L": "alt", "Alt_R": "alt",
        "Super_L": "windows", "Super_R": "windows",
    }
    return m.get(keysym, keysym.lower())


class BallApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("好球")
        self.root.geometry(WIN_SIZE_NORMAL)
        self.root.resizable(True, True)
        self.root.minsize(480, 180)

        self._running = False
        self._log_visible = False
        self._keys_visible = False
        self._ball_hotkey_registered = None  # 当前已注册的卡球键名（键盘时用于 remove_hotkey）
        self._mouse_listener = None  # 卡球为鼠标键时的 pynput 监听器

        # 键位：卡球触发、切球键、放球键；间隔时间（毫秒，默认 3500）
        self._key_ball = "f1"
        self._key_shift = "shift"
        self._key_ctrl = "ctrl"
        self._interval_ms = 3500

        self._build_ui()
        self._load_config()
        self._bind_keys()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_config(self):
        """从配置文件读取并应用配置，更新界面显示。"""
        data = _load_config_static()
        if not data:
            return
        if isinstance(data.get("key_ball"), str):
            self._key_ball = data["key_ball"]
            self._lbl_ball.config(text=self._ball_key_display(self._key_ball))
        if isinstance(data.get("key_shift"), str):
            self._key_shift = data["key_shift"]
            self._lbl_shift.config(text=self._key_shift)
        if isinstance(data.get("key_ctrl"), str):
            self._key_ctrl = data["key_ctrl"]
            self._lbl_ctrl.config(text=self._key_ctrl)
        if isinstance(data.get("interval_ms"), (int, float)) and data["interval_ms"] >= 1000:
            self._interval_ms = int(data["interval_ms"])
            self._lbl_interval.config(text=f"{self._interval_ms} ms")

    def _save_config(self):
        """将当前配置写入配置文件。"""
        _save_config_static({
            "key_ball": self._key_ball,
            "key_shift": self._key_shift,
            "key_ctrl": self._key_ctrl,
            "interval_ms": self._interval_ms,
        })

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        hint = "就绪（开始后按卡球快捷键执行序列）"
        if not HAS_KEYBOARD:
            hint += " [未安装 keyboard]"
        self.status_var = tk.StringVar(value=hint)
        ttk.Label(main, textvariable=self.status_var, font=("", 10)).pack(pady=(0, 12))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        self.btn_start = ttk.Button(btn_frame, text="开始", command=self.start)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_stop = ttk.Button(btn_frame, text="结束", command=self.stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_log = ttk.Button(btn_frame, text="查看日志", command=self._toggle_log)
        self.btn_log.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_keys = ttk.Button(btn_frame, text="键位配置", command=self._toggle_keys)
        self.btn_keys.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_interval = ttk.Button(btn_frame, text="间隔时间", command=self._config_interval)
        self.btn_interval.pack(side=tk.LEFT, padx=(0, 4))
        self._lbl_interval = ttk.Label(btn_frame, text=f"{self._interval_ms} ms")
        self._lbl_interval.pack(side=tk.LEFT)

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
        for phrase in ("需要自己调整", "3500-4000", "20-100", "不得用于商业用途", "不得将本工具外传", "马没了^_^"):
            start = self._notice_text.search(phrase, "1.0", tk.END)
            if start:
                end = f"{start}+{len(phrase)}c"
                self._notice_text.tag_add("red", start, end)
        self._notice_text.config(state=tk.DISABLED)
        self._notice_text.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # 键位配置区域
        self._keys_frame = ttk.LabelFrame(main, text="键位配置", padding=8)
        kf = ttk.Frame(self._keys_frame)
        kf.pack(fill=tk.X)
        ttk.Label(kf, text="卡球：", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 4))
        self._lbl_ball = ttk.Label(kf, text=self._ball_key_display(self._key_ball))
        self._lbl_ball.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(kf, text="配置键盘", command=self._config_ball_keyboard).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(kf, text="配置鼠标", command=self._config_ball_mouse).pack(side=tk.LEFT, padx=(0, 16))

        kf2 = ttk.Frame(self._keys_frame)
        kf2.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(kf2, text="切球：", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 4))
        self._lbl_shift = ttk.Label(kf2, text=self._key_shift)
        self._lbl_shift.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(kf2, text="配置", command=self._config_shift).pack(side=tk.LEFT, padx=(0, 16))

        kf3 = ttk.Frame(self._keys_frame)
        kf3.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(kf3, text="放球：", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 4))
        self._lbl_ctrl = ttk.Label(kf3, text=self._key_ctrl)
        self._lbl_ctrl.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(kf3, text="配置", command=self._config_ctrl).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(self._keys_frame, text="卡球：卡球动作执行键", font=("", 9)).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(self._keys_frame, text="切球：双面神切换键", font=("", 9)).pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(self._keys_frame, text="放球：双面神使用键", font=("", 9)).pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(
            self._keys_frame,
            text="操作流程：双面神切换到球后，走到需要卡球的位置，按卡球键即可（在开始状态才生效）",
            font=("", 9),
            wraplength=480,
        ).pack(anchor=tk.W, pady=(8, 0))
        ttk.Button(self._keys_frame, text="确定", command=self._hide_keys).pack(pady=(8, 0))

        # 日志区域
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

    def _capture_key(self, title, keyboard_only=True):
        """弹窗等待用户按下一个键，返回 keyboard 库键名或 None。"""
        result = [None]

        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text="请按下要设置的键…").pack(pady=12, padx=16)
        e = ttk.Entry(win, width=20)
        e.pack(pady=(0, 12), padx=16)
        e.focus_set()

        def on_key(event):
            keysym = event.keysym
            key = keysym_to_keyboard(keysym)
            if key:
                result[0] = key
                e.delete(0, tk.END)
                e.insert(0, key)
                win.after(100, win.destroy)

        win.bind("<KeyPress>", on_key)
        win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())
        self._center_popup(win)
        win.wait_window()
        return result[0]

    def _ball_key_display(self, key):
        """卡球键的显示文本（键盘键名或鼠标描述）。"""
        if key in MOUSE_BUTTON_NAMES:
            return MOUSE_BUTTON_NAMES[key]
        return key

    def _config_ball_keyboard(self):
        k = self._capture_key("卡球快捷键（键盘）", keyboard_only=True)
        if k:
            self._key_ball = k
            self._lbl_ball.config(text=self._ball_key_display(k))
            self._log_append(f"卡球快捷键已设为: {k}")
            self._save_config()
            if self._running:
                self._reregister_ball_hotkey()

    def _config_ball_mouse(self):
        if not HAS_PYNPUT:
            messagebox.showinfo("提示", "请先安装 pynput：pip install pynput")
            return
        result = [None]

        win = tk.Toplevel(self.root)
        win.title("卡球快捷键（鼠标）")
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text="请按下鼠标键（中键或侧键）…").pack(pady=12, padx=16)
        self._center_popup(win)

        def on_click(x, y, button, pressed):
            if not pressed:
                return
            ball_key = PYNPUT_TO_BALL.get(button)
            if ball_key:
                result[0] = ball_key
                try:
                    listener.stop()
                except Exception:
                    pass
                self.root.after(0, win.destroy)

        listener = mouse.Listener(on_click=on_click)
        listener.start()

        win.protocol("WM_DELETE_WINDOW", lambda: (listener.stop(), win.destroy()))
        win.wait_window()
        try:
            listener.stop()
        except Exception:
            pass

        if result[0]:
            self._key_ball = result[0]
            self._lbl_ball.config(text=self._ball_key_display(result[0]))
            self._log_append(f"卡球快捷键已设为: {MOUSE_BUTTON_NAMES.get(result[0], result[0])}")
            self._save_config()
            if self._running:
                self._reregister_ball_hotkey()

    def _config_shift(self):
        k = self._capture_key("切球键（仅键盘）", keyboard_only=True)
        if k:
            self._key_shift = k
            self._lbl_shift.config(text=k)
            self._log_append(f"切球键已设为: {k}")
            self._save_config()

    def _config_ctrl(self):
        k = self._capture_key("放球键（仅键盘）", keyboard_only=True)
        if k:
            self._key_ctrl = k
            self._lbl_ctrl.config(text=k)
            self._log_append(f"放球键已设为: {k}")
            self._save_config()

    def _config_interval(self):
        win = tk.Toplevel(self.root)
        win.title("间隔时间")
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text="间隔时间（毫秒），默认 3500：").pack(pady=(12, 4), padx=16)
        var = tk.StringVar(value=str(self._interval_ms))
        e = ttk.Entry(win, textvariable=var, width=12)
        e.pack(pady=(0, 12), padx=16)
        e.focus_set()

        def ok():
            try:
                v = int(var.get().strip())
                if v < 1000:
                    messagebox.showwarning("提示", "间隔时间不能小于 1000 毫秒", parent=win)
                    return
                self._interval_ms = v
                self._lbl_interval.config(text=f"{v} ms")
                self._log_append(f"间隔时间已设为: {v} ms（切球后等待 {(v - 1000) / 1000:.3f}s）")
                self._save_config()
                win.destroy()
            except ValueError:
                messagebox.showwarning("提示", "请输入有效数字", parent=win)

        ttk.Label(win, text="建议间隔时间：3500-4000，每次调节20-100", font=("", 9)).pack(pady=(0, 6))
        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=(0, 12))
        ttk.Button(btn_frame, text="确定", command=ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="取消", command=win.destroy).pack(side=tk.LEFT, padx=4)
        win.bind("<Return>", lambda ev: ok())
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self._center_popup(win)

    def _center_popup(self, popup):
        """将弹窗固定在主窗口中心，弹窗宽度在内容基础上加 20 像素。"""
        popup.update_idletasks()
        pw = popup.winfo_width() + 20
        ph = popup.winfo_height()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        x = rx + (rw - pw) // 2
        y = ry + (rh - ph) // 2
        popup.geometry(f"{pw}x{ph}+{x}+{y}")

    def _reregister_ball_hotkey(self):
        # 先移除/停止原有
        if HAS_KEYBOARD and self._ball_hotkey_registered:
            try:
                keyboard.remove_hotkey(self._ball_hotkey_registered)
            except Exception:
                pass
            self._ball_hotkey_registered = None
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None

        key = self._key_ball
        if key.startswith("mouse_"):
            if not HAS_PYNPUT:
                self._log_append("未安装 pynput，无法使用鼠标键")
                return
            # 卡球为鼠标键：用 pynput 监听对应按键
            ball_key = key
            reverse_map = {v: k for k, v in PYNPUT_TO_BALL.items()}
            target_button = reverse_map.get(ball_key)
            if target_button is None:
                return

            def on_click(x, y, button, pressed):
                if pressed and button == target_button:
                    self._on_ball_triggered()

            self._mouse_listener = mouse.Listener(on_click=on_click)
            self._mouse_listener.start()
        else:
            if not HAS_KEYBOARD:
                return
            try:
                keyboard.add_hotkey(key, self._on_ball_triggered, suppress=False)
                self._ball_hotkey_registered = key
            except Exception as e:
                self._log_append(f"注册卡球热键失败: {e}")

    def _on_ball_triggered(self):
        """卡球热键被按下时在后台执行 run_sequence。"""
        ctrl_key = self._key_ctrl
        shift_key = self._key_shift
        interval_ms = self._interval_ms
        def run():
            try:
                run_sequence(ctrl_key=ctrl_key, shift_key=shift_key, interval_ms=interval_ms)
                self.root.after(0, lambda: self._log_append("已执行卡球序列"))
            except Exception as e:
                self.root.after(0, lambda: self._log_append(f"执行出错: {e}"))
        threading.Thread(target=run, daemon=True).start()

    def _toggle_keys(self):
        if self._keys_visible:
            self._hide_keys()
            return
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
        self._notice_frame.pack_forget()
        self._keys_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_KEYS)
        self._keys_visible = True

    def _hide_keys(self):
        if not self._keys_visible:
            return
        self._keys_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_NORMAL)
        self._keys_visible = False

    def _toggle_log(self):
        if self._log_visible:
            self._log_frame.pack_forget()
            self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
            self._log_visible = False
        else:
            if self._keys_visible:
                self._keys_frame.pack_forget()
                self._keys_visible = False
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
        pass

    def _on_close(self):
        if HAS_KEYBOARD and self._ball_hotkey_registered:
            try:
                keyboard.remove_hotkey(self._ball_hotkey_registered)
            except Exception:
                pass
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
        if HAS_KEYBOARD:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
        self.root.destroy()

    def _set_running(self, running):
        self._running = running
        if running:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        else:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

    def start(self):
        if self._running:
            return
        self._set_running(True)
        self.status_var.set("运行中（按卡球快捷键执行）")
        self._log_append("已开始，按卡球快捷键执行序列")
        self._reregister_ball_hotkey()

    def stop(self):
        if not self._running:
            return
        if HAS_KEYBOARD and self._ball_hotkey_registered:
            try:
                keyboard.remove_hotkey(self._ball_hotkey_registered)
            except Exception:
                pass
            self._ball_hotkey_registered = None
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None
        self._set_running(False)
        self.status_var.set("就绪（开始后按卡球快捷键执行序列）")
        self._log_append("已结束")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BallApp()
    app.run()
