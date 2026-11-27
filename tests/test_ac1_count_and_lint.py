"""AC1：cases.jsonl 恰有 40 条，eval-lint 校验通过，eval-pii-scan 无 error。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suites" / "ops_assist.event_copy"


def load_cases():
    text = (SUITE / "cases.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_cases_count_is_40():
    assert len(load_cases()) == 40


def test_eval_lint_passes():
    proc = subprocess.run([sys.executable, "scripts/eval-lint", str(SUITE)],
                          cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stdout
    assert "eval-lint: PASS" in proc.stdout


def test_eval_pii_scan_no_error():
    proc = subprocess.run([sys.executable, "scripts/eval-pii-scan", str(SUITE)],
                          cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stdout
    assert "eval-pii-scan: PASS" in proc.stdout
    assert "0 error" in proc.stdout


def test_case_keys_unique_kebab():
    import re
    keys = [c["case_key"] for c in load_cases()]
    assert len(set(keys)) == 40
    assert all(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", k) for k in keys)
