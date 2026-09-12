# 任务 30：总览瘦身草案（先读 00-shared.md）

## 目标
把 `agent-memory/00-overview.md`（26.8k 字）压成 **≤ 4,000 字**的草案，并证明没有信息丢失（只是搬家）。

## 做法
1. 读 `00-overview.md` 全文和 `AGENTS.md` 里「4.1 00-overview.md」对总览章节的要求。
2. 写草案到 `SCRATCH/variants/overview-trimmed.md`（SCRATCH 见下）——**不要改原文件**：
   - §1 项目身份、§4 偏好、§7 待解决问题：原样精简。
   - §2 当前状态：只留「最近 7 天重要变化」≤ 5 条，每条 ≤ 2 行，必须带指向详细文件的路径；其余历史叙述搬到 `SCRATCH/variants/changelog.md`（按日期倒序，保留原文，Front Matter type: knowledge, load: rarely）。
   - §3 核心事实：压缩到 ≤ 1,500 字，每条一句；能在 `03-project-context.md` / `knowledge/architecture-*.md` 里找到的，改成一行 + 指针。
   - §5 决策、§6 经验：改为「一句话 → 文件路径」，各 ≤ 10 条。
   - §8 快速加载指引：删除，改为一段 ≤ 5 行的说明：用 `scripts/mem/mem.py boot / search / outline / body` 找文件。
3. 写 `SCRATCH/variants/overview-trace.md`：原总览每一个二级/三级要点 → 现在在哪（草案第几节 / changelog / 某详细文件已有）。任何「在详细文件里找不到、只存在于总览」的事实必须列出来，标记「需回写到 xx 文件」。
4. 用 `python3 -c "print(len(open(p).read()))"` 报告草案字数。

SCRATCH = `/tmp/claude-1000/-home-peterq-dev-projects-peterq-agent-memory-osec-spider/edcb70a1-a862-43ac-9227-02c51ee68d85/scratchpad`

## 交付
`results-30.md`：草案字数、搬家统计（多少条进 changelog / 多少条指针化 / 多少条需回写详细文件）、你认为有争议的取舍。
