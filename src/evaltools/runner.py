"""eval-run 核心：用 echo mock 跑通评测并生成报告。

mock 方式：被测工具的输出直接取每条用例的 reference_output（echo），
不调任何真实模型与真实接口；评分只做机器可判的四类要点：
  - keyword：要点 keywords 全出现在 mock 草稿里；
  - length：mock 草稿去空白后字数在 max_chars 内；
  - placeholder：mock 草稿含【待补充】；
  - absent：要点 keywords 全不在 mock 草稿里。
用例通过条件：全部 must 要点通过。通过率达到 suite.yaml 的
pass_threshold 即整套通过，退出码 0；否则非 0。
报告写到 --out 目录（默认 reports/）：eval-report.json 与 eval-report.md。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evaltools.common import PLACEHOLDER, compact, load_cases, parse_suite_yaml, resolve_suite


def score_point(point: dict, mock: str) -> bool:
    ptype = point.get("type")
    if ptype == "keyword":
        kws = point.get("keywords") or []
        return isinstance(mock, str) and all(k in mock for k in kws)
    if ptype == "length":
        mc = point.get("max_chars")
        return isinstance(mc, int) and len(compact(mock)) <= mc
    if ptype == "placeholder":
        return PLACEHOLDER in mock
    if ptype == "absent":
        kws = point.get("keywords") or []
        return isinstance(mock, str) and all(k not in mock for k in kws)
    return False


def run_suite(suite_path: str, out_dir: Path) -> tuple[dict, int]:
    suite_dir, cases_path = resolve_suite(Path(suite_path))
    meta = parse_suite_yaml(suite_dir / "suite.yaml")
    threshold = float(meta.get("pass_threshold", 0.8))
    cases, errors = load_cases(cases_path)
    if errors:
        raise RuntimeError("cases.jsonl 解析失败：%s" % "; ".join(errors))
    results = []
    for _, case in cases:
        mock = case.get("reference_output") or ""  # echo mock：原样回显标准答案
        failed = [p.get("id") for p in case.get("expected_points") or []
                  if p.get("must") and not score_point(p, mock)]
        results.append({"case_key": case.get("case_key"), "passed": not failed,
                        "failed_points": failed})
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    rate = passed / total if total else 0.0
    report = {
        "suite_key": meta.get("suite_key"),
        "version": meta.get("version"),
        "mock": "echo (reference_output)",
        "total": total,
        "passed": passed,
        "pass_rate": round(rate, 4),
        "pass_threshold": threshold,
        "overall_pass": rate >= threshold,
        "cases": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "eval-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# eval-run 报告（echo mock）", "",
             "- 套件：%s v%s" % (meta.get("suite_key"), meta.get("version")),
             "- 通过：%d/%d，通过率 %.2f，阈值 %.2f" % (passed, total, rate, threshold),
             "- 结论：%s" % ("通过" if rate >= threshold else "不通过"), "",
             "## 逐条结果", ""]
    for r in results:
        lines.append("- %s：%s" % (r["case_key"], "通过" if r["passed"] else
                                   "不通过（%s）" % "、".join(r["failed_points"])))
    (out_dir / "eval-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report, (0 if rate >= threshold else 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval-run")
    parser.add_argument("suite")
    parser.add_argument("--out", default="reports")
    args = parser.parse_args(argv)
    report, code = run_suite(args.suite, Path(args.out))
    print("eval-run: %d/%d 通过，通过率 %.2f" % (report["passed"], report["total"], report["pass_rate"]))
    print("eval-run: %s" % ("PASS" if code == 0 else "FAIL"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
