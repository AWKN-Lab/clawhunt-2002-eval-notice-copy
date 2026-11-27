#!/usr/bin/env python3
"""变异自证：证明门禁会红（不是只会绿）。

A 相：原样跑 pytest，全过。
B1 相：把一条信息缺失类用例草稿里的【待补充】删掉，eval-lint 必须非 0，
       且报错含「待补充」。
B2 相：把一条用例的 must 全改 false，eval-lint 必须非 0，
       且报错含「must=true」。
B3 相：往一条闭门会用例草稿里塞一个嘉宾姓名，eval-lint 必须非 0，
       且报错含「嘉宾」。
B4 相：往一条含费用类用例草稿里加「合计 200 元」，eval-pii-scan 必须非 0。
C 相：恢复原样再跑 pytest，全过；cases.jsonl 的 SHA256 与 A 相前一致。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suites" / "ops_assist.event_copy"
CASES = SUITE / "cases.jsonl"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pytest() -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"],
                          cwd=ROOT, text=True, capture_output=True)


def run_lint(suite_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "scripts/eval-lint", str(suite_dir)],
                          cwd=ROOT, text=True, capture_output=True)


def run_pii(suite_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "scripts/eval-pii-scan", str(suite_dir)],
                          cwd=ROOT, text=True, capture_output=True)


def load() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_tmp(cases: list[dict]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="mut-"))
    suite = tmp / "ops_assist.event_copy"
    shutil.copytree(SUITE, suite)
    (suite / "cases.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
    return suite


def main() -> int:
    before = sha256(CASES)
    print("== mutation A: pytest 原样 ==")
    a = run_pytest()
    print(a.stdout.strip().splitlines()[-1] if a.stdout.strip() else a.stderr.strip()[-500:])
    if a.returncode != 0:
        print("MUTATION CHECK: FAIL（A 相 pytest 未过）")
        return 1

    cases = load()
    print("== mutation B1: 删【待补充】，lint 必须红 ==")
    c1 = json.loads(json.dumps(cases))
    miss = next(c for c in c1 if c["tags"] == ["missing-info"])
    miss["reference_output"] = miss["reference_output"].replace("【待补充】", "待定")
    suite1 = write_tmp(c1)
    r1 = run_lint(suite1)
    print("exit=%d" % r1.returncode)
    if r1.returncode == 0 or "待补充" not in r1.stdout:
        print("MUTATION CHECK: FAIL（B1 相 lint 未按预期报错）")
        return 1
    print("B1 拦住：%s" % [line for line in r1.stdout.splitlines() if "待补充" in line][0])

    print("== mutation B2: must 全改 false，lint 必须红 ==")
    c2 = json.loads(json.dumps(cases))
    for p in c2[0]["expected_points"]:
        p["must"] = False
    suite2 = write_tmp(c2)
    r2 = run_lint(suite2)
    print("exit=%d" % r2.returncode)
    if r2.returncode == 0 or "must=true" not in r2.stdout:
        print("MUTATION CHECK: FAIL（B2 相 lint 未按预期报错）")
        return 1
    print("B2 拦住：%s" % [line for line in r2.stdout.splitlines() if "must=true" in line][0])

    print("== mutation B3: 闭门会草稿塞嘉宾姓名，lint 必须红 ==")
    c3 = json.loads(json.dumps(cases))
    closed = next(c for c in c3 if c["input"]["event_type"] == "闭门会")
    name = closed["input"]["guests"][0].replace("（虚构）", "")
    closed["reference_output"] = closed["reference_output"] + "嘉宾%s到场。" % name
    suite3 = write_tmp(c3)
    r3 = run_lint(suite3)
    print("exit=%d" % r3.returncode)
    if r3.returncode == 0 or "嘉宾" not in r3.stdout:
        print("MUTATION CHECK: FAIL（B3 相 lint 未按预期报错）")
        return 1
    print("B3 拦住：%s" % [line for line in r3.stdout.splitlines() if "嘉宾" in line][0])

    print("== mutation B4: 费用草稿加「合计」，pii-scan 必须红 ==")
    c4 = json.loads(json.dumps(cases))
    fee = next(c for c in c4 if c["tags"] == ["fee"])
    fee["reference_output"] = fee["reference_output"] + "合计 200 元。"
    suite4 = write_tmp(c4)
    r4 = run_pii(suite4)
    print("exit=%d" % r4.returncode)
    if r4.returncode == 0:
        print("MUTATION CHECK: FAIL（B4 相 pii-scan 未按预期报错）")
        return 1
    print("B4 拦住：%s" % [line for line in r4.stdout.splitlines() if "合计" in line or "金额" in line][0])

    print("== mutation C: 恢复后 pytest 再过，cases.jsonl SHA 不变 ==")
    c = run_pytest()
    print(c.stdout.strip().splitlines()[-1] if c.stdout.strip() else c.stderr.strip()[-500:])
    if c.returncode != 0:
        print("MUTATION CHECK: FAIL（C 相 pytest 未过）")
        return 1
    after = sha256(CASES)
    print("cases.jsonl SHA256 前后一致：%s" % (before == after))
    if before != after:
        print("MUTATION CHECK: FAIL（cases.jsonl 被改动）")
        return 1
    print("MUTATION CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
