"""
找图 picture/again.png 并点击 → 0.1秒后按回车 → 0.5秒后开始循环
依赖: pip install pynput pyautogui opencv-python
"""
import sys
import time
from pathlib import Path

# 直接运行本脚本时，将项目根目录加入 path，以便导入 Utils
if not getattr(sys, "frozen", False):
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import pyautogui
from pynput.keyboard import Key, Controller as KeyController

from Utils.find_image import find_image_and_click

# ========== 可调参数 ==========
BASE_DIR = Path(__file__).parent
AGAIN_IMAGE = BASE_DIR / "picture" / "again.png"
SEARCH_REGION = (0, 0, *pyautogui.size())  # 全屏找图，也可改为 (x1, y1, x2, y2)
MATCH_THRESHOLD = 0.99
DELAY_AFTER_CLICK = 0.1   # 点击后等待 0.1 秒再按回车
MOUSE_MOVE_DOWN = 50      # 按回车后鼠标下移像素，防止遮挡
DELAY_BEFORE_LOOP = 0.5   # 程序启动后 0.5 秒开始循环
LOOP_INTERVAL = 1.0       # 每轮循环间隔（秒），可按需修改
# =============================

keyboard = KeyController()


def one_round():
    """执行一轮：找图 again.png 并点击 → 等 0.1 秒 → 按回车"""
    if not find_image_and_click(SEARCH_REGION, AGAIN_IMAGE, threshold=MATCH_THRESHOLD):
        return False
    time.sleep(DELAY_AFTER_CLICK)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    pyautogui.moveRel(0, MOUSE_MOVE_DOWN)  # 下移防止遮挡
    return True


def main():
    print("=" * 40)
    print("  找图 again.png 并点击 → 0.1秒 → 回车 → 循环")
    print("=" * 40)
    print(f"  搜索区域: {SEARCH_REGION}")
    print(f"  {DELAY_BEFORE_LOOP} 秒后开始循环，按 Ctrl+C 停止")
    print("=" * 40)

    time.sleep(DELAY_BEFORE_LOOP)

    round_count = 0
    try:
        while True:
            round_count += 1
            ok = one_round()
            if ok:
                print(f"  第 {round_count} 轮完成")
            else:
                print(f"  第 {round_count} 轮: 未找到 {AGAIN_IMAGE.name}")
            time.sleep(LOOP_INTERVAL)
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
