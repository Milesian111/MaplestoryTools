"""
空格连点功能 - 按 F6 开启/关闭，间隔 0.2 秒
"""
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller, Key

# 间隔时间（秒）
INTERVAL = 0.2

# 控制状态
running = False
controller = Controller()


def press_space_loop():
    """循环按下空格键"""
    global running
    while running:
        controller.press(Key.space)
        controller.release(Key.space)
        time.sleep(INTERVAL)


def on_press(key):
    """监听按键"""
    global running
    try:
        if key == keyboard.Key.f6:
            running = not running
            if running:
                print("空格连点已开启 (F6 关闭)")
                t = threading.Thread(target=press_space_loop, daemon=True)
                t.start()
            else:
                print("空格连点已关闭")
    except AttributeError:
        pass


def main():
    print("空格连点 - 按 F6 开启/关闭，间隔 0.2 秒")
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
