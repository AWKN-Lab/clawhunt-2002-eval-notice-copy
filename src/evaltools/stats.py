"""分布统计脚本核心：输出 4 类分布、要点口径与三类业务规则核对。

通过条件：regular 24、missing-info 8、conflict 4、fee 4；每条要点 3-6 条
且至少 1 条 must=true；信息缺失类草稿含【待补充】；限制冲突类草稿字数
在上限内；含费用类草稿原样引用 fee_text；闭门会草稿不出现嘉宾姓名。
退出码 0 为通过，非 0 为不通过。
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from evaltools.common import (
    DISTRIBUTION, PLACEHOLDER, compact, date_cn, deadline_cn, guest_short,
    load_cases, resolve_suite,
)


def stats_suite(suite_path: str) -> tuple[list[str], bool]:
    _, cases_path = resolve_suite(Path(suite_path))
    lines: list[str] = []
    ok = True
    cases, errors = load_cases(cases_path)
    if errors:
        return errors, False
    counts: Counter = Counter()
    bad_points: list[str] = []
    missing_bad: list[str] = []
    conflict_bad: list[str] = []
    fee_bad: list[str] = []
    closed_bad: list[str] = []
    for _, case in cases:
        kind = (case.get("tags") or [None])[0]
        counts[kind] += 1
        pts = case.get("expected_points") or []
        if not 3 <= len(pts) <= 6 or not any(p.get("must") for p in pts):
            bad_points.append(case.get("case_key", "?"))
        ref = case.get("reference_output") or ""
        inp = case.get("input") or {}
        if kind == "missing-info" and PLACEHOLDER not in ref:
            missing_bad.append(case.get("case_key", "?"))
        if kind == "conflict":
            wl = inp.get("word_limit")
            if not isinstance(wl, int) or len(compact(ref)) > wl:
                conflict_bad.append(case.get("case_key", "?"))
        if kind == "fee":
            fee = inp.get("fee_text")
            if not isinstance(fee, str) or fee not in ref:
                fee_bad.append(case.get("case_key", "?"))
        if inp.get("event_type") == "闭门会":
            names = [guest_short(g) for g in inp.get("guests") or []]
            if any(n in ref for n in names):
                closed_bad.append(case.get("case_key", "?"))
    lines.append("4 类分布（共 %d 条）：" % len(cases))
    for kind, want in DISTRIBUTION.items():
        got = counts.get(kind, 0)
        lines.append("  %s：%d 条（说明 %d 条）" % (kind, got, want))
        if got != want:
            ok = False
    lines.append("每条要点 3-6 条且至少 1 条 must=true：%s"
                 % ("是" if not bad_points else "否（%s）" % "、".join(bad_points)))
    lines.append("信息缺失类草稿含【待补充】：%s"
                 % ("是" if not missing_bad else "否（%s）" % "、".join(missing_bad)))
    lines.append("限制冲突类草稿字数在上限内：%s"
                 % ("是" if not conflict_bad else "否（%s）" % "、".join(conflict_bad)))
    lines.append("含费用类草稿原样引用 fee_text：%s"
                 % ("是" if not fee_bad else "否（%s）" % "、".join(fee_bad)))
    lines.append("闭门会草稿不出现嘉宾姓名：%s"
                 % ("是" if not closed_bad else "否（%s）" % "、".join(closed_bad)))
    if bad_points or missing_bad or conflict_bad or fee_bad or closed_bad:
        ok = False
    return lines, ok


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("用法：stats <套件目录或 cases.jsonl 路径>", file=sys.stderr)
        return 2
    lines, ok = stats_suite(args[0])
    for line in lines:
        print(line)
    print("stats: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
