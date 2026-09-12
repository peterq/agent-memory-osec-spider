---
title: 记忆仓库 scripts/ 脚本清单
type: procedure
status: active
created_at: 2026-09-13T20:10:00+08:00
updated_at: 2026-09-13T21:20:00+08:00
priority: medium
keywords: [scripts, claude-rc, remote-control, systemd, notify-admin, agent-browser, cdp]
questions:
  - 怎么后台启动当前工作空间的 Claude Remote Control 会话
  - 记忆仓库 scripts/ 下有哪些可复用脚本，各自做什么
  - 怎么给管理员发邮件通知
summary: MEMORY 仓库 scripts/ 下可复用脚本一览（claude-rc systemd 用户服务托管 Remote Control、notify-admin 邮件、agent-browser/cdp 带登录态浏览器、mem 记忆工具），含用法与注意事项
load: on-demand
related:
  - agent-memory/procedures/workflow-带登录态的浏览器自动化.md
---

# 记忆仓库 scripts/ 脚本清单

均以项目相对路径调用，避免在对话里重复输出脚本内容。

| 脚本 | 用途 | 用法 |
|---|---|---|
| `scripts/claude-rc.sh` + `scripts/claude-rc.service` | headless `claude remote-control` 服务，由 systemd 用户服务托管：开机自启（已 `enable-linger`）、日志 `rc.log`（gitignore）、失败自动重启；五个业务仓库靠 `.claude/settings.local.json` 的 `permissions.additionalDirectories` 挂载 | 首次 `systemctl --user enable --now $PWD/scripts/claude-rc.service`；日常 `systemctl --user status\|restart\|stop claude-rc`；`~/.local/bin/claude-rc` 是脚本软链 |
| `scripts/notify-admin.sh` | 经 cf-worker 给管理员发 HTML 邮件 | `scripts/notify-admin.sh "<主题>" "<html>" [source]` |
| `scripts/agent-browser.sh` | 启动/查看项目内独立 profile 的 Chrome 调试会话（9222，带登录态） | `start [url]` / `status` |
| `scripts/cdp.py` | 通过 CDP 驱动上述浏览器 | 见文件头 docstring |
| `scripts/mem/mem.py` | 记忆库检索/索引/lint | 见 `scripts/mem/README.md` |

## 注意
- `claude remote-control` 子命令不接受 `--add-dir`，多目录放 settings 的 `permissions.additionalDirectories` `[事实]`。顶层 `claude --remote-control <name> --add-dir ...` 需要 TTY，无 TTY 会退化成 `--print` 报错，不适合做服务 `[事实]`（2026-09-13 实测）。
- 服务无法弹信任对话框：工作区必须先在终端里跑过一次 `claude` 接受信任（`~/.claude.json` 里 `projects[<dir>].hasTrustDialogAccepted`），否则报 `Workspace not trusted` `[事实]`。VSCode 扩展里的会话不会写这个标记。
- 首次启用 remote-control 会问 `Enable Remote Control? (y/n)`，服务无 stdin 会卡住：先在终端跑一次 `claude remote-control` 按 y 再 Ctrl+C，同意会持久化，之后服务正常 `[事实]`（2026-09-13 实测）。
- `rc.log` 里的 `[7A[J … Connected · Capacity 1/32` 重复块是 TUI 状态行的 ANSI 重绘，连上后即停止增长（约 60 次/2 分钟后稳定在 ~24KB），不是死循环 `[事实]`。
- Agent 在 auto 模式下不能改 `.claude/settings*.json`、`~/.claude.json`（自修改被拦），这类改动需用户手动完成 `[事实]`。
- bash 变量名不能以数字开头，故脚本内用 `ONE_S_ROOT` 而非 CLAUDE.md 里的 `1S_ROOT` 记法。
