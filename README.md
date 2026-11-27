# clawhunt-2002-eval-notice-copy

ClawHunt #2002（S5-EVAL-009）最小可验证样品：为「运营辅助」的活动文案能力编写评测集 `ops_assist.event_copy`，共 40 条，全部用虚构测试数据。

## 一键复跑

```bash
bash setup.sh
```

预期输出：`SELFTEST: PASS`（pytest + 变异自证 + 演示 + MANIFEST 核验）。
Python >= 3.11；无 pytest 时 setup.sh 会建本地 `.venv` 并按 `requirements.txt` 安装（只依赖 pytest）。

## 四条命令

```bash
python3 scripts/eval-lint evals/suites/ops_assist.event_copy
# eval-lint: PASS

python3 scripts/eval-pii-scan evals/suites/ops_assist.event_copy
# eval-pii-scan: PASS（0 error）

python3 scripts/stats.py evals/suites/ops_assist.event_copy
# stats: PASS

python3 scripts/eval-run evals/suites/ops_assist.event_copy --out reports
# eval-run: 40/40 通过，通过率 1.00
# eval-run: PASS
```

## 套件结构

- `evals/suites/ops_assist.event_copy/`：`suite.yaml` 与 `cases.jsonl`（40 条）
- `src/evaltools/`：`common.py`、`lint.py`、`pii_scan.py`、`runner.py`、`stats.py`（纯标准库）
- `scripts/`：`eval-lint`、`eval-pii-scan`、`eval-run`、`stats.py`、`demo.py`、`mutation_check.py`
- `tests/`：pytest 测试（AC1、AC2、AC3 规则、AC4 评测、lint 细节）
- `docs/`：`distribution.md`（分布统计表）、`sample-checks.md`（10 条抽样自查记录）
- `schema/case.schema.json`：用例 JSON Schema
- `MANIFEST`：文件清单（sha256；不含 MANIFEST 自身与每次自测都会重写的 `evidence/selftest-setup-sh-20261127.log`，后者仍在仓外工作目录）
- `ACCEPTANCE-EVIDENCE.md`：验收证据（命令输出原文与测试数字）

## 分布（40 条）

| 类别 | 条数 | 规则 |
| --- | --- | --- |
| regular（常规） | 24 | 4 渠道 × 3 类型 × 2 |
| missing-info（信息缺失） | 8 | 缺嘉宾 4、缺场地 2、缺名额 2；草稿用【待补充】占位，不得编造 |
| conflict（限制冲突） | 4 | 字数上限 60 或 80 字；优先保留时间、地点、截止时间 |
| fee（含费用） | 4 | 费用只能原样引用 input 中的费用文本，不得计算折扣或合计 |

## 规则口径

- 每条 expected_points 3–6 条，且至少 1 条 must=true；要点类型：keyword、length、placeholder、absent。
- 闭门会共 9 条，草稿均不出现嘉宾姓名（写「嘉宾名单不对外公布」）。
- 场地一律「示例空间…」，嘉宾一律姓氏加职称加「（虚构）」，不出现客户名称与任何真实个人信息。
- 被测工具输出在业务中只进复核队列、不得直接对外发送，AI 不计算金额。
- eval-run 用 echo mock：被测输出取每条用例的 reference_output 原样回显；接真实被测工具时只换 runner 里取 reference_output 的那一行。

## 变异自证

`scripts/mutation_check.py`：A 相 pytest 全过；B1 相删【待补充】后 lint 报错；B2 相 must 全改 false 后 lint 报错；B3 相闭门会草稿塞嘉宾姓名后 lint 报错；B4 相费用草稿加「合计」后 pii-scan 报错；C 相恢复后 pytest 再过且 cases.jsonl SHA256 不变。输出 `MUTATION CHECK: PASS`。
