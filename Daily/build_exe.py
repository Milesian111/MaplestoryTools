"""
运行此脚本可将 build_sweep_execution.py 打包为 exe（Daily 扫荡任务）。
需要先安装（请用与运行本脚本相同的 Python）：python -m pip install pyinstaller keyboard
在 Daily 目录下执行：python build_exe.py
每次运行会将版本号 +1（如 0.0.1 -> 0.0.2），并写入 build_version.txt 供下次使用。
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

# 若未安装 PyInstaller，给出明确提示（避免 pip 装到别的 Python）
try:
    import PyInstaller
except ImportError:
    print("未检测到 PyInstaller，请用【当前运行本脚本的 Python】执行：")
    print(f"  {sys.executable} -m pip install pyinstaller keyboard")
    sys.exit(1)

# Daily 目录（本脚本所在目录）
DAILY_DIR = Path(__file__).resolve().parent
VERSION_FILE = DAILY_DIR / "build_version.txt"

# 项目根目录，用于 --paths 以便打包 Utils
PROJECT_ROOT = DAILY_DIR.parent


def get_version():
    if VERSION_FILE.exists():
        raw = VERSION_FILE.read_text(encoding="utf-8").strip()
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", raw)
        if m:
            return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return "0.0.1"


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
NAME = f"好扫货v{VERSION}"

ENTRY = "build_sweep_execution.py"

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",
    "--windowed",  # GUI 无控制台
    "--uac-admin",
    "--hidden-import=keyboard",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    f"--paths={PROJECT_ROOT}",  # 打包 Utils 等依赖
    "--add-data=picture;picture",
    f"--icon={DAILY_DIR / 'icon' / 'icon.png'}",
    f"--name={NAME}",
    "--clean",
    str(DAILY_DIR / ENTRY),
]

result = subprocess.run(cmd, cwd=str(DAILY_DIR))

if result.returncode == 0:
    bump_version()
    build_dir = DAILY_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("已删除 build 文件夹")
    for spec in DAILY_DIR.glob("*.spec"):
        spec.unlink()
        print(f"已删除 {spec.name}")
    print("打包成功！版本号已更新为下次打包准备。")
    print(f"exe 输出在 dist/{NAME}.exe")
else:
    print("打包失败，版本号未更新。")
