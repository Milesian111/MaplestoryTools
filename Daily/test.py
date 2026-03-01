import sys
import time
from pathlib import Path

import pyautogui

# 直接运行本脚本时，将项目根目录加入 path，以便导入 Utils（打包为 exe 时由入口脚本设置 path）
if not getattr(sys, "frozen", False):
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from Utils.find_image import find_image_and_click

BASE_DIR = Path(__file__).parent
SEARCH_REGION = (0, 0, 1920, 1080)

find_image_and_click(SEARCH_REGION, BASE_DIR / "picture/btn_done.png") or find_image_and_click(SEARCH_REGION, BASE_DIR / "picture/btn_free.png")