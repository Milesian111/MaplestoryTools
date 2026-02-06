import pyautogui
import cv2
import numpy as np
import winsound
import time
from pathlib import Path

# 获取当前脚本所在目录
BASE_DIR = Path(__file__).parent

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
    
    # 截取屏幕指定区域（只需要截取一次）
    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    screen_array = np.array(screenshot)
    screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    
    # 遍历所有图片文件
    for img_file in IMAGE_FILES:
        img_path = BASE_DIR / img_file
        
        if not img_path.exists():
            print(f"警告: 图片文件不存在 - {img_path}")
            continue
        
        print(f"正在查找: {img_file}")
        
        try:
            # 读取模板图片
            template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if template is None:
                print(f"✗ 无法读取图片: {img_file}")
                continue
            
            # 检查模板是否大于搜索区域
            if template.shape[0] > height or template.shape[1] > width:
                print(f"✗ 模板图片尺寸({template.shape[1]}x{template.shape[0]})大于搜索区域({width}x{height})")
                continue
            
            # 使用模板匹配
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            print(f"  匹配分数: {max_val:.4f} (阈值: {MATCH_THRESHOLD})")
            
            # 检查是否超过阈值
            if max_val >= MATCH_THRESHOLD:
                # 计算实际屏幕坐标
                actual_x = left + max_loc[0]
                actual_y = top + max_loc[1]
                print(f"✓ 找到图片: {img_file}")
                print(f"  位置: ({actual_x}, {actual_y})")
                print(f"  匹配分数: {max_val:.4f}")
                return True
            else:
                print(f"✗ 未找到: {img_file} (匹配分数 {max_val:.4f} < 阈值 {MATCH_THRESHOLD})")
                
        except Exception as e:
            print(f"✗ 查找 {img_file} 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return False


def perform_click_sequence():
    """执行完整点击序列（未找到图片时使用）
    返回True表示找到bag_full.png需要结束任务，False表示继续"""
    print("\n执行点击序列...")
    # 1. 点击精华
    print("点击 精华")
    pyautogui.click(698, 548)
    time.sleep(0.2)
    
    # 2. 点击是
    print("点击 是")
    pyautogui.click(647, 470)
    time.sleep(1.5)  
    
    # 3. 点击使用10个,并点击是
    should_exit = perform_use_sequence()
    if should_exit:
        return True  # 返回True表示需要结束任务
    return False  # 返回False表示继续循环


def find_bag_full():
    """查找bag_full.png图片"""
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    img_path = BASE_DIR / 'picture/bag_full.png'
    
    if not img_path.exists():
        print(f"警告: 图片文件不存在 - {img_path}")
        return False
    
    print(f"正在查找: picture/bag_full.png")
    
    try:
        # 截取屏幕指定区域
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        
        # 读取模板图片
        template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"✗ 无法读取图片: picture/bag_full.png")
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
            actual_x = left + max_loc[0]
            actual_y = top + max_loc[1]
            print(f"✓ 找到图片: picture/bag_full.png")
            print(f"  位置: ({actual_x}, {actual_y})")
            print(f"  匹配分数: {max_val:.4f}")
            return True
        else:
            print(f"✗ 未找到: picture/bag_full.png (匹配分数 {max_val:.4f} < 阈值 {MATCH_THRESHOLD})")
            return False
            
    except Exception as e:
        print(f"✗ 查找 picture/bag_full.png 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def perform_use_sequence():
    """执行使用序列（找到图片后使用）
    返回True表示找到bag_full.png需要结束任务，False表示继续"""
    print("\n执行使用序列...")
    # 点击使用10个
    print("点击 使用10个")
    pyautogui.click(783, 506)
    time.sleep(0.1)  # 等待0.1秒后查找bag_full.png
    
    # 查找bag_full.png
    if find_bag_full():
        print(f"\n✓ 找到bag_full.png，发出长beep声并结束任务")
        winsound.Beep(1000, 1000)  # 频率1000Hz，持续时间1000ms（长beep）
        return True  # 返回True表示需要结束任务
    
    # 如果没找到bag_full.png，继续点击"是"
    print("点击 是")
    pyautogui.click(647, 448)
    time.sleep(0.2)
    return False  # 返回False表示继续循环  
    


if __name__ == "__main__":
    print("开始查找图片...")
    print(f"查找目标: {', '.join(IMAGE_FILES)}\n")
    
    while True:
        # 查找图片
        found = find_image_in_region()
        
        if found:
            print(f"\n✓ 找到图片，发出beep声")
            winsound.Beep(1000, 200)  # 频率1000Hz，持续时间200ms
            # 执行使用序列（第3、4步），如果返回True表示找到bag_full需要结束
            should_exit = perform_use_sequence()
            if should_exit:
                break  # 找到bag_full.png，结束任务
            print("\n继续查找...\n" + "="*50 + "\n")
        else:
            print(f"\n✗ 未找到任何图片，执行完整点击序列后继续循环")
            # 执行完整点击序列，如果返回True表示找到bag_full需要结束
            should_exit = perform_click_sequence()
            if should_exit:
                break  # 找到bag_full.png，结束任务
            print("\n" + "="*50 + "\n")

