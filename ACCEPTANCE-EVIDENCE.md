# 验收证据（#2002，S5-EVAL-009，ops_assist.event_copy）

平台验收标准原文（GET /api/v1/problems/2002 实读，2026-11-27）：

1. cases.jsonl 恰有 40 条，eval-lint 校验通过（命令输出）
2. eval-pii-scan 扫描无 error（命令输出）
3. 4 类分布与说明一致，每条要点 3–6 条且至少 1 条 must=true（统计脚本输出）
4. 用 echo mock 适配器跑通一次 eval-run 并生成报告

## 逐条对照（命令输出原文）

### AC1

- cases.jsonl 共 40 行。
- eval-lint 输出原文：`eval-lint: PASS`
- eval-pii-scan 输出原文：`eval-pii-scan: PASS（0 error）`

### AC2

- eval-pii-scan 输出原文：`eval-pii-scan: PASS（0 error）`
- 全文无手机号、邮箱、身份证号、银行卡号形态；含费用类草稿里的金额只来自 fee_text 原样引用。

### AC3

- stats 输出原文：
  - `regular：24 条（说明 24 条）`
  - `missing-info：8 条（说明 8 条）`
  - `conflict：4 条（说明 4 条）`
  - `fee：4 条（说明 4 条）`
  - `每条要点 3-6 条且至少 1 条 must=true：是`
  - `信息缺失类草稿含【待补充】：是`
  - `限制冲突类草稿字数在上限内：是`
  - `含费用类草稿原样引用 fee_text：是`
  - `闭门会草稿不出现嘉宾姓名：是`
  - `stats: PASS`

### AC4

- eval-run 输出原文：`eval-run: 40/40 通过，通过率 1.00`，`eval-run: PASS`
- 报告：`reports/eval-report.json` 与 `reports/eval-report.md`（运行产物，不进仓）。

## 测试与自证

- pytest 输出原文：`21 passed`（AC1 4 项、AC2 4 项、AC3 5 项、AC4 2 项、lint 细节 6 项）。
- 变异自证输出原文：`MUTATION CHECK: PASS`（A 相 21 passed；B1 相删【待补充】后 lint 退出 1，报「要点 p5 要求草稿含【待补充】，实际没有」；B2 相 must 全改 false 后 lint 退出 1，报「至少 1 条 must=true，实际 0 条」；B3 相闭门会草稿塞嘉宾姓名后 lint 退出 1，报「关键词出现在 reference_output 里（闭门会不出现嘉宾名单）」；B4 相费用草稿加「合计 200 元」后 pii-scan 退出 1，报「含折扣/合计类词」；C 相 21 passed，cases.jsonl SHA256 前后一致）。
- 演示输出原文：`DEMO: PASS`。
- 自测输出原文：`SELFTEST: PASS`（`bash setup.sh`）。
- cases.jsonl SHA256：`7d3d440ed8e827803cc95e5f59d6ae8b71173cf8fbca7d458872fcf930c08e22`。

## 原始日志

`evidence/` 下七份日志：eval-lint、eval-pii-scan、stats、eval-run、pytest、mutation-check、demo（均为 2026-11-27 实跑输出）。
