from __future__ import annotations

import configparser
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk
from typing import Optional

import keyboard
import pyautogui

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Utils.find_image import find_image_with_score, get_image_center


SEARCH_RECT = (0, 0, 1366, 768)


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
        self.up_hold_timeout_seconds = 5.0
        self.pre_click_interval_seconds = 0.2
        self.gather_key = self._ini_get("Settings", "GatherKey", "space")
        self.jump_key = self._ini_get("Settings", "JumpKey", "c")
        self.timer_enabled = self._ini_get("Settings", "TimerEnabled", "0") == "1"
        self.timer_minutes = self._ini_get("Settings", "TimerMinutes", "60")
        self.pending_key_target: Optional[str] = None

        self.running = False
        self.stop_event = threading.Event()
        self.worker: Optional[threading.Thread] = None
        self._f12_hotkey_registered = False
        self._f12_hotkey_ref = None
        self.need_activate_window_once = False
        self.auto_stop_deadline: Optional[float] = None

        self.root = tk.Tk()
        self.root.title("PartyBug GUI")
        self.root.geometry("360x300")
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

        ttk.Label(top, text="跳跃键").grid(row=0, column=2, padx=(16, 6), pady=4, sticky="w")
        self.btn_jump_key = ttk.Button(top, text=self.jump_key.upper(), width=12, command=self._start_set_jump_key)
        self.btn_jump_key.grid(row=0, column=3, pady=4, sticky="w")

        self.var_timer_enabled = tk.IntVar(value=1 if self.timer_enabled else 0)
        ttk.Checkbutton(top, text="定时停止(分钟)", variable=self.var_timer_enabled).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        self.ent_timer_minutes = ttk.Entry(top, width=8)
        self.ent_timer_minutes.insert(0, self.timer_minutes)
        self.ent_timer_minutes.grid(row=1, column=2, sticky="w", pady=(4, 0))

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

    def _start_set_jump_key(self) -> None:
        self.pending_key_target = "jump"
        self.btn_jump_key.configure(text="请按键...")
        self._log("[设置] 请按下新的跳跃键")
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
        elif self.pending_key_target == "jump":
            self.jump_key = key
            self.btn_jump_key.configure(text=key.upper())
            self._set_ini("Settings", "JumpKey", self.jump_key)
            self._log(f"[设置] 跳跃键已设置为 {key}")
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
        for image_name in ("无名村.png", "组队地图.png", "工会大厅.png", "光谱退场.png"):
            center = get_image_center(SEARCH_RECT, self.picture_dir / image_name, threshold=self.match_threshold)
            if center is None:
                continue
            pyautogui.click(center[0], center[1])
            cur_x, cur_y = pyautogui.position()
            pyautogui.moveTo(cur_x + 50, cur_y)
            self.need_activate_window_once = False
            self._log(f"[激活] 命中 {image_name}，已点击中心激活窗口")
            return
        self._log("[激活] 未命中无名村/组队地图/工会大厅/光谱退场，继续等待")

    def _run_until_image_disappears(self, image_name: str, hold_key: str) -> None:
        keyboard.press(hold_key)
        start = time.time()
        try:
            while not self.stop_event.is_set():
                found, _ = self._find(image_name)
                if not found:
                    break
                if time.time() - start >= self.up_hold_timeout_seconds:
                    raise RuntimeError(f"按住 {hold_key} 点按 up 超过{self.up_hold_timeout_seconds:.1f}秒仍匹配 {image_name}")
                self._tap_key("up")
                if not self._wait_or_stop(self.double_c_interval_seconds):
                    return
        finally:
            keyboard.release(hold_key)

    def process_once(self) -> None:
        self._activate_window_once_if_needed()

        found_nameless, score_nameless = self._find("无名村.png")
        if found_nameless:
            self._log(f"[无名村] 命中 score={score_nameless:.4f}，开始 下拉->次元->组队->移动")
            if not self._wait_or_stop(1.0):
                return
            for name in ("下拉.png", "次元.png", "组队.png", "移动.png"):
                if self.stop_event.is_set():
                    return
                if not self._click_if_found(name):
                    self._log(f"[无名村] 未找到 {name}，前置流程终止")
                    break
                self._log(f"[无名村] 已点击 {name}")
                cur_x, cur_y = pyautogui.position()
                pyautogui.moveTo(cur_x + 50, cur_y)
                if not self._wait_or_stop(self.pre_click_interval_seconds):
                    return

        found_team_map, score_team_map = self._find("组队地图.png")
        if found_team_map:
            self._log(f"[组队地图] 命中 score={score_team_map:.4f}")
            if not self._wait_or_stop(1):
                return
            self._tap_key("left")
            if not self._wait_or_stop(0.1):
                return
            self._tap_key(self.jump_key)
            if not self._wait_or_stop(self.double_c_interval_seconds):
                return
            self._tap_key(self.jump_key)
            if not self._wait_or_stop(1.0):
                return
            self._run_until_image_disappears("组队地图.png", "left")

        found_guild, score_guild = self._find("工会大厅.png")
        if found_guild:
            self._log(f"[工会大厅] 命中 score={score_guild:.4f}")
            if not self._wait_or_stop(1):
                return
            self._tap_key(self.jump_key)
            if not self._wait_or_stop(self.double_c_interval_seconds):
                return
            self._tap_key(self.jump_key)
            if not self._wait_or_stop(1.0):
                return
            self._run_until_image_disappears("工会大厅.png", "right")

        found_spec_exit, score_spec = self._find("光谱退场.png")
        if found_spec_exit:
            self._log(f"[光谱退场] 命中 score={score_spec:.4f}")
            if self._click_if_found("光谱退场npc.png"):
                self._log("[光谱退场] 已点击 光谱退场npc.png")
                if not self._wait_or_stop(0.2):
                    return
                self._tap_key(self.gather_key)
                if not self._wait_or_stop(self.double_c_interval_seconds):
                    return
                self._tap_key(self.gather_key)
                self._log("[光谱退场] 已按两次采集键")
            else:
                self._log("[光谱退场] 未找到 光谱退场npc.png")

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
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def stop(self) -> None:
        if not self.running:
            return
        self.stop_event.set()
        self.auto_stop_deadline = None
        self.running = False
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        self._log("[系统] 停止中...")

    def on_close(self) -> None:
        self.stop_event.set()
        self._unhook_hotkeys()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    PartyBugApp().run()
