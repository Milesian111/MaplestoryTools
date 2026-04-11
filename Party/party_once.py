# -*- coding: utf-8 -*-
"""
基于 party.py 的精简挂机：监控逻辑与 PartyApp 相同，但
- 一旦识别到「光谱地图」或「光谱退场」：不执行连招/退出流程，直接停止挂机；
- 不写 party.log 文件。

运行：在 Party 目录下执行  python party_once.py
（依赖与 party.py 相同）
"""
from __future__ import annotations

from party import PartyApp, SEARCH_RECT, match_template_in_rect


class PartyOnceApp(PartyApp):
    """光谱地图 / 光谱退场优先检测；命中后直接 stop_monitoring；无日志文件。"""

    def _log_line(self, msg: str) -> None:
        pass

    def show_log_detail(self) -> None:
        self.messagebox.showinfo("提示", "本模式不写入日志文件。")

    def _bot_tick_once(self) -> None:
        r = SEARCH_RECT
        tol = self.tolerance

        def find_scene(name: str) -> bool:
            return match_template_in_rect(r, self._template_path(name), tol) is not None

        if find_scene("光谱地图"):
            self.stop_monitoring("状态：🌈 识别光谱地图，已停止任务")
            return
        if find_scene("光谱退场"):
            self.stop_monitoring("状态：🚨 识别光谱退场，已停止任务")
            return
        if self._bot_tick_scene_chain(find_scene):
            return
        self.status_var.set("状态：🔍 监控中 (0,0)–(1366,768)...")


def main() -> None:
    app = PartyOnceApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()
