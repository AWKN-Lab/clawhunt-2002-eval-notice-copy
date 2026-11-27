#!/usr/bin/env python3
"""演示：依次跑 eval-lint、eval-pii-scan、stats、eval-run，打印每步结论。

只用 echo mock，不调真实模型与真实接口；报告写到 reports/（运行产物，不进仓）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suites" / "ops_assist.event_copy"


def run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    return proc.returncode


def main() -> int:
    steps = [
        ("eval-lint", [sys.executable, "scripts/eval-lint", str(SUITE)]),
        ("eval-pii-scan", [sys.executable, "scripts/eval-pii-scan", str(SUITE)]),
        ("stats", [sys.executable, "scripts/stats.py", str(SUITE)]),
        ("eval-run", [sys.executable, "scripts/eval-run", str(SUITE), "--out", "reports"]),
    ]
    for name, cmd in steps:
        print("== demo: %s ==" % name)
        if run(cmd) != 0:
            print("DEMO: FAIL（%s 未通过）" % name)
            return 1
    cases = [json.loads(line) for line in
             (SUITE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    print("== demo: 抽样展示 ==")
    for key in ("regular-miniapp-public-01", "missing-guests-01", "conflict-01", "fee-03"):
        case = next(c for c in cases if c["case_key"] == key)
        print("--- %s（%s / %s）---" % (key, case["input"]["channel"], case["input"]["event_type"]))
        print(case["reference_output"])
    print("DEMO: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
