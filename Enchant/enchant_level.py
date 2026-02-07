import pyautogui
import cv2
import numpy as np
import winsound
import time
from pathlib import Path
import sys
import os

# 尝试导入 PIL/Pillow 作为 cv2 读取失败时的回退
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
    
    # 使用get_resource_path获取正确的资源路径（兼容打包）
    img_path_str = get_resource_path(IMAGE_FILE)
    img_path = Path(img_path_str)
    
    log_callback(f"[调试] 查找图片: {IMAGE_FILE}")
    log_callback(f"[调试] 图片路径: {img_path_str}")
    log_callback(f"[调试] BASE_DIR: {BASE_DIR}")
    try:
        meipass = sys._MEIPASS
        log_callback(f"[调试] sys._MEIPASS: {meipass}")
    except:
        log_callback(f"[调试] sys._MEIPASS: 未设置（开发环境）")
    
    if not img_path.exists():
        log_callback(f"[调试] ✗ 图片文件不存在: {img_path_str}")
        return False
    else:
        log_callback(f"[调试] ✓ 图片文件存在: {img_path_str}")
    
    try:
        # 截取屏幕指定区域
        log_callback(f"[调试] 开始截图，区域: ({left}, {top}, {width}, {height})")
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        log_callback(f"[调试] ✓ 截图成功，尺寸: {screenshot.size}")
        
        # 转换为numpy数组并转为灰度图
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        log_callback(f"[调试] ✓ 屏幕图像处理完成，尺寸: {screen_gray.shape}")
        
        # 读取模板图片
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
        
        # 检查模板是否大于搜索区域
        if template.shape[0] > height or template.shape[1] > width:
            log_callback(f"[调试] ✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
            return False
        else:
            log_callback(f"[调试] ✓ 模板尺寸检查通过: {template.shape[1]}x{template.shape[0]} <= {width}x{height}")
        
        # 使用模板匹配
        log_callback(f"[调试] 开始模板匹配...")
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        log_callback(f"[调试] 匹配结果 - 最高分数: {max_val:.4f}, 阈值: {MATCH_THRESHOLD}, 位置: {max_loc}")
        
        # 检查是否超过阈值
        if max_val >= MATCH_THRESHOLD:
            log_callback(f"[调试] ✓ 找到图片，匹配分数: {max_val:.4f} >= {MATCH_THRESHOLD}")
            return True
        else:
            log_callback(f"[调试] ✗ 未找到图片，匹配分数: {max_val:.4f} < {MATCH_THRESHOLD}")
            return False
            
    except Exception as e:
        log_callback(f"[调试] ✗ 查找图片时发生异常: {e}")
        import traceback
        log_callback(f"[调试] 异常堆栈:\n{traceback.format_exc()}")
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
    
    # 使用get_resource_path获取正确的资源路径（兼容打包）
    img_path_str = get_resource_path(image_file)
    img_path = Path(img_path_str)
    
    log_callback(f"[调试] 查找并点击图片: {image_file}")
    log_callback(f"[调试] 图片路径: {img_path_str}")
    log_callback(f"[调试] BASE_DIR: {BASE_DIR}")
    try:
        meipass = sys._MEIPASS
        log_callback(f"[调试] sys._MEIPASS: {meipass}")
    except:
        log_callback(f"[调试] sys._MEIPASS: 未设置（开发环境）")
    
    if not img_path.exists():
        log_callback(f"[调试] ✗ 图片文件不存在: {img_path_str}")
        log_callback(f"警告: 图片文件不存在 - {img_path}")
        return False
    else:
        log_callback(f"[调试] ✓ 图片文件存在: {img_path_str}")
    
    log_callback(f"正在查找: {image_file}")
    
    try:
        # 截取屏幕指定区域
        log_callback(f"[调试] 开始截图，区域: ({left}, {top}, {width}, {height})")
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        log_callback(f"[调试] ✓ 截图成功，尺寸: {screenshot.size}")
        
        # 转换为numpy数组并转为灰度图
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        log_callback(f"[调试] ✓ 屏幕图像处理完成，尺寸: {screen_gray.shape}")
        
        # 读取模板图片
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
                    log_callback(f"✗ 无法读取图片: {image_file}")
                    return False
            else:
                log_callback(f"[调试] ✗ PIL不可用，无法回退")
                log_callback(f"✗ 无法读取图片: {image_file}")
                return False
        else:
            log_callback(f"[调试] ✓ cv2读取成功，尺寸: {template.shape}")
        
        # 检查模板是否大于搜索区域
        if template.shape[0] > height or template.shape[1] > width:
            log_callback(f"[调试] ✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
            log_callback(f"✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
            return False
        else:
            log_callback(f"[调试] ✓ 模板尺寸检查通过: {template.shape[1]}x{template.shape[0]} <= {width}x{height}")
        
        # 使用模板匹配
        log_callback(f"[调试] 开始模板匹配...")
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        log_callback(f"[调试] 匹配结果 - 最高分数: {max_val:.4f}, 阈值: {threshold}, 位置: {max_loc}")
        
        log_callback(f"  匹配分数: {max_val:.4f} (阈值: {threshold})")
        
        # 检查是否超过阈值
        if max_val >= threshold:
            # 计算实际屏幕坐标（图片中心点）
            center_x = left + max_loc[0] + template.shape[1] // 2
            center_y = top + max_loc[1] + template.shape[0] // 2
            log_callback(f"[调试] ✓ 找到图片，准备点击位置: ({center_x}, {center_y})")
            log_callback(f"✓ 找到图片: {image_file}")
            log_callback(f"  位置: ({center_x}, {center_y})")
            log_callback(f"  匹配分数: {max_val:.4f}")
            # 点击图片中心
            pyautogui.click(center_x, center_y)
            log_callback(f"  已点击: ({center_x}, {center_y})")
            # 点击后鼠标右移100像素
            pyautogui.moveRel(100, 0)
            log_callback(f"[调试] ✓ 鼠标已右移100像素")
            return True
        else:
            log_callback(f"[调试] ✗ 未找到图片，匹配分数: {max_val:.4f} < {threshold}")
            log_callback(f"✗ 未找到: {image_file} (匹配分数 {max_val:.4f} < 阈值 {threshold})")
            return False
            
    except Exception as e:
        log_callback(f"[调试] ✗ 查找 {image_file} 时发生异常: {e}")
        import traceback
        log_callback(f"[调试] 异常堆栈:\n{traceback.format_exc()}")
        log_callback(f"✗ 查找 {image_file} 时出错: {e}")
        traceback.print_exc()
        return False


def perform_click_sequence(log_callback=None):
    """执行点击序列"""
    if log_callback is None:
        log_callback = lambda msg: print(msg)
    
    # 1. 按第一次空格
    log_callback(f"[调试] 准备按第一次空格键")
    if HAS_KEYBOARD:
        log_callback(f"[调试] 使用keyboard库发送空格键")
        keyboard.press_and_release('space')
    else:
        log_callback(f"[调试] 使用pyautogui发送空格键")
        pyautogui.press('space')
    log_callback(f"[调试] ✓ 第一次空格键已发送")
    time.sleep(0.1)
    
    # 2. 0.1秒后按第二次空格
    log_callback(f"[调试] 准备按第二次空格键")
    if HAS_KEYBOARD:
        keyboard.press_and_release('space')
    else:
        pyautogui.press('space')
    log_callback(f"[调试] ✓ 第二次空格键已发送")
    log_callback(f"[调试] 等待1.5秒后继续...")
    time.sleep(1.5)  # 等待1.5秒后再次查找图片


def run_enchant_level_loop(stop_event, status_callback, log_callback=None):
    """在后台线程中执行上绿的主循环，遇 stop_event 或找到目标图片时退出"""
    if log_callback is None:
        log_callback = lambda msg: None
    
    count = 0
    
    log_callback(f"[调试] ========== 开始上绿循环 ==========")
    log_callback(f"[调试] 查找图片: {IMAGE_FILE}")
    log_callback(f"[调试] 匹配阈值: {MATCH_THRESHOLD}")
    log_callback(f"[调试] 搜索区域: {SEARCH_REGION}")
    log_callback(f"[调试] BASE_DIR: {BASE_DIR}")
    log_callback(f"[调试] HAS_PIL: {HAS_PIL}")
    log_callback(f"[调试] HAS_KEYBOARD: {HAS_KEYBOARD}")
    
    try:
        while not stop_event.is_set():
            log_callback(f"[调试] ---------- 第 {count + 1} 次循环开始 ----------")
            # 查找图片
            found = find_image_in_region(log_callback=log_callback)
            
            if found:
                log_callback(f"[调试] ✓ 找到目标图片，任务完成")
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
                    log_callback(f"[调试] 检测到停止信号")
                    status_callback("任务已停止")
                    break
                log_callback(f"[调试] ---------- 第 {count} 次循环结束 ----------")
    except Exception as e:
        error_msg = f"运行出错: {e}"
        log_callback(f"[调试] ✗ 主循环发生异常: {e}")
        import traceback
        log_callback(f"[调试] 异常堆栈:\n{traceback.format_exc()}")
        log_callback(error_msg)
        status_callback(error_msg)
        traceback.print_exc()


if __name__ == "__main__":
    import threading
    stop_event = threading.Event()
    status_callback = lambda msg: print(f"[状态] {msg}")
    log_callback = lambda msg: print(msg)
    run_enchant_level_loop(stop_event, status_callback, log_callback)

