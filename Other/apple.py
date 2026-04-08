"""
按住 Enter 不放，鼠标在当前位置连点。
F12 开启/关闭。

Windows 上使用 keybd_event / mouse_event（比手写 SendInput 结构更不易写错）。
此前 SendInput 若把 KEYBDINPUT.dwExtraInfo 写成“指针”会在 64 位系统上布局错误，导致任何窗口都收不到键。

依赖: pip install keyboard
（非 Windows 时需: pip install pynput）
"""
from __future__ import annotations

import ctypes
import sys
import threading
import time

import keyboard

# 鼠标连点间隔（秒）
CLICK_INTERVAL = 0.05

# ---------- Windows：keybd_event + mouse_event ----------
if sys.platform == "win32":
    VK_RETURN = 0x0D
    KEYEVENTF_KEYUP = 0x0002
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004

    _user32 = ctypes.windll.user32
    _keybd_event = _user32.keybd_event
    _keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint, ctypes.c_size_t]
    _keybd_event.restype = None
    _mouse_event = _user32.mouse_event
    _mouse_event.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t]
    _mouse_event.restype = None

    def enter_key_down() -> None:
        _keybd_event(VK_RETURN, 0, 0, 0)

    def enter_key_up() -> None:
        _keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)

    def mouse_left_click() -> None:
        _mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        _mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

else:
    from pynput.keyboard import Key, Controller as KeyController
    from pynput.mouse import Button, Controller as MouseController

    _key = KeyController()
    _mouse = MouseController()

    def enter_key_down() -> None:
        _key.press(Key.enter)

    def enter_key_up() -> None:
        _key.release(Key.enter)

    def mouse_left_click() -> None:
        _mouse.click(Button.left, 1)


running = False
state_lock = threading.Lock()
stop_event = threading.Event()


def toggle() -> None:
    global running
    with state_lock:
        running = not running
    print("开启" if running else "关闭")


def worker() -> None:
    while not stop_event.is_set():
        if not running:
            time.sleep(0.02)
            continue
        enter_key_down()
        try:
            while running and not stop_event.is_set():
                mouse_left_click()
                time.sleep(CLICK_INTERVAL)
        finally:
            try:
                enter_key_up()
            except Exception:
                pass


def main() -> None:
    if sys.platform == "win32":
        print("输入方式: keybd_event(Enter) + mouse_event(左键)")
    else:
        print("输入方式: pynput（非 Windows）")
    print("F12：开启/关闭（按住 Enter + 鼠标连点）")
    print("Ctrl+C：退出")
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    try:
        keyboard.add_hotkey("f12", toggle, suppress=False)
    except Exception as e:
        print(f"注册 F12 失败：{e}")
        sys.exit(1)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_event.set()
        with state_lock:
            running = False
        try:
            enter_key_up()
        except Exception:
            pass
        print("已退出")


if __name__ == "__main__":
    main()
