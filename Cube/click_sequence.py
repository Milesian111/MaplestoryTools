"""
Cube 任务公用：执行点击序列（改为按空格键，不依赖坐标）、激活窗口（找 flag 并点击）。
各任务脚本通过 from click_sequence import perform_click_sequence, activate_window 使用。
"""
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui
import keyboard

# 激活窗口用图
FLAG_IMAGE = "picture/flag.png"
MATCH_THRESHOLD = 0.99


def activate_window(base_dir, search_region, image_path=None):
    """在 search_region 内查找 flag 图并点击，用于激活窗口。返回是否找到并点击。"""
    image_path = image_path or FLAG_IMAGE
    img_path = Path(base_dir) / image_path
    if not img_path.exists():
        print(f"警告: 激活窗口用图不存在 - {img_path}")
        return False
    x1, y1, x2, y2 = search_region
    left, top = x1, y1
    width, height = x2 - x1, y2 - y1
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if template is None or template.shape[0] > height or template.shape[1] > width:
            return False
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < MATCH_THRESHOLD:
            return False
        click_x = left + max_loc[0] + template.shape[1] // 2
        click_y = top + max_loc[1] + template.shape[0] // 2
        print(f"激活窗口: 找到 {image_path}，点击 ({click_x}, {click_y})")
        pyautogui.click(click_x, click_y)
        time.sleep(0.3)
        return True
    except Exception as e:
        print(f"激活窗口时出错: {e}")
        return False


def perform_click_sequence():
    """执行按键序列：按空格 3 次，间隔 0.1s、0.1s，最后等待 1.0s 后再次找图。"""
    _press_space()
    time.sleep(0.1)
    _press_space()
    time.sleep(0.1)
    _press_space()
    time.sleep(1.0)


def _press_space():
    """按一次空格（优先 keyboard，否则 pyautogui）。"""
    try:
        keyboard.press_and_release('space')
    except Exception:
        pyautogui.press('space')