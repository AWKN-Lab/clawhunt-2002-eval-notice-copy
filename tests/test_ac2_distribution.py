"""AC2（本单口径）：4 类分布与说明一致，每条要点 3-6 条且至少 1 条 must=true。"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suites" / "ops_assist.event_copy"


def load_cases():
    text = (SUITE / "cases.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_distribution_matches_spec():
    dist = Counter(c["tags"][0] for c in load_cases())
    assert dict(dist) == {"regular": 24, "missing-info": 8, "conflict": 4, "fee": 4}


def test_regular_covers_channels_and_types():
    regs = [c for c in load_cases() if c["tags"] == ["regular"]]
    assert Counter(c["input"]["channel"] for c in regs) == {
        "小程序活动简介": 6, "社群群发": 6, "推文摘要": 6, "站内信": 6}
    assert Counter(c["input"]["event_type"] for c in regs) == {
        "公开": 8, "会员专享": 8, "闭门会": 8}


def test_points_count_and_must():
    for case in load_cases():
        pts = case["expected_points"]
        assert 3 <= len(pts) <= 6, case["case_key"]
        assert any(p["must"] for p in pts), case["case_key"]
        assert len({p["id"] for p in pts}) == len(pts), case["case_key"]


def test_stats_passes():
    proc = subprocess.run([sys.executable, "scripts/stats.py", str(SUITE)],
                          cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stdout
    assert "stats: PASS" in proc.stdout
    assert "regular：24 条" in proc.stdout
    assert "missing-info：8 条" in proc.stdout
    assert "conflict：4 条" in proc.stdout
    assert "fee：4 条" in proc.stdout
