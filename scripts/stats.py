#!/usr/bin/env python3
"""stats 命令入口：分布与业务规则统计。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evaltools.stats import main
if __name__ == "__main__":
    raise SystemExit(main())
