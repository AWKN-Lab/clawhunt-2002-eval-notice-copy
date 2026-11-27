"""eval-pii-scan 核心：检查评测集里的个人信息与费用计算。

检查项（错误一律带 cases.jsonl:行号，退出码非 0）：
  1. 全文不得出现真实个人信息形态：11 位手机号、邮箱、18 位身份证号、
     16-19 位银行卡号（本套件只用「虚构嘉宾 + 示例空间」这类虚构信息）。
  2. 每条 reference_output 不得含折扣/合计类词（不得计算折扣或合计）。
  3. 每条 reference_output 除 fee_text 原样引用外，不得含具体金额
     （数字 + 元/¥/人民币/块钱）；含费用类草稿里的金额只能来自 fee_text。
  4. 每条用例至少有一条 forbidden_point；含费用类须有「不得计算折扣或合计」。
"""
from __future__ import annotations

import sys
from pathlib import Path

from evaltools.common import (
    AMOUNT_RE, BANK_RE, DISCOUNT_WORDS, EMAIL_RE, ID_RE, PHONE_RE,
    load_cases, resolve_suite,
)

PII_CHECKS = [
    ("手机号", PHONE_RE),
    ("邮箱", EMAIL_RE),
    ("身份证号", ID_RE),
    ("银行卡号", BANK_RE),
]


def scan_suite(suite_path: str) -> list[str]:
    _, cases_path = resolve_suite(Path(suite_path))
    errors: list[str] = []
    if not cases_path.is_file():
        return ["%s: 缺 cases.jsonl" % cases_path]
    text = cases_path.read_text(encoding="utf-8")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        for label, pattern in PII_CHECKS:
            if pattern.search(raw):
                errors.append("%s:%d: 疑似真实%s" % (cases_path.name, lineno, label))
    cases, parse_errors = load_cases(cases_path)
    errors.extend(parse_errors)
    for lineno, case in cases:
        tag = "%s:%d" % (cases_path.name, lineno)
        ref = case.get("reference_output")
        if not isinstance(ref, str):
            continue
        if any(w in ref for w in DISCOUNT_WORDS):
            errors.append("%s: reference_output 含折扣/合计类词" % tag)
        fee = (case.get("input") or {}).get("fee_text")
        check_text = ref.replace(fee, "", 1) if isinstance(fee, str) and fee else ref
        if AMOUNT_RE.search(check_text):
            errors.append("%s: reference_output 含 fee_text 以外的具体金额" % tag)
        forb = case.get("forbidden_points")
        if not isinstance(forb, list) or not forb:
            errors.append("%s: forbidden_points 为空" % tag)
        elif (case.get("tags") or [None])[0] == "fee" and "不得计算折扣或合计" not in forb:
            errors.append("%s: 含费用类 forbidden_points 缺「不得计算折扣或合计」" % tag)
    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("用法：eval-pii-scan <套件目录或 cases.jsonl 路径>", file=sys.stderr)
        return 2
    errors = scan_suite(args[0])
    if errors:
        for e in errors:
            print(e)
        print("eval-pii-scan: FAIL（%d 个 error）" % len(errors))
        return 1
    print("eval-pii-scan: PASS（0 error）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
