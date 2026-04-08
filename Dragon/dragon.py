from __future__ import annotations

import configparser
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable, Optional

import pyautogui

try:
    import keyboard  # type: ignore
except Exception:  # pragma: no cover
    keyboard = None

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Utils.find_image import find_image_and_click, get_image_center


def _key_down(key: str) -> None:
    if keyboard is not None:
        try:
            keyboard.press(key)
            return
        except Exception:
            pass
    try:
        pyautogui.keyDown(key)
    except Exception:
        pass


def _key_up(key: str) -> None:
    if keyboard is not None:
        try:
            keyboard.release(key)
            return
        except Exception:
            pass
    try:
        pyautogui.keyUp(key)
    except Exception:
        pass


def _tap_key_stable(key: str, hold_seconds: float = 0.03) -> None:
    _key_down(key)
    time.sleep(max(0.0, hold_seconds))
    _key_up(key)


def _should_stop(stop_event: threading.Event, stop_key: str) -> bool:
    # 仅以 stop_event 作为停止信号。
    # F12 在 GUI 中通过 keyboard.add_hotkey 触发 toggle_running；
    # 如果这里再用 is_pressed(stop_key) 轮询，会导致“按下 F12 启动后，因为键尚未松开而立刻停止”。
    return stop_event.is_set()


def _wait(seconds: float, stop_event: threading.Event, stop_key: str) -> bool:
    deadline = time.time() + max(0.0, seconds)
    while time.time() < deadline:
        if _should_stop(stop_event, stop_key):
            return False
        time.sleep(0.05)
    return True


def _search_rect() -> tuple[int, int, int, int]:
    w, h = pyautogui.size()
    return 0, 0, int(w), int(h)


def _wait_image(
    path: Path,
    timeout_seconds: float,
    stop_event: threading.Event,
    stop_key: str,
    interval: float = 0.2,
):
    end_at = time.time() + max(0.0, timeout_seconds)
    rect = _search_rect()
    while time.time() < end_at:
        if _should_stop(stop_event, stop_key):
            return None
        center = get_image_center(rect, path)
        if center is not None:
            return center
        time.sleep(max(0.05, interval))
    return None


def _click_image(
    path: Path,
    timeout_seconds: float,
    stop_event: threading.Event,
    stop_key: str,
    interval: float = 0.2,
) -> bool:
    end_at = time.time() + max(0.0, timeout_seconds)
    rect = _search_rect()
    while time.time() < end_at:
        if _should_stop(stop_event, stop_key):
            return False
        if find_image_and_click(rect, path):
            return True
        time.sleep(max(0.05, interval))
    return False


def _monitor_retreat(
    pictures: dict[str, Path],
    retreat_event: threading.Event,
    stop_event: threading.Event,
    stop_key: str,
) -> None:
    rect = _search_rect()
    target = pictures["retreat"]
    while not _should_stop(stop_event, stop_key):
        try:
            if get_image_center(rect, target) is not None:
                retreat_event.set()
        except Exception:
            pass
        # 每 3 秒查一次，但保持可快速响应停止
        for _ in range(60):
            if _should_stop(stop_event, stop_key):
                return
            time.sleep(0.05)


def _handle_retreat_flow(
    *,
    pictures: dict[str, Path],
    stop_event: threading.Event,
    stop_key: str,
    auction_key: str,
    lina_home_xy: tuple[int, int],
    world_map_key: str,
    fav_xy: tuple[int, int],
    log: Optional[Callable[[str], None]] = None,
    start_from: str = "retreat",
) -> None:
    start_from = (start_from or "retreat").strip().lower()
    if start_from not in ("retreat", "home", "jj"):
        start_from = "retreat"

    if start_from == "retreat":
        # 1+2：按拍卖 -> 0.5s -> 点击丽娜家坐标；2s 后找“家”；直到找到“家”
        while True:
            if _should_stop(stop_event, stop_key):
                return
            _tap_key_stable(auction_key)
            if not _wait(0.5, stop_event, stop_key):
                return
            try:
                pyautogui.click(lina_home_xy[0], lina_home_xy[1])
            except Exception:
                pass
            if not _wait(2.0, stop_event, stop_key):
                return
            if get_image_center(_search_rect(), pictures["home"]) is not None:
                if log is not None:
                    log("到家，准备去啾啾岛")
                break
    elif start_from == "home":
        if log is not None:
            log("检测到已在家，准备去啾啾岛")

    if start_from in ("retreat", "home"):
        # 3：世界地图 -> 0.2s -> 双击收藏坐标 -> 0.2s -> 找“确认”并点击
        _tap_key_stable(world_map_key)
        if not _wait(0.2, stop_event, stop_key):
            return
        try:
            pyautogui.doubleClick(fav_xy[0], fav_xy[1])
        except Exception:
            return
        if not _wait(0.2, stop_event, stop_key):
            return
        _click_image(pictures["confirm"], timeout_seconds=6.0, stop_event=stop_event, stop_key=stop_key)
    else:
        if log is not None:
            log("检测到已在啾啾岛，准备进场")

    # 4：2s 后找“啾啾地图”；若命中则再按一次世界地图键关闭/切层，然后继续找“啾啾岛屠龙姐”等
    if not _wait(2.0, stop_event, stop_key):
        return
    rect = _search_rect()
    if get_image_center(rect, pictures["jj_map"]) is not None:
        _tap_key_stable(world_map_key)
        if not _wait(0.2, stop_event, stop_key):
            return

    center = _wait_image(pictures["jj_island"], timeout_seconds=10.0, stop_event=stop_event, stop_key=stop_key)
    if center is not None and not _should_stop(stop_event, stop_key):
        if log is not None:
            log("到啾啾岛，准备进场")
        try:
            pyautogui.click(center[0], center[1] - 50)
        except Exception:
            pass
    if not _wait(0.2, stop_event, stop_key):
        return
    _click_image(pictures["enter_war"], timeout_seconds=10.0, stop_event=stop_event, stop_key=stop_key)
    if not _wait(0.2, stop_event, stop_key):
        return
    _click_image(pictures["yes"], timeout_seconds=10.0, stop_event=stop_event, stop_key=stop_key)


def keysym_to_key_name(keysym: str) -> Optional[str]:
    if not keysym:
        return None
    m = {
        "Return": "enter",
        "KP_Enter": "enter",
        "space": "space",
        "Escape": "esc",
        "Prior": "page up",
        "Next": "page down",
        "comma": ",",
    }
    return m.get(keysym, keysym.lower())


class DragonApp:
    def __init__(self) -> None:
        # 资源（picture/icon）在打包后位于临时解压目录；配置文件必须放在 exe 同目录以便持久化
        self.script_dir = Path(__file__).resolve().parent
        self.frozen = bool(getattr(sys, "frozen", False))
        self.base_dir = Path(sys.executable).resolve().parent if self.frozen else self.script_dir
        self.ini_file = self.base_dir / "dragon_settings.ini"
        self.cp = configparser.ConfigParser()
        if self.ini_file.is_file():
            self.cp.read(self.ini_file, encoding="utf-8-sig")

        self.stop_key = "f12"

        self.attack_key = self._ini_get("Keys", "AttackKey", "a")
        self.auction_key = self._ini_get("Keys", "AuctionKey", "page up")
        self.world_map_key = self._ini_get("Keys", "WorldMapKey", ",")

        self.fav_x = int(self._ini_get("Points", "FavX", "1127"))
        self.fav_y = int(self._ini_get("Points", "FavY", "533"))
        self.lina_x = int(self._ini_get("Points", "LinaX", "413"))
        self.lina_y = int(self._ini_get("Points", "LinaY", "651"))

        self.attack_duration_seconds = float(self._ini_get("Attack", "DurationSeconds", "60"))
        self.tap_hold_seconds = float(self._ini_get("Attack", "TapHoldSeconds", "0.05"))
        self.tap_interval_seconds = float(self._ini_get("Attack", "TapIntervalSeconds", "0.05"))

        self.pictures = {
            "retreat": self.script_dir / "picture" / "退场屠龙姐.png",
            "home": self.script_dir / "picture" / "家.png",
            "confirm": self.script_dir / "picture" / "确认.png",
            "jj_map": self.script_dir / "picture" / "啾啾地图.png",
            "jj_island": self.script_dir / "picture" / "啾啾岛屠龙姐.png",
            "enter_war": self.script_dir / "picture" / "进入联盟战地.png",
            "yes": self.script_dir / "picture" / "是.png",
        }

        self.running = False
        self.stop_event = threading.Event()
        self.retreat_event = threading.Event()
        self.worker: Optional[threading.Thread] = None
        self.monitor: Optional[threading.Thread] = None

        self.pending_key_target: Optional[str] = None
        self.pending_point_target: Optional[str] = None

        self.root = tk.Tk()
        self.root.title("好厉害屠龙")
        self.root.geometry("420x520")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        icon_path = self.script_dir / "icon" / "icon.png"
        if icon_path.is_file():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
                self._icon_ref = icon  # 防止被 GC
            except Exception:
                pass

        self._build_ui()
        self._register_hotkey()

    def _ini_get(self, sec: str, key: str, default: str) -> str:
        try:
            return self.cp.get(sec, key, fallback=default)
        except Exception:
            return default

    def _ini_set(self, sec: str, key: str, val: str) -> None:
        if not self.cp.has_section(sec):
            self.cp.add_section(sec)
        self.cp.set(sec, key, str(val))
        with open(self.ini_file, "w", encoding="utf-8") as f:
            self.cp.write(f)

    def _register_hotkey(self) -> None:
        if keyboard is None:
            return
        try:
            keyboard.add_hotkey(self.stop_key, lambda: self.root.after(0, self.toggle_running))
        except Exception:
            pass

    def _build_ui(self) -> None:
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        key_box = ttk.LabelFrame(frm, text="按键配置", padding=10)
        key_box.pack(fill=tk.X)

        row = ttk.Frame(key_box)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="攻击键").pack(side=tk.LEFT)
        self.btn_attack_key = ttk.Button(row, text=self.attack_key.upper(), width=14, command=lambda: self._start_set_key("attack"))
        self.btn_attack_key.pack(side=tk.RIGHT)

        row = ttk.Frame(key_box)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="拍卖键").pack(side=tk.LEFT)
        self.btn_auction_key = ttk.Button(row, text=self.auction_key.upper(), width=14, command=lambda: self._start_set_key("auction"))
        self.btn_auction_key.pack(side=tk.RIGHT)

        row = ttk.Frame(key_box)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="世界地图键").pack(side=tk.LEFT)
        self.btn_world_map_key = ttk.Button(
            row,
            text=self.world_map_key.upper(),
            width=14,
            command=lambda: self._start_set_key("world_map"),
        )
        self.btn_world_map_key.pack(side=tk.RIGHT)

        point_box = ttk.LabelFrame(frm, text="坐标配置", padding=10)
        point_box.pack(fill=tk.X, pady=(10, 0))
        row = ttk.Frame(point_box)
        row.pack(fill=tk.X, pady=4)
        self.lbl_fav = ttk.Label(row, text=f"收藏地图坐标：({self.fav_x},{self.fav_y})")
        self.lbl_fav.pack(side=tk.LEFT)
        self.btn_set_fav = ttk.Button(row, text="设置", width=10, command=lambda: self._start_set_point("fav"))
        self.btn_set_fav.pack(side=tk.RIGHT)

        row = ttk.Frame(point_box)
        row.pack(fill=tk.X, pady=4)
        self.lbl_lina = ttk.Label(row, text=f"丽娜家坐标：({self.lina_x},{self.lina_y})")
        self.lbl_lina.pack(side=tk.LEFT)
        self.btn_set_lina = ttk.Button(row, text="设置", width=10, command=lambda: self._start_set_point("lina"))
        self.btn_set_lina.pack(side=tk.RIGHT)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(14, 0))
        self.btn_start = ttk.Button(btns, text="▶ 开始 (F12)", command=self.start, width=18)
        self.btn_start.pack(side=tk.LEFT)
        self.btn_stop = ttk.Button(btns, text="⏹ 停止 (F12)", command=self.stop, width=18, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.RIGHT)

        self.txt = tk.Text(frm, height=7)
        self.txt.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self._log("就绪，等待开始，开始后鼠标请勿遮挡关键NPC和左上角小地图")

        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<Button-1>", self._on_mouse_click)

    def _log(self, s: str) -> None:
        try:
            ts = time.strftime("%H:%M:%S")
            self.txt.insert(tk.END, f"[{ts}] {s}\n")
            self.txt.see(tk.END)
        except Exception:
            pass

    def _start_set_key(self, which: str) -> None:
        self.pending_key_target = which
        self.pending_point_target = None
        btn = {
            "attack": self.btn_attack_key,
            "auction": self.btn_auction_key,
            "world_map": self.btn_world_map_key,
        }.get(which)
        if btn is not None:
            btn.configure(text="请按键...")
        self._log("请按下新的按键。")
        self.root.focus_force()

    def _start_set_point(self, which: str) -> None:
        self.pending_point_target = which
        self.pending_key_target = None
        self._log("请在全屏蒙板上点击目标位置（会记录屏幕坐标）。按 ESC 取消。")
        self._show_point_overlay()

    def _show_point_overlay(self) -> None:
        # 全屏透明蒙板：用于稳定捕获屏幕坐标（不依赖主窗口是否激活）
        if getattr(self, "_overlay", None) is not None:
            try:
                self._overlay.destroy()
            except Exception:
                pass
            self._overlay = None

        ov = tk.Toplevel(self.root)
        self._overlay = ov
        ov.withdraw()
        ov.overrideredirect(True)
        try:
            ov.attributes("-topmost", True)
        except Exception:
            pass
        try:
            ov.attributes("-alpha", 0.15)
        except Exception:
            pass
        ov.configure(bg="black", cursor="crosshair")
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        ov.geometry(f"{w}x{h}+0+0")

        hint = tk.Label(
            ov,
            text="点击以记录坐标（ESC 取消）",
            fg="white",
            bg="black",
            font=("Segoe UI", 14),
        )
        hint.place(x=12, y=12)

        def _cancel(_evt=None) -> None:
            self.pending_point_target = None
            try:
                ov.destroy()
            except Exception:
                pass
            self._overlay = None
            self._log("已取消坐标设置。")

        def _capture(evt: tk.Event) -> None:
            if not self.pending_point_target:
                _cancel()
                return
            which = self.pending_point_target
            self.pending_point_target = None
            x = int(getattr(evt, "x_root", 0))
            y = int(getattr(evt, "y_root", 0))
            try:
                ov.destroy()
            except Exception:
                pass
            self._overlay = None
            self._set_point(which, x, y)

        ov.bind("<Escape>", _cancel)
        ov.bind("<Button-1>", _capture)
        ov.deiconify()
        ov.focus_force()

    def _on_key_press(self, event: tk.Event) -> None:
        if not self.pending_key_target:
            return
        key = keysym_to_key_name(getattr(event, "keysym", ""))
        if not key:
            return
        which = self.pending_key_target
        self.pending_key_target = None
        if which == "attack":
            self.attack_key = key
            self.btn_attack_key.configure(text=key.upper())
            self._ini_set("Keys", "AttackKey", key)
        elif which == "auction":
            self.auction_key = key
            self.btn_auction_key.configure(text=key.upper())
            self._ini_set("Keys", "AuctionKey", key)
        elif which == "world_map":
            self.world_map_key = key
            self.btn_world_map_key.configure(text=key.upper())
            self._ini_set("Keys", "WorldMapKey", key)
        self._log(f"已设置按键：{which} = {key}")

    def _set_point(self, which: str, x: int, y: int) -> None:
        if which == "fav":
            self.fav_x, self.fav_y = x, y
            self.lbl_fav.configure(text=f"收藏地图坐标：({self.fav_x},{self.fav_y})")
            self._ini_set("Points", "FavX", str(x))
            self._ini_set("Points", "FavY", str(y))
            self._log(f"已设置收藏地图坐标：({x},{y})")
        elif which == "lina":
            self.lina_x, self.lina_y = x, y
            self.lbl_lina.configure(text=f"丽娜家坐标：({self.lina_x},{self.lina_y})")
            self._ini_set("Points", "LinaX", str(x))
            self._ini_set("Points", "LinaY", str(y))
            self._log(f"已设置丽娜家坐标：({x},{y})")

    def _on_mouse_click(self, event: tk.Event) -> None:
        # 兜底：如果用户仍在主窗口上点击，也能记录
        if not self.pending_point_target:
            return
        which = self.pending_point_target
        self.pending_point_target = None
        x = int(getattr(event, "x_root", 0))
        y = int(getattr(event, "y_root", 0))
        self._set_point(which, x, y)

    def toggle_running(self) -> None:
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.retreat_event.clear()
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self._log("开始运行。")
        try:
            pyautogui.click(15, 15)
            time.sleep(0.1)
        except Exception:
            pass

        self.monitor = threading.Thread(
            target=_monitor_retreat,
            args=(self.pictures, self.retreat_event, self.stop_event, self.stop_key),
            daemon=True,
            name="retreat-monitor",
        )
        self.monitor.start()

        self.worker = threading.Thread(target=self._worker_loop, daemon=True, name="dragon-worker")
        self.worker.start()

    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        _key_up(self.attack_key)
        self._log("已停止。")

    def on_close(self) -> None:
        try:
            self.stop()
        finally:
            self.root.destroy()

    def _worker_loop(self) -> None:
        try:
            # 开始后先扫描一次：家、啾啾岛屠龙姐、退场屠龙姐
            rect = _search_rect()
            if get_image_center(rect, self.pictures["home"]) is not None:
                self.root.after(0, lambda: self._log("启动检测：在家"))
                _handle_retreat_flow(
                    pictures=self.pictures,
                    stop_event=self.stop_event,
                    stop_key=self.stop_key,
                    auction_key=self.auction_key,
                    lina_home_xy=(self.lina_x, self.lina_y),
                    world_map_key=self.world_map_key,
                    fav_xy=(self.fav_x, self.fav_y),
                    log=lambda msg: self.root.after(0, lambda: self._log(msg)),
                    start_from="home",
                )
                self.root.after(0, lambda: self._log("2秒后开始攻击"))
                if not _wait(2.0, self.stop_event, self.stop_key):
                    return
            elif get_image_center(rect, self.pictures["jj_island"]) is not None:
                self.root.after(0, lambda: self._log("启动检测：在啾啾岛"))
                _handle_retreat_flow(
                    pictures=self.pictures,
                    stop_event=self.stop_event,
                    stop_key=self.stop_key,
                    auction_key=self.auction_key,
                    lina_home_xy=(self.lina_x, self.lina_y),
                    world_map_key=self.world_map_key,
                    fav_xy=(self.fav_x, self.fav_y),
                    log=lambda msg: self.root.after(0, lambda: self._log(msg)),
                    start_from="jj",
                )
                self.root.after(0, lambda: self._log("2秒后开始攻击"))
                if not _wait(2.0, self.stop_event, self.stop_key):
                    return
            elif get_image_center(rect, self.pictures["retreat"]) is not None:
                self.root.after(0, lambda: self._log("启动检测：在退场图"))
                _handle_retreat_flow(
                    pictures=self.pictures,
                    stop_event=self.stop_event,
                    stop_key=self.stop_key,
                    auction_key=self.auction_key,
                    lina_home_xy=(self.lina_x, self.lina_y),
                    world_map_key=self.world_map_key,
                    fav_xy=(self.fav_x, self.fav_y),
                    log=lambda msg: self.root.after(0, lambda: self._log(msg)),
                    start_from="retreat",
                )
                self.root.after(0, lambda: self._log("2秒后开始攻击"))
                if not _wait(2.0, self.stop_event, self.stop_key):
                    return

            while not _should_stop(self.stop_event, self.stop_key):
                end_at = time.time() + max(0.0, self.attack_duration_seconds)
                while time.time() < end_at:
                    if _should_stop(self.stop_event, self.stop_key):
                        return
                    if self.retreat_event.is_set():
                        break
                    _tap_key_stable(self.attack_key, hold_seconds=self.tap_hold_seconds)
                    time.sleep(max(0.0, self.tap_interval_seconds))

                if self.retreat_event.is_set():
                    self.retreat_event.clear()
                    self.root.after(0, lambda: self._log("准备回家"))
                    _handle_retreat_flow(
                        pictures=self.pictures,
                        stop_event=self.stop_event,
                        stop_key=self.stop_key,
                        auction_key=self.auction_key,
                        lina_home_xy=(self.lina_x, self.lina_y),
                        world_map_key=self.world_map_key,
                        fav_xy=(self.fav_x, self.fav_y),
                        log=lambda msg: self.root.after(0, lambda: self._log(msg)),
                    )
                    self.root.after(0, lambda: self._log("退场流程结束"))
                    if not _wait(2.0, self.stop_event, self.stop_key):
                        return
                    continue

                time.sleep(0.5)
                _tap_key_stable("left", hold_seconds=self.tap_hold_seconds)
                time.sleep(0.5)
                _tap_key_stable("right", hold_seconds=self.tap_hold_seconds)
        except Exception as e:
            self.root.after(0, lambda: self._log(f"[异常] {e!r}"))
        finally:
            self.root.after(0, self.stop)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    DragonApp().run()

