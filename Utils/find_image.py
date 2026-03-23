"""
通用工具：在指定区域内查找图片，可选点击图片中心。
cv2 读取模板失败时回退到 PIL。
"""
import contextlib
import os

import cv2
import numpy as np
import pyautogui
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 降低 OpenCV 自身日志；libpng 的 iCCP 警告仍可能走 C 库 stderr，见 _silence_stderr_fd
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    try:
        cv2.setLogLevel(0)
    except Exception:
        pass

MATCH_THRESHOLD = 0.99


@contextlib.contextmanager
def _silence_stderr_fd():
    """屏蔽 C 库（如 libpng）直接写入 stderr 的提示，例如 iCCP: known incorrect sRGB profile。"""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_err = os.dup(2)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(old_err, 2)
        os.close(old_err)
        os.close(devnull)


def _load_template_gray(img_path_str):
    """用 cv2 读取模板灰度图，失败则用 PIL。返回 numpy 灰度数组或 None。

    Windows 上 cv2.imread 对含中文等非 ASCII 路径会失败并打印乱码警告，
    故优先用 Path.read_bytes + imdecode；纯英文路径同样适用。
    """
    p = Path(img_path_str)
    if not p.is_file():
        return None
    try:
        with _silence_stderr_fd():
            data = np.frombuffer(p.read_bytes(), dtype=np.uint8)
            template = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        if template is not None:
            return template
    except Exception:
        pass
    try:
        with _silence_stderr_fd():
            template = cv2.imread(str(p.resolve()), cv2.IMREAD_GRAYSCALE)
        if template is not None:
            return template
    except Exception:
        pass
    if HAS_PIL:
        try:
            with _silence_stderr_fd():
                pil_img = Image.open(p)
            if pil_img.mode != "L":
                pil_img = pil_img.convert("L")
            return np.array(pil_img)
        except Exception:
            pass
    return None


def _find_image_center_with_score(region, path, threshold=MATCH_THRESHOLD):
    """
    在 region 内查找图片，返回 (中心坐标或None, 最高匹配值)。
    未找到时中心为 None，但始终返回当次匹配的最高分数（便于日志输出）。
    """
    img_path = Path(path)
    if not img_path.exists():
        return None, None
    img_path_str = str(img_path.resolve())
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width, height = x2 - x1, y2 - y1
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        template = _load_template_gray(img_path_str)
        if template is None or template.shape[0] > height or template.shape[1] > width:
            return None, None
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            return None, float(max_val)
        center_x = left + max_loc[0] + template.shape[1] // 2
        center_y = top + max_loc[1] + template.shape[0] // 2
        return (center_x, center_y), float(max_val)
    except Exception:
        return None, None


def _find_image_center(region, path, threshold=MATCH_THRESHOLD):
    """在 region 内查找图片，返回匹配位置的图片中心坐标，未找到返回 None。"""
    center, _ = _find_image_center_with_score(region, path, threshold)
    return center


def _find_image_topleft_with_score(region, path, threshold=MATCH_THRESHOLD):
    """在 region 内查找图片，返回 (左上角坐标或None, 最高匹配值)。"""
    img_path = Path(path)
    if not img_path.exists():
        return None, None
    img_path_str = str(img_path.resolve())
    x1, y1, x2, y2 = region
    left, top = x1, y1
    width, height = x2 - x1, y2 - y1
    try:
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screen_array = np.array(screenshot)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        template = _load_template_gray(img_path_str)
        if template is None or template.shape[0] > height or template.shape[1] > width:
            return None, None
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            return None, float(max_val)
        topleft_x = left + max_loc[0]
        topleft_y = top + max_loc[1]
        return (topleft_x, topleft_y), float(max_val)
    except Exception:
        return None, None


def _find_image_topleft(region, path, threshold=MATCH_THRESHOLD):
    """在 region 内查找图片，返回匹配位置的图片左上角坐标（屏幕坐标），未找到返回 None。"""
    topleft, _ = _find_image_topleft_with_score(region, path, threshold)
    return topleft


def find_image(region, path, threshold=MATCH_THRESHOLD):
    """
    在 region 范围内查找 path 指定的图片。
    :param region: (x1, y1, x2, y2) 搜索区域
    :param path: 模板图片路径
    :param threshold: 匹配阈值 (0~1)，默认 0.99
    :return: 找到返回 True，否则返回 False
    """
    return _find_image_center(region, path, threshold) is not None


def get_image_center(region, path, threshold=MATCH_THRESHOLD):
    """
    在 region 内查找 path 图片，返回匹配位置的图片中心坐标。
    :param region: (x1, y1, x2, y2) 搜索区域
    :param path: 模板图片路径
    :param threshold: 匹配阈值 (0~1)，默认 0.99
    :return: 找到返回 (x, y)，否则返回 None
    """
    return _find_image_center(region, path, threshold)


def get_image_topleft(region, path, threshold=MATCH_THRESHOLD):
    """在 region 内查找 path 图片，返回匹配位置的图片左上角坐标（屏幕坐标），未找到返回 None。"""
    return _find_image_topleft(region, path, threshold)


def get_image_topleft_with_score(region, path, threshold=MATCH_THRESHOLD):
    """在 region 内查找 path 图片，返回 (左上角或None, 最高匹配值)。"""
    return _find_image_topleft_with_score(region, path, threshold)


def find_image_and_click(region, path, threshold=MATCH_THRESHOLD):
    """
    在 region 内查找 path 图片，找到则点击图片中心。
    :return: 找到并点击返回 True，否则返回 False
    """
    center, _ = _find_image_center_with_score(region, path, threshold)
    if center is None:
        return False
    pyautogui.click(center[0], center[1])
    return True


def find_image_and_click_with_score(region, path, threshold=MATCH_THRESHOLD):
    """
    在 region 内查找 path 图片，找到则点击图片中心。
    :return: (是否找到并点击, 最高匹配值)。未找到时最高匹配值可能为 None（如文件不存在）。
    """
    center, max_val = _find_image_center_with_score(region, path, threshold)
    if center is None:
        return False, max_val
    pyautogui.click(center[0], center[1])
    return True, max_val


def find_image_with_score(region, path, threshold=MATCH_THRESHOLD):
    """
    在 region 内查找 path 图片。
    :return: (是否找到, 最高匹配值)。未找到时最高匹配值可能为 None。
    """
    center, max_val = _find_image_center_with_score(region, path, threshold)
    return center is not None, max_val
