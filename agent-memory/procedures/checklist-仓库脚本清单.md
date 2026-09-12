---
title: 记忆仓库 scripts/ 脚本清单
type: procedure
status: active
created_at: 2026-09-13T20:10:00+08:00
updated_at: 2026-09-13T20:10:00+08:00
priority: medium
keywords: [scripts, claude-rc, remote-control, notify-admin, agent-browser, cdp]
questions:
  - 怎么后台启动当前工作空间的 Claude Remote Control 会话
  - 记忆仓库 scripts/ 下有哪些可复用脚本，各自做什么
  - 怎么给管理员发邮件通知
summary: MEMORY 仓库 scripts/ 下可复用脚本一览（claude-rc 后台启动 Remote Control、notify-admin 邮件、agent-browser/cdp 带登录态浏览器、mem 记忆工具），含用法与注意事项
load: on-demand
related:
  - agent-memory/procedures/workflow-带登录态的浏览器自动化.md
---

# 记忆仓库 scripts/ 脚本清单

均以项目相对路径调用，避免在对话里重复输出脚本内容。

| 脚本 | 用途 | 用法 |
|---|---|---|
| `scripts/claude-rc.sh` | nohup 后台启动本工作空间的 Claude Code Remote Control 会话：主目录 = MEMORY 仓库，`--add-dir` 挂 `1s/` 下 COMMON/SPIDER/STORAGE/API/NC-JS 五仓库，日志 `rc.log`（已 gitignore） | `scripts/claude-rc.sh [会话名=osec-spider] [permission-mode=auto]`；`ONE_S_ROOT` 可覆盖 1s 根目录；停止 `pkill -f 'claude --remote-control osec-spider'` |
| `scripts/notify-admin.sh` | 经 cf-worker 给管理员发 HTML 邮件 | `scripts/notify-admin.sh "<主题>" "<html>" [source]` |
| `scripts/agent-browser.sh` | 启动/查看项目内独立 profile 的 Chrome 调试会话（9222，带登录态） | `start [url]` / `status` |
| `scripts/cdp.py` | 通过 CDP 驱动上述浏览器 | 见文件头 docstring |
| `scripts/mem/mem.py` | 记忆库检索/索引/lint | 见 `scripts/mem/README.md` |

## 注意
- `claude remote-control` 子命令本身不接受 `--add-dir`，多目录必须走顶层 `claude --remote-control <name> --add-dir ...` 形式 `[事实]`（2026-09-13 `claude --help` 核对）。
- bash 变量名不能以数字开头，故脚本内用 `ONE_S_ROOT` 而非 CLAUDE.md 里的 `1S_ROOT` 记法。
