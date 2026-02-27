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

IMAGE_FILES = [
    'picture/str2.png',
    'picture/str9.png'
]

# 匹配阈值（0-1之间，越高越严格，建议0.95以上）
MATCH_THRESHOLD = 0.99

# 需要找到的匹配次数（找到3个不同位置才停止，可以是同一张图片的不同位置）
REQUIRED_MATCH_COUNT = 2

# 最小匹配距离（像素），用于过滤重复匹配
MIN_MATCH_DISTANCE = 10


def find_image_in_region():
    """在指定区域内查找图片，使用OpenCV进行精确匹配
    返回找到的图片列表（可以找到同一张图片的多个不同位置）"""
    # 计算区域参数 (left, top, width, height)
    x1, y1, x2, y2 = SEARCH_REGION
    left = x1
    top = y1
    width = x2 - x1
    height = y2 - y1
    
    print(f"搜索区域: ({left}, {top}, {width}, {height})")
    
    # 截取屏幕指定区域
    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    # 转换为numpy数组并转为BGR格式（OpenCV使用BGR）
    screen_array = np.array(screenshot)
    screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
    
    found_images = []  # 存储找到的图片信息
    
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
            
            # 找到所有超过阈值的匹配位置
            locations = np.where(result >= MATCH_THRESHOLD)
            matches = list(zip(*locations[::-1]))  # 转换为(x, y)坐标列表
            
            if len(matches) == 0:
                print(f"✗ 未找到: {img_file} (无匹配位置超过阈值 {MATCH_THRESHOLD})")
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
                print(f"✓ 找到图片: {img_file}")
                print(f"  位置: ({match['x']}, {match['y']})")
                print(f"  匹配分数: {match['score']:.4f}")
                found_images.append(match)
            
            if len(filtered_matches) == 0:
                print(f"✗ 未找到: {img_file} (所有匹配都被过滤为重复)")
            else:
                print(f"  共找到 {len(filtered_matches)} 个不同位置的匹配")
                
        except Exception as e:
            print(f"✗ 查找 {img_file} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    return found_images


def perform_click_sequence():
    """执行点击序列"""
    print("\n执行点击序列...")
    # 1. 鼠标左键单击390,749
    print("点击 (390, 749)")
    pyautogui.click(390, 749)
    time.sleep(0.1)
    
    # 2. 0.1秒后单击640,464
    print("点击 (640, 464)")
    pyautogui.click(640, 464)
    time.sleep(0.1)
    
    # 3. 0.1秒后单击640,474
    print("点击 (640, 474)")
    pyautogui.click(640, 474)
    time.sleep(1.5)  # 等待1秒后再次查找图片


if __name__ == "__main__":
    print("开始查找图片...")
    print(f"需要找到 {REQUIRED_MATCH_COUNT} 次及以上匹配才会停止")
    print(f"（可以是同一张图片的不同位置，或不同图片）\n")
    
    while True:
        # 查找图片
        found_images = find_image_in_region()
        found_count = len(found_images)
        
        print(f"\n找到 {found_count} 次匹配")
        
        # 如果找到3个不同位置，beep并停止
        if found_count >= REQUIRED_MATCH_COUNT:
            print(f"✓ 找到 {found_count} 个不同位置的匹配，达到阈值 {REQUIRED_MATCH_COUNT}，停止任务")
            winsound.Beep(1000, 1000)  # 频率1000Hz，持续时间200ms
            break
        else:
            print(f"✗ 只找到 {found_count} 次匹配，未达到阈值 {REQUIRED_MATCH_COUNT}，继续循环")
            # 执行点击序列
            perform_click_sequence()
            print("\n" + "="*50 + "\n")

