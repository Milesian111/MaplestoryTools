"""
运行此脚本可将 build_monster_execution.py 打包为 exe。
需要先安装：pip install pyinstaller keyboard
在 Cube 目录下执行：python build_exe.py
（keyboard 用于全局 F11/F12 热键，未安装则仅窗口内有效）
每次运行会将版本号 +1（如 0.0.1 -> 0.0.2），并写入 build_version.txt 供下次使用。
"""
import re
import subprocess
import sys
from pathlib import Path

# Cube 目录（本脚本所在目录）
CUBE_DIR = Path(__file__).resolve().parent
VERSION_FILE = CUBE_DIR / "build_version.txt"

# 读当前版本（格式 0.0.1）
def get_version():
    if VERSION_FILE.exists():
        raw = VERSION_FILE.read_text(encoding="utf-8").strip()
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", raw)
        if m:
            return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    # 首次或无效：使用 0.0.1
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
NAME = f"好怪魔方v{VERSION}"

# Windows 下 PyInstaller --add-data 用分号，多个数据目录需要分别指定
ENTRY = "build_monster_execution.py"

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",           # 单文件 exe
    "--windowed",          # 无控制台窗口（GUI 程序）
    "--uac-admin",         # 默认以管理员权限启动（UAC 会弹窗确认）
    "--hidden-import=keyboard",  # 全局热键，需一并打包
    "--add-data=picture;picture",  # 打包picture目录
    "--add-data=sound;sound",      # 打包sound目录
    f"--name={NAME}",
    "--clean",
    str(CUBE_DIR / ENTRY),
]

# 执行打包
result = subprocess.run(cmd, cwd=str(CUBE_DIR))

# 打包完成后再修改版本号
if result.returncode == 0:
    bump_version()
    print(f"打包成功！版本号已更新为下次打包准备。")
else:
    print(f"打包失败，版本号未更新。")
