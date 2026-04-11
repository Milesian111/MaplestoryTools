from __future__ import annotations

import configparser
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk
from typing import Any, Optional

import keyboard
import pyautogui

_ROOT = Path(__file__).resolve().parent.parent
_PARTY_DIR = _ROOT / "Party"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Utils.find_image import find_image_with_score, get_image_center


SEARCH_RECT = (0, 0, 1366, 768)

_KEY_ALIASES = {
    "space": "space",
    " ": "space",
    "enter": "enter",
    "return": "enter",
    "next": "page down",
    "pagedown": "page down",
    "page_down": "page down",
    "pgdn": "page down",
    "prior": "page up",
    "pageup": "page up",
    "page_up": "page up",
    "pgup": "page up",
    "esc": "esc",
    "escape": "esc",
    "tab": "tab",
    "alt": "alt",
    "ctrl": "ctrl",
    "shift": "shift",
    "win": "win",
    "windows": "win",
}

_PY_AUTO_KEY_ALIASES = {
    "page up": "pageup",
    "page down": "pagedown",
    "return": "enter",
    "windows": "win",
}


class PartyBugApp:
    def __init__(self) -> None:
        self.script_dir = Path(__file__).resolve().parent
        self.picture_dir = self.script_dir / "picture"
        self.ini_file = self.script_dir / "settings.ini"
        self.cp = configparser.ConfigParser()
        if self.ini_file.is_file():
            self.cp.read(self.ini_file, encoding="utf-8-sig")

        self.match_threshold = 0.95
        self.poll_interval_seconds = 0.3
        self.game_key_hold_seconds = 0.05
        self.double_c_interval_seconds = 0.2
        self.up_press_hold_seconds = 0.05
        self.up_press_interval_seconds = 0.05
        self.up_hold_timeout_seconds = 5.0
        self.pre_click_interval_seconds = 0.2
        self.gather_key = self._ini_get("Settings", "GatherKey", "space")
        self.timer_enabled = self._ini_get("Settings", "TimerEnabled", "0") == "1"
        self.timer_minutes = self._ini_get("Settings", "TimerMinutes", "60")
        _rm = self._ini_get("Settings", "RunMode", "harvest")
        self._initial_run_mode = _rm if _rm in ("spectrum", "harvest") else "harvest"
        self.pending_key_target: Optional[str] = None

        self.running = False
        self.stop_event = threading.Event()
        self.worker: Optional[threading.Thread] = None
        self._f12_hotkey_registered = False
        self._f12_hotkey_ref = None
        self.need_activate_window_once = False
        self.auto_stop_deadline: Optional[float] = None

        self.root = tk.Tk()
        self.root.title("好不厉害组队")
        self.root.geometry("360x380")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        icon_path = self.script_dir / "icon" / "icon.png"
        if icon_path.is_file():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
                self._icon_ref = icon
            except Exception:
                pass

        self._build_ui()
        self._register_hotkeys()
        self._log("[系统] GUI 初始化完成")

    def _ini_get(self, sec: str, key: str, default: str) -> str:
        try:
            return self.cp.get(sec, key, fallback=default)
        except Exception:
            return default

    def _set_ini(self, sec: str, key: str, val: str) -> None:
        if not self.cp.has_section(sec):
            self.cp.add_section(sec)
        self.cp.set(sec, key, val)
        with open(self.ini_file, "w", encoding="utf-8") as f:
            self.cp.write(f)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="采集键").grid(row=0, column=0, padx=(0, 6), pady=4, sticky="w")
        self.btn_gather_key = ttk.Button(top, text=self.gather_key.upper(), width=12, command=self._start_set_gather_key)
        self.btn_gather_key.grid(row=0, column=1, pady=4, sticky="w")

        self.var_timer_enabled = tk.IntVar(value=1 if self.timer_enabled else 0)
        ttk.Checkbutton(top, text="定时停止(分钟)", variable=self.var_timer_enabled).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        self.ent_timer_minutes = ttk.Entry(top, width=8)
        self.ent_timer_minutes.insert(0, self.timer_minutes)
        self.ent_timer_minutes.grid(row=1, column=2, sticky="w", pady=(4, 0))

        self.var_run_mode = tk.StringVar(value=self._initial_run_mode)
        mode_fr = ttk.Frame(top)
        mode_fr.grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self._run_mode_widgets: list[tk.Widget] = []
        r1 = ttk.Radiobutton(
            mode_fr,
            text="找光谱",
            variable=self.var_run_mode,
            value="spectrum",
            command=self._save_run_mode,
        )
        r1.pack(side=tk.LEFT)
        self._run_mode_widgets.append(r1)
        r2 = ttk.Radiobutton(
            mode_fr,
            text="收菜",
            variable=self.var_run_mode,
            value="harvest",
            command=self._save_run_mode,
        )
        r2.pack(side=tk.LEFT, padx=(12, 0))
        self._run_mode_widgets.append(r2)

        self.btn_find_spectrum = ttk.Button(
            top,
            text="找光谱配置",
            command=self._open_party_spectrum_config,
        )
        self.btn_find_spectrum.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self._party_spectrum_app: Optional[Any] = None
        self._party_once_host: Optional[tk.Toplevel] = None
        self._party_once_runner: Optional[Any] = None
        self._party_once_status_trace: Optional[str] = None

        btn_row = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        btn_row.pack(fill=tk.X)
        self.btn_start = ttk.Button(btn_row, text="开始 (F12)", command=self.start)
        self.btn_start.pack(side=tk.LEFT)
        self.btn_stop = ttk.Button(btn_row, text="停止 (F12)", command=self.stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=8)

        self.log_text = scrolledtext.ScrolledText(self.root, height=28, font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state=tk.DISABLED)

        self.root.bind("<KeyPress>", self._on_key_press)

    def _open_party_spectrum_config(self) -> None:
        """打开 Party 的「任务配置 + 全局参数」弹窗（采集键使用本窗口的采集键）。"""
        if not _PARTY_DIR.is_dir():
            self._log("[找光谱] 未找到 Party 目录，请确认仓库结构。")
            return
        party_pkg = str(_PARTY_DIR.resolve())
        if party_pkg not in sys.path:
            sys.path.insert(0, party_pkg)

        try:
            from party import PartyApp
        except ImportError as e:
            self._log(f"[找光谱] 无法加载 party 模块：{e}")
            return

        top = tk.Toplevel(self.root)
        top.transient(self.root)
        try:
            self._party_spectrum_app = PartyApp(
                top,
                embed_mode=True,
                config_root=_PARTY_DIR,
                gather_key_supplier=lambda: self.gather_key,
            )
        except Exception as e:
            self._log(f"[找光谱] 打开失败：{e}")
            top.destroy()
            self._party_spectrum_app = None

    def _save_run_mode(self) -> None:
        self._set_ini("Settings", "RunMode", self.var_run_mode.get())

    def _set_run_mode_widgets_state(self, state: str) -> None:
        for w in self._run_mode_widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _ensure_party_once_runner(self) -> bool:
        """创建隐藏的 PartyOnceApp（与 party_once 相同监控逻辑），失败则返回 False。"""
        if self._party_once_runner is not None:
            return True
        if not _PARTY_DIR.is_dir():
            self._log("[找光谱] 未找到 Party 目录，请确认仓库结构。")
            return False
        party_pkg = str(_PARTY_DIR.resolve())
        if party_pkg not in sys.path:
            sys.path.insert(0, party_pkg)
        try:
            from party_once import PartyOnceApp
        except ImportError as e:
            self._log(f"[找光谱] 无法加载 party_once：{e}")
            return False

        host = tk.Toplevel(self.root)
        host.withdraw()
        host.transient(self.root)
        try:
            app = PartyOnceApp(
                host,
                embed_mode=True,
                config_root=_PARTY_DIR,
                gather_key_supplier=lambda: self.gather_key,
            )
        except Exception as e:
            self._log(f"[找光谱] 初始化失败：{e}")
            host.destroy()
            return False

        self._party_once_host = host
        self._party_once_runner = app
        self._party_once_status_trace = ""

        def on_status(*_a: Any) -> None:
            try:
                v = app.status_var.get()
            except Exception:
                return
            if v == self._party_once_status_trace:
                return
            self._party_once_status_trace = v
            self._log(f"[找光谱] {v}")

        try:
            app.status_var.trace_add("write", on_status)
        except AttributeError:
            app.status_var.trace("w", lambda *_x: on_status())

        return True

    def _sync_party_once_timer_and_keys(self) -> None:
        app = self._party_once_runner
        if app is None:
            return
        if getattr(app, "_gather_key_supplier", None) is not None:
            app.gather_key = app._gather_key_supplier()
        try:
            app.var_chk_autostop.set(1 if self.timer_enabled else 0)
            app.ed_autostop_dur.delete(0, tk.END)
            app.ed_autostop_dur.insert(0, self.timer_minutes)
        except Exception:
            pass

    def _schedule_party_once_watch(self) -> None:
        """Party 侧自行 stop_monitoring 时，同步本窗口按钮状态。"""
        if not self.running:
            return
        app = self._party_once_runner
        if self.var_run_mode.get() != "spectrum" or app is None:
            return
        if not app.is_monitoring:
            self.root.after(0, self._on_party_once_self_stopped)
            return
        self.root.after(300, self._schedule_party_once_watch)

    def _on_party_once_self_stopped(self) -> None:
        if not self.running:
            return
        if self.var_run_mode.get() != "spectrum":
            return
        self._log("[系统] 找光谱监控已结束（任务内停止）。")
        self.stop()

    def _log(self, message: str) -> None:
        ts = time.strftime("%H:%M:%S")
        line = f"{ts} {message}\n"
        self.root.after(0, self._append_log, line)

    def _append_log(self, line: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _tap_key(self, key: str) -> None:
        keyboard.press(key)
        time.sleep(self.game_key_hold_seconds)
        keyboard.release(key)

    def _normalize_send_key(self, key: str) -> str:
        n = (key or "").strip().lower()
        return _KEY_ALIASES.get(n, n)

    def _key_down_game(self, key: str) -> None:
        k = self._normalize_send_key(key)
        if not k:
            return
        try:
            keyboard.press(k)
            return
        except Exception:
            pass
        try:
            pyautogui.keyDown(_PY_AUTO_KEY_ALIASES.get(k, k))
        except Exception:
            pass

    def _key_up_game(self, key: str) -> None:
        k = self._normalize_send_key(key)
        if not k:
            return
        try:
            keyboard.release(k)
            return
        except Exception:
            pass
        try:
            pyautogui.keyUp(_PY_AUTO_KEY_ALIASES.get(k, k))
        except Exception:
            pass

    def _tap_game_key_stable(self, key: str) -> None:
        # 游戏里对“瞬时点按”不稳定，这里改为短按住再释放并兜底重试。
        k = self._normalize_send_key(key)
        if not k:
            return
        hold_seconds = max(0.03, self.up_press_hold_seconds)
        try:
            keyboard.press(k)
            time.sleep(hold_seconds)
            keyboard.release(k)
            return
        except Exception:
            pass
        k2 = _PY_AUTO_KEY_ALIASES.get(k, k)
        try:
            pyautogui.keyDown(k2)
            time.sleep(hold_seconds)
            pyautogui.keyUp(k2)
        except Exception:
            pass

    def _normalize_key(self, keysym: str) -> str:
        m = {
            "Return": "enter",
            "space": "space",
            "Escape": "esc",
            "Control_L": "ctrl",
            "Control_R": "ctrl",
            "Shift_L": "shift",
            "Shift_R": "shift",
            "Alt_L": "alt",
            "Alt_R": "alt",
        }
        return m.get(keysym, keysym.lower())

    def _start_set_gather_key(self) -> None:
        self.pending_key_target = "gather"
        self.btn_gather_key.configure(text="请按键...")
        self._log("[设置] 请按下新的采集键")
        self.root.focus_force()

    def _on_key_press(self, event: tk.Event) -> None:
        if not self.pending_key_target:
            return
        key = self._normalize_key(event.keysym)
        if not key:
            return
        if self.pending_key_target == "gather":
            self.gather_key = key
            self.btn_gather_key.configure(text=key.upper())
            self._set_ini("Settings", "GatherKey", self.gather_key)
            self._log(f"[设置] 采集键已设置为 {key}")
        self.pending_key_target = None
        self._log("[设置] 按键设置完成")

    def _wait_or_stop(self, seconds: float) -> bool:
        end_time = time.time() + max(0.0, seconds)
        while time.time() < end_time:
            if self.stop_event.is_set():
                return False
            if self.auto_stop_deadline is not None and time.monotonic() >= self.auto_stop_deadline:
                self._log("[系统] 定时时间已到，自动停止。")
                self.stop_event.set()
                return False
            time.sleep(0.02)
        return True

    def _find(self, image_name: str) -> tuple[bool, Optional[float]]:
        return find_image_with_score(
            SEARCH_RECT, self.picture_dir / image_name, threshold=self.match_threshold
        )

    def _click_if_found(self, image_name: str) -> bool:
        center = get_image_center(SEARCH_RECT, self.picture_dir / image_name, threshold=self.match_threshold)
        if center is None:
            return False
        pyautogui.click(center[0], center[1])
        return True

    def _activate_window_once_if_needed(self) -> None:
        if not self.need_activate_window_once:
            return
        for image_name in ("无名村.png", "图书馆地图.png", "工会大厅.png", "光谱退场.png"):
            center = get_image_center(SEARCH_RECT, self.picture_dir / image_name, threshold=self.match_threshold)
            if center is None:
                continue
            pyautogui.click(center[0], center[1])
            cur_x, cur_y = pyautogui.position()
            pyautogui.moveTo(cur_x + 50, cur_y)
            self.need_activate_window_once = False
            self._log(f"[激活] 命中 {image_name}，已点击中心激活窗口")
            return
        self._log("[激活] 未命中无名村/图书馆地图/工会大厅/光谱退场，继续等待")

    def _run_until_image_disappears(self, image_name: str, hold_key: str) -> None:
        reverse_key = "right" if hold_key == "left" else "left" if hold_key == "right" else hold_key

        def _run_stage(stage_key: str, seconds: float) -> tuple[bool, bool]:
            """返回 (是否消失, 是否被停止)。"""
            self._key_down_game(stage_key)
            start = time.time()
            try:
                while not self.stop_event.is_set():
                    found, _ = self._find(image_name)
                    if not found:
                        return True, False
                    if time.time() - start >= seconds:
                        return False, False
                    self._tap_game_key_stable("up")
                    if not self._wait_or_stop(self.up_press_interval_seconds):
                        return False, True
                return False, True
            finally:
                self._key_up_game(stage_key)

        try:
            cleared, stopped = _run_stage(hold_key, self.up_hold_timeout_seconds)
            if stopped or cleared:
                return

            self._log(f"[脱困] {image_name} 反着来一次")
            cleared, stopped = _run_stage(reverse_key, 3.0)
            if stopped or cleared:
                return

            self._log(f"[脱困] {image_name} 还没出去？再来一次")
            cleared, stopped = _run_stage(reverse_key, 10.0)
            if stopped or cleared:
                return

            raise RuntimeError(
                f"按住 {hold_key} 点按 up {self.up_hold_timeout_seconds:.1f}秒 + 反方向 {reverse_key} 3秒 + 10秒后仍匹配 {image_name}"
            )
        finally:
            # 兜底释放，避免异常时残留方向键被按住
            self._key_up_game(hold_key)
            self._key_up_game(reverse_key)

    def process_once(self) -> None:
        self._activate_window_once_if_needed()

        found_nameless, score_nameless = self._find("无名村.png")
        if found_nameless:
            self._log(f"[无名村] ，开始进入图书馆...")
            if not self._wait_or_stop(0.5):
                return
            for name in ("下拉.png", "次元.png", "图书馆.png", "移动.png"):
                if self.stop_event.is_set():
                    return
                if not self._click_if_found(name):
                    self._log(f"[无名村] 未找到 {name}，流程终止")
                    break
                self._log(f"[无名村] 已点击 {name}")
                cur_x, cur_y = pyautogui.position()
                pyautogui.moveTo(cur_x + 50, cur_y)
                if not self._wait_or_stop(self.pre_click_interval_seconds):
                    return

        found_team_map, score_team_map = self._find("图书馆地图.png")
        if found_team_map:
            self._log(f"[图书馆地图] 准备离开...")
            self._run_until_image_disappears("图书馆地图.png", "left")

        found_guild, score_guild = self._find("工会大厅.png")
        if found_guild:
            self._log(f"[工会大厅] 准备离开...")
            self._run_until_image_disappears("工会大厅.png", "right")

        found_spec_exit, score_spec = self._find("光谱退场.png")
        if found_spec_exit:
            self._log(f"[光谱退场] 命中")
            if self._click_if_found("光谱退场npc.png"):
                self._log("[光谱退场] 点击光谱退场npc")
                cur_x, cur_y = pyautogui.position()
                pyautogui.moveTo(cur_x + 50, cur_y)
                if not self._wait_or_stop(0.2):
                    return
                self._tap_key(self.gather_key)
                if not self._wait_or_stop(self.double_c_interval_seconds):
                    return
                self._tap_key(self.gather_key)
                self._log("[光谱退场] 按采集键")
            else:
                self._log("[光谱退场] 未找到 光谱退场npc")

    def _worker_loop(self) -> None:
        self._log("[系统] 监控开始")
        try:
            while not self.stop_event.is_set():
                if self.auto_stop_deadline is not None and time.monotonic() >= self.auto_stop_deadline:
                    self._log("[系统] 定时时间已到，自动停止。")
                    self.root.after(0, self.stop)
                    break
                self.process_once()
                if self.stop_event.is_set():
                    break
                if not self._wait_or_stop(self.poll_interval_seconds):
                    break
        except Exception as e:
            self._log(f"[异常] {e}")
            self.root.after(0, self.stop)
            return
        self._log("[系统] 监控已停止")

    def _on_hotkey_toggle(self) -> None:
        self.root.after(0, self.toggle_running)

    def _register_hotkeys(self) -> None:
        try:
            self._f12_hotkey_ref = keyboard.add_hotkey("f12", self._on_hotkey_toggle, suppress=False)
            self._f12_hotkey_registered = True
            self._log("[系统] 全局热键已注册：F12 开始/停止")
        except Exception as e:
            self._f12_hotkey_registered = False
            self._f12_hotkey_ref = None
            self._log(f"[系统] F12 热键注册失败：{e}")

    def _unhook_hotkeys(self) -> None:
        if not self._f12_hotkey_registered:
            return
        try:
            if self._f12_hotkey_ref is not None:
                keyboard.remove_hotkey(self._f12_hotkey_ref)
        except Exception:
            pass
        self._f12_hotkey_registered = False
        self._f12_hotkey_ref = None

    def toggle_running(self) -> None:
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        if self.running:
            return

        self.timer_enabled = bool(self.var_timer_enabled.get())
        self.timer_minutes = self.ent_timer_minutes.get().strip() or "60"
        self._set_ini("Settings", "TimerEnabled", "1" if self.timer_enabled else "0")
        self._set_ini("Settings", "TimerMinutes", self.timer_minutes)

        mode = self.var_run_mode.get()
        if mode == "spectrum":
            if not self._ensure_party_once_runner():
                return
            self._sync_party_once_timer_and_keys()
            self.stop_event.clear()
            self.auto_stop_deadline = None
            self._log("[系统] 找光谱监控开始（F12 或「停止」结束）")
            if self.timer_enabled:
                try:
                    minutes = float(self.timer_minutes)
                    if minutes <= 0:
                        raise ValueError
                    self._log(
                        f"[系统] 定时停止已开启：约 {minutes:g} 分钟内由组队逻辑在适当时机停止（与 Party 一致）"
                    )
                except Exception:
                    self._log(f"[系统] 定时停止参数无效：{self.timer_minutes}，已忽略定时")

            self.running = True
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_stop.configure(state=tk.NORMAL)
            self._set_run_mode_widgets_state(tk.DISABLED)
            self._party_once_runner.start_monitoring()
            self._schedule_party_once_watch()
            return

        self.auto_stop_deadline = None
        if self.timer_enabled:
            try:
                minutes = float(self.timer_minutes)
                if minutes <= 0:
                    raise ValueError
                self.auto_stop_deadline = time.monotonic() + minutes * 60.0
                self._log(f"[系统] 定时停止已开启：{minutes:g} 分钟后自动停止")
            except Exception:
                self._log(f"[系统] 定时停止参数无效：{self.timer_minutes}，已忽略定时")

        self.stop_event.clear()
        self.need_activate_window_once = True
        self.running = True
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self._set_run_mode_widgets_state(tk.DISABLED)
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def stop(self) -> None:
        if not self.running:
            return
        if self.var_run_mode.get() == "spectrum" and self._party_once_runner is not None:
            try:
                self._party_once_runner.stop_monitoring()
            except Exception:
                pass
        self.stop_event.set()
        self.auto_stop_deadline = None
        self.running = False
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        self._set_run_mode_widgets_state(tk.NORMAL)
        self._log("[系统] 停止中...")

    def on_close(self) -> None:
        self.stop_event.set()
        if self._party_once_runner is not None:
            try:
                self._party_once_runner.stop_monitoring()
            except Exception:
                pass
            self._party_once_runner = None
        if self._party_once_host is not None:
            try:
                self._party_once_host.destroy()
            except Exception:
                pass
            self._party_once_host = None
        self._unhook_hotkeys()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    PartyBugApp().run()
