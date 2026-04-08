"""
运行此脚本可将 Fire GUI 打包为 exe。

打包参数：
- 单文件：--onefile
- 无控制台：--windowed
- 管理员启动：--uac-admin
- 资源目录：picture（存在就打包）
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
VERSION_FILE = PROJECT_DIR / "build_version.txt"


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


def main() -> None:
    version = get_version()
    name = f"好火花v{version}"
    entry = PROJECT_DIR / "build_fire_execution.py"
    project_root = PROJECT_DIR.parent
    icon_png = PROJECT_DIR / "icon" / "icon.png"

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
        f"--paths={project_root}",
        "--clean",
        f"--name={name}",
    ]

    # 资源目录：存在就打进去
    if (PROJECT_DIR / "picture").is_dir():
        cmd.append("--add-data=picture;picture")
    if (PROJECT_DIR / "icon").is_dir():
        cmd.append("--add-data=icon;icon")
    if icon_png.is_file():
        cmd.append(f"--icon={icon_png}")

    cmd.append(str(entry))

    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))

    if result.returncode == 0:
        bump_version()
        build_dir = PROJECT_DIR / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)
            print("已删除 build 文件夹")
        for spec in PROJECT_DIR.glob("*.spec"):
            spec.unlink()
            print(f"已删除 {spec.name}")
        print("打包成功！版本号已更新为下次打包准备。")
        print(f"exe 输出在 dist/{name}.exe")
    else:
        print("打包失败，版本号未更新。")


if __name__ == "__main__":
    main()

