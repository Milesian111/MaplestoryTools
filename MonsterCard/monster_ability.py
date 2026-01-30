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

def find_image_and_click(template_path, region):
    """在指定区域内查找模板图，找到后点击匹配中心。
    返回 True 表示找到并已点击，False 表示未找到。"""
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width = x2 - x1
    height = y2 - y1

    img_path = BASE_DIR / template_path
    if not img_path.exists():
        print(f"✗ 模板不存在: {template_path}")
        return False

    template = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if template is None:
        print(f"✗ 无法读取: {template_path}")
        return False

    if template.shape[0] > height or template.shape[1] > width:
        print(f"✗ 模板 {template_path} 大于搜索区域")
        return False

    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    screen_array = np.array(screenshot)
    screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val < MATCH_THRESHOLD:
        print(f"✗ 未找到: {template_path} (最高分数 {max_val:.4f} < {MATCH_THRESHOLD})")
        return False

    # 匹配框左上角在区域内的坐标
    match_x, match_y = max_loc
    tw, th = template.shape[1], template.shape[0]
    # 匹配中心在屏幕上的坐标
    click_x = left + match_x + tw // 2
    click_y = top + match_y + th // 2

    print(f"✓ 找到 {template_path}，点击 ({click_x}, {click_y})")
    pyautogui.click(click_x, click_y)
    return True


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


def perform_click_sequence(log_callback=None):
    """执行点击序列：找图点击重设 -> 找图点击确认。log_callback(msg) 用于输出到 GUI 日志。"""
    print("\n执行点击序列...")
    # 1. 找图点击重设按钮
    if not find_image_and_click("picture/btn_reset.png", BTN_RESET_REGION):
        msg = '错误：未找到"重新设定"按钮，请确认是否打开怪怪页面并选择魔方！'
        if log_callback:
            log_callback(msg)
        print(msg)
    time.sleep(0.1)

    # 2. 找图点击确认按钮
    find_image_and_click("picture/btn_confirm.png", BTN_CONFIRM_REGION)
    # 点击确认后将鼠标下移 100 像素
    x, y = pyautogui.position()
    pyautogui.moveTo(x, y + 100)
    time.sleep(1.5)  # 1.5秒后再次找图


if __name__ == "__main__":
    print("开始查找图片...")
    print("终止条件：")
    print("  1. 不同位置找到2次 picture/final.png")
    print("  2. 不同位置找到2次 picture/monster_atk.png 加上1次 picture/skill_2.png")
    print("  3. 不同位置找到2次 picture/monster_magic.png 加上1次 picture/skill_2.png")
    print("  4. 不同位置找到1次 picture/final.png 加上2次 picture/monster_atk.png 或 picture/monster_magic.png")
    print("  5. 不同位置找到1次 picture/final.png 加上1次 picture/skill_2.png 加上1次 picture/monster_atk.png 或 picture/monster_magic.png\n")
    
    while True:
        # 查找图片
        found_images = find_image_in_region()
        
        # 统计各类图片的匹配数
        final_count = sum(1 for img in found_images if img['file'] == 'picture/final.png')
        monster_atk_count = sum(1 for img in found_images if img['file'] == 'picture/monster_atk.png')
        monster_magic_count = sum(1 for img in found_images if img['file'] == 'picture/monster_magic.png')
        skill_2_count = sum(1 for img in found_images if img['file'] == 'picture/skill_2.png')
        
        print(f"\n找到匹配统计:")
        print(f"  final.png: {final_count} 次")
        print(f"  monster_atk.png: {monster_atk_count} 次")
        print(f"  monster_magic.png: {monster_magic_count} 次")
        print(f"  skill_2.png: {skill_2_count} 次")
        
        # 判断是否满足停止条件
        condition1 = final_count >= 2
        condition2 = monster_atk_count >= 2 and skill_2_count >= 1
        condition3 = monster_magic_count >= 2 and skill_2_count >= 1
        condition4 = final_count >= 1 and (monster_atk_count >= 2 or monster_magic_count >= 2)
        condition5 = final_count >= 1 and skill_2_count >= 1 and (monster_atk_count >= 1 or monster_magic_count >= 1)
        
        if condition1 or condition2 or condition3 or condition4 or condition5:
            if condition1:
                print(f"\n✓ 满足条件1: 找到 {final_count} 次 final.png，停止任务")
            if condition2:
                print(f"\n✓ 满足条件2: 找到 {monster_atk_count} 次 monster_atk.png 和 {skill_2_count} 次 skill_2.png，停止任务")
            if condition3:
                print(f"\n✓ 满足条件3: 找到 {monster_magic_count} 次 monster_magic.png 和 {skill_2_count} 次 skill_2.png，停止任务")
            if condition4:
                print(f"\n✓ 满足条件4: 找到 {final_count} 次 final.png 和 {monster_atk_count + monster_magic_count} 次 monster_atk/magic（至少2次），停止任务")
            if condition5:
                print(f"\n✓ 满足条件5: 找到 {final_count} 次 final.png、{skill_2_count} 次 skill_2.png 和 {monster_atk_count + monster_magic_count} 次 monster_atk/magic，停止任务")
            winsound.Beep(1000, 200)  # 频率1000Hz，持续时间200ms
            break
        else:
            print(f"\n✗ 未满足任何终止条件，执行点击序列后继续循环")
            # 执行点击序列
            perform_click_sequence()
            print("\n" + "="*50 + "\n")
