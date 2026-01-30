import pyautogui
import cv2
import numpy as np
import winsound
import time
from pathlib import Path

# 获取当前脚本所在目录
BASE_DIR = Path(__file__).parent

# 查找范围 (x1, y1, x2, y2)
SEARCH_REGION = (0, 0, 1366, 768)

# 图片文件
IMAGE_FILE = 'picture/level4.png'

# 匹配阈值（0-1之间，越高越严格，建议0.95以上）
MATCH_THRESHOLD = 0.99


def find_image_in_region():
    """在指定区域内查找图片，使用OpenCV进行精确匹配
    返回是否找到图片"""
    # 计算区域参数 (left, top, width, height)
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    print(f"搜索区域: ({left}, {top}, {width}, {height})")
    
    img_path = BASE_DIR / IMAGE_FILE
    
    if not img_path.exists():
        print(f"警告: 图片文件不存在 - {img_path}")
        return False
    
    print(f"正在查找: {IMAGE_FILE}")
    
    try:
        # 截取屏幕指定区域
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        # 转换为numpy数组并转为灰度图
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        
        # 读取模板图片
        template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"✗ 无法读取图片: {IMAGE_FILE}")
            return False
        
        # 检查模板是否大于搜索区域
        if template.shape[0] > height or template.shape[1] > width:
            print(f"✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
            return False
        
        # 使用模板匹配
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        print(f"  匹配分数: {max_val:.4f} (阈值: {MATCH_THRESHOLD})")
        
        # 检查是否超过阈值
        if max_val >= MATCH_THRESHOLD:
            # 计算实际屏幕坐标
            actual_x = left + max_loc[0]
            actual_y = top + max_loc[1]
            print(f"✓ 找到图片: {IMAGE_FILE}")
            print(f"  位置: ({actual_x}, {actual_y})")
            print(f"  匹配分数: {max_val:.4f}")
            return True
        else:
            print(f"✗ 未找到: {IMAGE_FILE} (匹配分数 {max_val:.4f} < 阈值 {MATCH_THRESHOLD})")
            return False
            
    except Exception as e:
        print(f"✗ 查找 {IMAGE_FILE} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def perform_click_sequence():
    """执行点击序列"""
    print("\n执行点击序列...")
    # 1. 鼠标左键单击397,752
    print("点击 (397, 752)")
    pyautogui.click(397, 752)
    time.sleep(0.1)
    
    # 2. 0.1秒后单击646,466
    print("点击 (646, 466)")
    pyautogui.click(646, 466)
    time.sleep(1.5)  # 等待1.5秒后再次查找图片


if __name__ == "__main__":
    print("开始查找图片...")
    print(f"查找目标: {IMAGE_FILE}\n")
    
    while True:
        # 查找图片
        found = find_image_in_region()
        
        if found:
            print(f"\n✓ 找到图片，停止任务")
            winsound.Beep(1000, 1000)  # 频率1000Hz，持续时间200ms
            break
        else:
            print(f"\n✗ 未找到图片，继续循环")
            # 执行点击序列
            perform_click_sequence()
            print("\n" + "="*50 + "\n")

