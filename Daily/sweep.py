"""
Daily 扫荡：找图并点击 btn_down、btn_daily，然后循环找 btn_done 并点击、按回车。
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
    find_image_and_click,
    find_image_and_click_with_score,
    find_image_with_score,
)

from tenebris import run_tenebris_loop

BASE_DIR = Path(__file__).parent
SEARCH_REGION = (0, 0, 1920, 1080)


def _sleep_check_stop(stop_event, seconds):
    """分段 sleep，每 0.3 秒检查一次 stop_event，便于及时响应结束。"""
    if stop_event is None:
        time.sleep(seconds)
        return
    elapsed = 0.0
    while elapsed < seconds:
        if stop_event.is_set():
            return
        time.sleep(min(0.3, seconds - elapsed))
        elapsed += 0.3


def sweep(log_callback=None, stop_event=None, role_index=None, tenebris_enabled=False):
    """找图 picture/btn_down.png 并点击，再找 picture/btn_daily.png 并点击。
    log_callback(msg): 可选，GUI 传入则用其输出日志，否则用 print。
    stop_event: 可选，GUI 传入时在等待/循环中检查，置位则立即返回。
    role_index: 可选，当前角色序号；提供时在找到 btn_down 后打印「开始扫荡第X个角色。」。
    tenebris_enabled: 为 True 时，在判断切换角色成功（找到 btn_down）后先执行泰涅布利斯流程，再点击 btn_down 进入主流程。"""
    _log = log_callback if log_callback else lambda msg: print(msg, flush=True)
    region = SEARCH_REGION
    btn_down_path = BASE_DIR / "picture/btn_down.png"
    btn_menu_path = BASE_DIR / "picture/btn_menu.png"

    # 1. 每 3 秒找图 btn_menu（不点击），找到即表示切换角色成功；最多找 40 次
    last_score = None
    for attempt in range(1, 41):
        if stop_event is not None and stop_event.is_set():
            return
        found, max_val = find_image_with_score(region, btn_menu_path, threshold=0.95)
        if found:
            break
        last_score = max_val
        _sleep_check_stop(stop_event, 3)
    else:
        score_msg = f"，最高匹配阈值: {last_score:.3f}" if last_score is not None else ""
        _log("错误，切角色卡住了哥" + score_msg)
        return

    # 2. 若勾选泰涅布利斯，先执行泰涅布利斯扫荡流程（每个角色一次）
    if tenebris_enabled:
        run_tenebris_loop(stop_event, log_callback=_log)
        if stop_event is not None and stop_event.is_set():
            return

    # 3. 找图 btn_down 并点击，进入扫荡主流程；最多找 40 次
    last_score = None
    for attempt in range(1, 41):
        if stop_event is not None and stop_event.is_set():
            return
        found, max_val = find_image_and_click_with_score(region, btn_down_path, threshold=0.95)
        if found:
            _sleep_check_stop(stop_event, 0.5)
            if role_index is not None:
                _log(f"开始扫荡第{role_index}个角色。")
            break
        last_score = max_val
        _sleep_check_stop(stop_event, 3)
    else:
        score_msg = f"，最高匹配阈值: {last_score:.3f}" if last_score is not None else ""
        _log("错误，切角色卡住了哥" + score_msg)
        return

    if stop_event is not None and stop_event.is_set():
        return
    # 2. 找图 btn_daily 并点击（阈值 0.95）
    if find_image_and_click(region, BASE_DIR / "picture/btn_daily.png", threshold=0.95):
        _sleep_check_stop(stop_event, 0.5)

    loop_done(stop_event=stop_event)
    if stop_event is not None and stop_event.is_set():
        return

    # 3. 找图 grandis 并点击，再执行一轮 loop_done
    if find_image_and_click(region, BASE_DIR / "picture/grandis.png"):
        _sleep_check_stop(stop_event, 0.5)
    loop_done(stop_event=stop_event)
    if stop_event is not None and stop_event.is_set():
        return

    # 4. 找图 btn_menu 并点击
    found_menu, menu_score = find_image_and_click_with_score(region, BASE_DIR / "picture/btn_menu.png")
    if found_menu:
        _sleep_check_stop(stop_event, 0.5)
    else:
        score_msg = f"，最高匹配阈值: {menu_score:.3f}" if menu_score is not None else ""
        _log('错误：未找到"选单"键，请确认是否遮挡，或存在背景干扰！' + score_msg)
    if stop_event is not None and stop_event.is_set():
        return
    # 5. 找图 change_char 并点击
    if find_image_and_click(region, BASE_DIR / "picture/change_char.png"):
        _sleep_check_stop(stop_event, 0.5)
    if stop_event is not None and stop_event.is_set():
        return
    # 6. 按右键 →，再按回车
    pyautogui.press("right")
    _sleep_check_stop(stop_event, 0.1)
    pyautogui.press("enter")
    _sleep_check_stop(stop_event, 0.1)
    pyautogui.press("enter")
    _sleep_check_stop(stop_event, 3)


def loop_done(stop_event=None):
    """循环找 btn_done 或 btn_free 并点击，找到则按 5 次回车；都找不到则退出。stop_event 置位时立即退出。"""
    region = SEARCH_REGION
    while True:
        if stop_event is not None and stop_event.is_set():
            break
        # 找到并点击 btn_done 或 btn_free 任一即可继续
        clicked = find_image_and_click(region, BASE_DIR / "picture/btn_done.png") or find_image_and_click(region, BASE_DIR / "picture/btn_free.png")
        if not clicked:
            break
        _sleep_check_stop(stop_event, 0.1)
        for _ in range(5):
            if stop_event is not None and stop_event.is_set():
                break
            pyautogui.press("enter")
            _sleep_check_stop(stop_event, 0.1)
        _sleep_check_stop(stop_event, 0.1)


def run_main(total_roles=53):
    """主入口：total_roles 轮扫荡循环。供直接运行或 exe 入口调用。"""
    for x in range(1, total_roles + 1):
        sweep(role_index=x)


def run_sweep_loop(stop_event, status_callback, log_callback=None, total_roles=53, tenebris_enabled=False):
    """供 GUI 在后台线程调用：可中断的扫荡循环。
    stop_event.is_set() 时退出；log_callback 用于输出日志。
    tenebris_enabled 为 True 时，每个角色在进入主扫荡前先执行一次泰涅布利斯流程。"""
    if log_callback is None:
        log_callback = lambda msg: None
    try:
        for x in range(1, total_roles + 1):
            if stop_event.is_set():
                log_callback("已手动停止")
                status_callback("已手动停止")
                return
            sweep(log_callback=log_callback, stop_event=stop_event, role_index=x, tenebris_enabled=tenebris_enabled)
        log_callback("全部角色扫荡完成。")
        status_callback("全部角色扫荡完成。")
    except Exception as e:
        log_callback(f"运行出错: {e}")
        status_callback(f"运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_main()
