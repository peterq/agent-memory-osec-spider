---
title: 任务进度与异常邮件汇报流程
type: procedure
status: active
created_at: 2026-09-15T15:40:00+08:00
updated_at: 2026-09-16T08:30:00+08:00
priority: high
keywords: [邮件汇报, notify.py, 进度, 异常, 阻塞, Monitor, 巡检, 不在电脑旁, Markdown, HTML邮件]
questions:
  - 任务进行中什么时候该给用户发邮件
  - 进度/异常邮件怎么写、用什么脚本发
  - 用户不在电脑旁怎么通知他
summary: 用户常不在电脑旁：长任务的开始/里程碑/完成、任何异常或阻塞都要主动用 scripts/mail/notify.py 发 Markdown 渲染的 HTML 邮件；本文定义触发时机、级别、正文模板与禁忌
load: on-demand
related:
  - agent-memory/02-user-preferences.md
  - agent-memory/lessons/failure-notify脚本静默降级把原始Markdown发成邮件.md
  - agent-memory/procedures/checklist-仓库脚本清单.md
---

# 任务进度与异常邮件汇报流程

[用户确认 2026-09-15]「我经常不在电脑旁边，任务的进度和异常及时通过邮件发送给我，要求简约美观。」

## 1. 触发时机（满足任一即发，不要攒）

| 时机 | 级别 `-l` | 说明 |
|---|---|---|
| 长任务（预计 >30 min 或跨会话）开始 | `progress` | 说明目标、预计时长、下一次汇报时间 |
| 关键里程碑 / 阶段切换 | `progress` | 如灰度比例跨档、批次完成、上线生效 |
| 异常、失败、被拦截、需要用户裁定 | `error` / `warn` | **立即发**，影响 + 已做处理 + 需要用户做什么放最前 |
| 任务完成并验证 | `done` | 结果、验证依据、遗留事项 |
| 巡检类长期监控 | `progress` | 固定间隔（如 `search_canary_report.sh` 每 30 min），无变化也发一行「正常」 |

- 需要用户回答的问题，邮件里给出**默认选项和不回复时的处理**，避免任务空等。
- 同一异常 30 min 内不重复发，除非升级；恢复后补一封 `done`。

## 2. 怎么发

```bash
scripts/mail/notify.py -s "P5 阶段 D 灰度" -f /tmp/report.md -l progress --kv 阶段=D --kv 进度=31% --source p5-canary
```

- 正文写 Markdown（标题/列表/表格/粗体/代码块），脚本渲染成带色条与级别徽标的 HTML 卡片；发前可 `--preview /tmp/x.html` 检查。
- **调用一律写 `scripts/mail/notify.py ...`（走 shebang 的系统 python），不要 `python3 scripts/mail/notify.py`**：miniforge 的 python 没有 markdown 模块，09-16 曾因此把原文当代码块发出；脚本现已自动换解释器/内置兜底，但仍以此为准 → `lessons/failure-notify脚本静默降级把原始Markdown发成邮件.md`
- `--source` 按任务命名，便于用户在邮箱按来源过滤。
- 老的 `scripts/notify-admin.sh` 只接受裸 HTML，新汇报一律用 `notify.py`。
- 子 Agent 也可直接调用该脚本；派长任务子 Agent 时在任务简报里写明汇报时机。

## 3. 正文模板

```markdown
## 结论
一句话：现在处于什么状态 / 出了什么问题。

## 数据
| 指标 | 值 |
|---|---|

## 已做 / 下一步
- 已做：…
- 下一步（预计 hh:mm 再汇报）：…

## 需要你
- 无 / 请裁定 X（默认按 Y 处理）
```

## 4. 禁忌

- 不写明文密钥、口令、AK/SK（`02-user-preferences.md` 第 10 条）。
- 长日志 ≤30 行放代码块，其余给文件路径。
- 不用邮件替代记忆：邮件内容中有长期价值的仍要写进 `agent-memory/`。
