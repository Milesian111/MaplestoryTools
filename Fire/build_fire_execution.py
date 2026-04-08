"""
Fire GUI：模仿 Cube/build_cube_execution.py
按钮：开始 结束 查看日志 选择装备 选择属性
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Dict, List, Optional

try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    keyboard = None
    HAS_KEYBOARD = False

from fire_logic import run_fire_loop

_FIRE_DIR = Path(__file__).resolve().parent

def _picture_dir(fire_dir: Path) -> Path:
    return fire_dir / "picture"


WIN_SIZE_NORMAL = "600x260"
WIN_SIZE_WITH_LOG = "600x520"
WIN_SIZE_WITH_EQUIP = "600x380"
WIN_SIZE_WITH_ATTR = "600x320"


# 装备 -> 可选属性（图片名，不含 .png）
EQUIP_TO_ATTRS: Dict[str, List[str]] = {
    "140首饰": [
        "str140", "str112", "str84",
        "dex140", "dex112", "dex84",
        "luk140", "luk112", "luk84",
        "int140", "int112", "int84",
        "atk7", "magic7", "all7",
    ],
    "160首饰": [
        "str168", "str133", "str98",
        "dex168", "dex133", "dex98",
        "luk168", "luk133", "luk98",
        "int168", "int133", "int98",
        "atk7", "magic7", "all7",
    ],
    "200防具首饰": [
        "str203", "str161", "str119",
        "dex203", "dex161", "dex119",
        "luk203", "luk161", "luk119",
        "int203", "int161", "int119",
        "atk7", "magic7", "all7",
    ],
    "250防具首饰": [
        "str231", "str182", "str133", "str84",
        "dex231", "dex182", "dex133", "dex84",
        "luk231", "luk182", "luk133", "luk84",
        "int231", "int182", "int133", "int84",
        "atk7", "magic7", "all7",
    ],
    "武器": ["atk", "magic", "boss"],
}


def _attr_to_column(key: str) -> str:
    if key.startswith("str"):
        return "str"
    if key.startswith("dex"):
        return "dex"
    if key.startswith("luk"):
        return "luk"
    if key.startswith("int"):
        return "int"
    if key.startswith("atk"):
        return "atk"
    if key.startswith("magic"):
        return "magic"
    if key.startswith("all"):
        return "all"
    return "other"


ATTR_COLUMN_ORDER = ("str", "dex", "luk", "int", "atk", "magic", "all", "other")


class FireApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("好火花")
        self.root.geometry(WIN_SIZE_NORMAL)
        self.root.minsize(520, 220)
        icon_path = _FIRE_DIR / "icon" / "icon.png"
        if icon_path.is_file():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
                self._icon_ref = icon  # 防止被 GC
            except Exception:
                pass

        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self._log_visible = False
        self._equip_visible = False
        self._attr_visible = False

        self._equip_var = tk.StringVar(value="140首饰")
        self._termination_groups: List[List[str]] = []

        self._build_ui()
        self._bind_keys()
        self._register_global_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="就绪（F11 开始 / F12 结束）")
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

        # 注意事项（模仿 Cube：首页展示，部分词红色）
        self._notice_frame = ttk.Frame(main)
        NOTICE_TEXT = """注意事项：
1.请将冒冒窗口调至1366*768及以下
2.请将冒冒窗口置于屏幕左上角（可用快捷键win + ←实现快速置于左上角）
3.如有多个屏幕，请将冒冒窗口置于主屏左上角
4.请确保窗口内能看到词条区域（属性图需与词条清晰匹配）
5.若无法自动点击/按键，请尝试管理员权限打开本工具
6.置灰的属性代表还没有对应的截图，如果错过变异数字顶，自认倒霉！
"""
        self._notice_text = tk.Text(
            self._notice_frame,
            height=10,
            width=66,
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
        for phrase in ("管理员权限", "flag.png", "双空格", "0.5秒"):
            start = self._notice_text.search(phrase, "1.0", tk.END)
            if start:
                end = f"{start}+{len(phrase)}c"
                self._notice_text.tag_add("red", start, end)
        self._notice_text.config(state=tk.DISABLED)
        self._notice_text.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # 选择装备
        self._equip_frame = ttk.LabelFrame(main, text="选择装备", padding=8)
        for name in ("140首饰", "160首饰", "200防具首饰", "250防具首饰", "武器"):
            ttk.Radiobutton(self._equip_frame, text=name, variable=self._equip_var, value=name, command=self._on_equip_changed).pack(
                anchor=tk.W, pady=3
            )
        ttk.Button(self._equip_frame, text="确定", command=self._hide_equip).pack(pady=(8, 0))

        # 选择属性（终止条件组）
        self._attr_frame = ttk.LabelFrame(main, text="选择属性（终止条件组：任一组满足即停止）", padding=8)
        top_row = ttk.Frame(self._attr_frame)
        top_row.pack(fill=tk.X)
        ttk.Button(top_row, text="添加组合", command=self._open_attr_popup).pack(side=tk.LEFT)
        ttk.Button(top_row, text="清空组合", command=self._clear_groups).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top_row, text="确定", command=self._hide_attr).pack(side=tk.RIGHT)

        self._group_label = ttk.Label(self._attr_frame, text="", font=("", 9), wraplength=520, justify=tk.LEFT)
        self._group_label.pack(fill=tk.X, pady=(10, 0))
        self._update_group_display()

        # 日志
        self._log_frame = ttk.LabelFrame(main, text="运行日志", padding=4)
        self._log_text = tk.Text(self._log_frame, height=16, width=60, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED)
        scroll = ttk.Scrollbar(self._log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scroll.set)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_equip_changed(self) -> None:
        self._update_group_display()

    def _clear_groups(self) -> None:
        self._termination_groups.clear()
        self._update_group_display()

    def _update_group_display(self) -> None:
        equip = self._equip_var.get()
        if not self._termination_groups:
            self._group_label.config(text=f"{equip}:（无组合）")
            return
        lines = []
        for g in self._termination_groups:
            lines.append("[" + " ".join(g) + "]")
        self._group_label.config(text=f"{equip}:\n" + "\n".join(lines))

    def _toggle_equip(self) -> None:
        if self._equip_visible:
            self._hide_equip()
            return
        if self._attr_visible:
            self._hide_attr()
        if self._log_visible:
            self._toggle_log()
        self._notice_frame.pack_forget()
        self._equip_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_EQUIP)
        self._equip_visible = True

    def _hide_equip(self) -> None:
        if not self._equip_visible:
            return
        self._equip_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_NORMAL)
        self._equip_visible = False

    def _toggle_attr(self) -> None:
        if self._attr_visible:
            self._hide_attr()
            return
        if self._equip_visible:
            self._hide_equip()
        if self._log_visible:
            self._toggle_log()
        self._notice_frame.pack_forget()
        self._update_group_display()
        self._attr_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_ATTR)
        self._attr_visible = True

    def _hide_attr(self) -> None:
        if not self._attr_visible:
            return
        self._attr_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_NORMAL)
        self._attr_visible = False

    def _toggle_log(self) -> None:
        if self._log_visible:
            self._log_frame.pack_forget()
            self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
            self._log_visible = False
            return
        if self._equip_visible:
            self._hide_equip()
        if self._attr_visible:
            self._hide_attr()
        self._notice_frame.pack_forget()
        self._log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_LOG)
        self.btn_log.config(text="隐藏日志")
        self._log_visible = True

    def _open_attr_popup(self) -> None:
        equip = self._equip_var.get()
        attrs = EQUIP_TO_ATTRS.get(equip, [])
        if not attrs:
            self.status_var.set("请先选择装备类型")
            return

        pic_dir = _picture_dir(_FIRE_DIR)
        popup = tk.Toplevel(self.root)
        popup.title("选择属性（点击添加；点“完成一组”保存并继续选下一组）")
        popup.resizable(False, False)

        selected: List[str] = []
        btn_widgets = {}

        def on_click(key: str) -> None:
            nonlocal selected
            # 同组允许重复点击同一 key（需要就重复）
            selected.append(key)
            if len(selected) >= 3:
                self._finish_group(selected)
                selected.clear()
                return

        # 按列分组显示
        cols = {c: [] for c in ATTR_COLUMN_ORDER}
        for k in attrs:
            cols[_attr_to_column(k)].append(k)

        col_idx = 0
        for col_name in ATTR_COLUMN_ORDER:
            keys = cols.get(col_name, [])
            if not keys:
                continue
            ttk.Label(popup, text=col_name.upper()).grid(row=0, column=col_idx, padx=8, pady=(8, 4))
            for r, key in enumerate(keys, start=1):
                bt = ttk.Button(popup, text=key, width=12, command=lambda kk=key: on_click(kk))
                if not (pic_dir / f"{key}.png").is_file():
                    bt.config(state=tk.DISABLED)
                bt.grid(row=r, column=col_idx, padx=6, pady=2, sticky=tk.W)
                btn_widgets[key] = bt
            col_idx += 1

        bottom = ttk.Frame(popup)
        bottom.grid(row=100, column=0, columnspan=max(1, col_idx), pady=(10, 8))
        bottom.columnconfigure(0, weight=1)

        # 当前已保存的组合 + 当前选择
        info = ttk.Frame(bottom)
        info.pack(side=tk.LEFT)
        ttk.Label(info, text="已保存组合：").pack(anchor=tk.W)
        saved = ttk.Label(info, text="", width=48, justify=tk.LEFT)
        saved.pack(anchor=tk.W, pady=(2, 6))
        ttk.Label(info, text="当前选择：").pack(anchor=tk.W)
        cur = ttk.Label(info, text="", width=48, justify=tk.LEFT)
        cur.pack(anchor=tk.W, pady=(2, 0))

        def refresh() -> None:
            cur.config(text=" ".join(selected))
            lines = ["[" + " ".join(g) + "]" for g in self._termination_groups] or ["（无）"]
            saved.config(text="\n".join(lines))
            # 动态刷新：如果弹窗打开后新增了图片文件，按钮会自动解灰
            for k, bt in btn_widgets.items():
                try:
                    bt.config(state=(tk.NORMAL if (pic_dir / f"{k}.png").is_file() else tk.DISABLED))
                except Exception:
                    pass
            popup.after(120, refresh)

        refresh()

        btns = ttk.Frame(bottom)
        btns.pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(btns, text="完成一组", command=lambda: (self._finish_group(selected), selected.clear())).pack(fill=tk.X)
        ttk.Button(btns, text="清空当前", command=lambda: selected.clear()).pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btns, text="关闭", command=popup.destroy).pack(fill=tk.X, pady=(6, 0))

        # 居中
        popup.update_idletasks()
        pw, ph = popup.winfo_width(), popup.winfo_height()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        rx, ry = self.root.winfo_x(), self.root.winfo_y()
        popup.geometry(f"+{rx + (rw - pw)//2}+{ry + (rh - ph)//2}")

    def _finish_group(self, selected: List[str]) -> None:
        if not selected:
            return
        self._termination_groups.append(list(selected))
        self._update_group_display()

    def _log_append(self, msg: str) -> None:
        def _do():
            self._log_text.config(state=tk.NORMAL)
            self._log_text.insert(tk.END, msg + "\n")
            self._log_text.see(tk.END)
            self._log_text.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _log_clear(self) -> None:
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete(1.0, tk.END)
        self._log_text.config(state=tk.DISABLED)

    def _bind_keys(self) -> None:
        self.root.bind("<F11>", lambda _e: self.start())
        self.root.bind("<F12>", lambda _e: self.stop())

    def _register_global_hotkeys(self) -> None:
        if not HAS_KEYBOARD or keyboard is None:
            return

        def on_f11():
            self.root.after(0, self.start)

        def on_f12():
            self.root.after(0, self.stop)

        try:
            keyboard.add_hotkey("f11", on_f11, suppress=False)
            keyboard.add_hotkey("f12", on_f12, suppress=False)
        except Exception:
            pass

    def _on_close(self) -> None:
        if HAS_KEYBOARD and keyboard is not None:
            try:
                keyboard.remove_hotkey("f11")
                keyboard.remove_hotkey("f12")
            except Exception:
                try:
                    keyboard.unhook_all_hotkeys()
                except Exception:
                    pass
        self.root.destroy()

    def _set_running(self, running: bool) -> None:
        if running:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        else:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

    def _status_callback(self, msg: str) -> None:
        def _update():
            self.status_var.set(msg)
            self._set_running(False)
        self.root.after(0, _update)

    def _log_callback(self, msg: str) -> None:
        self.root.after(0, lambda m=msg: self._log_append(m))

    def start(self) -> None:
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.stop_event.clear()
        self.status_var.set("运行中…")
        self._set_running(True)
        self.root.after(0, self._log_clear)
        equip = self._equip_var.get()
        groups = list(self._termination_groups)
        self.worker_thread = threading.Thread(
            target=run_fire_loop,
            args=(self.stop_event, self._status_callback, self._log_callback, equip, groups, _FIRE_DIR),
            daemon=True,
        )
        self.worker_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.status_var.set("正在停止…")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = FireApp()
    app.run()

