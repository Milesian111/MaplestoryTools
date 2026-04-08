from __future__ import annotations

import sys
import time
from pathlib import Path

import pyautogui

try:
    import keyboard  # type: ignore
except Exception:  # pragma: no cover
    keyboard = None

try:
    import winsound
except Exception:  # pragma: no cover
    winsound = None

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Utils.find_image import get_image_center


def _press_space_twice() -> None:
    try:
        if keyboard is not None:
            keyboard.press_and_release("space")
            keyboard.press_and_release("space")
            return
    except Exception:
        pass
    try:
        pyautogui.press("space")
        pyautogui.press("space")
    except Exception:
        pass


def _search_rect_fullscreen() -> tuple[int, int, int, int]:
    w, h = pyautogui.size()
    return 0, 0, int(w), int(h)


def _picture_dir(base_dir: Path) -> Path:
    return base_dir / "picture"


def _activate_window_by_flag(pic_dir: Path, rect: tuple[int, int, int, int]) -> bool:
    flag = pic_dir / "flag.png"
    if not flag.is_file():
        print(f"警告：未找到激活图 {flag}")
        return False
    center = get_image_center(rect, flag)
    if center is None:
        return False
    x, y = center[0], center[1] + 50
    pyautogui.click(x, y)
    time.sleep(0.2)
    return True


def _found(pic_dir: Path, rect: tuple[int, int, int, int], name: str) -> bool:
    p = pic_dir / f"{name}.png"
    if not p.is_file():
        return False
    return get_image_center(rect, p) is not None


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    pic_dir = _picture_dir(base_dir)
    rect = _search_rect_fullscreen()

    pyautogui.FAILSAFE = True

    print("开始：先找 flag.png 激活窗口…")
    # 持续等待直到激活成功（避免窗口没就位）
    while True:
        if _activate_window_by_flag(pic_dir, rect):
            break
        time.sleep(0.3)

    print("开始循环：找 str182 或 str133 或 (str84+all7)，否则双空格，等待0.5秒。")
    while True:
        hit_str182 = _found(pic_dir, rect, "str182")
        hit_str133 = _found(pic_dir, rect, "str133")
        hit_str84 = _found(pic_dir, rect, "str84")
        hit_all7 = _found(pic_dir, rect, "all7")

        if hit_str182 or hit_str133 or (hit_str84 and hit_all7):
            print("命中目标，停止。")
            try:
                if winsound is not None:
                    winsound.Beep(1000, 300)
            except Exception:
                pass
            return

        _press_space_twice()
        time.sleep(0.5)


if __name__ == "__main__":
    main()

