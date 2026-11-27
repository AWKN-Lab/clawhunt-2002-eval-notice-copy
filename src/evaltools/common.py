"""ops_assist.event_copy 评测集共用加载器（纯标准库）。

suite.yaml 只用「key: value」与「- 列表项」两种写法，本模块用手写
解析器读取，不依赖 PyYAML；cases.jsonl 每行一个 JSON 用例。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

EVENT_TYPES = ["公开", "会员专享", "闭门会"]
CHANNELS = ["小程序活动简介", "社群群发", "推文摘要", "站内信"]
TAGS = ["regular", "missing-info", "conflict", "fee"]
DISTRIBUTION = {"regular": 24, "missing-info": 8, "conflict": 4, "fee": 4}
EXPECTED_COUNT = 40
CASE_KEY_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PHONE_RE = re.compile(r"1[3-9]\d{9}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"\b\d{17}[\dXx]\b")
BANK_RE = re.compile(r"\b\d{16,19}\b")
AMOUNT_RE = re.compile(r"\d+(\.\d+)?\s*(元|¥|人民币|块钱)")
DISCOUNT_WORDS = ("折扣", "合计", "总价", "立减", "优惠价", "打折")
PLACEHOLDER = "【待补充】"
POINT_TYPES = ("keyword", "length", "placeholder", "absent")


def compact(text: str) -> str:
    """去掉全部空白后的文本（字数上限按此口径数）。"""
    return re.sub(r"\s+", "", text)


def date_cn(iso_date: str) -> str:
    y, m, d = iso_date.split("-")
    return "%s月%s日" % (int(m), int(d))


def deadline_cn(iso_dt: str) -> str:
    d, hm = iso_dt.split(" ")
    return "%s %s" % (date_cn(d), hm)


def guest_short(name: str) -> str:
    return name.replace("（虚构）", "")


def resolve_suite(path: Path) -> tuple[Path, Path]:
    """参数可以是套件目录或 cases.jsonl 路径，返回 (套件目录, cases.jsonl)。"""
    p = Path(path)
    if p.is_file():
        return p.parent, p
    return p, p / "cases.jsonl"


def parse_suite_yaml(path: Path) -> dict:
    """极简 YAML 解析：只支持顶层 `key: value` 与 `- 项` 列表。"""
    data: dict = {}
    cur_key: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^(\S[^:]*):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            cur_key = m.group(1).strip()
            val = m.group(2).strip().strip('"').strip("'")
            if val == "":
                data[cur_key] = []
            else:
                try:
                    data[cur_key] = int(val)
                except ValueError:
                    try:
                        data[cur_key] = float(val)
                    except ValueError:
                        data[cur_key] = val
            continue
        m2 = re.match(r"^\s*-\s*(.+)$", line)
        if m2 and cur_key is not None:
            item = m2.group(1).strip().strip('"').strip("'")
            if not isinstance(data.get(cur_key), list):
                data[cur_key] = []
            data[cur_key].append(item)
    return data


def load_cases(cases_path: Path) -> tuple[list[tuple[int, dict]], list[str]]:
    """返回 ([(行号, 用例)], [解析错误])。行号从 1 开始。"""
    cases: list[tuple[int, dict]] = []
    errors: list[str] = []
    for lineno, raw in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append("%s:%d: JSON 非法（%s）" % (cases_path.name, lineno, exc.msg))
            continue
        if not isinstance(obj, dict):
            errors.append("%s:%d: 用例不是 JSON 对象" % (cases_path.name, lineno))
            continue
        cases.append((lineno, obj))
    return cases, errors
