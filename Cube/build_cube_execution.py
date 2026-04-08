"""
魔方（洗装备）GUI：打包为 exe 的入口。
提供图形界面：开始/结束、查看日志、选择装备、选择属性。
F11/F12 使用全局热键，在任意窗口下都有效（需安装 keyboard：pip install keyboard）。
"""
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

from click_sequence import activate_window, perform_click_sequence
from cube_logic import check_any_termination_satisfied, check_green_found, find_target_hits, SEARCH_REGION

# 与 build_cube_execution.py 同级的 picture 目录，即项目下的 Cube/picture/
_CUBE_DIR = Path(__file__).resolve().parent
_PICTURE_DIR = _CUBE_DIR / "picture"

WIN_SIZE_NORMAL = "600x250"
WIN_SIZE_WITH_LOG = "600x480"
WIN_SIZE_WITH_EQUIP = "600x420"
WIN_SIZE_WITH_ATTR = "600x280"

# 图片名（不含.png）-> 显示标签
ATTR_LABELS = {
    "all1x": "全属性1%", "all2x": "全属性2%", "all5": "全属性5%", "all6": "全属性6%",
    "all6u": "全属性6%", "all7u": "全属性7%",
    "atk9": "攻击力9%", "atk10": "攻击力10%", "atk12": "攻击力12%", "atk13": "攻击力13%",
    "magic9": "魔力9%", "magic10": "魔力10%", "magic12": "魔力12%", "magic13": "魔力13%",
    "cd1": "冷却-1", "cri1": "爆伤1%", "cri3": "爆伤3%",
    "dex1": "敏捷+1", "dex2": "敏捷+2", "dex2x": "敏捷2%", "dex3x": "敏捷3%",
    "dex6": "敏捷6%", "dex7u": "敏捷7%", "dex8": "敏捷8%", "dex9u": "敏捷9%",
    "str1": "力量+1", "str2": "力量+2", "str2x": "力量2%", "str3x": "力量3%",
    "str6": "力量6%", "str7u": "力量7%", "str8": "力量8%", "str9u": "力量9%",
    "luk1": "运气+1", "luk2": "运气+2", "luk2x": "运气2%", "luk3x": "运气3%",
    "luk6": "运气6%", "luk7u": "运气7%", "luk8": "运气8%", "luk9u": "运气9%",
    "int1": "智力+1", "int2": "智力+2", "int2x": "智力2%", "int3x": "智力3%",
    "int6": "智力6%", "int7u": "智力7%", "int8": "智力8%", "int9u": "智力9%",
    "any": "any",  # 不选择，显示为 any
}

# 装备类型 -> 可选属性列表（图片名）
EQUIP_TO_ATTRS = {
    "200防具饰品": ["str6", "str8", "str1", "str2", "dex6", "dex8", "dex1", "dex2",
                   "luk6", "luk8", "luk1", "luk2", "int6", "int8", "int1", "int2",
                   "all5", "all6", "cri1"],
    "200帽子": ["str6", "str8", "str1", "str2", "dex6", "dex8", "dex1", "dex2",
               "luk6", "luk8", "luk1", "luk2", "int6", "int8", "int1", "int2",
               "all5", "all6", "cri1", "cd1"],
    "200手套": ["str6", "str8", "str1", "str2", "dex6", "dex8", "dex1", "dex2",
               "luk6", "luk8", "luk1", "luk2", "int6", "int8", "int1", "int2",
               "all5", "all6", "cri1", "cri3"],
    "250防具饰品": ["str7u", "str9u", "str1", "str2", "dex7u", "dex9u", "dex1", "dex2",
                   "luk7u", "luk9u", "luk1", "luk2", "int7u", "int9u", "int1", "int2",
                   "all6u", "all7u", "cri1"],
    "250帽子": ["str7u", "str9u", "str1", "str2", "dex7u", "dex9u", "dex1", "dex2",
               "luk7u", "luk9u", "luk1", "luk2", "int7u", "int9u", "int1", "int2",
               "all6u", "all7u", "cri1", "cd1"],
    "250手套": ["str7u", "str9u", "str1", "str2", "dex7u", "dex9u", "dex1", "dex2",
               "luk7u", "luk9u", "luk1", "luk2", "int7u", "int9u", "int1", "int2",
               "all6u", "all7u", "cri1", "cri3"],
    "200级三大件": ["atk10", "atk13", "magic10", "magic13"],
    "140副手": ["atk9", "atk12", "magic9", "magic12"],
    "休彼得曼": ["str2x", "str3x", "dex2x", "dex3x", "luk2x", "luk3x", "int2x", "int3x",
                "all1x", "all2x"],
}

# 属性列顺序：不同属性竖着排，全属性/CD/爆伤合并为一列
ATTR_COLUMN_ORDER = ("str", "dex", "luk", "int", "all_cd_cri", "atk", "magic")


def _attr_to_column(key):
    """将属性key映射到列组。all、cd、cri 归为 all_cd_cri 列。"""
    if key.startswith("str"):
        return "str"
    if key.startswith("dex"):
        return "dex"
    if key.startswith("luk"):
        return "luk"
    if key.startswith("int"):
        return "int"
    if key.startswith("all"):
        return "all_cd_cri"
    if key.startswith("cd"):
        return "all_cd_cri"
    if key.startswith("cri"):
        return "all_cd_cri"
    if key.startswith("atk"):
        return "atk"
    if key.startswith("magic"):
        return "magic"
    return "other"


def run_cube_loop(stop_event, status_callback, log_callback=None, equipment_type=None, termination_groups=None, base_dir=None, picture_dir=None, green_only=False):
    """
    魔方主循环：在屏幕范围内按终止条件找图，多组为或逻辑；找到则停止，否则执行点击序列后继续。
    equipment_type: 当前选择的装备类型。
    termination_groups: 终止条件组列表，如 [["str8","str8","str6"]]，任一组满足即停止；green_only 时忽略。
    base_dir: Cube 目录（用于 activate_window），默认与本脚本同级。
    picture_dir: 属性图片目录（如 str8.png、green.png），默认 Cube/picture/。
    green_only: True 时终止条件为找到 picture/green.png，与主循环逻辑一致。
    """
    if log_callback is None:
        log_callback = lambda msg: None
    base_dir = Path(base_dir or _CUBE_DIR).resolve()
    picture_dir = Path(picture_dir or _PICTURE_DIR).resolve()
    try:
        log_callback("激活窗口…")
        activate_window(base_dir, SEARCH_REGION)
        time.sleep(0.5)
        n = 0
        found_condition = False
        while not stop_event.is_set():
            n += 1
            if green_only:
                if check_green_found(SEARCH_REGION, picture_dir):
                    log_callback(f"第{n}次，满足条件[绿]")
                    if HAS_WINSOUND:
                        try:
                            winsound.Beep(1000, 500)
                        except Exception:
                            pass
                    status_callback("已找到终止条件")
                    found_condition = True
                    break
                log_callback(f"第{n}次，未找到目标条件")
                perform_click_sequence()
                if stop_event.is_set():
                    break
                time.sleep(0.3)
                continue
            if not termination_groups:
                log_callback(f"第{n}次，未设置终止条件，请在选择属性中添加")
                time.sleep(1.0)
                continue
            satisfied_group = check_any_termination_satisfied(SEARCH_REGION, termination_groups, picture_dir)
            if satisfied_group is not None:
                labels_str = " ".join(ATTR_LABELS.get(k, k) for k in satisfied_group)
                log_callback(f"第{n}次，满足条件[{labels_str}]")
                if HAS_WINSOUND:
                    try:
                        winsound.Beep(1000, 500)
                    except Exception:
                        pass
                status_callback("已找到终止条件")
                found_condition = True
                break
            hits = find_target_hits(SEARCH_REGION, termination_groups, picture_dir)
            if hits:
                parts = [f"{cnt}个{ATTR_LABELS.get(key, key)}" for key, cnt in sorted(hits.items())]
                log_callback(f"第{n}次，找到" + "，".join(parts))
            else:
                log_callback(f"第{n}次，未找到目标条件")
            perform_click_sequence()
            if stop_event.is_set():
                break
            time.sleep(0.3)
    except Exception as e:
        log_callback(f"运行出错: {e}")
        status_callback(f"运行出错: {e}")
    else:
        if not found_condition:
            log_callback("已手动停止")
            status_callback("已手动停止")


class CubeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("好附加")
        self.root.geometry(WIN_SIZE_NORMAL)
        self.root.resizable(True, True)
        self.root.minsize(480, 180)

        self.stop_event = threading.Event()
        self.worker_thread = None
        self._log_visible = False
        self._equip_visible = False
        self._attr_visible = False
        # 装备类型（单选），记录打开装备面板时的选择，用于修改装备时自动清除属性
        self._equip_var = tk.StringVar(value="200防具饰品")
        self._equip_when_opened = None
        self._green_mode = False
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
        self.btn_attr.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_green = ttk.Button(btn_frame, text="上绿", command=self._toggle_green)
        self.btn_green.pack(side=tk.LEFT)

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
            "200帽子",
            "200手套",
            "250防具饰品",
            "250帽子",
            "250手套",
            "200级三大件",
            "140副手",
            "休彼得曼",
        ]
        self._equip_frame = ttk.LabelFrame(main, text="选择装备", padding=8)
        for opt in EQUIP_OPTIONS:
            ttk.Radiobutton(self._equip_frame, text=opt, variable=self._equip_var, value=opt).pack(anchor=tk.W, pady=2)
        ttk.Button(self._equip_frame, text="确定", command=self._hide_equip).pack(pady=(8, 0))

        # 选择属性区域（终止条件），按组存储，每组最多3个
        self._termination_attrs = []  # 如 [["str8", "str8", "all6"], ["str8", "str8", "str2"]]
        self._attr_frame = ttk.LabelFrame(main, text="选择属性", padding=8)
        attr_btn_row = ttk.Frame(self._attr_frame)
        attr_btn_row.pack(anchor=tk.W)
        ttk.Button(attr_btn_row, text="添加终止条件", command=self._show_add_termination_popup).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(attr_btn_row, text="清除选择", command=self._clear_termination_attrs).pack(side=tk.LEFT)
        self._attr_display_frame = ttk.Frame(self._attr_frame)
        self._attr_display_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._attr_display_label = ttk.Label(
            self._attr_display_frame, text="", font=("", 9), wraplength=480
        )
        self._attr_display_label.pack(anchor=tk.W)
        ttk.Button(self._attr_frame, text="确定", command=self._hide_attr).pack(pady=(8, 0))

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
        self._equip_when_opened = self._equip_var.get()
        self._equip_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_EQUIP)
        self._equip_visible = True

    def _toggle_green(self):
        """上绿模式：终止条件为找到 green.png；开启后禁用选择装备、选择属性。"""
        self._green_mode = not self._green_mode
        if self._green_mode:
            self.btn_green.config(text="取消上绿")
            self.btn_equip.config(state=tk.DISABLED)
            self.btn_attr.config(state=tk.DISABLED)
        else:
            self.btn_green.config(text="上绿")
            self.btn_equip.config(state=tk.NORMAL)
            self.btn_attr.config(state=tk.NORMAL)

    def _hide_equip(self):
        if not self._equip_visible:
            return
        if self._equip_var.get() != self._equip_when_opened:
            self._termination_attrs.clear()
            self._update_attr_display()
        self._equip_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_NORMAL)
        self._equip_visible = False

    def _clear_termination_attrs(self):
        """清除所有已选终止条件。"""
        self._termination_attrs.clear()
        self._update_attr_display()

    def _update_attr_display(self):
        """刷新已选终止条件的显示。前缀为当前装备名，每组中括号、空格分隔，新组换行。"""
        equip_name = self._equip_var.get()
        if not self._termination_attrs:
            self._attr_display_label.config(text=f"{equip_name}: （无）")
        else:
            lines = []
            for group in self._termination_attrs:
                labels = [ATTR_LABELS.get(k, k) for k in group]
                lines.append("[" + " ".join(labels) + "]")
            self._attr_display_label.config(text=equip_name + ":\n" + "\n".join(lines))

    def _show_add_termination_popup(self):
        """弹窗选择属性作为终止条件，选3个后自动关闭。属性为按钮，可重复选择（点击切换选中）。"""
        equip = self._equip_var.get()
        attrs = EQUIP_TO_ATTRS.get(equip, [])
        if not attrs:
            self.status_var.set("请先选择装备类型")
            return
        popup = tk.Toplevel(self.root)
        popup.title("选择终止条件（选3个，可重复）")
        popup.transient(self.root)
        popup.grab_set()
        selected = []  # 可重复，如 ["str8", "str8", "str6"]
        btn_widgets = {}

        def update_btn_text():
            for key, (btn, base_label) in btn_widgets.items():
                n = selected.count(key)
                btn.config(text=base_label if n == 0 else f"{base_label} ×{n}")

        def on_attr_click(key):
            nonlocal selected
            if len(selected) >= 3:
                return
            selected.append(key)
            update_btn_text()
            if len(selected) == 3:
                self._termination_attrs.append(list(selected))
                self._update_attr_display()
                popup.destroy()

        by_col = {}
        for key in attrs:
            col = _attr_to_column(key)
            by_col.setdefault(col, []).append(key)
        col_idx = 0
        for col_name in ATTR_COLUMN_ORDER:
            keys = by_col.pop(col_name, [])
            if not keys:
                continue
            for row_idx, key in enumerate(keys):
                label = ATTR_LABELS.get(key, key)
                btn = ttk.Button(popup, text=label, command=lambda k=key: on_attr_click(k))
                btn.grid(row=row_idx, column=col_idx, sticky=tk.W, padx=6, pady=2)
                btn_widgets[key] = (btn, label)
            col_idx += 1
        for col_name, keys in by_col.items():
            for row_idx, key in enumerate(keys):
                label = ATTR_LABELS.get(key, key)
                btn = ttk.Button(popup, text=label, command=lambda k=key: on_attr_click(k))
                btn.grid(row=row_idx, column=col_idx, sticky=tk.W, padx=6, pady=2)
                btn_widgets[key] = (btn, label)
            col_idx += 1

        # any = 不选择，底部居中
        popup.columnconfigure(0, weight=1)
        bottom_frame = ttk.Frame(popup)
        bottom_frame.grid(row=100, column=0, columnspan=col_idx + 1, sticky=tk.EW, pady=(8, 0))
        bottom_frame.columnconfigure(0, weight=1)
        any_label = ATTR_LABELS["any"]
        any_btn = ttk.Button(bottom_frame, text="any（不选择）", command=lambda: on_attr_click("any"))
        any_btn.pack(anchor=tk.CENTER)
        btn_widgets["any"] = (any_btn, any_label)

        # 弹窗固定在主窗口中心
        popup.update_idletasks()
        pw = popup.winfo_width()
        ph = popup.winfo_height()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        x = rx + (rw - pw) // 2
        y = ry + (rh - ph) // 2
        popup.geometry(f"+{x}+{y}")

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
        self._update_attr_display()
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
        termination_groups = list(self._termination_attrs)
        green_only = self._green_mode
        self.worker_thread = threading.Thread(
            target=run_cube_loop,
            args=(self.stop_event, self._status_callback, self._log_callback, equipment_type, termination_groups, _CUBE_DIR, _PICTURE_DIR, green_only),
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
