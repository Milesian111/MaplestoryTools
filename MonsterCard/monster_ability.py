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

# 词条图片文件名（不含目录），怪怪魔方用 picture/one/，怪怪恢复魔方用 picture/three/
IMAGE_FILE_NAMES = [
    'final.png',
    'monster_atk.png',
    'monster_magic.png',
    'skill_2.png',
    'monster_all.png',
    'monster_str.png',
    'monster_dex.png',
    'monster_int.png',
    'monster_luk.png',
    'monster_cri.png',
    'monster_hp.png',
    'monster_ignore.png',
    'monster_buff.png',
]

# 匹配阈值（0-1之间，越高越严格，建议0.95以上）
MATCH_THRESHOLD = 0.99

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

    if template.shape[0] > height or template.shape[1] > width:
        return False

    # 截取屏幕指定区域（添加异常捕获）
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
    except Exception:
        return False  # 截图失败，返回False
    
    try:
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    except Exception:
        return False  # 图像处理失败，返回False

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val < MATCH_THRESHOLD:
        return False

    # 匹配框左上角在区域内的坐标
    match_x, match_y = max_loc
    tw, th = template.shape[1], template.shape[0]
    # 匹配中心在屏幕上的坐标
    click_x = left + match_x + tw // 2
    click_y = top + match_y + th // 2

    pyautogui.click(click_x, click_y)
    return True


def check_image_exists(template_path, region=None, log_callback=None):
    """检查指定区域内是否存在模板图片，不进行点击
    返回 True 表示找到，False 表示未找到"""
    if region is None:
        region = SEARCH_REGION
    
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

    if template.shape[0] > height or template.shape[1] > width:
        return False

    # 截取屏幕指定区域（添加异常捕获）
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
    except Exception:
        return False  # 截图失败，返回False
    
    try:
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    except Exception:
        return False  # 图像处理失败，返回False

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val < MATCH_THRESHOLD:
        return False

    return True


def find_all_matches(template_path, region=None, log_callback=None):
    """在指定区域内查找模板图的所有匹配位置。
    返回列表，每项为 dict: {'x': 屏幕x, 'y': 屏幕y, 'w': 宽, 'h': 高}（匹配框左上角及模板宽高）"""
    if region is None:
        region = SEARCH_REGION
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width = x2 - x1
    height = y2 - y1

    img_path = get_resource_path(template_path)
    img_path_obj = Path(img_path)
    if not img_path_obj.exists():
        return []
    img_path_str = str(img_path_obj.resolve())
    template = cv2.imread(img_path_str, cv2.IMREAD_GRAYSCALE)
    if template is None and HAS_PIL:
        try:
            pil_img = Image.open(img_path_str)
            if pil_img.mode != 'L':
                pil_img = pil_img.convert('L')
            template = np.array(pil_img)
        except Exception:
            return []
    if template is None:
        return []
    tw, th = template.shape[1], template.shape[0]
    if th > height or tw > width:
        return []

    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    except Exception:
        return []

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= MATCH_THRESHOLD)
    matches = list(zip(*locations[::-1]))

    out = []
    for match_x, match_y in matches:
        actual_x = left + match_x
        actual_y = top + match_y
        is_duplicate = any(
            abs(actual_x - m['x']) < MIN_MATCH_DISTANCE and abs(actual_y - m['y']) < MIN_MATCH_DISTANCE
            for m in out
        )
        if not is_duplicate:
            out.append({'x': actual_x, 'y': actual_y, 'w': tw, 'h': th})
    return out


def find_image_in_region(region=None, log_callback=None, match_threshold=None, image_subdir="one"):
    """在指定区域内查找图片，使用OpenCV进行精确匹配
    region: (x1,y1,x2,y2)，None 则使用 SEARCH_REGION
    match_threshold: 匹配阈值，None 则使用 MATCH_THRESHOLD
    image_subdir: 图库子目录，"one"=怪怪魔方(picture/one/)，"three"=怪怪恢复魔方(picture/three/)
    返回找到的图片列表，每项 file 为 picture/{image_subdir}/{filename}"""
    if region is None:
        region = SEARCH_REGION
    # 计算区域参数 (left, top, width, height)
    x1, y1, x2, y2 = region
    left = int(x1)
    top = int(y1)
    width = int(x2 - x1)
    height = int(y2 - y1)
    if match_threshold is None:
        match_threshold = MATCH_THRESHOLD
    use_threshold = match_threshold
    
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

    # 遍历所有图片文件（路径为 picture/{image_subdir}/{name}）
    for name in IMAGE_FILE_NAMES:
        img_file = f"picture/{image_subdir}/{name}"
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
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 找到所有超过阈值的匹配位置
            locations = np.where(result >= use_threshold)
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
                        'x': int(actual_x),
                        'y': int(actual_y),
                        'score': match_score
                    })
            
            # 添加到结果列表
            for match in filtered_matches:
                found_images.append(match)
            
        except Exception:
            continue

    return found_images


def _press_space():
    """按一次空格（优先 keyboard，否则 pyautogui）。"""
    try:
        import keyboard
        keyboard.press_and_release('space')
    except Exception:
        pyautogui.press('space')


def perform_click_sequence(log_callback=None, first_run=False):
    """怪怪魔方模式的点击序列。
    仅首次（first_run=True）时查找 picture/btn_reset.png，未找到则输出错误并返回 False。
    若找到或非首次：按空格 -> sleep(0.1) -> 再按空格，返回 True。"""
    if first_run:
        if not find_image_and_click("picture/btn_reset.png", region=BTN_RESET_REGION, log_callback=log_callback):
            if log_callback:
                log_callback('错误：未找到"重新设定"按钮，请确认是否打开怪怪页面并选择魔方！')
            return False
    _press_space()
    time.sleep(0.1)
    _press_space()
    time.sleep(1.5)  # 等1.5秒再开始下一轮找图
    return True


# 怪怪恢复魔方：三个 after 框的尺寸（往右下划定的矩形）
AFTER_BOX_W = 225
AFTER_BOX_H = 242


def perform_click_sequence_recovery(log_callback=None):
    """怪怪恢复魔方(一次洗三个)的点击序列：找图 btn_reset3，点击中心，0.1秒后按空格，再0.1秒后按空格。
    返回 True 表示找到并已执行，False 表示未找到 btn_reset3。"""
    if not find_image_and_click("picture/btn_reset3.png", BTN_RESET_REGION, log_callback):
        return False
    pyautogui.moveRel(0, 50)  # 点击后鼠标下移 50 像素
    time.sleep(0.1)
    try:
        import keyboard
        keyboard.press_and_release('space')
    except Exception:
        pyautogui.press('space')
    time.sleep(0.1)
    try:
        import keyboard
        keyboard.press_and_release('space')
    except Exception:
        pyautogui.press('space')
    return True


