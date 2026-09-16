---
title: 失败经验：notify.py 因解释器不同静默降级，把原始 Markdown 当代码块发给了用户
type: lesson
status: active
created_at: 2026-09-16T08:30:00+08:00
updated_at: 2026-09-16T09:30:00+08:00
priority: high
keywords:
  - notify.py
  - 邮件汇报
  - Markdown未渲染
  - env python3
  - miniforge
  - 静默降级
  - shebang
questions:
  - 邮件里为什么收到的是原始 Markdown 而不是渲染后的卡片
  - 脚本用 env python3 有什么坑
  - 依赖缺失时脚本该怎么降级才不会坑用户
summary: notify.py 被 miniforge python 执行时缺 markdown 模块静默降级，原文当 <pre> 发出；一律走 shebang 系统 python
load: on-demand
related:
  - agent-memory/procedures/workflow-任务进度邮件汇报.md
  - agent-memory/procedures/checklist-仓库脚本清单.md
---

# 失败经验：notify.py 因解释器不同静默降级，把原始 Markdown 当代码块发给了用户

## 问题背景

2026-09-16 08:03 十项提案并行开发的「【进度】」邮件，用户手机上看到的正文是一整块黑色代码块里的 Markdown 原文（`##`、反引号、`**` 全裸露）。`[事实]` 用户反馈截图确认。

## 失败方法

`scripts/mail/notify.py` 的 shebang 是 `#!/usr/bin/env python3`，渲染依赖 apt 包 `python3-markdown`（只装在系统 `/usr/bin/python3`）。`import markdown` 失败时脚本**静默**退化为 `<pre>` 包裹原文，没有任何提示。

## 失败表现

派子 Agent 的会话里 PATH 首位是 `~/dev/env/miniforge3/bin`，`env python3` 命中 miniforge 的 python 3.12（无 markdown 模块）→ 走了退化分支 → 邮件正文变成代码块。脚本退出码仍是 0、打印「已发送」，调用方完全无感。

## 根本原因

1. **依赖只存在于一个解释器**，而 shebang 用 `env` 由 PATH 决定解释器，环境一变就失效。
2. **降级路径静默且结果不可接受**：`<pre>` 包原文对邮件这种「发出去就收不回」的场景不是可接受的降级，等于把错误交给用户发现。
3. README 写「已装 3.5.2」误导为处处可用，没说清是哪个解释器。

## 规避方法（已落地，commit 见 changelog 09-16）

- shebang 改为 `#!/usr/bin/python3`；调用一律走 `scripts/mail/notify.py ...`，**不要写 `python3 scripts/mail/notify.py`**。
- 脚本启动先 `ensure_markdown_module()`：当前解释器缺模块就 `os.execv` 换 `/usr/bin/python3` 重跑（`NOTIFY_NO_REEXEC=1` 防循环）。
- 仍缺失时用内置精简渲染器（标题/列表/表格/粗体/行内代码/代码块/引用/分割线）并 stderr 警告；三种场景已用同一份正文验证（headless chrome 截图）。

## 下次行动建议

- 写依赖第三方模块的仓库脚本：shebang 固定到装有依赖的解释器，或启动即自检并给出清晰报错；**对外发送类脚本禁止静默降级**，降级也要保证结果可读并打警告。
- 新脚本先在 miniforge python 和系统 python 各跑一次 `--preview`/`--dry-run`。
- 收到「渲染不对」类反馈先查 `which python3` / `sys.executable`，再怀疑正文格式。

## 适用边界

本机（asus）PATH 同时含 miniforge 与系统 python 的环境；其他机器若只有一个 python 但没装 `python3-markdown`，会走内置渲染器（可读但样式略简）。
