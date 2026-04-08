"""
Fire 主逻辑：按“终止条件组”找图，任一组满足即停止；否则双空格并等待。
GUI 入口见 build_fire_execution.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import pyautogui

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import keyboard  # type: ignore
    HAS_KEYBOARD = True
except Exception:  # pragma: no cover
    keyboard = None
    HAS_KEYBOARD = False

try:
    import winsound
    HAS_WINSOUND = True
except Exception:  # pragma: no cover
    winsound = None
    HAS_WINSOUND = False

from Utils.find_image import get_image_center


def _press_space_twice() -> None:
    try:
        if HAS_KEYBOARD and keyboard is not None:
            keyboard.press_and_release("space")
            time.sleep(0.1)
            keyboard.press_and_release("space")
            return
    except Exception:
        pass
    try:
        pyautogui.press("space")
        time.sleep(0.1)
        pyautogui.press("space")
    except Exception:
        pass


def _beep_found() -> None:
    try:
        if HAS_WINSOUND and winsound is not None:
            winsound.Beep(1000, 300)
    except Exception:
        pass


def _search_rect_fullscreen() -> tuple[int, int, int, int]:
    w, h = pyautogui.size()
    return 0, 0, int(w), int(h)


def _picture_dir(fire_dir: Path) -> Path:
    return fire_dir / "picture"


def activate_window_by_flag(fire_dir: Path, offset_y: int = 50) -> bool:
    """先找 flag.png，找到后点击中心下方 offset_y 像素，用于激活窗口。"""
    rect = _search_rect_fullscreen()
    pic_dir = _picture_dir(Path(fire_dir))
    flag = pic_dir / "flag.png"
    if not flag.is_file():
        return False
    center = get_image_center(rect, flag)
    if center is None:
        return False
    pyautogui.click(center[0], center[1] + int(offset_y))
    time.sleep(0.2)
    return True


def _found(pic_dir: Path, rect: tuple[int, int, int, int], key: str) -> bool:
    p = pic_dir / f"{key}.png"
    if not p.is_file():
        return False
    return get_image_center(rect, p) is not None


def check_group_satisfied(pic_dir: Path, rect: tuple[int, int, int, int], group: list[str]) -> bool:
    """一组条件满足：组内每个 key 都能在屏幕上找到。"""
    for key in group:
        if key == "any":
            continue
        if not _found(pic_dir, rect, key):
            return False
    return True


def check_any_group_satisfied(pic_dir: Path, rect: tuple[int, int, int, int], groups: list[list[str]]) -> Optional[list[str]]:
    for g in groups or []:
        if check_group_satisfied(pic_dir, rect, g):
            return g
    return None


def find_target_hits(pic_dir: Path, rect: tuple[int, int, int, int], groups: list[list[str]]) -> list[str]:
    """统计本轮“目标集”(groups 内出现过的 key)命中了哪些。"""
    targets: list[str] = []
    seen = set()
    for g in groups or []:
        for key in g:
            if key == "any":
                continue
            if key in seen:
                continue
            seen.add(key)
            targets.append(key)
    hits: list[str] = []
    for key in targets:
        if _found(pic_dir, rect, key):
            hits.append(key)
    return hits


def run_fire_loop(
    stop_event,
    status_callback,
    log_callback=None,
    equipment_type: Optional[str] = None,
    termination_groups: Optional[list[list[str]]] = None,
    fire_dir: Optional[Path] = None,
) -> None:
    """
    主循环：
    - 先激活窗口（flag.png 点击中心下方50）
    - 每轮检查任一组终止条件是否满足
    - 未满足：双空格 + 等待0.5秒
    - 满足：beep 0.3秒，停止
    """
    if log_callback is None:
        log_callback = lambda _m: None
    fire_dir = Path(fire_dir or Path(__file__).resolve().parent)
    pic_dir = _picture_dir(fire_dir)
    rect = _search_rect_fullscreen()

    pyautogui.FAILSAFE = True
    try:
        log_callback("激活窗口…")
        while not stop_event.is_set():
            if activate_window_by_flag(fire_dir, offset_y=50):
                break
            time.sleep(0.3)
        if stop_event.is_set():
            status_callback("已手动停止")
            return

        n = 0
        equip = (equipment_type or "").strip()
        while not stop_event.is_set():
            n += 1
            if not termination_groups:
                log_callback(f"第{n}次，未设置终止条件，请在选择属性中添加")
                _press_space_twice()
                time.sleep(0.5)
                continue

            # 武器特殊规则：必须同时命中 +28.png 才算满足终止条件
            groups = termination_groups
            if equip == "武器":
                groups = [[*g, "+28"] if "+28" not in g else list(g) for g in (termination_groups or [])]

            satisfied = check_any_group_satisfied(pic_dir, rect, groups)
            if satisfied is not None:
                log_callback(f"第{n}次，命中：[{', '.join(satisfied)}]，停止")
                _beep_found()
                status_callback("已命中终止条件，任务结束")
                return

            hits = find_target_hits(pic_dir, rect, groups)
            if hits:
                log_callback(f"第{n}次，找到：{', '.join(hits)}")
            else:
                log_callback(f"第{n}次，未找到目标属性")

            _press_space_twice()
            time.sleep(0.5)

        status_callback("已手动停止")
    except Exception as e:
        status_callback(f"运行出错: {e}")
        log_callback(str(e))

