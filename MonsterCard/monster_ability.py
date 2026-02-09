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

# 图片文件列表
IMAGE_FILES = [
    'picture/final.png',
    'picture/monster_atk.png',
    'picture/monster_magic.png',
    'picture/skill_2.png',
    'picture/monster_all.png',
    'picture/monster_str.png',
    'picture/monster_dex.png',
    'picture/monster_int.png',
    'picture/monster_luk.png',
    'picture/monster_cri.png',
    'picture/monster_hp.png',
    'picture/monster_ignore.png',
    'picture/monster_buff.png',
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
    if log_callback is None:
        log_callback = lambda msg: None
    
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width = x2 - x1
    height = y2 - y1

    # 使用get_resource_path获取正确的资源路径（兼容打包）
    img_path = get_resource_path(template_path)
    img_path_obj = Path(img_path)
    img_path_str = str(img_path_obj.resolve())
    
    log_callback(f"[调试] 查找并点击图片: {template_path}")
    log_callback(f"[调试] 图片路径: {img_path_str}")
    try:
        meipass = sys._MEIPASS
        log_callback(f"[调试] sys._MEIPASS: {meipass}")
    except:
        log_callback(f"[调试] sys._MEIPASS: 未设置（开发环境）")
    
    if not img_path_obj.exists():
        log_callback(f"[调试] ✗ 图片文件不存在: {img_path_str}")
        return False
    else:
        log_callback(f"[调试] ✓ 图片文件存在: {img_path_str}")

    # 尝试使用cv2读取
    log_callback(f"[调试] 尝试使用cv2读取图片: {img_path_str}")
    template = cv2.imread(img_path_str, cv2.IMREAD_GRAYSCALE)
    if template is None:
        log_callback(f"[调试] ✗ cv2读取失败，返回None")
        # 如果cv2读取失败，尝试使用PIL读取
        if HAS_PIL:
            log_callback(f"[调试] 尝试使用PIL读取图片")
            try:
                pil_img = Image.open(img_path_str)
                log_callback(f"[调试] ✓ PIL读取成功，原始模式: {pil_img.mode}, 尺寸: {pil_img.size}")
                # 转换为灰度图
                if pil_img.mode != 'L':
                    pil_img = pil_img.convert('L')
                    log_callback(f"[调试] ✓ 已转换为灰度图")
                # 转换为numpy数组
                template = np.array(pil_img)
                log_callback(f"[调试] ✓ PIL图像转换为numpy数组，尺寸: {template.shape}")
            except Exception as e:
                log_callback(f"[调试] ✗ PIL读取也失败: {e}")
                return False
        else:
            log_callback(f"[调试] ✗ PIL不可用，无法回退")
            return False
    else:
        log_callback(f"[调试] ✓ cv2读取成功，尺寸: {template.shape}")

    if template.shape[0] > height or template.shape[1] > width:
        log_callback(f"[调试] ✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
        return False
    else:
        log_callback(f"[调试] ✓ 模板尺寸检查通过: {template.shape[1]}x{template.shape[0]} <= {width}x{height}")

    # 截取屏幕指定区域（添加异常捕获）
    log_callback(f"[调试] 开始截图，区域: ({left}, {top}, {width}, {height})")
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        log_callback(f"[调试] ✓ 截图成功，尺寸: {screenshot.size}")
    except Exception as e:
        log_callback(f"[调试] ✗ 截图失败: {e}")
        return False  # 截图失败，返回False
    
    try:
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        log_callback(f"[调试] ✓ 屏幕图像处理完成，尺寸: {screen_gray.shape}")
    except Exception as e:
        log_callback(f"[调试] ✗ 图像处理失败: {e}")
        return False  # 图像处理失败，返回False

    log_callback(f"[调试] 开始模板匹配...")
    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    log_callback(f"[调试] 匹配结果 - 最高分数: {max_val:.4f}, 阈值: {MATCH_THRESHOLD}, 位置: {max_loc}")

    if max_val < MATCH_THRESHOLD:
        log_callback(f"[调试] ✗ 未找到图片，匹配分数: {max_val:.4f} < {MATCH_THRESHOLD}")
        return False

    # 匹配框左上角在区域内的坐标
    match_x, match_y = max_loc
    tw, th = template.shape[1], template.shape[0]
    # 匹配中心在屏幕上的坐标
    click_x = left + match_x + tw // 2
    click_y = top + match_y + th // 2

    log_callback(f"[调试] ✓ 找到图片，准备点击位置: ({click_x}, {click_y})")
    pyautogui.click(click_x, click_y)
    log_callback(f"[调试] ✓ 已点击: ({click_x}, {click_y})")
    return True


def check_image_exists(template_path, region=None, log_callback=None):
    """检查指定区域内是否存在模板图片，不进行点击
    返回 True 表示找到，False 表示未找到"""
    if log_callback is None:
        log_callback = lambda msg: None
    
    if region is None:
        region = SEARCH_REGION
    
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width = x2 - x1
    height = y2 - y1

    # 使用get_resource_path获取正确的资源路径（兼容打包）
    img_path = get_resource_path(template_path)
    img_path_obj = Path(img_path)
    img_path_str = str(img_path_obj.resolve())
    
    log_callback(f"[调试] 检查图片是否存在: {template_path}")
    log_callback(f"[调试] 图片路径: {img_path_str}")
    
    if not img_path_obj.exists():
        log_callback(f"[调试] ✗ 图片文件不存在: {img_path_str}")
        return False
    else:
        log_callback(f"[调试] ✓ 图片文件存在: {img_path_str}")

    # 尝试使用cv2读取
    log_callback(f"[调试] 尝试使用cv2读取图片: {img_path_str}")
    template = cv2.imread(img_path_str, cv2.IMREAD_GRAYSCALE)
    if template is None:
        log_callback(f"[调试] ✗ cv2读取失败，返回None")
        # 如果cv2读取失败，尝试使用PIL读取
        if HAS_PIL:
            log_callback(f"[调试] 尝试使用PIL读取图片")
            try:
                pil_img = Image.open(img_path_str)
                log_callback(f"[调试] ✓ PIL读取成功，原始模式: {pil_img.mode}, 尺寸: {pil_img.size}")
                # 转换为灰度图
                if pil_img.mode != 'L':
                    pil_img = pil_img.convert('L')
                    log_callback(f"[调试] ✓ 已转换为灰度图")
                # 转换为numpy数组
                template = np.array(pil_img)
                log_callback(f"[调试] ✓ PIL图像转换为numpy数组，尺寸: {template.shape}")
            except Exception as e:
                log_callback(f"[调试] ✗ PIL读取也失败: {e}")
                return False
        else:
            log_callback(f"[调试] ✗ PIL不可用，无法回退")
            return False
    else:
        log_callback(f"[调试] ✓ cv2读取成功，尺寸: {template.shape}")

    if template.shape[0] > height or template.shape[1] > width:
        log_callback(f"[调试] ✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
        return False
    else:
        log_callback(f"[调试] ✓ 模板尺寸检查通过: {template.shape[1]}x{template.shape[0]} <= {width}x{height}")

    # 截取屏幕指定区域（添加异常捕获）
    log_callback(f"[调试] 开始截图，区域: ({left}, {top}, {width}, {height})")
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        log_callback(f"[调试] ✓ 截图成功，尺寸: {screenshot.size}")
    except Exception as e:
        log_callback(f"[调试] ✗ 截图失败: {e}")
        return False  # 截图失败，返回False
    
    try:
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        log_callback(f"[调试] ✓ 屏幕图像处理完成，尺寸: {screen_gray.shape}")
    except Exception as e:
        log_callback(f"[调试] ✗ 图像处理失败: {e}")
        return False  # 图像处理失败，返回False

    log_callback(f"[调试] 开始模板匹配...")
    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    log_callback(f"[调试] 匹配结果 - 最高分数: {max_val:.4f}, 阈值: {MATCH_THRESHOLD}, 位置: {max_loc}")

    if max_val < MATCH_THRESHOLD:
        log_callback(f"[调试] ✗ 未找到图片，匹配分数: {max_val:.4f} < {MATCH_THRESHOLD}")
        return False

    log_callback(f"[调试] ✓ 找到图片，匹配分数: {max_val:.4f} >= {MATCH_THRESHOLD}")
    return True


def find_image_in_region(log_callback=None):
    """在指定区域内查找图片，使用OpenCV进行精确匹配
    返回找到的图片列表（可以找到同一张图片的多个不同位置）"""
    if log_callback is None:
        log_callback = lambda msg: None
    
    # 计算区域参数 (left, top, width, height)
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    log_callback(f"[调试] ========== 开始查找所有图片 ==========")
    log_callback(f"[调试] 搜索区域: {SEARCH_REGION}")
    log_callback(f"[调试] 匹配阈值: {MATCH_THRESHOLD}")
    log_callback(f"[调试] 最小匹配距离: {MIN_MATCH_DISTANCE}像素")
    log_callback(f"[调试] 图片文件数量: {len(IMAGE_FILES)}")
    try:
        meipass = sys._MEIPASS
        log_callback(f"[调试] sys._MEIPASS: {meipass}")
    except:
        log_callback(f"[调试] sys._MEIPASS: 未设置（开发环境）")
    
    # 截取屏幕指定区域（添加异常捕获）
    log_callback(f"[调试] 开始截图，区域: ({left}, {top}, {width}, {height})")
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        log_callback(f"[调试] ✓ 截图成功，尺寸: {screenshot.size}")
    except Exception as e:
        log_callback(f"[调试] ✗ 截图失败: {e}")
        return []  # 截图失败，返回空列表
    
    try:
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        log_callback(f"[调试] ✓ 屏幕图像处理完成，尺寸: {screen_gray.shape}")
    except Exception as e:
        log_callback(f"[调试] ✗ 图像处理失败: {e}")
        return []  # 图像处理失败，返回空列表
    
    found_images = []  # 存储找到的图片信息
    
    # 遍历所有图片文件
    for idx, img_file in enumerate(IMAGE_FILES, 1):
        log_callback(f"[调试] ---------- 查找第 {idx}/{len(IMAGE_FILES)} 张图片: {img_file} ----------")
        # 使用get_resource_path获取正确的资源路径（兼容打包）
        img_path = get_resource_path(img_file)
        img_path_obj = Path(img_path)
        img_path_str = str(img_path_obj.resolve())
        
        log_callback(f"[调试] 图片路径: {img_path_str}")
        
        if not img_path_obj.exists():
            log_callback(f"[调试] ✗ 图片文件不存在: {img_path_str}")
            continue
        else:
            log_callback(f"[调试] ✓ 图片文件存在: {img_path_str}")
        
        try:
            # 尝试使用cv2读取
            log_callback(f"[调试] 尝试使用cv2读取图片: {img_path_str}")
            template = cv2.imread(img_path_str, cv2.IMREAD_GRAYSCALE)
            if template is None:
                log_callback(f"[调试] ✗ cv2读取失败，返回None")
                # 如果cv2读取失败，尝试使用PIL读取
                if HAS_PIL:
                    log_callback(f"[调试] 尝试使用PIL读取图片")
                    try:
                        pil_img = Image.open(img_path_str)
                        log_callback(f"[调试] ✓ PIL读取成功，原始模式: {pil_img.mode}, 尺寸: {pil_img.size}")
                        # 转换为灰度图
                        if pil_img.mode != 'L':
                            pil_img = pil_img.convert('L')
                            log_callback(f"[调试] ✓ 已转换为灰度图")
                        # 转换为numpy数组
                        template = np.array(pil_img)
                        log_callback(f"[调试] ✓ PIL图像转换为numpy数组，尺寸: {template.shape}")
                    except Exception as e:
                        log_callback(f"[调试] ✗ PIL读取也失败: {e}")
                        continue
                else:
                    log_callback(f"[调试] ✗ PIL不可用，无法回退")
                    continue
            else:
                log_callback(f"[调试] ✓ cv2读取成功，尺寸: {template.shape}")
            
            # 检查模板是否大于搜索区域
            if template.shape[0] > height or template.shape[1] > width:
                log_callback(f"[调试] ✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
                continue
            else:
                log_callback(f"[调试] ✓ 模板尺寸检查通过: {template.shape[1]}x{template.shape[0]} <= {width}x{height}")
            
            # 使用模板匹配
            log_callback(f"[调试] 开始模板匹配...")
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            
            # 找到所有超过阈值的匹配位置
            locations = np.where(result >= MATCH_THRESHOLD)
            matches = list(zip(*locations[::-1]))  # 转换为(x, y)坐标列表
            
            log_callback(f"[调试] 找到 {len(matches)} 个初始匹配位置")
            
            if len(matches) == 0:
                log_callback(f"[调试] ✗ 未找到匹配位置")
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
            
            log_callback(f"[调试] 过滤后剩余 {len(filtered_matches)} 个匹配位置")
            for i, match in enumerate(filtered_matches, 1):
                log_callback(f"[调试]   匹配{i}: 位置({match['x']}, {match['y']}), 分数: {match['score']:.4f}")
            
            # 添加到结果列表
            for match in filtered_matches:
                found_images.append(match)
            
        except Exception as e:
            log_callback(f"[调试] ✗ 处理图片时发生异常: {e}")
            import traceback
            log_callback(f"[调试] 异常堆栈:\n{traceback.format_exc()}")
            continue
    
    log_callback(f"[调试] ========== 查找完成，共找到 {len(found_images)} 个匹配 ==========")
    return found_images


def perform_click_sequence(log_callback=None):
    """执行点击序列：找图点击重设 -> 找图点击确认。log_callback(msg) 用于输出到 GUI 日志。"""
    if log_callback is None:
        log_callback = lambda msg: None
    
    log_callback(f"[调试] ========== 开始执行点击序列 ==========")
    
    # 1. 找图点击重设按钮
    log_callback(f"[调试] 步骤1: 查找并点击重设按钮")
    if not find_image_and_click("picture/btn_reset.png", BTN_RESET_REGION, log_callback):
        log_callback('错误：未找到"重新设定"按钮，请确认是否打开怪怪页面并选择魔方！')
    else:
        log_callback(f"[调试] ✓ 重设按钮点击成功")
    time.sleep(0.1)

    # 2. 找图点击确认按钮
    log_callback(f"[调试] 步骤2: 查找并点击确认按钮")
    if find_image_and_click("picture/btn_confirm.png", BTN_CONFIRM_REGION, log_callback):
        log_callback(f"[调试] ✓ 确认按钮点击成功")
    else:
        log_callback(f"[调试] ✗ 未找到确认按钮")
    
    # 点击确认后将鼠标下移 100 像素
    x, y = pyautogui.position()
    pyautogui.moveTo(x, y + 100)
    log_callback(f"[调试] ✓ 鼠标已下移100像素到: ({x}, {y + 100})")
    log_callback(f"[调试] 等待1.5秒后继续...")
    time.sleep(1.5)  # 1.5秒后再次找图
    
    log_callback(f"[调试] ========== 点击序列执行完成 ==========")


