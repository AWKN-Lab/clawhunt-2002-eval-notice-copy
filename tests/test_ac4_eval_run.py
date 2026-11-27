"""AC4：用 echo mock 适配器跑通一次 eval-run 并生成报告。"""
import json
from pathlib import Path

from evaltools.runner import run_suite, score_point

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suites" / "ops_assist.event_copy"


def test_eval_run_all_pass(tmp_path):
    report, code = run_suite(str(SUITE), tmp_path)
    assert code == 0
    assert report["total"] == 40
    assert report["passed"] == 40
    assert report["pass_rate"] == 1.0
    assert report["overall_pass"] is True
    assert (tmp_path / "eval-report.json").is_file()
    assert (tmp_path / "eval-report.md").is_file()
    saved = json.loads((tmp_path / "eval-report.json").read_text(encoding="utf-8"))
    assert saved["passed"] == 40
    assert all(c["passed"] for c in saved["cases"])


def test_score_point_types():
    assert score_point({"type": "keyword", "keywords": ["截止"]}, "报名截止12月3日") is True
    assert score_point({"type": "keyword", "keywords": ["截止"]}, "欢迎报名") is False
    assert score_point({"type": "length", "max_chars": 5}, "一二三四五") is True
    assert score_point({"type": "length", "max_chars": 5}, "一二三四五六") is False
    assert score_point({"type": "placeholder"}, "嘉宾：【待补充】") is True
    assert score_point({"type": "placeholder"}, "嘉宾：待定") is False
    assert score_point({"type": "absent", "keywords": ["陈教授"]}, "嘉宾名单不对外公布") is True
    assert score_point({"type": "absent", "keywords": ["陈教授"]}, "嘉宾陈教授") is False
