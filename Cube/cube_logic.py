"""
魔方主逻辑：在指定区域内按终止条件找图，多组之间为或逻辑。
参考 int.py 的找图与过滤逻辑。
"""
import cv2
import numpy as np
import pyautogui
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 查找范围 (x1, y1, x2, y2)，与 int.py 一致
SEARCH_REGION = (0, 0, 1366, 768)

MATCH_THRESHOLD = 0.99
MIN_MATCH_DISTANCE = 10


def _load_template_gray(img_path):
    """读取模板灰度图，返回 numpy 数组或 None。"""
    path_str = str(Path(img_path).resolve())
    template = cv2.imread(path_str, cv2.IMREAD_GRAYSCALE)
    if template is not None:
        return template
    if HAS_PIL:
        try:
            pil_img = Image.open(path_str)
            if pil_img.mode != "L":
                pil_img = pil_img.convert("L")
            return np.array(pil_img)
        except Exception:
            pass
    return None


def find_image_positions(region, image_path, threshold=MATCH_THRESHOLD, min_distance=MIN_MATCH_DISTANCE):
    """
    在 region 内查找图片，返回所有不重叠的匹配位置（屏幕坐标）。
    :param region: (x1, y1, x2, y2)
    :param image_path: 模板图片路径
    :param threshold: 匹配阈值
    :param min_distance: 最小匹配间距，小于此距离视为同一位置
    :return: [(x, y), ...]，按匹配分数从高到低保留
    """
    path = Path(image_path)
    if not path.exists():
        return []
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width, height = x2 - x1, y2 - y1
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        template = _load_template_gray(path)
        if template is None or template.shape[0] > height or template.shape[1] > width:
            return []
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        matches = list(zip(*locations[::-1]))
        if not matches:
            return []
        # 按分数从高到低排序，便于保留最优匹配
        matches_with_score = [
            (left + mx + template.shape[1] // 2, top + my + template.shape[0] // 2, float(result[my, mx]))
            for mx, my in matches
        ]
        matches_with_score.sort(key=lambda t: -t[2])
        filtered = []
        for cx, cy, score in matches_with_score:
            too_near = False
            for (ex, ey) in filtered:
                if np.sqrt((cx - ex) ** 2 + (cy - ey) ** 2) < min_distance:
                    too_near = True
                    break
            if not too_near:
                filtered.append((cx, cy))
        return filtered
    except Exception:
        return []


def _group_required_counts(group):
    """将一组终止条件转为每个 key 需要的次数，跳过 'any'。"""
    required = {}
    for key in group:
        if key == "any":
            continue
        required[key] = required.get(key, 0) + 1
    return required


def _max_required_counts(groups):
    """统计多组条件下每个 key 的最大需求次数（跳过 'any'）。"""
    max_required = {}
    for group in groups or []:
        required = _group_required_counts(group)
        for key, count in required.items():
            prev = max_required.get(key, 0)
            if count > prev:
                max_required[key] = count
    return max_required


def find_target_hits(region, groups, picture_dir, threshold=MATCH_THRESHOLD, min_distance=MIN_MATCH_DISTANCE):
    """
    在 region 内统计“目标集”(groups 中出现过的 key)的命中次数。
    为避免日志噪音，单个 key 的返回次数会被截断到该 key 在各组中的最大需求次数。
    :return: dict[str, int]，仅包含命中次数 > 0 的 key
    """
    picture_dir = Path(picture_dir)
    max_required = _max_required_counts(groups)
    hits = {}
    for key, cap in max_required.items():
        img_path = picture_dir / f"{key}.png"
        positions = find_image_positions(region, img_path, threshold, min_distance)
        n = len(positions)
        if n <= 0:
            continue
        hits[key] = n if n < cap else cap
    return hits


def check_group_satisfied(region, group, picture_dir, threshold=MATCH_THRESHOLD, min_distance=MIN_MATCH_DISTANCE):
    """
    检查某一组终止条件是否满足：在 region 内找到每组要求的次数（不同位置）。
    例如 group=["str8","str8","str6"] 表示需要 str8 两处、str6 一处。
    """
    required = _group_required_counts(group)
    if not required:
        return True
    picture_dir = Path(picture_dir)
    for key, count in required.items():
        img_path = picture_dir / f"{key}.png"
        positions = find_image_positions(region, img_path, threshold, min_distance)
        if len(positions) < count:
            return False
    return True


def check_green_found(region, picture_dir, threshold=MATCH_THRESHOLD):
    """在 region 内是否找到 picture/green.png（上绿终止条件）。"""
    path = Path(picture_dir) / "green.png"
    positions = find_image_positions(region, path, threshold=threshold, min_distance=MIN_MATCH_DISTANCE)
    return len(positions) > 0


def check_any_termination_satisfied(region, groups, picture_dir, threshold=MATCH_THRESHOLD, min_distance=MIN_MATCH_DISTANCE):
    """
    多组终止条件为或逻辑：任一组满足即返回该组，否则返回 None。
    :param groups: 如 [["str8","str8","str6"], ["str8","str8","str2"]]
    :return: 第一个满足的 group（列表），都不满足返回 None
    """
    picture_dir = Path(picture_dir)
    for group in groups:
        if check_group_satisfied(region, group, picture_dir, threshold, min_distance):
            return group
    return None
