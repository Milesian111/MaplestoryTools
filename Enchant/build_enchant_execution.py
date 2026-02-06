"""
强化任务 GUI：打包为 exe 的入口。
提供图形界面：开始/结束按钮，F11 开始、F12 结束。
F11/F12 使用全局热键，在任意窗口下都有效（需安装 keyboard：pip install keyboard）。
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# 全局热键（任意窗口下 F11/F12 生效）
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

# 导入 enchant_level 的核心逻辑
from enchant_level import run_enchant_level_loop, find_image_and_click
# 导入 enchant_ability 的核心逻辑
from enchant_ability import find_image_in_region, perform_click_sequence

# 窗口尺寸常量
WIN_SIZE_NORMAL = "400x300"
WIN_SIZE_WITH_LOG = "400x500"
WIN_SIZE_WITH_CONDITIONS = "600x500"  # 选择终止条件时的窗口高度


class EnchantExecutionApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("好内搭-测试版")
        self.root.geometry(WIN_SIZE_NORMAL)
        
        self.stop_event = threading.Event()
        self.worker_thread = None
        
        # 功能选择变量（单选）
        self._function_var = tk.StringVar(value="上绿")  # 默认选择"上绿"
        
        # 日志显示状态
        self._log_visible = False
        self._conditions_visible = False
        
        # 洗属性终止条件变量
        self._cond1_var = tk.BooleanVar(value=False)  # 三攻
        self._cond2_var = tk.BooleanVar(value=False)  # 双攻
        self._cond3_var = tk.BooleanVar(value=False)  # 双攻力
        self._cond4_var = tk.BooleanVar(value=False)  # 双攻敏
        self._cond5_var = tk.BooleanVar(value=False)  # 双攻运
        self._cond6_var = tk.BooleanVar(value=False)  # 双攻血
        self._cond7_var = tk.BooleanVar(value=False)  # 单攻力
        self._cond8_var = tk.BooleanVar(value=False)  # 单攻敏
        self._cond9_var = tk.BooleanVar(value=False)  # 单攻运
        self._cond10_var = tk.BooleanVar(value=False)  # 单攻血
        self._cond11_var = tk.BooleanVar(value=False)  # 三魔
        self._cond12_var = tk.BooleanVar(value=False)  # 双魔
        self._cond13_var = tk.BooleanVar(value=False)  # 双魔智
        self._cond14_var = tk.BooleanVar(value=False)  # 单魔智
        
        self._updating_cond2_state = False  # 防止递归更新
        
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

        self.btn_log = ttk.Button(btn_frame, text="显示日志", command=self._toggle_log)
        self.btn_log.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_function = ttk.Button(btn_frame, text="功能选择", command=self._show_function_selection)
        self.btn_function.pack(side=tk.LEFT, padx=(0, 8))
        
        self.btn_conditions = ttk.Button(btn_frame, text="选择终止条件", command=self._show_conditions)
        self.btn_conditions.pack(side=tk.LEFT)

        # 功能选择区域（默认不显示）
        self._function_frame = ttk.LabelFrame(main, text="功能选择", padding=8)
        # 不pack，由_show_function_selection控制
        
        # 创建单选按钮
        ttk.Radiobutton(
            self._function_frame,
            text="上绿",
            variable=self._function_var,
            value="上绿"
        ).pack(anchor=tk.W, pady=4)
        
        ttk.Radiobutton(
            self._function_frame,
            text="洗属性",
            variable=self._function_var,
            value="洗属性"
        ).pack(anchor=tk.W, pady=4)
        
        ttk.Button(self._function_frame, text="确定", command=self._hide_function_selection).pack(pady=(8, 0))

        # 日志区域（默认隐藏）
        self._log_frame = ttk.LabelFrame(main, text="运行日志", padding=4)
        # 不 pack，由 _toggle_log 控制

        self._log_text = tk.Text(
            self._log_frame,
            height=14,
            width=50,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        log_scroll = ttk.Scrollbar(self._log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 终止条件选择区域（默认不显示，只在选择"洗属性"时显示）
        self._conditions_frame = ttk.LabelFrame(main, text="终止条件", padding=8)
        # 不pack，由_show_conditions控制
        
        # 创建两列布局
        conditions_left = ttk.Frame(self._conditions_frame)
        conditions_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        conditions_right = ttk.Frame(self._conditions_frame)
        conditions_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 左列：攻相关条件
        ttk.Label(conditions_left, text="攻相关条件：", font=("", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))
        ttk.Checkbutton(conditions_left, text="三攻", variable=self._cond1_var).pack(anchor=tk.W, pady=2)
        self._cond2_check = ttk.Checkbutton(conditions_left, text="双攻", variable=self._cond2_var, command=self._on_cond2_toggle)
        self._cond2_check.pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(conditions_left, text="双攻力", variable=self._cond3_var).pack(anchor=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(conditions_left, text="双攻敏", variable=self._cond4_var).pack(anchor=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(conditions_left, text="双攻运", variable=self._cond5_var).pack(anchor=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(conditions_left, text="双攻血", variable=self._cond6_var).pack(anchor=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(conditions_left, text="单攻力", variable=self._cond7_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(conditions_left, text="单攻敏", variable=self._cond8_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(conditions_left, text="单攻运", variable=self._cond9_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(conditions_left, text="单攻血", variable=self._cond10_var).pack(anchor=tk.W, pady=2)
        
        # 右列：魔相关条件
        ttk.Label(conditions_right, text="魔相关条件：", font=("", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))
        ttk.Checkbutton(conditions_right, text="三魔", variable=self._cond11_var).pack(anchor=tk.W, pady=2)
        self._cond12_check = ttk.Checkbutton(conditions_right, text="双魔", variable=self._cond12_var, command=self._on_cond12_toggle)
        self._cond12_check.pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(conditions_right, text="双魔智", variable=self._cond13_var).pack(anchor=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(conditions_right, text="单魔智", variable=self._cond14_var).pack(anchor=tk.W, pady=2)
        
        ttk.Button(self._conditions_frame, text="确定", command=self._hide_conditions).pack(pady=(8, 0))

    def _show_function_selection(self):
        """显示功能选择区域"""
        if hasattr(self, '_function_visible') and self._function_visible:
            return
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="显示日志")
        self._function_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self._function_visible = True

    def _hide_function_selection(self):
        """隐藏功能选择区域"""
        if not hasattr(self, '_function_visible') or not self._function_visible:
            return
        self._function_frame.pack_forget()
        self.root.geometry(WIN_SIZE_NORMAL)
        self._function_visible = False
    
    def _show_conditions(self):
        """显示终止条件选择区域（仅在选择"洗属性"时可用）"""
        if self._function_var.get() != "洗属性":
            messagebox.showinfo("提示", '请先选择"洗属性"功能')
            return
        if self._conditions_visible:
            return
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="显示日志")
        if hasattr(self, '_function_visible') and self._function_visible:
            self._function_frame.pack_forget()
            self._function_visible = False
        self._conditions_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_WITH_CONDITIONS)
        self._conditions_visible = True
    
    def _hide_conditions(self):
        """隐藏终止条件选择区域"""
        if not self._conditions_visible:
            return
        self._conditions_frame.pack_forget()
        self.root.geometry(WIN_SIZE_NORMAL)
        self._conditions_visible = False
    
    def _on_cond2_toggle(self):
        """双攻勾选时，自动勾选双攻力、双攻敏、双攻运、双攻血"""
        if self._updating_cond2_state:
            return
        self._updating_cond2_state = True
        if self._cond2_var.get():
            self._cond3_var.set(True)  # 双攻力
            self._cond4_var.set(True)  # 双攻敏
            self._cond5_var.set(True)  # 双攻运
            self._cond6_var.set(True)  # 双攻血
        self._updating_cond2_state = False
    
    def _on_cond12_toggle(self):
        """双魔勾选时，自动勾选双魔智"""
        if self._updating_cond2_state:
            return
        self._updating_cond2_state = True
        if self._cond12_var.get():
            self._cond13_var.set(True)  # 双魔智
        self._updating_cond2_state = False

    def _toggle_log(self):
        """切换日志显示"""
        if self._log_visible:
            self._log_frame.pack_forget()
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="显示日志")
            self._log_visible = False
        else:
            if hasattr(self, '_function_visible') and self._function_visible:
                self._function_frame.pack_forget()
                self._function_visible = False
            self._log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_WITH_LOG)
            self.btn_log.config(text="隐藏日志")
            self._log_visible = True

    def _log_append(self, msg):
        """追加日志消息"""
        def _do():
            self._log_text.config(state=tk.NORMAL)
            self._log_text.insert(tk.END, msg + "\n")
            self._log_text.see(tk.END)
            self._log_text.config(state=tk.DISABLED)

        self.root.after(0, _do)

    def _bind_keys(self):
        """窗口内焦点时的按键"""
        self.root.bind("<F11>", lambda e: self.start())
        self.root.bind("<F12>", lambda e: self.stop())

    def _register_global_hotkeys(self):
        """注册全局热键，在别的窗口按 F11/F12 也生效"""
        if not HAS_KEYBOARD:
            return
        # 回调在键盘库线程执行，需用 after 切回主线程
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
        """退出时移除全局热键"""
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
        """设置运行状态"""
        if running:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        else:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

    def _status_callback(self, msg):
        """状态回调"""
        def _update():
            self.status_var.set(msg)
            self._set_running(False)

        self.root.after(0, _update)

    def _log_callback(self, msg):
        """日志回调"""
        self.root.after(0, lambda m=msg: self._log_append(m))

    def start(self):
        """开始任务"""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        
        # 检查功能选择
        selected_function = self._function_var.get()
        
        if selected_function == "洗属性":
            # 检查是否至少选择了一个终止条件
            has_condition = (
                self._cond1_var.get() or self._cond2_var.get() or self._cond3_var.get() or
                self._cond4_var.get() or self._cond5_var.get() or self._cond6_var.get() or
                self._cond7_var.get() or self._cond8_var.get() or self._cond9_var.get() or
                self._cond10_var.get() or self._cond11_var.get() or self._cond12_var.get() or
                self._cond13_var.get() or self._cond14_var.get()
            )
            if not has_condition:
                messagebox.showwarning("警告", "请至少选择一个终止条件！")
                return
        
        # 在开始执行前，先查找并点击 window_flag.png
        # 使用静默的 log_callback 避免输出详细日志
        silent_log = lambda msg: None
        found = find_image_and_click('picture/window_flag.png', log_callback=silent_log)
        self._log_callback("激活冒冒窗口")
        import time
        time.sleep(0.2)  # 等待一下再开始
        
        self.stop_event.clear()
        self.status_var.set("运行中…")
        self._set_running(True)
        # 新一轮开始时清空日志
        self.root.after(0, self._log_clear)
        
        # 根据选择的功能启动对应的循环
        if selected_function == "上绿":
            self.worker_thread = threading.Thread(
                target=run_enchant_level_loop,
                args=(self.stop_event, self._status_callback, self._log_callback),
                daemon=True,
            )
            self.worker_thread.start()
        elif selected_function == "洗属性":
            # 构建条件标志字典
            condition_flags = {
                'c1': self._cond1_var.get(),
                'c2': self._cond2_var.get(),
                'c3': self._cond3_var.get(),
                'c4': self._cond4_var.get(),
                'c5': self._cond5_var.get(),
                'c6': self._cond6_var.get(),
                'c7': self._cond7_var.get(),
                'c8': self._cond8_var.get(),
                'c9': self._cond9_var.get(),
                'c10': self._cond10_var.get(),
                'c11': self._cond11_var.get(),
                'c12': self._cond12_var.get(),
                'c13': self._cond13_var.get(),
                'c14': self._cond14_var.get(),
            }
            self.worker_thread = threading.Thread(
                target=run_enchant_ability_loop,
                args=(self.stop_event, self._status_callback, self._log_callback, condition_flags),
                daemon=True,
            )
            self.worker_thread.start()

    def _log_clear(self):
        """清空日志"""
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete(1.0, tk.END)
        self._log_text.config(state=tk.DISABLED)

    def stop(self):
        """停止任务"""
        self.stop_event.set()
        self.status_var.set("正在停止…")

    def run(self):
        """运行GUI"""
        self.root.mainloop()


def run_enchant_ability_loop(stop_event, status_callback, log_callback=None, condition_flags=None):
    """在后台线程中执行洗属性的主循环"""
    if log_callback is None:
        log_callback = lambda msg: None
    
    if condition_flags is None:
        condition_flags = {}
    
    # 从 condition_flags 中获取各个条件的启用状态
    enable_c1 = condition_flags.get('c1', False)  # 三攻
    enable_c2 = condition_flags.get('c2', False)  # 双攻
    enable_c3 = condition_flags.get('c3', False)  # 双攻力
    enable_c4 = condition_flags.get('c4', False)  # 双攻敏
    enable_c5 = condition_flags.get('c5', False)  # 双攻运
    enable_c6 = condition_flags.get('c6', False)  # 双攻血
    enable_c7 = condition_flags.get('c7', False)  # 单攻力
    enable_c8 = condition_flags.get('c8', False)  # 单攻敏
    enable_c9 = condition_flags.get('c9', False)  # 单攻运
    enable_c10 = condition_flags.get('c10', False)  # 单攻血
    enable_c11 = condition_flags.get('c11', False)  # 三魔
    enable_c12 = condition_flags.get('c12', False)  # 双魔
    enable_c13 = condition_flags.get('c13', False)  # 双魔智
    enable_c14 = condition_flags.get('c14', False)  # 单魔智
    
    find_count = 0
    
    try:
        while not stop_event.is_set():
            find_count += 1
            # 使用静默的 log_callback 避免输出详细日志
            silent_log = lambda msg: None
            found_images = find_image_in_region(log_callback=silent_log)
            log_callback(f"第{find_count}次")
            
            # 统计各种图片的找到次数
            atk_count = sum(1 for img in found_images if img['file'] == 'picture/atk_enchant.png')
            magic_count = sum(1 for img in found_images if img['file'] == 'picture/magic_enchant.png')
            str_count = sum(1 for img in found_images if img['file'] == 'picture/str_enchant.png')
            dex_count = sum(1 for img in found_images if img['file'] == 'picture/dex_enchant.png')
            int_count = sum(1 for img in found_images if img['file'] == 'picture/int_enchant.png')
            luk_count = sum(1 for img in found_images if img['file'] == 'picture/luk_enchant.png')
            hp_count = sum(1 for img in found_images if img['file'] == 'picture/hp_enchant.png')
            
            # 检查终止条件
            condition1 = atk_count >= 3  # 三攻
            condition2 = atk_count >= 2  # 双攻
            condition3 = atk_count >= 2 and str_count >= 1  # 双攻力
            condition4 = atk_count >= 2 and dex_count >= 1  # 双攻敏
            condition5 = atk_count >= 2 and luk_count >= 1  # 双攻运
            condition6 = atk_count >= 2 and hp_count >= 1  # 双攻血
            condition7 = atk_count >= 1 and str_count >= 2  # 单攻力
            condition8 = atk_count >= 1 and dex_count >= 2  # 单攻敏
            condition9 = atk_count >= 1 and luk_count >= 2  # 单攻运
            condition10 = atk_count >= 1 and hp_count >= 2  # 单攻血
            condition11 = magic_count >= 3  # 三魔
            condition12 = magic_count >= 2  # 双魔
            condition13 = magic_count >= 2 and int_count >= 1  # 双魔智
            condition14 = magic_count >= 1 and int_count >= 2  # 单魔智
            
            satisfied = (
                (condition1 and enable_c1) or
                (condition2 and enable_c2) or
                (condition3 and enable_c3) or
                (condition4 and enable_c4) or
                (condition5 and enable_c5) or
                (condition6 and enable_c6) or
                (condition7 and enable_c7) or
                (condition8 and enable_c8) or
                (condition9 and enable_c9) or
                (condition10 and enable_c10) or
                (condition11 and enable_c11) or
                (condition12 and enable_c12) or
                (condition13 and enable_c13) or
                (condition14 and enable_c14)
            )
            
            if satisfied:
                log_callback("满足条件，停止洗属性！")
                import winsound
                winsound.Beep(1000, 200)
                status_callback("已满足终止条件，任务结束")
                break
            
            if stop_event.is_set():
                break
            
            # 使用静默的 log_callback 避免输出详细日志
            perform_click_sequence(log_callback=silent_log)
        else:
            log_callback("已手动停止")
            status_callback("已手动停止")
    except Exception as e:
        log_callback(f"运行出错: {e}")
        status_callback(f"运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    app = EnchantExecutionApp()
    app.run()

