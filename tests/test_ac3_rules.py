"""AC3 相关业务规则：缺失占位、字数上限、费用原样引用、闭门会不列嘉宾。"""
import json
import re
from pathlib import Path

from evaltools.common import DISCOUNT_WORDS, PLACEHOLDER, compact, date_cn, deadline_cn

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suites" / "ops_assist.event_copy"


def load_cases():
    text = (SUITE / "cases.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def short(name):
    return name.replace("（虚构）", "")


def test_missing_info_placeholder_and_no_invention():
    miss = [c for c in load_cases() if c["tags"] == ["missing-info"]]
    assert len(miss) == 8
    for case in miss:
        inp, ref = case["input"], case["reference_output"]
        assert PLACEHOLDER in ref, case["case_key"]
        assert "不得编造缺失信息" in case["forbidden_points"]
        if not inp["guests"]:
            assert "嘉宾：【待补充】" in ref or "嘉宾【待补充】" in ref, case["case_key"]
        if inp["venue"] is None:
            assert "地点：【待补充】" in ref, case["case_key"]
        if inp["quota"] is None:
            assert re.search(r"名额[：]?【待补充】", ref), case["case_key"]


def test_conflict_word_limit_keeps_time_venue_deadline():
    conf = [c for c in load_cases() if c["tags"] == ["conflict"]]
    assert len(conf) == 4
    for case in conf:
        inp, ref = case["input"], case["reference_output"]
        assert len(compact(ref)) <= inp["word_limit"], case["case_key"]
        assert date_cn(inp["time"].split(" ")[0]) in ref
        assert inp["venue"] in ref
        assert deadline_cn(inp["deadline"]) in ref
        assert "优先保留时间、地点、截止时间" in case["forbidden_points"]


def test_fee_quoted_verbatim_no_computation():
    fees = [c for c in load_cases() if c["tags"] == ["fee"]]
    assert len(fees) == 4
    for case in fees:
        inp, ref = case["input"], case["reference_output"]
        assert inp["fee_text"] in ref, case["case_key"]
        assert not any(w in ref for w in DISCOUNT_WORDS), case["case_key"]
        assert "不得计算折扣或合计" in case["forbidden_points"]
        assert not re.search(r"合计\s*\d", ref)


def test_closed_door_no_guest_names():
    closed = [c for c in load_cases() if c["input"]["event_type"] == "闭门会"]
    assert len(closed) == 9  # 常规 8 + 含费用 1
    for case in closed:
        names = [short(g) for g in case["input"]["guests"]]
        assert all(n not in case["reference_output"] for n in names), case["case_key"]
        assert "不出现嘉宾名单" in case["forbidden_points"]


def test_no_real_personal_info_patterns():
    text = (SUITE / "cases.jsonl").read_text(encoding="utf-8")
    assert not re.search(r"1[3-9]\d{9}", text)
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    assert "示例空间" in text  # 场地一律虚构
