"""
按键序列任务：与按键精灵脚本等效。
放球键 -> 500ms -> 按住 Right 2s -> 500ms -> 放球键 -> 1s -> 切球键 -> 2720ms -> Right 一次
使用 keyboard 库发送按键；放球/切球键可通过参数指定（默认 ctrl / shift）。
依赖：pip install keyboard
"""
import time
import keyboard

# 执行前给几秒切换到目标窗口（直接运行脚本时用）
START_DELAY = 3


def run_sequence(ctrl_key="ctrl", shift_key="shift", interval_ms=3500):
    """
    执行卡球按键序列。ctrl_key 为放球键（两处），shift_key 为切球键（一处）。
    interval_ms：间隔时间（毫秒），默认 3500；切球键按下后的 sleep = (interval_ms - 1000) / 1000 秒。
    键名使用 keyboard 库格式，如 "ctrl", "shift", "alt"。
    """
    keyboard.press_and_release(ctrl_key)
    time.sleep(0.5)

    keyboard.press("right")
    time.sleep(2.0)
    keyboard.release("right")
    time.sleep(0.5)

    keyboard.press_and_release(ctrl_key)
    time.sleep(1.0)

    keyboard.press_and_release(shift_key)
    # 间隔时间(ms)减去 1000，剩余转为秒；time.sleep 支持浮点，如 3654ms -> 2.654s
    sleep_after_shift = max(0.0, (interval_ms - 1000) / 1000.0)
    time.sleep(sleep_after_shift)

    keyboard.press_and_release("right")


if __name__ == "__main__":
    print(f"{START_DELAY} 秒后开始执行按键序列，请切换到目标窗口…")
    time.sleep(START_DELAY)
    run_sequence()
    print("执行完毕。")
