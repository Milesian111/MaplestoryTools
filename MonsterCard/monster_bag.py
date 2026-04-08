import pyautogui
import cv2
import numpy as np
import winsound
import time
import threading
from pathlib import Path
from typing import Callable, Literal, Optional

from monster_ability import check_image_exists

BagStepResult = Literal["continue", "bag_full", "no_more"]

# 找图顺序与 IMAGE_FILES 一致，用于开包模式简短日志
_MATCH_KEY_BY_FILE: dict[str, str] = {
    "picture/lcd.png": "lcd",
    "picture/kl.png": "kl",
    "picture/sl.png": "sl",
    "picture/ark.png": "ark",
    "picture/bag_full.png": "bag_full",
}

_AOTIAN_LOG: dict[str, str] = {
    "kl": "卡琳傲天",
    "lcd": "路西德傲天",
    "sl": "赛轮傲天",
    "ark": "奥尔卡傲天",
}

# 获取当前脚本所在目录
BASE_DIR = Path(__file__).parent


def _default_bag_log(msg: str = "") -> None:
    print(msg)


_bag_log: Callable[[str], None] = _default_bag_log


def set_bag_log(fn: Optional[Callable[[str], None]]) -> None:
    global _bag_log
    _bag_log = fn if fn is not None else _default_bag_log

# 查找范围 (x1, y1, x2, y2)
SEARCH_REGION = (480, 267, 885, 567)

# 图片文件列表
IMAGE_FILES = [
    'picture/lcd.png',
    'picture/kl.png',
    'picture/sl.png',
    'picture/ark.png',
    'picture/bag_full.png'
]

# 匹配阈值（0-1之间，越高越严格，建议0.95以上）
MATCH_THRESHOLD = 0.95


def find_and_click_in_region(relative_path: str) -> bool:
    """在 SEARCH_REGION 内找图并点击模板中心。未找到返回 False。"""
    rel = relative_path.replace("\\", "/")
    img_path = BASE_DIR / rel
    x1, y1, x2, y2 = SEARCH_REGION
    left, top = x1, y1
    width, height = x2 - x1, y2 - y1

    if not img_path.is_file():
        return False
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            return False
        if template.shape[0] > height or template.shape[1] > width:
            return False
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val < MATCH_THRESHOLD:
            return False
        tw, th = template.shape[1], template.shape[0]
        cx = left + max_loc[0] + tw // 2
        cy = top + max_loc[1] + th // 2
        pyautogui.click(cx, cy)
        return True
    except Exception:
        return False


def find_first_match_key() -> Optional[str]:
    """在 SEARCH_REGION 内按 IMAGE_FILES 顺序找第一张匹配的图，不输出日志。
    返回 'lcd'|'kl'|'sl'|'ark'|'bag_full' 或 None。"""
    x1, y1, x2, y2 = SEARCH_REGION
    left, top = x1, y1
    width, height = x2 - x1, y2 - y1
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    except Exception:
        return None

    for img_file in IMAGE_FILES:
        img_path = BASE_DIR / img_file
        if not img_path.exists():
            continue
        try:
            template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if template is None:
                continue
            if template.shape[0] > height or template.shape[1] > width:
                continue
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _min_val, max_val, _min_loc, _max_loc = cv2.minMaxLoc(result)
            if max_val >= MATCH_THRESHOLD:
                return _MATCH_KEY_BY_FILE.get(img_file)
        except Exception:
            continue
    return None


def find_image_in_region():
    """在指定区域内查找图片，使用OpenCV进行精确匹配
    返回是否找到图片"""
    # 计算区域参数 (left, top, width, height)
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    _bag_log(f"搜索区域: ({left}, {top}, {width}, {height})")
    
    # 截取屏幕指定区域（只需要截取一次）
    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    screen_array = np.array(screenshot)
    screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    
    # 遍历所有图片文件
    for img_file in IMAGE_FILES:
        img_path = BASE_DIR / img_file
        
        if not img_path.exists():
            _bag_log(f"警告: 图片文件不存在 - {img_path}")
            continue
        
        _bag_log(f"正在查找: {img_file}")
        
        try:
            # 读取模板图片
            template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if template is None:
                _bag_log(f"✗ 无法读取图片: {img_file}")
                continue
            
            # 检查模板是否大于搜索区域
            if template.shape[0] > height or template.shape[1] > width:
                _bag_log(f"✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
                continue
            
            # 使用模板匹配
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            _bag_log(f"  匹配分数: {max_val:.4f} (阈值: {MATCH_THRESHOLD})")
            
            # 检查是否超过阈值
            if max_val >= MATCH_THRESHOLD:
                # 计算实际屏幕坐标
                actual_x = left + max_loc[0]
                actual_y = top + max_loc[1]
                _bag_log(f"✓ 找到图片: {img_file}")
                _bag_log(f"  位置: ({actual_x}, {actual_y})")
                _bag_log(f"  匹配分数: {max_val:.4f}")
                return True
            else:
                _bag_log(f"✗ 未找到: {img_file} (匹配分数 {max_val:.4f} < 阈值 {MATCH_THRESHOLD})")
                
        except Exception as e:
            _bag_log(f"✗ 查找 {img_file} 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return False


def perform_click_sequence() -> BagStepResult:
    """执行完整点击序列（未找到傲天时使用）。"""
    _bag_log("\n执行点击序列...")
    # 1. refine.png -> 2. yes2.png -> 3. perform_use_sequence（内含 no_more / use_ten / bag_full / yes）
    _bag_log("找图 refine.png")
    if not find_and_click_in_region("picture/refine.png"):
        return "continue"
    time.sleep(0.2)
    _bag_log("找图 yes2.png")
    if not find_and_click_in_region("picture/yes2.png"):
        return "continue"
    time.sleep(1.5)
    return perform_use_sequence()


def find_bag_full():
    """查找bag_full.png图片"""
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    img_path = BASE_DIR / 'picture/bag_full.png'
    
    if not img_path.exists():
        _bag_log(f"警告: 图片文件不存在 - {img_path}")
        return False
    
    _bag_log(f"正在查找: picture/bag_full.png")
    
    try:
        # 截取屏幕指定区域
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        
        # 读取模板图片
        template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            _bag_log(f"✗ 无法读取图片: picture/bag_full.png")
            return False
        
        # 检查模板是否大于搜索区域
        if template.shape[0] > height or template.shape[1] > width:
            _bag_log(f"✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
            return False
        
        # 使用模板匹配
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        _bag_log(f"  匹配分数: {max_val:.4f} (阈值: {MATCH_THRESHOLD})")
        
        # 检查是否超过阈值
        if max_val >= MATCH_THRESHOLD:
            actual_x = left + max_loc[0]
            actual_y = top + max_loc[1]
            _bag_log(f"✓ 找到图片: picture/bag_full.png")
            _bag_log(f"  位置: ({actual_x}, {actual_y})")
            _bag_log(f"  匹配分数: {max_val:.4f}")
            return True
        else:
            _bag_log(f"✗ 未找到: picture/bag_full.png (匹配分数 {max_val:.4f} < 阈值 {MATCH_THRESHOLD})")
            return False
            
    except Exception as e:
        _bag_log(f"✗ 查找 picture/bag_full.png 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def perform_use_sequence() -> BagStepResult:
    """执行使用序列（找到傲天时或点击序列末尾）。每次执行前检测 no_more。"""
    _bag_log("\n执行使用序列...")
    if check_image_exists("picture/no_more.png"):
        return "no_more"
    _bag_log("找图 use_ten.png")
    if not find_and_click_in_region("picture/use_ten.png"):
        return "continue"
    time.sleep(0.1)
    if find_bag_full():
        _bag_log(f"\n✓ 找到bag_full.png，发出长beep声并结束任务")
        winsound.Beep(1000, 1000)
        return "bag_full"
    _bag_log("找图 yes.png")
    if not find_and_click_in_region("picture/yes.png"):
        return "continue"
    time.sleep(0.2)
    return "continue"


def run_bag_loop(stop_event: threading.Event, status_callback, log_callback=None) -> None:
    """供 GUI 调用：与脚本主循环相同逻辑，可通过 stop_event 结束。"""
    if log_callback is None:
        log_callback = lambda _m: None

    # 开包模式：不输出找图细节，仅输出「第n次」摘要
    set_bag_log(lambda _m: None)
    try:
        if check_image_exists("picture/cg_on.png", log_callback=log_callback):
            log_callback("错误：请关闭特效按钮！")
            status_callback("错误：请关闭特效按钮！")
            return
        if not check_image_exists("picture/card_bag.png", log_callback=log_callback):
            log_callback("错误：请打开卡包！")
            status_callback("错误：请打开卡包！")
            return
        count = 0
        while not stop_event.is_set():
            count += 1
            key = find_first_match_key()
            if stop_event.is_set():
                break
            if key is None:
                log_callback(f"第{count}次，没有找到傲天")
                r = perform_click_sequence()
                if r == "no_more":
                    log_callback("卡包用完了！")
                    status_callback("卡包用完了！")
                    return
                if r == "bag_full":
                    log_callback("开包结束（背包已满）")
                    status_callback("开包结束（背包已满）")
                    return
                if stop_event.is_set():
                    break
                continue
            if key in _AOTIAN_LOG:
                log_callback(f"第{count}次，找到{_AOTIAN_LOG[key]}！")
                winsound.Beep(1000, 200)
                r = perform_use_sequence()
                if r == "no_more":
                    log_callback("卡包用完了！")
                    status_callback("卡包用完了！")
                    return
                if r == "bag_full":
                    log_callback("开包结束（背包已满）")
                    status_callback("开包结束（背包已满）")
                    return
                if stop_event.is_set():
                    break
                continue
            # bag_full 等（优先匹配到背包满图时）
            winsound.Beep(1000, 200)
            r = perform_use_sequence()
            if r == "no_more":
                log_callback("卡包用完了！")
                status_callback("卡包用完了！")
                return
            if r == "bag_full":
                log_callback("开包结束（背包已满）")
                status_callback("开包结束（背包已满）")
                return
            if stop_event.is_set():
                break
        if stop_event.is_set():
            status_callback("已手动停止")
        else:
            status_callback("就绪（F11 开始 / F12 结束）")
    except Exception as e:
        status_callback(f"运行出错: {e}")
        log_callback(str(e))
    finally:
        set_bag_log(None)


if __name__ == "__main__":
    _evt = threading.Event()
    run_bag_loop(_evt, lambda msg: print(msg), print)

