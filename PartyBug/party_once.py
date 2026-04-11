# -*- coding: utf-8 -*-
"""入口转发到 Party/party_once.py（便于从 PartyBug 目录启动）。"""
from __future__ import annotations

import sys
from pathlib import Path

_PARTY = Path(__file__).resolve().parent.parent / "Party"
if str(_PARTY) not in sys.path:
    sys.path.insert(0, str(_PARTY))

from party_once import main  # noqa: E402

if __name__ == "__main__":
    main()
