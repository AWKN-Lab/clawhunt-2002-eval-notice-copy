"""eval-lint 核心：校验 ops_assist.event_copy 套件的结构、分布与业务规则。

检查项（错误一律带 cases.jsonl:行号，退出码非 0）：
  1. suite.yaml 与 cases.jsonl 存在；条数等于 suite.yaml 的 expected_count（40）。
  2. 每行合法 JSON；case_key 为 kebab-case 且套件内唯一。
  3. 必填字段齐全：input 11 字段、expected_points、forbidden_points、reference_output。
  4. event_type 在 3 类枚举内；channel 在 4 渠道枚举内；tags 在白名单内。
  5. expected_points 3-6 条，id 唯一，must 为布尔值，至少 1 条 must=true；
     keyword 要点带非空 keywords 且全部出现在 reference_output 里；
     length 要点带 max_chars 整数且草稿去空白后字数在上限内；
     placeholder 要点要求草稿含【待补充】；absent 要点要求关键词全不在草稿里。
  6. 分布：regular 24、missing-info 8、conflict 4、fee 4。
  7. 信息缺失类：缺失字段在 input 里确为空（guests 空列表 / venue 为 null /
     quota 为 null），草稿含【待补充】，forbidden_points 含「不得编造缺失信息」。
  8. 限制冲突类：word_limit 非空，草稿去空白后字数在上限内，且含活动日期、
     场地全名、报名截止时间；forbidden_points 含「优先保留时间、地点、截止时间」。
  9. 含费用类：fee_text 非空且在草稿里原样出现，草稿不含折扣/合计类词；
     forbidden_points 含「不得计算折扣或合计」。
  10. 闭门会：草稿不出现任何嘉宾姓名；forbidden_points 含「不出现嘉宾名单」。
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from evaltools.common import (
    CASE_KEY_RE, CHANNELS, DISCOUNT_WORDS, DISTRIBUTION, EVENT_TYPES,
    PLACEHOLDER, POINT_TYPES, TAGS, compact, date_cn, deadline_cn,
    guest_short, load_cases, parse_suite_yaml, resolve_suite,
)


def lint_suite(suite_path: str) -> list[str]:
    suite_dir, cases_path = resolve_suite(Path(suite_path))
    errors: list[str] = []
    yaml_path = suite_dir / "suite.yaml"
    if not yaml_path.is_file():
        return ["%s: 缺 suite.yaml" % suite_dir]
    if not cases_path.is_file():
        return ["%s: 缺 cases.jsonl" % suite_dir]
    meta = parse_suite_yaml(yaml_path)
    whitelist = set(meta.get("tag_whitelist") or [])
    expected_count = meta.get("expected_count")

    cases, parse_errors = load_cases(cases_path)
    errors.extend(parse_errors)
    if expected_count is not None and len(cases) != expected_count:
        errors.append("%s: 条数 %d，与 suite.yaml 的 expected_count=%s 不符"
                      % (cases_path.name, len(cases), expected_count))

    seen_keys: dict[str, int] = {}
    counts: Counter = Counter()
    for lineno, case in cases:
        tag = "%s:%d" % (cases_path.name, lineno)
        key = case.get("case_key")
        if not isinstance(key, str) or not CASE_KEY_RE.match(key):
            errors.append("%s: case_key 缺失或不是 kebab-case（%r）" % (tag, key))
        elif key in seen_keys:
            errors.append("%s: case_key 重复（首次出现在第 %d 行）" % (tag, seen_keys[key]))
        else:
            seen_keys[key] = lineno

        tags = case.get("tags")
        if not isinstance(tags, list) or not tags or any(t not in TAGS for t in tags):
            errors.append("%s: tags 缺失或不在白名单内（%r）" % (tag, tags))
            tags = []
        if tags:
            if any(t not in whitelist for t in tags):
                errors.append("%s: tags 不在 suite.yaml 的 tag_whitelist 内（%r）" % (tag, tags))
            counts[tags[0]] += 1
        kind = tags[0] if tags else ""

        inp = case.get("input")
        if not isinstance(inp, dict):
            errors.append("%s: input 缺失或不是对象" % tag)
            continue
        for f in ("event_type", "title", "time", "deadline", "channel", "tone"):
            if not isinstance(inp.get(f), str) or not inp[f].strip():
                errors.append("%s: input.%s 缺失或为空" % (tag, f))
        if inp.get("event_type") not in EVENT_TYPES:
            errors.append("%s: event_type 不在 3 类枚举内（%r）" % (tag, inp.get("event_type")))
        if inp.get("channel") not in CHANNELS:
            errors.append("%s: channel 不在 4 渠道枚举内（%r）" % (tag, inp.get("channel")))
        guests = inp.get("guests")
        if not isinstance(guests, list) or any(not isinstance(g, str) for g in guests):
            errors.append("%s: input.guests 缺失或不是字符串列表" % tag)
            guests = []
        if inp.get("venue") is not None and not isinstance(inp.get("venue"), str):
            errors.append("%s: input.venue 不是字符串或 null" % tag)
        if inp.get("quota") is not None and not isinstance(inp.get("quota"), int):
            errors.append("%s: input.quota 不是整数或 null" % tag)

        ref = case.get("reference_output")
        if not isinstance(ref, str) or not ref.strip():
            errors.append("%s: reference_output 缺失或为空" % tag)
            continue

        pts = case.get("expected_points")
        if not isinstance(pts, list) or not 3 <= len(pts) <= 6:
            errors.append("%s: expected_points 不是 3-6 条（%r）" % (tag, pts))
            pts = []
        seen_pids: set[str] = set()
        must_count = 0
        for p in pts:
            if not isinstance(p, dict):
                errors.append("%s: expected_points 里有非对象条目" % tag)
                continue
            pid = p.get("id")
            if pid in seen_pids:
                errors.append("%s: expected_points id 重复（%r）" % (tag, pid))
            seen_pids.add(pid)
            if p.get("must") is True:
                must_count += 1
            elif p.get("must") is not False:
                errors.append("%s: 要点 %s 的 must 不是布尔值" % (tag, pid))
            ptype = p.get("type")
            if ptype not in POINT_TYPES:
                errors.append("%s: 要点 %s 的 type 不在枚举内（%r）" % (tag, pid, ptype))
                continue
            if ptype == "keyword":
                kws = p.get("keywords")
                if not isinstance(kws, list) or not kws or any(not k for k in kws):
                    errors.append("%s: 要点 %s keyword 缺非空 keywords" % (tag, pid))
                elif any(k not in ref for k in kws):
                    errors.append("%s: 要点 %s 的 keywords 未全出现在 reference_output 里" % (tag, pid))
            elif ptype == "length":
                mc = p.get("max_chars")
                if not isinstance(mc, int):
                    errors.append("%s: 要点 %s length 缺 max_chars 整数" % (tag, pid))
                elif len(compact(ref)) > mc:
                    errors.append("%s: 要点 %s 字数 %d 超上限 %d" % (tag, pid, len(compact(ref)), mc))
            elif ptype == "placeholder":
                if PLACEHOLDER not in ref:
                    errors.append("%s: 要点 %s 要求草稿含【待补充】，实际没有" % (tag, pid))
            elif ptype == "absent":
                kws = p.get("keywords")
                if not isinstance(kws, list) or not kws:
                    errors.append("%s: 要点 %s absent 缺非空 keywords" % (tag, pid))
                elif any(k in ref for k in kws):
                    errors.append("%s: 要点 %s 的关键词出现在 reference_output 里（闭门会不出现嘉宾名单）" % (tag, pid))
        if pts and must_count == 0:
            errors.append("%s: expected_points 至少 1 条 must=true，实际 0 条" % tag)

        forb = case.get("forbidden_points")
        if not isinstance(forb, list) or not forb:
            errors.append("%s: forbidden_points 为空" % tag)
            forb = []

        etype = inp.get("event_type")
        names = [guest_short(g) for g in guests]
        if etype == "闭门会":
            if any(n in ref for n in names):
                errors.append("%s: 闭门会草稿出现嘉宾姓名" % tag)
            if "不出现嘉宾名单" not in forb:
                errors.append("%s: 闭门会 forbidden_points 缺「不出现嘉宾名单」" % tag)

        if kind == "missing-info":
            missing = [f for f, empty in
                       (("guests", not guests), ("venue", inp.get("venue") is None),
                        ("quota", inp.get("quota") is None)) if empty]
            if not missing:
                errors.append("%s: 信息缺失类未缺任何字段（guests/venue/quota 均非空）" % tag)
            if PLACEHOLDER not in ref:
                errors.append("%s: 信息缺失类草稿缺【待补充】占位" % tag)
            if "不得编造缺失信息" not in forb:
                errors.append("%s: 信息缺失类 forbidden_points 缺「不得编造缺失信息」" % tag)
        if kind == "conflict":
            wl = inp.get("word_limit")
            if not isinstance(wl, int):
                errors.append("%s: 限制冲突类缺 word_limit 整数" % tag)
            else:
                if len(compact(ref)) > wl:
                    errors.append("%s: 限制冲突类草稿字数 %d 超上限 %d" % (tag, len(compact(ref)), wl))
                if date_cn(inp["time"].split(" ")[0]) not in ref:
                    errors.append("%s: 限制冲突类草稿缺活动日期" % tag)
                if isinstance(inp.get("venue"), str) and inp["venue"] not in ref:
                    errors.append("%s: 限制冲突类草稿缺场地" % tag)
                if deadline_cn(inp["deadline"]) not in ref:
                    errors.append("%s: 限制冲突类草稿缺报名截止时间" % tag)
            if "优先保留时间、地点、截止时间" not in forb:
                errors.append("%s: 限制冲突类 forbidden_points 缺「优先保留时间、地点、截止时间」" % tag)
        if kind == "fee":
            fee = inp.get("fee_text")
            if not isinstance(fee, str) or not fee.strip():
                errors.append("%s: 含费用类缺 fee_text" % tag)
            elif fee not in ref:
                errors.append("%s: 含费用类草稿未原样引用 fee_text" % tag)
            if any(w in ref for w in DISCOUNT_WORDS):
                errors.append("%s: 含费用类草稿出现折扣/合计类词" % tag)
            if "不得计算折扣或合计" not in forb:
                errors.append("%s: 含费用类 forbidden_points 缺「不得计算折扣或合计」" % tag)

    for kind, want in DISTRIBUTION.items():
        got = counts.get(kind, 0)
        if got != want:
            errors.append("分布：%s 为 %d 条，与说明的 %d 条不一致" % (kind, got, want))
    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("用法：eval-lint <套件目录或 cases.jsonl 路径>", file=sys.stderr)
        return 2
    errors = lint_suite(args[0])
    if errors:
        for e in errors:
            print(e)
        print("eval-lint: FAIL（%d 个错误）" % len(errors))
        return 1
    print("eval-lint: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
