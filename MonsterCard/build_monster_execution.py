"""
怪物能力任务 GUI：打包为 exe 的入口。
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

# 导入 monster_ability 的核心逻辑
from monster_ability import find_image_in_region, perform_click_sequence
import winsound
from pathlib import Path
import sys
import os

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容PyInstaller打包后的exe"""
    try:
        # PyInstaller打包后会设置_MEIPASS属性
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境，使用脚本所在目录
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


def run_monster_loop(stop_event, status_callback, log_callback=None, condition_flags=None):
    """在后台线程中执行 monster_ability 的主循环，遇 stop_event 或满足终止条件时退出。
    condition_flags: (enable_c2, enable_c3, enable_c4, enable_c5, enable_c6, enable_c7, c3_sub_flags)，condition1 始终启用。
    c3_sub_flags: (enable_c3_1, enable_c3_2, ..., enable_c3_11) 条件3的11个子条件"""
    if log_callback is None:
        log_callback = lambda msg: None
    if condition_flags is None:
        condition_flags = (True, False, True, True, True, True, (True,)*11)  # c2=True, c3=False, c4=True, c5=True, c6=True, c7=True, c3_sub全部True
    enable_c2, enable_c3, enable_c4, enable_c5, enable_c6, enable_c7, c3_sub_flags = condition_flags
    enable_c3_1, enable_c3_2, enable_c3_3, enable_c3_4, enable_c3_5, enable_c3_6, enable_c3_7, enable_c3_8, enable_c3_9, enable_c3_10, enable_c3_11 = c3_sub_flags
    find_count = 0
    try:
        while not stop_event.is_set():
            find_count += 1
            found_images = find_image_in_region()

            final_count = sum(1 for img in found_images if img["file"] == "picture/final.png")
            monster_atk_count = sum(1 for img in found_images if img["file"] == "picture/monster_atk.png")
            monster_magic_count = sum(1 for img in found_images if img["file"] == "picture/monster_magic.png")
            skill_2_count = sum(1 for img in found_images if img["file"] == "picture/skill_2.png")
            monster_all_count = sum(1 for img in found_images if img["file"] == "picture/monster_all.png")
            monster_str_count = sum(1 for img in found_images if img["file"] == "picture/monster_str.png")
            monster_dex_count = sum(1 for img in found_images if img["file"] == "picture/monster_dex.png")
            monster_int_count = sum(1 for img in found_images if img["file"] == "picture/monster_int.png")
            monster_luk_count = sum(1 for img in found_images if img["file"] == "picture/monster_luk.png")
            monster_cri_count = sum(1 for img in found_images if img["file"] == "picture/monster_cri.png")
            monster_hp_count = sum(1 for img in found_images if img["file"] == "picture/monster_hp.png")
            monster_ignore_count = sum(1 for img in found_images if img["file"] == "picture/monster_ignore.png")
            monster_buff_count = sum(1 for img in found_images if img["file"] == "picture/monster_buff.png")

            # 按照指定顺序和名称映射构建日志
            count_items = [
                (final_count, "终"),
                (monster_atk_count, "攻"),
                (monster_magic_count, "魔"),
                (skill_2_count, "被"),
                (monster_all_count, "全"),
                (monster_str_count, "力"),
                (monster_dex_count, "敏"),
                (monster_int_count, "智"),
                (monster_luk_count, "运"),
                (monster_cri_count, "爆"),
                (monster_hp_count, "血"),
                (monster_ignore_count, "无视"),
                (monster_buff_count, "buff"),
            ]
            
            # 过滤出count > 0的项
            found_items = [(count, name) for count, name in count_items if count > 0]
            
            if not found_items:
                # 所有图都没找到
                log_callback(f"第{find_count}次，无有效词条")
            else:
                # 构建输出字符串：数字+名称，用顿号分隔
                result_parts = [f"{count}{name}" for count, name in found_items]
                log_callback(f"第{find_count}次，找到{'、'.join(result_parts)}")

            condition1 = final_count >= 3  # 三终（必选）
            condition2 = final_count >= 2  # 双终0
            
            # 条件3的11个子条件
            condition3_1 = condition2 and monster_atk_count >= 1  # 双终攻
            condition3_2 = condition2 and monster_magic_count >= 1  # 双终魔
            condition3_3 = condition2 and monster_all_count >= 1  # 双终全
            condition3_4 = condition2 and monster_str_count >= 1  # 双终力
            condition3_5 = condition2 and monster_dex_count >= 1  # 双终敏
            condition3_6 = condition2 and monster_int_count >= 1  # 双终智
            condition3_7 = condition2 and monster_luk_count >= 1  # 双终运
            condition3_8 = condition2 and monster_cri_count >= 1  # 双终爆
            condition3_9 = condition2 and monster_hp_count >= 1  # 双终血
            condition3_10 = condition2 and monster_ignore_count >= 1  # 双终无视
            condition3_11 = condition2 and monster_buff_count >= 1  # 双终buff
            
            # 条件3：所有启用的子条件的并集
            condition3 = (
                (condition3_1 and enable_c3_1) or
                (condition3_2 and enable_c3_2) or
                (condition3_3 and enable_c3_3) or
                (condition3_4 and enable_c3_4) or
                (condition3_5 and enable_c3_5) or
                (condition3_6 and enable_c3_6) or
                (condition3_7 and enable_c3_7) or
                (condition3_8 and enable_c3_8) or
                (condition3_9 and enable_c3_9) or
                (condition3_10 and enable_c3_10) or
                (condition3_11 and enable_c3_11)
            )
            
            condition4 = (monster_atk_count >= 2 or monster_magic_count >= 2) and skill_2_count >= 1  # 双攻被、双魔被
            condition5 = final_count >= 1 and (monster_atk_count >= 2 or monster_magic_count >= 2)  # 双攻终、双魔终
            condition6 = (
                final_count >= 1
                and skill_2_count >= 1
                and (monster_atk_count >= 1 or monster_magic_count >= 1)
            )  # 终攻被、终魔被
            condition7 = monster_atk_count >= 3 or monster_magic_count >= 3  # 三攻、三魔

            satisfied = condition1 or (condition2 and enable_c2) or (condition3 and enable_c3) or (condition4 and enable_c4) or (condition5 and enable_c5) or (condition6 and enable_c6) or (condition7 and enable_c7)
            if satisfied:
                log_callback("满足条件，停止魔方！")
                # 判断是否满足条件1、条件3_1或条件3_2
                play_wav = (
                    condition1 or
                    (condition3_1 and enable_c3_1) or
                    (condition3_2 and enable_c3_2)
                )
                if play_wav:
                    # 额外输出日志
                    log_callback("沃日！狗叫！分钱！")
                    # 播放wav文件（兼容PyInstaller打包）
                    wav_path = get_resource_path("sound/wangwang.wav")
                    if os.path.exists(wav_path):
                        winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                    else:
                        winsound.Beep(1000, 200)  # 如果文件不存在，回退到beep
                else:
                    winsound.Beep(1000, 200)
                status_callback("已满足终止条件，任务结束")
                break

            if stop_event.is_set():
                break

            perform_click_sequence(log_callback=log_callback)
        else:
            log_callback("已手动停止")
            status_callback("已手动停止")
    except Exception as e:
        log_callback(f"运行出错: {e}")
        status_callback(f"运行出错: {e}")
        import traceback
        traceback.print_exc()


# 窗口尺寸（初始高度拉大）
WIN_SIZE_NORMAL = "520x250"
WIN_SIZE_WITH_CONDITIONS = "520x370"  # 选择终止条件时拉高（增加了高度以容纳条件3的子条件）
WIN_SIZE_WITH_CONDITIONS_EXPANDED = "520x600"  # 条件3展开时的窗口高度
WIN_SIZE_WITH_LOG = "520x480"


class MonsterAbilityApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("好怪魔方")
        self.root.geometry(WIN_SIZE_NORMAL)
        self.root.resizable(True, True)
        self.root.minsize(480, 180)

        self.stop_event = threading.Event()
        self.worker_thread = None
        self._log_visible = False
        self._conditions_visible = False
        # 终止条件勾选：condition1 固定启用，condition2~7 可勾选
        self._cond2_var = tk.BooleanVar(value=True)
        self._cond3_var = tk.BooleanVar(value=True)  # 双终+有效
        self._cond4_var = tk.BooleanVar(value=True)
        self._cond5_var = tk.BooleanVar(value=True)
        self._cond6_var = tk.BooleanVar(value=True)
        self._cond7_var = tk.BooleanVar(value=True)
        
        # 条件3的11个子条件
        self._cond3_1_var = tk.BooleanVar(value=True)  # 双终攻
        self._cond3_2_var = tk.BooleanVar(value=True)  # 双终魔
        self._cond3_3_var = tk.BooleanVar(value=True)  # 双终全
        self._cond3_4_var = tk.BooleanVar(value=True)  # 双终力
        self._cond3_5_var = tk.BooleanVar(value=True)  # 双终敏
        self._cond3_6_var = tk.BooleanVar(value=True)  # 双终智
        self._cond3_7_var = tk.BooleanVar(value=True)  # 双终运
        self._cond3_8_var = tk.BooleanVar(value=True)  # 双终爆
        self._cond3_9_var = tk.BooleanVar(value=True)  # 双终血
        self._cond3_10_var = tk.BooleanVar(value=True)  # 双终无视
        self._cond3_11_var = tk.BooleanVar(value=True)  # 双终buff
        
        # 条件3子条件展开状态
        self._cond3_expanded = False
        self._updating_cond3_state = False  # 防止递归更新
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

        self.btn_conditions = ttk.Button(btn_frame, text="选择终止条件", command=self._show_conditions_inline)
        self.btn_conditions.pack(side=tk.LEFT)

        # 注意事项（隐藏详情时显示，与顶上状态同风格，无框；部分词红色）
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
        # 将指定词语标红
        for phrase in ("关闭强化动画","管理员权限", "不得用于商业用途", "不得将本工具外传", "马没了^_^"):
            start = self._notice_text.search(phrase, "1.0", tk.END)
            if start:
                end = f"{start}+{len(phrase)}c"
                self._notice_text.tag_add("red", start, end)
        self._notice_text.config(state=tk.DISABLED)
        self._notice_text.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # 终止条件选择区域（与注意事项同位置切换，默认不显示）
        self._conditions_frame = ttk.Frame(main)
        cf = self._conditions_frame
        ttk.Label(cf, text="以下满足任一即停止：", font=("", 9)).pack(anchor=tk.W)
        ttk.Separator(cf, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(4, 8))
        _var1 = tk.BooleanVar(value=True)
        ttk.Checkbutton(cf, text="三终（必选）", variable=_var1, state=tk.DISABLED).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(cf, text="双终0", variable=self._cond2_var).pack(anchor=tk.W, pady=2)
        
        # 条件3：双终+有效（带展开按钮）
        cond3_frame = ttk.Frame(cf)
        cond3_frame.pack(anchor=tk.W, pady=2, fill=tk.X)
        self._cond3_check = ttk.Checkbutton(cond3_frame, text="双终+有效", variable=self._cond3_var, command=self._on_cond3_toggle)
        self._cond3_check.pack(side=tk.LEFT)
        self._cond3_expand_btn = ttk.Button(cond3_frame, text="▼", width=3, command=self._toggle_cond3_expand)
        self._cond3_expand_btn.pack(side=tk.LEFT, padx=(4, 0))
        
        # 条件3的11个子条件（默认隐藏）
        self._cond3_sub_frame = ttk.Frame(cf)
        # 不pack，由_toggle_cond3_expand控制
        
        # 创建11个子条件的复选框
        sub_labels = ["双终攻", "双终魔", "双终全", "双终力", "双终敏", "双终智", "双终运", "双终爆", "双终血", "双终无视", "双终buff"]
        sub_vars = [self._cond3_1_var, self._cond3_2_var, self._cond3_3_var, self._cond3_4_var,
                    self._cond3_5_var, self._cond3_6_var, self._cond3_7_var, self._cond3_8_var, self._cond3_9_var,
                    self._cond3_10_var, self._cond3_11_var]
        self._cond3_sub_checks = []
        for label, var in zip(sub_labels, sub_vars):
            check = ttk.Checkbutton(self._cond3_sub_frame, text=label, variable=var)
            check.pack(anchor=tk.W, pady=1, padx=(20, 0))  # 缩进20像素
            self._cond3_sub_checks.append(check)
        
        # 绑定子条件的变更事件
        for var in sub_vars:
            var.trace_add("write", lambda *args: self._update_cond3_state())
        
        # 绑定条件2的变更事件：当条件2被勾选时，条件3必须勾选且不可取消
        self._cond2_var.trace_add("write", lambda *args: self._on_cond2_toggle())
        
        # 初始化时检查条件2的状态
        if self._cond2_var.get():
            self._on_cond2_toggle()
        
        self._cond4_check = ttk.Checkbutton(cf, text="双攻被、双魔被", variable=self._cond4_var)
        self._cond4_check.pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(cf, text="双攻终、双魔终", variable=self._cond5_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(cf, text="终攻被、终魔被", variable=self._cond6_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(cf, text="三攻、三魔", variable=self._cond7_var).pack(anchor=tk.W, pady=2)
        ttk.Button(cf, text="确定", command=self._hide_conditions).pack(pady=(12, 0))

        # 日志区域（默认隐藏）
        self._log_frame = ttk.LabelFrame(main, text="运行日志", padding=4)
        # 不 pack，由 _toggle_log 控制

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

    def _show_conditions_inline(self):
        """在注意事项位置显示终止条件选择区域。"""
        if self._conditions_visible:
            return
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
        self._notice_frame.pack_forget()
        self._conditions_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        # 根据条件3是否展开来决定窗口高度
        if self._cond3_expanded:
            self.root.geometry(WIN_SIZE_WITH_CONDITIONS_EXPANDED)
        else:
            self.root.geometry(WIN_SIZE_WITH_CONDITIONS)
        self._conditions_visible = True

    def _hide_conditions(self):
        """收起终止条件区域，恢复显示注意事项。"""
        if not self._conditions_visible:
            return
        self._conditions_frame.pack_forget()
        self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.root.geometry(WIN_SIZE_NORMAL)
        self._conditions_visible = False
    
    def _toggle_cond3_expand(self):
        """展开/收起条件3的子条件"""
        if self._cond3_expanded:
            # 收起
            self._cond3_sub_frame.pack_forget()
            self._cond3_expand_btn.config(text="▼")
            self._cond3_expanded = False
            # 恢复窗口高度
            if self._conditions_visible:
                self.root.geometry(WIN_SIZE_WITH_CONDITIONS)
        else:
            # 展开：在条件3和条件4之间插入子条件
            # 使用pack的after参数，在条件3的frame之后插入
            cond3_frame = self._cond3_check.master
            self._cond3_sub_frame.pack(anchor=tk.W, pady=(0, 2), fill=tk.X, after=cond3_frame)
            self._cond3_expand_btn.config(text="▲")
            self._cond3_expanded = True
            # 增大窗口高度
            if self._conditions_visible:
                self.root.geometry(WIN_SIZE_WITH_CONDITIONS_EXPANDED)
    
    def _on_cond2_toggle(self):
        """当条件2被勾选/取消时的处理"""
        if self._cond2_var.get():
            # 条件2被勾选，条件3必须勾选且不可取消
            self._updating_cond3_state = True
            try:
                self._cond3_var.set(True)
                self._cond3_check.config(state=tk.DISABLED)
                # 确保所有子条件都勾选
                sub_vars = [self._cond3_1_var, self._cond3_2_var, self._cond3_3_var, self._cond3_4_var,
                            self._cond3_5_var, self._cond3_6_var, self._cond3_7_var, self._cond3_8_var, self._cond3_9_var,
                            self._cond3_10_var, self._cond3_11_var]
                for var in sub_vars:
                    var.set(True)
                # 禁用所有子条件的复选框
                for check in self._cond3_sub_checks:
                    check.config(state=tk.DISABLED)
                self._cond3_check.state(['!alternate'])  # 清除indeterminate状态
            finally:
                self._updating_cond3_state = False
        else:
            # 条件2被取消，条件3可以正常操作
            self._cond3_check.config(state=tk.NORMAL)
            # 启用所有子条件的复选框
            for check in self._cond3_sub_checks:
                check.config(state=tk.NORMAL)
            # 更新条件3的状态
            self._update_cond3_state()
    
    def _update_cond3_state(self):
        """根据子条件的状态更新条件3的状态"""
        if self._updating_cond3_state:
            return  # 防止递归调用
        
        # 如果条件2被勾选，条件3必须保持勾选状态
        if self._cond2_var.get():
            self._updating_cond3_state = True
            try:
                self._cond3_var.set(True)
                self._cond3_check.state(['!alternate'])  # 清除indeterminate状态
            finally:
                self._updating_cond3_state = False
            return
        
        self._updating_cond3_state = True
        try:
            sub_vars = [self._cond3_1_var, self._cond3_2_var, self._cond3_3_var, self._cond3_4_var,
                        self._cond3_5_var, self._cond3_6_var, self._cond3_7_var, self._cond3_8_var, self._cond3_9_var,
                        self._cond3_10_var, self._cond3_11_var]
            enabled_count = sum(1 for var in sub_vars if var.get())
            total_count = len(sub_vars)
            
            if enabled_count == 0:
                # 全部取消，条件3变为未勾选
                self._cond3_var.set(False)
                self._cond3_check.state(['!alternate'])  # 清除indeterminate状态
            elif enabled_count == total_count:
                # 全部勾选，条件3变为勾选
                self._cond3_var.set(True)
                self._cond3_check.state(['!alternate'])  # 清除indeterminate状态
            else:
                # 部分勾选，条件3变为indeterminate（方块）
                self._cond3_var.set(True)  # 需要先设为True才能设置indeterminate
                self._cond3_check.state(['alternate'])  # ttk的indeterminate状态
        finally:
            self._updating_cond3_state = False
    
    def _on_cond3_toggle(self):
        """当条件3被勾选/取消时的处理"""
        if self._updating_cond3_state:
            return  # 防止递归调用
        
        # 如果条件2被勾选，条件3不可操作
        if self._cond2_var.get():
            return
        
        self._updating_cond3_state = True
        try:
            sub_vars = [self._cond3_1_var, self._cond3_2_var, self._cond3_3_var, self._cond3_4_var,
                        self._cond3_5_var, self._cond3_6_var, self._cond3_7_var, self._cond3_8_var, self._cond3_9_var,
                        self._cond3_10_var, self._cond3_11_var]
            if self._cond3_var.get():
                # 如果条件3被勾选，且所有子条件都未勾选，则全部勾选
                if not any(var.get() for var in sub_vars):
                    # 全部未勾选，则全部勾选
                    for var in sub_vars:
                        var.set(True)
            else:
                # 如果条件3被取消，则取消所有子条件
                for var in sub_vars:
                    var.set(False)
        finally:
            self._updating_cond3_state = False

    def _toggle_log(self):
        if self._log_visible:
            self._log_frame.pack_forget()
            self._notice_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
            self.root.geometry(WIN_SIZE_NORMAL)
            self.btn_log.config(text="查看日志")
            self._log_visible = False
        else:
            self._notice_frame.pack_forget()
            self._conditions_frame.pack_forget()
            self._conditions_visible = False
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
        # 新一轮开始时清空日志
        self.root.after(0, self._log_clear)
        c3_sub_flags = (
            self._cond3_1_var.get(),
            self._cond3_2_var.get(),
            self._cond3_3_var.get(),
            self._cond3_4_var.get(),
            self._cond3_5_var.get(),
            self._cond3_6_var.get(),
            self._cond3_7_var.get(),
            self._cond3_8_var.get(),
            self._cond3_9_var.get(),
            self._cond3_10_var.get(),
            self._cond3_11_var.get(),
        )
        condition_flags = (
            self._cond2_var.get(),
            self._cond3_var.get(),
            self._cond4_var.get(),
            self._cond5_var.get(),
            self._cond6_var.get(),
            self._cond7_var.get(),
            c3_sub_flags,
        )
        self.worker_thread = threading.Thread(
            target=run_monster_loop,
            args=(self.stop_event, self._status_callback, self._log_callback, condition_flags),
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
    app = MonsterAbilityApp()
    app.run()
