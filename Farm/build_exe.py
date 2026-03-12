"""
运行此脚本可将 build_ball_execution.py 打包为 exe。
需要先安装：pip install pyinstaller keyboard
在 Farm 目录下执行：python build_exe.py
（keyboard 用于卡球热键；可选 pynput 用于鼠标键）
每次运行会将版本号 +1（如 0.0.1 -> 0.0.2），并写入 build_version.txt 供下次使用。
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Farm 目录（本脚本所在目录）
FARM_DIR = Path(__file__).resolve().parent
VERSION_FILE = FARM_DIR / "build_version.txt"

# 读当前版本（格式 0.0.1）
def get_version():
    if VERSION_FILE.exists():
        raw = VERSION_FILE.read_text(encoding="utf-8").strip()
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", raw)
        if m:
            return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return "0.0.1"

# 版本号 +1 写回
def bump_version():
    if VERSION_FILE.exists():
        raw = VERSION_FILE.read_text(encoding="utf-8").strip()
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", raw)
        if m:
            a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
            next_ver = f"{a}.{b}.{c + 1}"
            VERSION_FILE.write_text(next_ver + "\n", encoding="utf-8")
        else:
            VERSION_FILE.write_text("0.0.2\n", encoding="utf-8")
    else:
        VERSION_FILE.write_text("0.0.2\n", encoding="utf-8")

VERSION = get_version()
NAME = f"好球v{VERSION}"

ENTRY = "build_ball_execution.py"

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",
    "--windowed",
    "--uac-admin",
    "--hidden-import=keyboard",
    "--hidden-import=pynput",
    "--hidden-import=pynput.mouse",
    f"--name={NAME}",
    "--clean",
    str(FARM_DIR / ENTRY),
]

# exe 图标
icon_path = FARM_DIR / "icon" / "icon.png"
if icon_path.exists():
    cmd.insert(-1, f"--icon={icon_path}")

result = subprocess.run(cmd, cwd=str(FARM_DIR))

if result.returncode == 0:
    bump_version()
    build_dir = FARM_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("已删除 build 文件夹")
    for spec in FARM_DIR.glob("*.spec"):
        spec.unlink()
        print(f"已删除 {spec.name}")
    print("打包成功！版本号已更新为下次打包准备。")
else:
    print("打包失败，版本号未更新。")
