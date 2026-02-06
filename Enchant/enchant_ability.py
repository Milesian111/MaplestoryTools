import pyautogui
import cv2
import numpy as np
import winsound
import time
from pathlib import Path
import sys
import os
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 尝试导入 keyboard 库用于发送按键（更可靠）
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容PyInstaller打包后的exe"""
    try:
        # PyInstaller打包后会设置_MEIPASS属性
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境，使用脚本所在目录
        base_path = os.path.abspath(os.path.dirname(__file__))
    # 将相对路径中的正斜杠转换为系统路径分隔符
    relative_path = relative_path.replace('/', os.sep).replace('\\', os.sep)
    full_path = os.path.join(base_path, relative_path)
    # 规范化路径（处理 .. 和 . 等）
    full_path = os.path.normpath(full_path)
    return full_path

# 获取当前脚本所在目录（兼容打包）
try:
    # PyInstaller打包后
    BASE_DIR = Path(sys._MEIPASS)
except Exception:
    # 开发环境
    BASE_DIR = Path(__file__).parent

# 查找范围 (x1, y1, x2, y2)
SEARCH_REGION = (0, 0, 1366, 768)

# 图片文件列表
IMAGE_FILES = [
    'picture/all_enchant.png',
    'picture/atk_enchant.png',
    'picture/magic_enchant.png',
    'picture/str_enchant.png',
    'picture/dex_enchant.png',
    'picture/int_enchant.png',
    'picture/luk_enchant.png',
    'picture/hp_enchant.png',
]

# 匹配阈值（0-1之间，越高越严格，建议0.95以上）
MATCH_THRESHOLD = 0.95

# 最小匹配距离（像素），用于过滤重复匹配
MIN_MATCH_DISTANCE = 10

# 按钮查找区域，与 SEARCH_REGION 一致（全屏找图）
BTN_RESET_REGION = SEARCH_REGION
BTN_CONFIRM_REGION = SEARCH_REGION

def find_image_and_click(template_path, region, log_callback=None):
    """在指定区域内查找模板图，找到后点击匹配中心。
    返回 True 表示找到并已点击，False 表示未找到。"""
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width = x2 - x1
    height = y2 - y1

    # 使用get_resource_path获取正确的资源路径（兼容打包）
    img_path = get_resource_path(template_path)
    img_path_obj = Path(img_path)
    
    if not img_path_obj.exists():
        return False

    # 使用绝对路径字符串，cv2.imread需要字符串路径
    img_path_str = str(img_path_obj.resolve())
    # 尝试使用cv2读取
    template = cv2.imread(img_path_str, cv2.IMREAD_GRAYSCALE)
    if template is None:
        # 如果cv2读取失败，尝试使用PIL读取
        if HAS_PIL:
            try:
                pil_img = Image.open(img_path_str)
                # 转换为灰度图
                if pil_img.mode != 'L':
                    pil_img = pil_img.convert('L')
                # 转换为numpy数组
                template = np.array(pil_img)
            except Exception:
                return False
        else:
            return False

    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
    except Exception:
        return False

    try:
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    except Exception:
        return False

    if template.shape[0] > height or template.shape[1] > width:
        return False

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= MATCH_THRESHOLD:
        center_x = left + max_loc[0] + template.shape[1] // 2
        center_y = top + max_loc[1] + template.shape[0] // 2
        pyautogui.click(center_x, center_y)
        # 点击后鼠标右移100像素
        pyautogui.moveRel(100, 0)
        return True
    return False


def find_image_in_region(log_callback=None):
    """在指定区域内查找图片，使用OpenCV进行精确匹配
    返回找到的图片列表（可以找到同一张图片的多个不同位置）"""
    # 计算区域参数 (left, top, width, height)
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    # 截取屏幕指定区域（添加异常捕获）
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
    except Exception:
        return []  # 截图失败，返回空列表
    
    try:
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    except Exception:
        return []  # 图像处理失败，返回空列表
    
    found_images = []  # 存储找到的图片信息
    
    # 遍历所有图片文件
    for img_file in IMAGE_FILES:
        # 使用get_resource_path获取正确的资源路径（兼容打包）
        img_path = get_resource_path(img_file)
        img_path_obj = Path(img_path)
        
        if not img_path_obj.exists():
            continue
        
        try:
            # 读取模板图片（使用字符串路径，cv2.imread需要字符串）
            img_path_str = str(img_path_obj.resolve())
        
            # 尝试使用cv2读取
            template = cv2.imread(img_path_str, cv2.IMREAD_GRAYSCALE)
            if template is None:
                # 如果cv2读取失败，尝试使用PIL读取
                if HAS_PIL:
                    try:
                        pil_img = Image.open(img_path_str)
                        # 转换为灰度图
                        if pil_img.mode != 'L':
                            pil_img = pil_img.convert('L')
                        # 转换为numpy数组
                        template = np.array(pil_img)
                    except Exception:
                        continue
                else:
                    continue
            
            # 检查模板是否大于搜索区域
            if template.shape[0] > height or template.shape[1] > width:
                continue
            
            # 使用模板匹配
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            
            # 找到所有超过阈值的匹配位置
            locations = np.where(result >= MATCH_THRESHOLD)
            matches = list(zip(*locations[::-1]))  # 转换为(x, y)坐标列表
            
            if len(matches) == 0:
                continue
            
            # 过滤掉距离太近的重复匹配
            filtered_matches = []
            for match_x, match_y in matches:
                # 计算实际屏幕坐标
                actual_x = left + match_x
                actual_y = top + match_y
                match_score = result[match_y, match_x]
                
                # 检查是否与已有匹配距离太近
                is_duplicate = False
                for i, existing in enumerate(filtered_matches):
                    distance = np.sqrt((actual_x - existing['x'])**2 + (actual_y - existing['y'])**2)
                    if distance < MIN_MATCH_DISTANCE:
                        # 如果新匹配分数更高，替换旧的
                        if match_score > existing['score']:
                            filtered_matches[i] = {
                                'file': img_file,
                                'x': actual_x,
                                'y': actual_y,
                                'score': match_score
                            }
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    filtered_matches.append({
                        'file': img_file,
                        'x': actual_x,
                        'y': actual_y,
                        'score': match_score
                    })
            
            # 添加到结果列表
            for match in filtered_matches:
                found_images.append(match)
            
        except Exception:
            continue
    
    return found_images


def perform_click_sequence(log_callback=None):
    """执行点击序列：按两次空格（与 enchant_level 一致）"""
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
    time.sleep(1.5)  # 1.5秒后再次找图
