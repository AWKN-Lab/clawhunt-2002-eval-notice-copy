"""lint 细节：非法夹具必须被拦，且报错指到具体规则。"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suites" / "ops_assist.event_copy"


def load_cases():
    text = (SUITE / "cases.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def mutated_suite(tmp_path, mutate):
    suite = tmp_path / "ops_assist.event_copy"
    shutil.copytree(SUITE, suite)
    cases = load_cases()
    mutate(cases)
    (suite / "cases.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
    return suite


def run_lint(suite):
    return subprocess.run([sys.executable, "scripts/eval-lint", str(suite)],
                          cwd=ROOT, text=True, capture_output=True)


def run_pii(suite):
    return subprocess.run([sys.executable, "scripts/eval-pii-scan", str(suite)],
                          cwd=ROOT, text=True, capture_output=True)


def test_missing_placeholder_fails_lint(tmp_path):
    def mutate(cases):
        miss = next(c for c in cases if c["tags"] == ["missing-info"])
        miss["reference_output"] = miss["reference_output"].replace("【待补充】", "待定")
    proc = run_lint(mutated_suite(tmp_path, mutate))
    assert proc.returncode != 0
    assert "待补充" in proc.stdout


def test_no_must_fails_lint(tmp_path):
    def mutate(cases):
        for p in cases[0]["expected_points"]:
            p["must"] = False
    proc = run_lint(mutated_suite(tmp_path, mutate))
    assert proc.returncode != 0
    assert "must=true" in proc.stdout


def test_count_mismatch_fails_lint(tmp_path):
    def mutate(cases):
        cases.pop()
    proc = run_lint(mutated_suite(tmp_path, mutate))
    assert proc.returncode != 0
    assert "expected_count" in proc.stdout


def test_closed_door_guest_name_fails_lint(tmp_path):
    def mutate(cases):
        closed = next(c for c in cases if c["input"]["event_type"] == "闭门会")
        name = closed["input"]["guests"][0].replace("（虚构）", "")
        closed["reference_output"] += "嘉宾%s到场。" % name
    proc = run_lint(mutated_suite(tmp_path, mutate))
    assert proc.returncode != 0
    assert "嘉宾" in proc.stdout


def test_fee_discount_word_fails_pii(tmp_path):
    def mutate(cases):
        fee = next(c for c in cases if c["tags"] == ["fee"])
        fee["reference_output"] += "合计 200 元。"
    proc = run_pii(mutated_suite(tmp_path, mutate))
    assert proc.returncode != 0
    assert "合计" in proc.stdout or "金额" in proc.stdout


def test_conflict_over_limit_fails_lint(tmp_path):
    def mutate(cases):
        conf = next(c for c in cases if c["tags"] == ["conflict"])
        conf["reference_output"] += "欢迎带朋友一起来参加本次活动，现场还有茶歇。"
    proc = run_lint(mutated_suite(tmp_path, mutate))
    assert proc.returncode != 0
    assert "超上限" in proc.stdout
