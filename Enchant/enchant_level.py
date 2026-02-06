import pyautogui
import cv2
import numpy as np
import winsound
import time
from pathlib import Path

# 尝试导入 keyboard 库用于发送按键（更可靠）
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

# 获取当前脚本所在目录
BASE_DIR = Path(__file__).parent

# 查找范围 (x1, y1, x2, y2)
SEARCH_REGION = (0, 0, 1366, 768)

# 图片文件
IMAGE_FILE = 'picture/level4.png'

# 匹配阈值（0-1之间，越高越严格，建议0.95以上）
MATCH_THRESHOLD = 0.99


def find_image_in_region(log_callback=None):
    """在指定区域内查找图片，使用OpenCV进行精确匹配
    返回是否找到图片"""
    if log_callback is None:
        log_callback = lambda msg: print(msg)
    
    # 计算区域参数 (left, top, width, height)
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    img_path = BASE_DIR / IMAGE_FILE
    
    if not img_path.exists():
        return False
    
    try:
        # 截取屏幕指定区域
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        # 转换为numpy数组并转为灰度图
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        
        # 读取模板图片
        template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            return False
        
        # 检查模板是否大于搜索区域
        if template.shape[0] > height or template.shape[1] > width:
            return False
        
        # 使用模板匹配
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 检查是否超过阈值
        if max_val >= MATCH_THRESHOLD:
            return True
        else:
            return False
            
    except Exception as e:
        return False


def find_image_and_click(image_file, threshold=0.99, log_callback=None):
    """在指定区域内查找图片并点击
    返回是否找到并点击成功"""
    if log_callback is None:
        log_callback = lambda msg: print(msg)
    
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    img_path = BASE_DIR / image_file
    
    if not img_path.exists():
        log_callback(f"警告: 图片文件不存在 - {img_path}")
        return False
    
    log_callback(f"正在查找: {image_file}")
    
    try:
        # 截取屏幕指定区域
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        # 转换为numpy数组并转为灰度图
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        
        # 读取模板图片
        template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            log_callback(f"✗ 无法读取图片: {image_file}")
            return False
        
        # 检查模板是否大于搜索区域
        if template.shape[0] > height or template.shape[1] > width:
            log_callback(f"✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
            return False
        
        # 使用模板匹配
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        log_callback(f"  匹配分数: {max_val:.4f} (阈值: {threshold})")
        
        # 检查是否超过阈值
        if max_val >= threshold:
            # 计算实际屏幕坐标（图片中心点）
            center_x = left + max_loc[0] + template.shape[1] // 2
            center_y = top + max_loc[1] + template.shape[0] // 2
            log_callback(f"✓ 找到图片: {image_file}")
            log_callback(f"  位置: ({center_x}, {center_y})")
            log_callback(f"  匹配分数: {max_val:.4f}")
            # 点击图片中心
            pyautogui.click(center_x, center_y)
            log_callback(f"  已点击: ({center_x}, {center_y})")
            # 点击后鼠标右移100像素
            pyautogui.moveRel(100, 0)
            return True
        else:
            log_callback(f"✗ 未找到: {image_file} (匹配分数 {max_val:.4f} < 阈值 {threshold})")
            return False
            
    except Exception as e:
        log_callback(f"✗ 查找 {image_file} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def perform_click_sequence(log_callback=None):
    """执行点击序列"""
    # 1. 按第一次空格
    if HAS_KEYBOARD:
        keyboard.press_and_release('space')
    else:
        pyautogui.press('space')
    time.sleep(0.1)
    
    # 2. 0.1秒后按第二次空格
    if HAS_KEYBOARD:
        keyboard.press_and_release('space')
    else:
        pyautogui.press('space')
    time.sleep(1.5)  # 等待1.5秒后再次查找图片


def run_enchant_level_loop(stop_event, status_callback, log_callback=None):
    """在后台线程中执行上绿的主循环，遇 stop_event 或找到目标图片时退出"""
    if log_callback is None:
        log_callback = lambda msg: None
    
    count = 0
    
    try:
        while not stop_event.is_set():
            # 查找图片
            found = find_image_in_region(log_callback=log_callback)
            
            if found:
                winsound.Beep(1000, 300)  # 频率1000Hz，持续时间300ms
                status_callback("已找到目标图片，任务完成")
                break
            else:
                count += 1
                log_callback(f"第{count}次")
                # 执行点击序列
                perform_click_sequence(log_callback=log_callback)
                
                # 检查是否被停止
                if stop_event.is_set():
                    status_callback("任务已停止")
                    break
    except Exception as e:
        error_msg = f"运行出错: {e}"
        log_callback(error_msg)
        status_callback(error_msg)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import threading
    stop_event = threading.Event()
    status_callback = lambda msg: print(f"[状态] {msg}")
    log_callback = lambda msg: print(msg)
    run_enchant_level_loop(stop_event, status_callback, log_callback)

