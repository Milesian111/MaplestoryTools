"""
运行此脚本可将 party.py 打包为 exe（Party 组队 GUI）。

参考 MonsterCard 的打包方式：
- 单文件：--onefile
- 无控制台：--windowed
- 管理员启动：--uac-admin
- 包含 picture 资源：--add-data=picture;picture

首次运行时程序会把打包内 picture 资源复制到 exe 同目录（可写），以支持“覆盖/保存截图模板”功能。
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path


PARTY_DIR = Path(__file__).resolve().parent
VERSION_FILE = PARTY_DIR / "build_version.txt"


def get_version() -> str:
    if VERSION_FILE.exists():
        raw = VERSION_FILE.read_text(encoding="utf-8").strip()
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", raw)
        if m:
            return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return "0.0.1"


def bump_version() -> None:
    if VERSION_FILE.exists():
        raw = VERSION_FILE.read_text(encoding="utf-8").strip()
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", raw)
        if m:
            a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
            VERSION_FILE.write_text(f"{a}.{b}.{c + 1}\n", encoding="utf-8")
            return
    VERSION_FILE.write_text("0.0.2\n", encoding="utf-8")


VERSION = get_version()
NAME = f"好厉害组队v{VERSION}"

ENTRY = "party.py"
PROJECT_ROOT = PARTY_DIR.parent

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",
    "--windowed",
    "--uac-admin",
    "--hidden-import=keyboard",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--add-data=picture;picture",
    f"--paths={PROJECT_ROOT}",
    "--clean",
    f"--name={NAME}",
    str(PARTY_DIR / ENTRY),
]

result = subprocess.run(cmd, cwd=str(PARTY_DIR))

if result.returncode == 0:
    bump_version()
    build_dir = PARTY_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("已删除 build 文件夹")
    for spec in PARTY_DIR.glob("*.spec"):
        spec.unlink()
        print(f"已删除 {spec.name}")
    print(f"打包成功！版本号已更新为下次打包准备。")
    print(f"exe 输出在 dist/{NAME}.exe")
else:
    print("打包失败，版本号未更新。")

