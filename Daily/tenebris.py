"""
泰涅布利斯：run_tenebris_loop 时先执行一次 btn_menu、vip 点击，再找 tenebris.png，
找到后执行三次「按 OFFSET 点击+4 次回车」的流程，然后结束泰涅布利斯扫荡。
"""
import sys
import time
from pathlib import Path

import pyautogui

# 直接运行本脚本时，将项目根目录加入 path，以便导入 Utils（打包为 exe 时由入口脚本设置 path）
if not getattr(sys, "frozen", False):
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from Utils.find_image import (
    find_image,
    find_image_and_click_with_score,
    get_image_topleft_with_score,
)

BASE_DIR = Path(__file__).parent
SEARCH_REGION = (0, 0, 1920, 1080)
DELAY = 0.3
OFFSET = (346, 14)
ENTER_DELAY = 0.2


def _sleep_check_stop(stop_event, seconds):
    if stop_event is None:
        time.sleep(seconds)
        return
    elapsed = 0.0
    while elapsed < seconds:
        if stop_event.is_set():
            return
        time.sleep(min(0.3, seconds - elapsed))
        elapsed += 0.3


def run_tenebris_once(log_callback=None, stop_event=None):
    """执行一轮：仅找 tenebris 并点击+4 次回车。若找到并点击返回 True，否则返回 False。"""
    _log = log_callback if log_callback else lambda msg: print(msg, flush=True)
    if stop_event is not None and stop_event.is_set():
        return False

    topleft, max_val = get_image_topleft_with_score(SEARCH_REGION, BASE_DIR / "picture" / "tenebris.png")
    if topleft is None:
        _log("未找到 tenebris.png" + (f"，最高匹配阈值: {max_val:.3f}" if max_val is not None else ""))
        return False
    x, y = topleft[0] + OFFSET[0], topleft[1] + OFFSET[1]
    pyautogui.moveTo(x, y)
    pyautogui.click(x, y)
    _log(f"已点击 左上角+{OFFSET}: ({x}, {y})")
    for _ in range(4):
        if stop_event is not None and stop_event.is_set():
            return True
        pyautogui.press("enter")
        _sleep_check_stop(stop_event, ENTER_DELAY)
    _log("已连按 4 下回车")
    return True


def _do_menu_and_vip(log_callback, stop_event):
    """找 btn_menu、vip 并各点击一次（仅执行一次，在循环外调用）。"""
    if log_callback is None:
        log_callback = lambda msg: None
    found_menu, menu_val = find_image_and_click_with_score(SEARCH_REGION, BASE_DIR / "picture" / "btn_menu.png", threshold=0.95)
    if found_menu:
        log_callback("已点击 btn_menu")
    else:
        score_msg = f"，最高匹配阈值: {menu_val:.3f}" if menu_val is not None else ""
        log_callback('错误：未找到"选单"键，请确认是否遮挡，或存在背景干扰！' + score_msg)
    _sleep_check_stop(stop_event, DELAY)
    if stop_event is not None and stop_event.is_set():
        return
    found_vip, vip_val = find_image_and_click_with_score(SEARCH_REGION, BASE_DIR / "picture" / "vip.png", threshold=0.95)
    if found_vip:
        log_callback("已点击 vip")
    else:
        score_msg = f"，最高匹配阈值: {vip_val:.3f}" if vip_val is not None else ""
        log_callback("未找到 vip.png" + score_msg)
    _sleep_check_stop(stop_event, DELAY)


def run_tenebris_loop(stop_event, log_callback=None):
    """先执行一次 btn_menu、vip 点击，再找 tenebris.png；找到后执行三次「按 OFFSET 点击+4 次回车」，然后结束。"""
    if log_callback is None:
        log_callback = lambda msg: None
    log_callback("开始泰涅布利斯扫荡。")
    _do_menu_and_vip(log_callback, stop_event)
    if stop_event is not None and stop_event.is_set():
        log_callback("泰涅布利斯流程结束。")
        return
    topleft, tenebris_val = get_image_topleft_with_score(SEARCH_REGION, BASE_DIR / "picture" / "tenebris.png")
    if topleft is None:
        score_msg = f"，最高匹配阈值: {tenebris_val:.3f}" if tenebris_val is not None else ""
        log_callback("未找到 tenebris.png，泰涅布利斯扫荡结束。" + score_msg)
        log_callback("泰涅布利斯流程结束。")
        return
    x, y = topleft[0] + OFFSET[0], topleft[1] + OFFSET[1]
    for i in range(3):
        if stop_event is not None and stop_event.is_set():
            break
        pyautogui.moveTo(x, y)
        pyautogui.click(x, y)
        log_callback(f"第{i+1}次 已点击 泰涅布利斯。")
        _sleep_check_stop(stop_event, 0.5)
        for _ in range(4):
            if stop_event is not None and stop_event.is_set():
                break
            pyautogui.press("enter")
            _sleep_check_stop(stop_event, ENTER_DELAY)
        _sleep_check_stop(stop_event, 0.2)
    # 流程结束后若出现 bug 弹窗则按 esc 关闭，再继续任务
    if find_image(SEARCH_REGION, BASE_DIR / "picture" / "bug_flag.png"):
        pyautogui.press("esc")
    log_callback("泰涅布利斯流程结束。")


if __name__ == "__main__":
    _log = lambda msg: print(msg, flush=True)
    _do_menu_and_vip(_log, None)
    run_tenebris_once(log_callback=_log, stop_event=None)
