"""
鼠标连点器 - 按热键开启/关闭自动点击
依赖: pip install pynput
"""
import time
import threading
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Listener as KeyListener, Key

# ========== 可调参数 ==========
CLICKS_PER_SECOND = 10   # 每秒点击次数
USE_RIGHT_BUTTON = False # True=右键连点, False=左键连点
TOGGLE_HOTKEY = Key.f11   # 按 F6 开启/关闭连点
STOP_HOTKEY = Key.f12     # 按 F7 强制停止（可选）
# ==============================

mouse = MouseController()
running = False
click_thread = None


def click_loop():
    """在后台线程中持续点击"""
    interval = 1.0 / CLICKS_PER_SECOND
    button = Button.right if USE_RIGHT_BUTTON else Button.left
    while running:
        mouse.click(button, 1)
        time.sleep(interval)


def on_press(key):
    global running, click_thread
    try:
        if key == TOGGLE_HOTKEY:
            running = not running
            if running:
                click_thread = threading.Thread(target=click_loop, daemon=True)
                click_thread.start()
                print("[连点器] 已开启")
            else:
                print("[连点器] 已关闭")
        elif key == STOP_HOTKEY:
            if running:
                running = False
                print("[连点器] 已强制停止")
    except Exception as e:
        print(f"错误: {e}")


def main():
    btn = "右键" if USE_RIGHT_BUTTON else "左键"
    print("=" * 40)
    print("  鼠标连点器")
    print("=" * 40)
    print(f"  点击方式: {btn}")
    print(f"  点击频率: {CLICKS_PER_SECOND} 次/秒")
    print(f"  按 F6: 开启/关闭连点")
    print(f"  按 F7: 强制停止")
    print("=" * 40)
    print("  程序运行中，按 F6 开始连点...")
    with KeyListener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
