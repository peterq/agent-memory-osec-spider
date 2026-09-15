---
title: 记忆仓库 scripts/ 脚本清单
type: procedure
status: active
created_at: 2026-09-13T20:10:00+08:00
updated_at: 2026-09-15T15:50:00+08:00
priority: medium
keywords: [scripts, 邮件汇报, notify.py, git-hooks, commit-msg, 违禁词, claude-rc, remote-control, systemd, notify-admin, agent-browser, cdp]
questions:
  - 记忆仓库 scripts/ 有哪些脚本，各做什么
  - 怎么给用户发进度/异常邮件, Markdown 怎么渲染成邮件
  - 怎么后台启动 Claude Remote Control 会话
summary: MEMORY 仓库 scripts/ 下可复用脚本一览（git-hooks 提交信息违禁词钩子、claude-rc systemd 托管 Remote Control、notify-admin 裸 HTML 邮件、mail/notify.py Markdown 渲染邮件汇报、agent-browser/cdp 浏览器、mem 记忆工具、xl_share_probe 迅雷分享探针）
load: on-demand
related:
  - agent-memory/procedures/workflow-带登录态的浏览器自动化.md
---

# 记忆仓库 scripts/ 脚本清单

均以项目相对路径调用，避免在对话里重复输出脚本内容。

| 脚本 | 用途 | 用法 |
|---|---|---|
| `scripts/claude-rc.sh` + `scripts/claude-rc.service` | headless `claude remote-control` 服务，由 systemd 用户服务托管：开机自启（已 `enable-linger`）、日志 `rc.log`（gitignore）、失败自动重启；五个业务仓库靠 `.claude/settings.local.json` 的 `permissions.additionalDirectories` 挂载 | 首次 `systemctl --user enable --now $PWD/scripts/claude-rc.service`；日常 `systemctl --user status\|restart\|stop claude-rc`；`~/.local/bin/claude-rc` 是脚本软链 |
| `scripts/mail/notify.py` | **任务进度/异常/完成邮件汇报首选**：Markdown 渲染为内联样式 HTML 卡片（色条+级别徽标+元信息），POST cf-worker `notify_admin`；`--preview` 只渲染、`--dry-run` 不发 | `scripts/mail/notify.py -s "主题" -f body.md -l progress\|done\|warn\|error\|info --kv 键=值`；文档 `scripts/mail/README.md` |
| `scripts/notify-admin.sh` | 经 cf-worker 发裸 HTML 邮件（老脚本，正文已是 HTML 时用） | `scripts/notify-admin.sh "<主题>" "<html>" [source]` |
| `scripts/git-hooks/` | `commit-msg` 提交信息违禁词钩子（正则表 `banned-patterns.txt`，初始：邮箱地址、「卧槽」；远端拒绝含邮箱的提交，本地兜底）。[事实 09-13] 已以符号链接装进本仓库 + 1S 五个仓库的 `.git/hooks/` | 改表即生效；换机器重跑 `scripts/git-hooks/install.sh`；细节 `scripts/git-hooks/README.md` |
| `scripts/agent-browser.sh` | 启动/查看项目内独立 profile 的 Chrome 调试会话（9222，带登录态） | `start [url]` / `status` |
| `scripts/cdp.py` | 通过 CDP 驱动上述浏览器 | 见文件头 docstring |
| `scripts/mem/mem.py` | 记忆库检索/索引/lint | 见 `scripts/mem/README.md` |

- `scripts/xl_share_probe.sh <host> <shareId> [pwd]`：经线上 `:9527` 调试代理查迅雷分享顶层结构与首个文件夹详情（排查 xlLoadShare 失败），`RAW=1` 出原始 JSON → `knowledge/domain-迅雷分享爬取.md` §6

## 注意
- cf-worker `notify_admin` 前有 Cloudflare，python-urllib 默认 UA 被拒 `403 error code: 1010`，须自定义 `User-Agent`（curl 默认 UA 可过）`[事实 09-15]`。
- `claude remote-control` 子命令不接受 `--add-dir`，多目录放 settings 的 `permissions.additionalDirectories` `[事实]`。顶层 `claude --remote-control <name> --add-dir ...` 需要 TTY，无 TTY 会退化成 `--print` 报错，不适合做服务 `[事实]`（2026-09-13 实测）。
- 服务无法弹信任对话框：工作区必须先在终端里跑过一次 `claude` 接受信任（`~/.claude.json` 里 `projects[<dir>].hasTrustDialogAccepted`），否则报 `Workspace not trusted` `[事实]`。VSCode 扩展里的会话不会写这个标记。
- 首次启用 remote-control 会问 `Enable Remote Control? (y/n)`，服务无 stdin 会卡住：先在终端跑一次 `claude remote-control` 按 y 再 Ctrl+C，同意会持久化，之后服务正常 `[事实]`（2026-09-13 实测）。
- `rc.log` 里的 `[7A[J … Connected · Capacity 1/32` 重复块是 TUI 状态行的 ANSI 重绘，连上后即停止增长（约 60 次/2 分钟后稳定在 ~24KB），不是死循环 `[事实]`。
- Agent 在 auto 模式下不能改 `.claude/settings*.json`、`~/.claude.json`（自修改被拦），这类改动需用户手动完成 `[事实]`。
- bash 变量名不能以数字开头，故脚本内用 `ONE_S_ROOT` 而非 CLAUDE.md 里的 `1S_ROOT` 记法。
