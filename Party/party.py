# -*- coding: utf-8 -*-
"""
游戏辅助挂机：模板匹配 + 点击连招。
依赖: pip install pyautogui opencv-python numpy pillow keyboard
"""
from __future__ import annotations

import configparser
import ctypes
import sys
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pyautogui
from PIL import Image, ImageTk

from Utils.find_image import _find_image_center_with_score

try:
    import keyboard as kb_lib

    HAS_KEYBOARD = True
except ImportError:
    kb_lib = None
    HAS_KEYBOARD = False

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

pyautogui.FAILSAFE = False

# 固定识别区域：左上角 (0,0)，右下角 (1366,768)，与 picture/ 下模板对应
SEARCH_RECT: Tuple[int, int, int, int] = (0, 0, 1366, 768)

# 车头 / 村庄车头：统一按序找图点击，步间间隔见 _run_carhead_image_sequence
CARHEAD_CLICK_IMAGES: Tuple[str, ...] = (
    "星星.png",
    "游戏中心.png",
    "参加.png",
    "多人组队.png",
    "下个.png",
)

TASK_NAMES: List[str] = [
    "首页提示",
    "任务配置",
]

TASKS_NEED_IMAGE: Dict[str, bool] = {
    "首页提示": False,
    "任务配置": False,
}

TASK_POINTS: Dict[str, List[str]] = {
    "任务配置": ["收藏地图坐标", "多人组队坐标", "系统设置坐标"],
    "拼图区域": [],
    "车头操作": [],
    "村庄车头操作": [],
}

DETECT_TASKS: List[str] = [
    "收藏地图",
    "拼图区域",
]


def _clamp(a: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, a))


def tolerance_to_match_threshold(tolerance: float) -> float:
    """直接使用 OpenCV 阈值（0~1）。"""
    return _clamp(float(tolerance), 0.0, 1.0)


def match_template_in_rect(
    rect: Tuple[int, int, int, int],
    image_path: Path,
    tolerance: float,
) -> Optional[Tuple[int, int]]:
    if not image_path.is_file():
        return None
    th = tolerance_to_match_threshold(tolerance)
    center, _ = _find_image_center_with_score(rect, str(image_path), threshold=th)
    return center


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
    "win": "win"
}


def send_raw_key(name: str, down: bool) -> None:
    n = (name or "").strip()
    if not n:
        return
    if not HAS_KEYBOARD or kb_lib is None:
        return
    low = n.lower()
    k = _KEY_ALIASES.get(low, low)
    if down:
        kb_lib.press(k)
    else:
        kb_lib.release(k)


def keysym_to_keyboard(keysym: str) -> Optional[str]:
    """将 Tk 的 keysym 转为与 Farm 一致的小写键名（修饰键、回车等统一）。"""
    if not keysym:
        return None
    m = {
        "Control_L": "ctrl",
        "Control_R": "ctrl",
        "Shift_L": "shift",
        "Shift_R": "shift",
        "Alt_L": "alt",
        "Alt_R": "alt",
        "Super_L": "windows",
        "Super_R": "windows",
        "Return": "return",
        "KP_Enter": "return",
        "Prior": "page up",
        "Next": "page down",
    }
    return m.get(keysym, keysym.lower())


def send_key_tap(name: str) -> None:
    n = (name or "").strip()
    if not n:
        return
    if not HAS_KEYBOARD or kb_lib is None:
        return
    low = n.lower()
    k = _KEY_ALIASES.get(low, low)
    kb_lib.press_and_release(k)


@dataclass
class PointData:
    x: Any = "未设置"
    y: Any = ""
    wait: str = "300"


class PartyApp:
    def __init__(
        self,
        master: Optional[Any] = None,
        *,
        embed_mode: bool = False,
        config_root: Optional[Path] = None,
        gather_key_supplier: Optional[Callable[[], str]] = None,
    ) -> None:
        self._embed_mode = embed_mode
        self._gather_key_supplier = gather_key_supplier

        self.script_dir = (config_root.resolve() if config_root else Path(__file__).resolve().parent)
        self.frozen = bool(getattr(sys, "frozen", False))
        # 打包后资源通常在 _MEIPASS 里（只读/临时），截图覆盖模板需要可写目录
        self.base_dir = Path(sys.executable).resolve().parent if self.frozen else self.script_dir

        self.picture_dir = self.base_dir / "picture"
        self.picture_dir.mkdir(parents=True, exist_ok=True)
        # 配置与日志也放到可写目录，便于 exe 持久化
        self.ini_file = self.base_dir / "settings.ini"

        self.cp = configparser.ConfigParser()
        if self.ini_file.is_file():
            self.cp.read(self.ini_file, encoding="utf-8-sig")

        self.is_monitoring = False
        self.auto_stop_active = False
        self.auto_stop_end_time = 0.0
        self.is_timer_expired = False

        self.tolerance = float(self._ini_get("Settings", "Tolerance", "0.99") or 0.99)
        self.auction_key = self._ini_get("Settings", "AuctionKey", "")
        self.world_map_key = self._ini_get("Settings", "WorldMapKey", "")
        self.gather_key = self._ini_get("Settings", "GatherKey", "Space")
        self.hook_key = self._ini_get("Settings", "HookKey", "Alt")
        self.carhead_key = self._ini_get("Settings", "CarheadKey", "")

        # 传送后等待固定 2000ms（已移除配置项）
        self.teleport_wait = 2000

        self.points_data: Dict[str, PointData] = {}
        self._load_points()

        self.detect_waits: Dict[str, int] = {}
        self._load_detect_waits()

        self.current_task = "任务配置" if embed_mode else TASK_NAMES[0]
        self.bot_thread: Optional[threading.Thread] = None
        self.log_path = self.base_dir / "party.log"
        self._log_lock = threading.Lock()
        self._last_logged_status = ""

        if self.frozen:
            # 首次启动时把打包内的 picture 资源复制到 exe 同目录（可写）
            self._ensure_picture_resources()

        import tkinter as tk
        from tkinter import ttk, messagebox

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox

        if embed_mode:
            if master is None:
                raise ValueError("embed_mode 需要传入 master（Toplevel）")
            self.root = master
            self.root.title("找光谱 · 任务与全局参数")
            self.root.geometry("860x720")
            self.root.configure(bg="#F5F5F7")
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self._build_gui_embed()
        else:
            self.root = tk.Tk()
            self.root.title("好厉害组队")
            self.root.geometry("820x600")
            self.root.configure(bg="#F5F5F7")
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self._build_gui()

        self.refresh_ui()
        if not embed_mode:
            self._bind_hotkeys()
            self.root.after(1000, self._check_autostop_timer)

    def _ensure_picture_resources(self) -> None:
        """
        PyInstaller --add-data=picture;picture 后，picture 会被解包到 _MEIPASS（临时目录）。
        由于本程序会“覆盖截图模板图片”，因此需要把 picture 复制到 exe 同目录（可写）。
        """
        meipass = getattr(sys, "_MEIPASS", None)
        if not meipass:
            return
        src_picture_dir = Path(meipass) / "picture"
        if not src_picture_dir.is_dir():
            return

        # 只拷贝缺失的文件，避免每次启动都重写用户修改/覆盖后的模板
        for src in src_picture_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(src_picture_dir)
            dst = self.picture_dir / rel
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def _ini_get(self, sec: str, key: str, default: str) -> str:
        if self.cp.has_option(sec, key):
            return self.cp.get(sec, key)
        return default

    def _log_line(self, msg: str) -> None:
        """写入本地日志文件（线程安全）。"""
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
        with self._log_lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

    def _attach_status_logging(self) -> None:
        """记录所有状态栏文案，避免连续重复刷屏。"""
        self._last_logged_status = ""

        def on_var_write(*_args: Any) -> None:
            v = self.status_var.get()
            if v == self._last_logged_status:
                return
            self._last_logged_status = v
            self._log_line(f"[状态] {v}")

        try:
            self.status_var.trace_add("write", on_var_write)
        except AttributeError:
            self.status_var.trace("w", lambda *_a: on_var_write())

    def show_log_detail(self) -> None:
        """打开日志详情弹窗（居中）。"""
        tk = self.tk
        ttk = self.ttk
        win = tk.Toplevel(self.root)
        win.title("日志详情")
        win.transient(self.root)
        win.grab_set()

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(frame, width=92, height=28, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_log() -> None:
            try:
                content = self.log_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                content = "(暂无日志)"
            except Exception as e:
                content = f"(读取日志失败: {e})"
            text.configure(state=tk.NORMAL)
            text.delete("1.0", tk.END)
            text.insert(tk.END, content)
            text.see(tk.END)
            text.configure(state=tk.DISABLED)

        btn_row = ttk.Frame(win, padding=(10, 0, 10, 10))
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="刷新", command=refresh_log).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="关闭", command=win.destroy).pack(side=tk.RIGHT)

        self._center_popup(win)
        refresh_log()

    def _load_points(self) -> None:
        for _tn, plist in TASK_POINTS.items():
            for pname in plist:
                def_wait = "300"
                # 兼容历史命名：早期系统设置点位叫“系统设置”，后续改为“系统设置坐标”。
                legacy_pname = "系统设置" if pname == "系统设置坐标" else pname
                x = self._ini_get("Points", f"{pname}_X", "未设置")
                if pname == "系统设置坐标" and (str(x).strip() == "未设置" or str(x).strip() == ""):
                    x = self._ini_get("Points", f"{legacy_pname}_X", "未设置")

                y = self._ini_get("Points", f"{pname}_Y", "")
                if pname == "系统设置坐标" and str(y).strip() == "":
                    y = self._ini_get("Points", f"{legacy_pname}_Y", "")

                # 等待时间固定 300ms（已删除配置项）。
                w = def_wait
                self.points_data[pname] = PointData(x=x, y=y, wait=w)

    def _load_detect_waits(self) -> None:
        for tname in DETECT_TASKS:
            if tname == "拼图区域":
                # 拼图等待仍允许配置；用于“识别后等待”的下一步稳定性。
                try:
                    self.detect_waits[tname] = int(self._ini_get("Combo", "PuzzleWaitDetect", "6000"))
                except ValueError:
                    self.detect_waits[tname] = 6000
            else:
                # 其它识别等待固定为 300ms（已移除配置项）。
                self.detect_waits[tname] = 300

    def _on_close(self) -> None:
        self.is_monitoring = False
        self._unhook_keyboard()
        self.root.destroy()

    def _unhook_keyboard(self) -> None:
        if HAS_KEYBOARD:
            try:
                kb_lib.unhook_all()
            except Exception:
                pass

    def _bind_hotkeys(self) -> None:
        if not HAS_KEYBOARD:
            self.status_var.set("状态：请 pip install keyboard 以启用全局 F12 / 车头热键")
            self.root.bind("<F12>", lambda e: self.toggle_bot())
            return
        try:
            kb_lib.unhook_all()
        except Exception:
            pass
        kb_lib.add_hotkey("f12", lambda: self.root.after(0, self.toggle_bot))
        if self.carhead_key:
            try:
                hk = (self.carhead_key or "").strip().lower()
                kb_lib.add_hotkey(hk, lambda: self.root.after(0, self.execute_carhead_sequence))
            except Exception:
                pass

    def _key_display(self, k: str) -> str:
        s = (k or "").strip()
        low = s.lower()
        if low in ("prior", "pageup", "page_up", "pgup"):
            return "PAGE UP"
        if low in ("next", "pagedown", "page_down", "pgdn"):
            return "PAGE DOWN"
        if low == "comma":
            return ","
        if not s:
            return "(未设置)"
        # 键名显示用大写；例如 f10 -> F10，y -> Y
        # 标点（如 ','）不受影响。
        return s.upper()

    def _center_popup(self, popup: Any) -> None:
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

    def _capture_key(self, title: str) -> Optional[str]:
        """弹窗等待用户按下一个键，返回与 Farm 一致的键名字符串或 None。"""
        tk = self.tk
        result: List[Optional[str]] = [None]

        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        ttk = self.ttk
        ttk.Label(win, text="请按下要设置的键…").pack(pady=12, padx=16)
        e = ttk.Entry(win, width=20)
        e.pack(pady=(0, 12), padx=16)
        e.focus_set()

        def on_key(event: Any) -> None:
            key = keysym_to_keyboard(event.keysym)
            if key:
                result[0] = key
                e.delete(0, tk.END)
                e.insert(0, key)
                win.after(100, win.destroy)

        win.bind("<KeyPress>", on_key)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self._center_popup(win)
        win.wait_window()
        return result[0]

    def _capture_setting_key(self, which: str) -> None:
        titles = {
            "auction": "拍卖券键",
            "world_map": "世界地图键",
            "carhead": "车头热键",
            "hook": "钩锁键",
            "gather": "采集键",
        }
        k = self._capture_key(f"设置 {titles[which]}")
        if not k:
            return
        display = self._key_display(k)
        if which == "auction":
            self.auction_key = k
            self.btn_auction_cfg.configure(text=f"{display}")
        elif which == "world_map":
            self.world_map_key = k
            self.btn_world_map_cfg.configure(text=f"{display}")
        elif which == "carhead":
            self.carhead_key = k
            self.btn_carhead_cfg.configure(text=f"{display}")
            self._bind_hotkeys()
        elif which == "hook":
            self.hook_key = k
            self.btn_hook_cfg.configure(text=f"{display}")
        elif which == "gather":
            self.gather_key = k
            if getattr(self, "btn_gather_cfg", None) is not None:
                self.btn_gather_cfg.configure(text=f"{display}")
        self.auto_save_all()
        self.status_var.set(f"状态：已设置 {titles[which]}：{k}")

    def smart_sleep(self, ms: int) -> bool:
        if ms >= 1000:
            self._log_line(f"[等待] 等待 {ms / 1000:.1f} 秒")
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            if not self.is_monitoring:
                return False
            time.sleep(0.05)
        return True

    def my_sleep_action(self, ms: int, is_test: bool) -> bool:
        if is_test:
            time.sleep(ms / 1000.0)
            return True
        return self.smart_sleep(ms)

    def safe_click(self, pname: str, click_count: int = 1) -> bool:
        pt = self.points_data.get(pname)
        if not pt or pt.x == "未设置" or pt.x == "":
            self.status_var.set(f"⚠️ 警告：尝试点击 [{pname}] 失败，坐标未设定！")
            return False
        try:
            x = int(pt.x)
            y = int(pt.y) if str(pt.y).strip() != "" else 0
        except ValueError:
            self.status_var.set(f"⚠️ 警告：[{pname}] 坐标无效！")
            return False
        for _ in range(click_count):
            pyautogui.click(x, y)
        wtime = 0
        if str(pt.wait).strip().isdigit():
            wtime = int(pt.wait)
        if wtime > 0:
            return self.smart_sleep(wtime)
        return True

    def _nudge_mouse_after_image_click(self, x: int, y: int) -> None:
        """识图点击后将鼠标向右挪动，减少遮挡下一次识图。"""
        try:
            pyautogui.moveTo(x + 50, y)
        except Exception:
            pass

    def click_leave_image(self) -> bool:
        """在识别区内匹配 picture/离开.png 并点击中心。"""
        path = self.picture_dir / "离开.png"
        if not path.is_file():
            self.status_var.set("⚠️ 缺少模板文件 picture/离开.png")
            return False
        center = match_template_in_rect(SEARCH_RECT, path, self.tolerance)
        if center is None:
            self.status_var.set("⚠️ 未匹配到 离开.png，请检查画面或模板")
            return False
        pyautogui.click(center[0], center[1])
        self._nudge_mouse_after_image_click(center[0], center[1])
        time.sleep(0.05)
        return True

    def click_custom_image(self, filename: str) -> bool:
        """在识别区内匹配 picture/<filename> 并点击中心。"""
        path = self.picture_dir / filename
        if not path.is_file():
            self.status_var.set(f"⚠️ 缺少模板文件 picture/{filename}")
            return False
        center = match_template_in_rect((0, 0, 1566, 968), path, self.tolerance)
        if center is None:
            self.status_var.set(f"⚠️ 未匹配到 {filename}，请检查画面或模板")
            return False
        pyautogui.click(center[0], center[1])
        self._nudge_mouse_after_image_click(center[0], center[1])
        time.sleep(0.05)
        return True

    def click_game_end_image(self) -> bool:
        """在识别区内匹配 picture/游戏结束.png 并点击中心。"""
        path = self.picture_dir / "游戏结束.png"
        if not path.is_file():
            self.status_var.set("⚠️ 缺少模板文件 picture/游戏结束.png")
            return False
        center = match_template_in_rect(SEARCH_RECT, path, self.tolerance)
        if center is None:
            self.status_var.set("⚠️ 未匹配到 游戏结束.png，请检查画面或模板")
            return False
        pyautogui.click(center[0], center[1])
        self._nudge_mouse_after_image_click(center[0], center[1])
        time.sleep(0.05)
        return True

    def click_carhead_template(self, filename: str) -> bool:
        """在识别区内匹配 picture 下指定文件名并点击中心。"""
        path = self.picture_dir / filename
        self._log_line(f"[车头] 开始匹配模板: picture/{filename}")
        if not path.is_file():
            self._log_line(f"[车头] 模板缺失: picture/{filename}")
            self.status_var.set(f"⚠️ 缺少模板文件 picture/{filename}")
            return False
        center = match_template_in_rect(SEARCH_RECT, path, self.tolerance)
        if center is None:
            self._log_line(f"[车头] 匹配失败: {filename}")
            self.status_var.set(f"⚠️ 未匹配到 {filename}，请检查画面或模板")
            return False
        self._log_line(f"[车头] 匹配成功: {filename} -> 点击坐标({center[0]}, {center[1]})")
        pyautogui.click(center[0], center[1])
        self._nudge_mouse_after_image_click(center[0], center[1])
        time.sleep(0.05)
        self._log_line(f"[车头] 已点击: {filename}")
        return True

    def click_carhead_multiplayer_point(self) -> bool:
        """车头流程中的多人组队步骤：点击收藏地图配置的多人组队坐标。"""
        pt = self.points_data.get("多人组队坐标")
        if not pt or pt.x in ("", "未设置"):
            self._log_line("[车头] 多人组队坐标未设置，步骤终止")
            self.status_var.set("⚠️ 警告：多人组队坐标未设定！")
            return False
        try:
            x = int(pt.x)
            y = int(pt.y) if str(pt.y).strip() != "" else 0
        except ValueError:
            self._log_line("[车头] 多人组队坐标无效，步骤终止")
            self.status_var.set("⚠️ 警告：多人组队坐标无效！")
            return False
        self._log_line(f"[车头] 多人组队步骤使用坐标点击 -> ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(0.05)
        self._log_line("[车头] 已点击多人组队坐标")
        return True

    def _run_carhead_image_sequence(self, done_msg: str) -> None:
        self._log_line("[车头] 连招开始")
        for i, fn in enumerate(CARHEAD_CLICK_IMAGES):
            self._log_line(f"[车头] 步骤 {i + 1}/{len(CARHEAD_CLICK_IMAGES)}: {fn}")
            if fn == "多人组队.png":
                if not self.click_carhead_multiplayer_point():
                    self._log_line("[车头] 步骤终止: 多人组队坐标点击失败")
                    return
            else:
                if not self.click_carhead_template(fn):
                    self._log_line(f"[车头] 步骤终止: {fn}")
                    return
            if i < len(CARHEAD_CLICK_IMAGES) - 1 and not self.smart_sleep(200):
                self._log_line("[车头] 等待200ms被中断，连招终止")
                return
            if i < len(CARHEAD_CLICK_IMAGES) - 1:
                self._log_line(f"[车头] 步骤间等待200ms完成: {fn}")
        self._log_line("[车头] 连招完成")
        self.status_var.set(done_msg)

    def press_confirm_enter(self) -> None:
        send_key_tap("enter")
        time.sleep(0.05)

    def perform_collection_teleport(self) -> bool:
        self.status_var.set("状态：🗺️ 打开世界地图，点击收藏地图坐标后按回车确认...")
        if self.world_map_key:
            send_key_tap(self.world_map_key)
        if not self.smart_sleep(800):
            return False
        if not self.safe_click("收藏地图坐标", 2):
            return False
        send_key_tap("enter")
        time.sleep(0.05)
        self.status_var.set("状态：⏳ 等待传送...")
        if self.teleport_wait > 0 and not self.smart_sleep(self.teleport_wait):
            return False
        return True

    def perform_cook_exit(self, is_test: bool = False) -> None:
        """识别做菜退场后：匹配并点击做菜退场npc.png，0.2 秒后按两次采集键。"""
        if not self.click_custom_image("做菜退场npc.png"):
            return
        if not self.my_sleep_action(200, is_test):
            return
        for i in range(2):
            if self.gather_key:
                send_key_tap(self.gather_key)
            if i < 1 and not self.my_sleep_action(200, is_test):
                return

    def perform_spec_exit(self, is_test: bool = False) -> None:
        if not self.click_custom_image("光谱退场npc.png"):
            return
        if not self.my_sleep_action(200, is_test):
            return
        for i in range(2):
            if self.gather_key:
                send_key_tap(self.gather_key)
            if i < 1 and not self.my_sleep_action(200, is_test):
                return

    def perform_fish_exit(self, is_test: bool = False) -> None:
        send_raw_key("right", True)
        if not self.my_sleep_action(300, is_test):
            send_raw_key("right", False)
            return
        send_raw_key("right", False)
        for _ in range(2):
            if self.gather_key:
                send_key_tap(self.gather_key)
                time.sleep(0.2)
            if not self.my_sleep_action(300, is_test):
                return

    def execute_carhead_sequence(self) -> None:
        self.status_var.set("状态：🚗 车头连招执行中...")
        self._run_carhead_image_sequence("状态：🚗 车头连招完成")

    def execute_village_carhead_sequence(self) -> None:
        self.status_var.set("状态：🏘️ 村庄车头连招执行中...")
        self._run_carhead_image_sequence("状态：🏘️ 村庄车头连招完成")

    def _template_path(self, scene_name: str) -> Path:
        return self.picture_dir / f"{scene_name}.png"

    def _spectrum_map_exit_sequence(self) -> None:
        """识别为光谱地图界面后的退出游戏流程（与原先 _bot_tick_once 末尾一致）。"""
        self.status_var.set("状态：🌈 识别光谱地图，结束游戏...")
        if not self.smart_sleep(300):
            return
        if not self.safe_click("系统设置坐标"):
            return
        if not self.click_game_end_image():
            return
        self.status_var.set("状态：🌈 按回车确认退出...")
        for _ in range(3):
            send_key_tap("enter")
            time.sleep(0.05)

    def _bot_tick_scene_chain(self, find_scene) -> bool:
        """除「光谱地图」外的全部场景分支；若已处理某一分支则返回 True。"""
        if find_scene("傻福捕鱼"):
            self.status_var.set("状态：🎣 识别傻福捕鱼，离开...")
            if not self.smart_sleep(300):
                return True
            if self.click_leave_image():
                if not self.smart_sleep(500):
                    return True
                self.press_confirm_enter()
                if not self.smart_sleep(500):
                    return True
                return True
            # 没有匹配到离开图时，回退尝试傻福捕鱼退场逻辑
            if find_scene("傻福捕鱼退场"):
                self.status_var.set("状态：🎣 未匹配离开图，改走傻福捕鱼退场...")
                if not self.smart_sleep(300):
                    return True
                self.perform_fish_exit(False)
                # 退场后若仍识别到傻福捕鱼，再尝试一次正常离开流程
                if find_scene("傻福捕鱼"):
                    self.status_var.set("状态：🎣 退场后仍在傻福捕鱼，重试离开...")
                    if not self.smart_sleep(300):
                        return True
                    if self.click_leave_image():
                        if not self.smart_sleep(500):
                            return True
                        self.press_confirm_enter()
                        if not self.smart_sleep(500):
                            return True
            return True

        if find_scene("傻福捕鱼退场"):
            self.status_var.set("状态：🎣 识别傻福捕鱼退场，执行退场...")
            if not self.smart_sleep(300):
                return True
            self.perform_fish_exit(False)
            return True

        if find_scene("做菜退场2"):
            self.status_var.set("状态：🍳 识别做菜退场2，执行收藏地图传送...")
            if not self.smart_sleep(300):
                return True
            if self.perform_collection_teleport():
                pass
            return True

        if find_scene("光谱退场2"):
            self.status_var.set("状态：🌈 识别光谱退场2，执行收藏地图传送...")
            if not self.smart_sleep(300):
                return True
            self.perform_collection_teleport()
            return True

        if find_scene("做菜退场"):
            self.status_var.set("状态：🍳 识别做菜退场，点击NPC并按采集键...")
            if not self.smart_sleep(300):
                return True
            self.perform_cook_exit(False)
            return True

        if find_scene("光谱退场"):
            self.status_var.set("状态：🚨 识别光谱退场，执行连招...")
            if not self.smart_sleep(300):
                return True
            self.perform_spec_exit(False)
            return True

        if find_scene("厨房区域"):
            self.status_var.set("状态：🍳 识别厨房区域，离开...")
            if not self.smart_sleep(300):
                return True
            if not self.click_leave_image():
                return True
            self.press_confirm_enter()
            return True

        if find_scene("星图区域"):
            self.status_var.set("状态：⭐ 识别星图区域，离开...")
            if not self.smart_sleep(300):
                return True
            if not self.click_custom_image("星图离开.png"):
                return True
            self.press_confirm_enter()
            return True

        if find_scene("拼图区域"):
            ew = self.detect_waits.get("拼图区域", 6000)
            self.status_var.set(f"状态：🧩 识别拼图区域...等待{ew / 1000:.1f}秒")
            if ew > 0 and not self.smart_sleep(ew):
                return True
            self.status_var.set("状态：🧩 匹配离开图并确认...")
            if not self.click_custom_image("拼图离开.png"):
                return True
            self.press_confirm_enter()
            return True

        if find_scene("游戏选人界面"):
            self.status_var.set("状态：🎮 识别选人界面，按回车开始...")
            if not self.smart_sleep(200):
                return True
            send_key_tap("enter")
            time.sleep(0.05)
            return True

        if find_scene("做菜地图"):
            self.status_var.set("状态：🍳 识别做菜地图...")
            if not self.smart_sleep(300):
                return True
            if not self.click_custom_image("做菜离开.png"):
                return True
            self.press_confirm_enter()
            return True

        if find_scene("收藏地图"):
            if self.is_timer_expired:
                self.var_chk_autostop.set(0)
                self.stop_monitoring("状态：⏱️ 定时已到，已进入收藏地图并停止。")
                return True
            self.status_var.set("状态：🗺️ 识别收藏地图，车头...")
            ew = self.detect_waits.get("收藏地图", 300)
            if ew > 0 and not self.smart_sleep(ew):
                return True
            self.execute_carhead_sequence()
            return True

        if find_scene("收藏村庄"):
            self.status_var.set("状态：🏘️ 识别收藏村庄，村庄车头...")
            ew = self.detect_waits.get("收藏村庄", 300)
            if ew > 0 and not self.smart_sleep(ew):
                return True
            self.execute_village_carhead_sequence()
            return True



        if find_scene("星图退场区域"):
            self.status_var.set("状态：⭐ 识别星图退场...")
            ew = self.detect_waits.get("星图退场区域", 300)
            if ew > 0 and not self.smart_sleep(ew):
                return True
            self.perform_fish_exit(False)
            return True

        return False

    def _bot_worker(self) -> None:
        time.sleep(0.5)
        while self.is_monitoring:
            try:
                self._bot_tick_once()
            except Exception as e:
                self.status_var.set(f"⚠️ 监控异常({e})，即将重试...")
            if not self.smart_sleep(500):
                break

    def _bot_tick_once(self) -> None:
        r = SEARCH_RECT
        tol = self.tolerance

        def find_scene(name: str) -> bool:
            return match_template_in_rect(r, self._template_path(name), tol) is not None

        if self._bot_tick_scene_chain(find_scene):
            return
        if find_scene("光谱地图"):
            self._spectrum_map_exit_sequence()
            return
        self.status_var.set("状态：🔍 监控中 (0,0)–(1366,768)...")

    def _build_mid_task_body(self, mid: Any, *, include_welcome: bool) -> None:
        """中间区域：任务点位、拼图等待、截图按钮、测试连招（嵌入时可不建首页说明）。"""
        tk = self.tk
        ttk = self.ttk

        self.mid_title = ttk.Label(mid, text="点位与延迟", font=("Microsoft YaHei UI", 12, "bold"))
        self.mid_title.pack(anchor=tk.W)

        if include_welcome:
            welcome = (
                "说明：\n"
                "1.请将冒冒窗口调至1366*768\n"
                "2.请将冒冒窗口置于屏幕左上角（可用快捷键win + ←实现快速置于左上角）\n"
                "3.如有多个屏幕，请将冒冒窗口置于主屏左上角\n"
                "4.首次启动请配置全局参数\n"
                "5.本软件不得用于商业用途,仅做学习交流\n"
                "6.未经允许，不得将本工具外传，不然你马没了^_^"
            )
            self.lbl_welcome = tk.Text(
                mid,
                height=12,
                width=70,
                wrap=tk.WORD,
                font=("", 14),
                spacing1=6,
                spacing2=6,
                spacing3=0,
                bd=0,
                highlightthickness=0,
                fg="black",
                bg="#F5F5F7",
            )
            self.lbl_welcome.insert(tk.END, welcome)
            self.lbl_welcome.configure(state=tk.DISABLED)
            self.lbl_welcome.pack(anchor=tk.W, pady=8)
        else:
            self.lbl_welcome = None  # type: ignore[assignment]

        self.point_frames: Dict[str, ttk.Frame] = {}
        self.point_widgets: Dict[str, Dict[str, Any]] = {}

        for tname, plist in TASK_POINTS.items():
            fr = ttk.Frame(mid)
            self.point_frames[tname] = fr
            self.point_widgets[tname] = {}
            for pname in plist:
                row = ttk.Frame(fr)
                row.pack(fill=tk.X, pady=2)
                pv = self.points_data[pname]
                txt = f"{pname}: {pv.x}" + (f",{pv.y}" if str(pv.y).strip() else "")
                if tname == "任务配置":
                    # “任务配置”需要展示较长的坐标文本，避免固定宽度截断。
                    lb = ttk.Label(row, text=txt, anchor=tk.W, justify=tk.LEFT, wraplength=180)
                else:
                    lb = ttk.Label(row, text=txt, width=14)
                bt = ttk.Button(row, text="定位", width=6, command=lambda pn=pname, l=lb: self.start_get_point(pn, l))
                lb.grid(row=0, column=0, sticky=tk.W)
                # “任务配置”里的“定位”按钮左移约 80px 对齐其它控件。
                btn_padx = 24 if tname == "任务配置" else 4
                bt.grid(row=0, column=1, padx=btn_padx)
                wdict: Dict[str, Any] = {"lbl": lb, "btn": bt}
                if tname == "任务配置" and pname in ("收藏地图坐标", "多人组队坐标", "系统设置坐标"):
                    help_map = {
                        "收藏地图坐标": ("收藏地图坐标说明.png", "收藏地图坐标说明"),
                        "多人组队坐标": ("多人组队坐标说明.png", "多人组队坐标说明"),
                        "系统设置坐标": ("系统设置坐标说明.png", "系统设置坐标说明"),
                    }
                    filename, title = help_map[pname]
                    # 在“定位”按钮右侧加说明图入口
                    help_btn = ttk.Button(
                        row,
                        text="说明图",
                        width=8,
                        command=lambda f=filename, t=title: self._open_help_image(f, t),
                    )
                    help_btn.grid(row=0, column=2, padx=8, sticky=tk.W)
                if tname != "任务配置":
                    # 其它点位（如后续扩展）才保留等待配置；当前“任务配置”固定 300ms。
                    lw = ttk.Label(row, text="等待:")
                    ew = ttk.Entry(row, width=5, justify=tk.CENTER)
                    ew.insert(0, str(pv.wait))
                    ew.bind("<KeyRelease>", lambda e, pn=pname: self._on_wait_edit(pn, e.widget.get()))
                    lw.grid(row=0, column=2)
                    ew.grid(row=0, column=3)
                    wdict["wait"] = ew
                    wdict["lblw"] = lw
                self.point_widgets[tname][pname] = wdict

        self.fr_puzzle_wait = ttk.Frame(mid)
        ttk.Label(self.fr_puzzle_wait, text="拼图等待(ms):").pack(side=tk.LEFT)
        self.ed_puzzle_wait = ttk.Entry(self.fr_puzzle_wait, width=8, justify=tk.CENTER)
        self.ed_puzzle_wait.insert(0, str(self.detect_waits.get("拼图区域", 6000)))
        self.ed_puzzle_wait.pack(side=tk.LEFT, padx=6)
        self.ed_puzzle_wait.bind("<KeyRelease>", lambda e: self.auto_save_all())

        ttk.Label(self.fr_puzzle_wait, text="小于3秒会闪退", foreground="#d00").pack(side=tk.LEFT, padx=(10, 0))

        # “收藏地图/村庄标识截图”改为同一行显示 + 右侧“说明图”
        self.fr_capture_map = ttk.Frame(mid)
        self.fr_capture_map.pack_forget()
        self.btn_capture_map_marker = ttk.Button(
            self.fr_capture_map,
            text="收藏地图标识截图",
            command=lambda: self.capture_fixed_template("收藏地图.png", "收藏地图"),
            width=22,
        )
        self.btn_capture_map_marker.pack(side=tk.LEFT)
        self.btn_capture_map_help = ttk.Button(
            self.fr_capture_map,
            text="说明图",
            width=8,
            command=lambda: self._open_help_image("收藏地图标识说明.png", "收藏地图标识说明"),
        )
        self.btn_capture_map_help.pack(side=tk.LEFT, padx=(8, 0))

        self.fr_capture_village_marker = ttk.Frame(mid)
        self.fr_capture_village_marker.pack_forget()
        self.btn_capture_village_marker = ttk.Button(
            self.fr_capture_village_marker,
            text="收藏村庄标识截图",
            command=lambda: self.capture_fixed_template("收藏村庄.png", "收藏村庄"),
            width=22,
        )
        self.btn_capture_village_marker.pack(side=tk.LEFT)
        self.btn_capture_village_help = ttk.Button(
            self.fr_capture_village_marker,
            text="说明图",
            width=8,
            command=lambda: self._open_help_image("收藏村庄标识说明.png", "收藏村庄标识说明"),
        )
        self.btn_capture_village_help.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_test = ttk.Button(mid, text="测试连招 (1 秒后)", command=self.test_combo)

    def _build_bot_global_params(self, bot: Any, *, show_gather_key: bool) -> None:
        tk = self.tk
        ttk = self.ttk

        ttk.Label(bot, text="全局参数（修改即保存）", font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W)

        row1 = ttk.Frame(bot)
        row1.pack(fill=tk.X, pady=4)
        ttk.Label(row1, text="识图匹配阈值:").pack(side=tk.LEFT)
        self.ed_tol = ttk.Entry(row1, width=6, justify=tk.CENTER)
        self.ed_tol.insert(0, str(self.tolerance))
        self.ed_tol.pack(side=tk.LEFT, padx=4)
        self.ed_tol.bind("<KeyRelease>", lambda e: self.auto_save_all())

        ttk.Label(row1, text="拍卖券键:").pack(side=tk.LEFT, padx=(12, 0))
        self.btn_auction_cfg = ttk.Button(
            row1,
            text=f"{self._key_display(self.auction_key)}",
            command=lambda: self._capture_setting_key("auction"),
        )
        self.btn_auction_cfg.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(row1, text="世界地图键:").pack(side=tk.LEFT, padx=(4, 0))
        self.btn_world_map_cfg = ttk.Button(
            row1,
            text=f"{self._key_display(self.world_map_key)}",
            command=lambda: self._capture_setting_key("world_map"),
        )
        self.btn_world_map_cfg.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(row1, text="车头热键:").pack(side=tk.LEFT, padx=(4, 0))
        self.btn_carhead_cfg = ttk.Button(
            row1,
            text=f"{self._key_display(self.carhead_key)}",
            command=lambda: self._capture_setting_key("carhead"),
        )
        self.btn_carhead_cfg.pack(side=tk.LEFT, padx=(0, 4))

        row2 = ttk.Frame(bot)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="钩锁键:").pack(side=tk.LEFT)
        self.btn_hook_cfg = ttk.Button(
            row2,
            text=f"{self._key_display(self.hook_key)}",
            command=lambda: self._capture_setting_key("hook"),
        )
        self.btn_hook_cfg.pack(side=tk.LEFT, padx=(0, 12))

        if show_gather_key:
            ttk.Label(row2, text="采集键:").pack(side=tk.LEFT, padx=(4, 0))
            self.btn_gather_cfg = ttk.Button(
                row2,
                text=f"{self._key_display(self.gather_key)}",
                command=lambda: self._capture_setting_key("gather"),
            )
            self.btn_gather_cfg.pack(side=tk.LEFT, padx=(0, 8))
        else:
            self.btn_gather_cfg = None  # type: ignore[assignment]

        self.var_chk_autostop = self.tk.IntVar(value=0)
        ttk.Checkbutton(row2, text="定时停止(分):", variable=self.var_chk_autostop).pack(side=tk.LEFT, padx=(16, 0))
        self.ed_autostop_dur = ttk.Entry(row2, width=5)
        self.ed_autostop_dur.insert(0, "60")
        self.ed_autostop_dur.pack(side=tk.LEFT, padx=4)

    def _build_gui_embed(self) -> None:
        """嵌入 PartyBug：仅任务配置 + 全局参数；采集键由宿主提供。"""
        tk = self.tk
        ttk = self.ttk
        root = self.root

        self.status_var = tk.StringVar(value="状态：就绪。")
        self.task_var = tk.StringVar(value="任务配置")

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        mid = ttk.Frame(outer)
        mid.pack(fill=tk.BOTH, expand=True, anchor=tk.W)
        self._build_mid_task_body(mid, include_welcome=False)

        bot = ttk.Frame(outer)
        bot.pack(fill=tk.X, pady=(12, 0))
        self._build_bot_global_params(bot, show_gather_key=False)

        ttk.Label(outer, textvariable=self.status_var, wraplength=800, font=("Microsoft YaHei UI", 10)).pack(
            fill=tk.X, pady=(8, 0)
        )

    def _build_gui(self) -> None:
        tk = self.tk
        ttk = self.ttk
        root = self.root

        self.status_var = tk.StringVar(value="状态：就绪。")
        self.task_var = tk.StringVar(value=self.current_task)
        self._attach_status_logging()
        self._log_line("[系统] 日志初始化完成")

        main = ttk.Frame(root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="任务选择", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)
        btn_frame = ttk.Frame(left)
        btn_frame.pack(anchor=tk.W, pady=(8, 0), fill=tk.X)
        ttk.Button(
            btn_frame,
            text="首页提示",
            width=22,
            command=lambda: self._select_task("首页提示"),
        ).pack(pady=(0, 6))
        ttk.Button(
            btn_frame,
            text="任务配置",
            width=22,
            command=lambda: self._select_task("任务配置"),
        ).pack(pady=(0, 6))

        self.btn_log_detail = ttk.Button(left, text="日志详情", command=self.show_log_detail, width=22)
        self.btn_log_detail.pack(pady=(14, 4))

        self.btn_start = ttk.Button(left, text="▶ 开始 (F12)", command=self.start_monitoring, width=22)
        self.btn_start.pack(pady=(16, 4))
        self.btn_stop = ttk.Button(left, text="⏹ 停止 (F12)", command=self.stop_monitoring, state=tk.DISABLED, width=22)
        self.btn_stop.pack()

        mid = ttk.Frame(main, width=280)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        self._build_mid_task_body(mid, include_welcome=True)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH)

        bot = ttk.Frame(root)
        bot.pack(fill=tk.X, padx=12, pady=8)
        self._build_bot_global_params(bot, show_gather_key=True)

        ttk.Label(root, textvariable=self.status_var, wraplength=780, font=("Microsoft YaHei UI", 10)).pack(
            fill=tk.X, padx=12, pady=(0, 8)
        )

    def _on_task_change(self, _evt=None) -> None:
        self.current_task = self.task_var.get()
        self.refresh_ui()

    def _select_task(self, task: str) -> None:
        self.current_task = task
        try:
            self.task_var.set(task)
        except Exception:
            pass
        self.refresh_ui()

    def _on_wait_edit(self, pname: str, val: str) -> None:
        if val.strip().isdigit():
            self.points_data[pname].wait = val
            self._write_ini_points_wait(pname, val)
        self.status_var.set("状态：已保存")

    def _write_detect_wait_key(self, task: str, val: str) -> None:
        if task == "拼图区域":
            self._set_ini("Combo", "PuzzleWaitDetect", val)
        else:
            if not self.cp.has_section("DetectWait"):
                self.cp.add_section("DetectWait")
            self.cp.set("DetectWait", task, val)
        self._save_ini()

    def refresh_ui(self) -> None:
        tk = self.tk
        if getattr(self, "_embed_mode", False):
            ct = "任务配置"
            self.current_task = "任务配置"
        else:
            ct = self.current_task
        is_welcome = ct == "首页提示"
        if self.lbl_welcome is not None:
            self.lbl_welcome.pack_forget()
            if is_welcome:
                self.lbl_welcome.pack(anchor=tk.W, pady=8, before=self.mid_title)

        for _tname, fr in self.point_frames.items():
            fr.pack_forget()
        self.fr_puzzle_wait.pack_forget()
        self.btn_test.pack_forget()
        self.fr_capture_map.pack_forget()
        self.fr_capture_village_marker.pack_forget()

        if ct in self.point_frames:
            self.point_frames[ct].pack(anchor=tk.W, fill=tk.X, pady=4, after=self.mid_title)
            for _pname, wdict in self.point_widgets[ct].items():
                lblw = wdict.get("lblw")
                wait = wdict.get("wait")
                if lblw:
                    lblw.pack_forget()
                    lblw.grid(row=0, column=2)
                if wait:
                    wait.pack_forget()
                    wait.grid(row=0, column=3)

        # “首页提示”不显示点位标题
        if ct == "首页提示":
            self.mid_title.configure(text="")
        elif ct == "任务配置":
            self.mid_title.configure(text="任务配置")
        else:
            self.mid_title.configure(text=f"[{ct}] 点位")

        if ct == "任务配置":
            self.ed_puzzle_wait.delete(0, self.tk.END)
            self.ed_puzzle_wait.insert(0, str(self.detect_waits.get("拼图区域", 6000)))
            self.fr_puzzle_wait.pack(anchor=tk.W, pady=2)
            self.fr_capture_map.pack(anchor=tk.W, pady=(4, 4))
            self.fr_capture_village_marker.pack(anchor=tk.W, pady=(0, 4))

    def _show_image_preview(self, label: Any, path: Path, max_w: int, max_h: int) -> None:
        try:
            im = Image.open(path)
            im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(im)
            label.configure(image=photo, text="")
            label.image = photo  # type: ignore
        except Exception:
            label.configure(image="", text="(无法加载)")

    def _open_help_image(self, filename: str, title: str) -> None:
        path = self.picture_dir / filename
        if not path.is_file():
            self.status_var.set(f"⚠️ 缺少说明图 picture/{filename}")
            try:
                self.messagebox.showerror("错误", f"缺少文件：picture/{filename}")
            except Exception:
                pass
            return

        ov = self.tk.Toplevel(self.root)
        ov.title(title)
        ov.resizable(False, False)

        # 统一缩放，避免图片过大遮挡界面
        try:
            im = Image.open(path)
            im.thumbnail((560, 420), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(im)
            lbl = self.tk.Label(ov, image=photo, bg="#FFFFFF")
            lbl.image = photo  # type: ignore
            lbl.pack(padx=12, pady=12)
            self._center_popup(ov)
        except Exception:
            try:
                self.messagebox.showerror("错误", f"无法加载说明图：picture/{filename}")
            except Exception:
                self.status_var.set(f"⚠️ 无法加载说明图 picture/{filename}")

    def _set_ini(self, sec: str, key: str, val: str) -> None:
        if not self.cp.has_section(sec):
            self.cp.add_section(sec)
        self.cp.set(sec, key, val)

    def _save_ini(self) -> None:
        with open(self.ini_file, "w", encoding="utf-8") as f:
            self.cp.write(f)

    def auto_save_all(self) -> None:
        if self._gather_key_supplier is not None:
            self.gather_key = self._gather_key_supplier()
        tol = self.ed_tol.get().strip()
        try:
            tv = float(tol)
            self.tolerance = _clamp(tv, 0.0, 1.0)
            self._set_ini("Settings", "Tolerance", str(self.tolerance))
        except ValueError:
            pass
        self._set_ini("Settings", "AuctionKey", self.auction_key)
        self._set_ini("Settings", "WorldMapKey", self.world_map_key)
        self._set_ini("Settings", "GatherKey", self.gather_key)
        self._set_ini("Settings", "HookKey", self.hook_key)
        self._set_ini("Settings", "CarheadKey", self.carhead_key)

        for _tn, plist in TASK_POINTS.items():
            for pname in plist:
                w = self.point_widgets.get(_tn, {}).get(pname, {}).get("wait")
                if w:
                    val = w.get().strip()
                    if val.isdigit():
                        self.points_data[pname].wait = val
                        self._set_ini("PointsWait", pname, val)

        pv = self.ed_puzzle_wait.get().strip()
        if pv.isdigit():
            self.detect_waits["拼图区域"] = int(pv)
            self._write_detect_wait_key("拼图区域", pv)

        self._save_ini()
        self.status_var.set("状态：已保存")

    def _write_ini_points_wait(self, pname: str, val: str) -> None:
        self._set_ini("PointsWait", pname, val)
        self._save_ini()

    def _check_autostop_timer(self) -> None:
        if self.auto_stop_active and not self.is_timer_expired and time.monotonic() >= self.auto_stop_end_time:
            self.is_timer_expired = True
            self.status_var.set("状态：定时时间已到，下次进入收藏地图后将停止。")
            self.auto_stop_active = False
        if self.root.winfo_exists():
            self.root.after(1000, self._check_autostop_timer)

    def toggle_bot(self) -> None:
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self) -> None:
        tk = self.tk
        self.is_monitoring = True
        self.is_timer_expired = False
        if self.var_chk_autostop.get():
            try:
                mins = int(self.ed_autostop_dur.get().strip() or "60")
            except ValueError:
                mins = 60
            self.auto_stop_active = True
            self.auto_stop_end_time = time.monotonic() + mins * 60
            self.status_var.set(f"状态：挂机中（约 {mins} 分钟后于收藏地图停止）")
        else:
            self.auto_stop_active = False
            self.status_var.set("状态：挂机中（F12 停止）")

        if hasattr(self, "btn_start"):
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_stop.configure(state=tk.NORMAL)

        self.bot_thread = threading.Thread(target=self._bot_worker, daemon=True)
        self.bot_thread.start()

    def stop_monitoring(self, reason: str = "") -> None:
        tk = self.tk
        self.is_monitoring = False
        if reason:
            self.status_var.set(reason)
        else:
            self.status_var.set("状态：已停止")
        ct = self.current_task
        is_welcome = ct == "首页提示"
        if hasattr(self, "btn_start"):
            self.btn_start.configure(state=tk.NORMAL)
            self.btn_stop.configure(state=tk.DISABLED)

    def test_combo(self) -> None:
        self.status_var.set(f"状态：1 秒后测试 [{self.current_task}] 连招")
        self.root.update()

        def run() -> None:
            time.sleep(1)
            ct = self.current_task
            self.root.after(0, lambda: self.status_var.set(f"状态：测试完成 [{ct}]"))

        threading.Thread(target=run, daemon=True).start()

    def capture_template(self) -> None:
        ct = self.current_task
        if not TASKS_NEED_IMAGE.get(ct):
            return
        path = self._template_path(ct)
        if path.is_file() and ct != "收藏地图":
            if not self.messagebox.askyesno("覆盖", "已存在模板，是否覆盖？"):
                return
        self._start_region_capture_for_template(path, ct)

    def capture_fixed_template(self, filename: str, display_name: str) -> None:
        """框选截图并覆盖 picture 下指定模板文件。"""
        path = self.picture_dir / filename
        self._start_region_capture_for_template(path, display_name)

    def _save_screenshot_region(self, left: int, top: int, width: int, height: int, path: Path, ct: str) -> None:
        try:
            im = pyautogui.screenshot(region=(left, top, width, height))
            im.save(str(path))
            self.refresh_ui()
            if ct in ("收藏地图", "收藏村庄"):
                self.status_var.set(f"状态：已覆盖 picture/{path.name}")
            else:
                self.status_var.set(f"状态：已保存 {path.name}")
        except Exception as e:
            self.messagebox.showerror("错误", str(e))

    def _start_region_capture_for_template(self, path: Path, ct: str) -> None:
        """全屏半透明遮罩，拖动框选区域，松开后保存为当前任务模板。"""
        tk = self.tk
        self.status_var.set("状态：按住左键拖动框选，松开保存；Esc 取消")

        ov = tk.Toplevel(self.root)
        ov.attributes("-fullscreen", True)
        ov.attributes("-topmost", True)
        ov.attributes("-alpha", 0.28)
        ov.configure(bg="black")

        canvas = tk.Canvas(ov, highlightthickness=0, bg="#1a1a1a", cursor="crosshair")
        canvas.pack(fill=tk.BOTH, expand=True)

        state: Dict[str, Any] = {"sx": None, "sy": None}

        def on_esc(_event=None) -> None:
            try:
                ov.destroy()
            except Exception:
                pass
            self.status_var.set("状态：已取消截图")

        def on_press(e: Any) -> None:
            state["sx"] = e.x
            state["sy"] = e.y

        def on_motion(e: Any) -> None:
            if state["sx"] is None:
                return
            canvas.delete("sel")
            canvas.create_rectangle(
                state["sx"],
                state["sy"],
                e.x,
                e.y,
                outline="#00ff88",
                width=2,
                tags="sel",
            )

        def on_release(e: Any) -> None:
            if state["sx"] is None:
                return
            ax, ay = state["sx"], state["sy"]
            bx, by = e.x, e.y
            w = abs(bx - ax)
            h = abs(by - ay)
            rx = ov.winfo_rootx()
            ry = ov.winfo_rooty()
            left = int(rx + min(ax, bx))
            top = int(ry + min(ay, by))
            width = int(w)
            height = int(h)
            state["sx"] = None
            state["sy"] = None
            try:
                ov.destroy()
            except Exception:
                pass
            if width < 8 or height < 8:
                self.status_var.set("状态：选区太小，已取消")
                return
            self.root.after(150, lambda: self._save_screenshot_region(left, top, width, height, path, ct))

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_motion)
        canvas.bind("<ButtonRelease-1>", on_release)
        ov.bind("<Escape>", on_esc)
        canvas.bind("<Escape>", on_esc)
        ov.after(80, lambda: canvas.focus_set())

    def start_get_point(self, pname: str, lbl: Any) -> None:
        self.status_var.set(f"状态：点击屏幕上的【{pname}】")
        ov = self.tk.Toplevel(self.root)
        ov.attributes("-fullscreen", True)
        ov.attributes("-alpha", 0.1)
        ov.configure(bg="black")
        ov.attributes("-topmost", True)

        def on_click(e):
            cx, cy = e.x_root, e.y_root
            ov.destroy()
            self.points_data[pname].x = str(cx)
            self.points_data[pname].y = str(cy)
            self._set_ini("Points", f"{pname}_X", str(cx))
            self._set_ini("Points", f"{pname}_Y", str(cy))
            self._save_ini()
            lbl.configure(text=f"{pname}: {cx},{cy}")
            self.status_var.set("状态：坐标已记录")

        fr = self.tk.Frame(ov, bg="black")
        fr.pack(fill=self.tk.BOTH, expand=True)
        fr.bind("<Button-1>", on_click)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if not HAS_KEYBOARD:
        print("提示: pip install keyboard 可启用全局 F12 / 车头热键")
    PartyApp().run()


if __name__ == "__main__":
    main()
