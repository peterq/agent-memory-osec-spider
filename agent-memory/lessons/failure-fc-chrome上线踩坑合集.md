---
title: 失败经验合集：fc-chrome 上线当天的 5 个小坑（/json/list 数组、pkill -f 自杀、镜像来源、函数超时切 WS、s 组件 cert 三件套）
type: lesson
status: active
created_at: 2026-09-13T11:00:00+08:00
updated_at: 2026-09-15T15:50:00+08:00
priority: medium
keywords: [/json/list, pkill -f, docker exec, FC timeout, WebSocket, fc3-domain certConfig, 镜像来源, ACR]
questions:
  - seedprep 为什么等不到扩展 target
  - FC 上 WebSocket 120 s 就断是为什么
summary: 2026-09-13 fc-chrome 上线踩到的 5 个具体坑与对策：Chrome /json/list 是 JSON 数组不是 {targetInfos}；docker exec 里 pkill -f <字样> 会杀掉自己的 bash；叠层用的 ACR :base 与本地 :base 不是同一版本；FC 函数 timeout 会切断长 WebSocket；fc3-domain 组件 certConfig 要三件套但可整体不传
load: on-demand
related:
  - agent-memory/procedures/workflow-fc-chrome上线.md
  - agent-memory/procedures/workflow-子agent任务简报.md
---

# fc-chrome 上线踩坑合集（2026-09-13）

| 坑 | 表现 | 根因 | 对策 |
|---|---|---|---|
| `/json/list` 解析 | 构建期预热 8/10 超时、带外预热 12/12 超时，"0 个候选"；同容器 `curl /json/list` 5 s 就看到扩展 | Chrome 的 HTTP `/json/list` 返回 **JSON 数组**，代码按 CDP `Target.getTargets` 的 `{"targetInfos":[…]}` 解析，Unmarshal 必失败且被吞 | 解析进 `[]targetInfo`；解析失败要计数/打日志而不是当"没看到" |
| `pkill -f google-chrome` | `docker exec bash -c '…pkill -f google-chrome…; chrome …&; seedprep'` 每次 10 s 就结束、无输出 | `-f` 匹配整条命令行，把当前 `bash -c` 自己（含该字样）也杀了 | `pkill -x chrome` 按进程名，或用不出现在命令行里的模式 |
| 镜像来源不一致 | 本地容器 2~3 s 看到 Tampermonkey，线上 20~40 s 没有；日志 `Skipping mandatory platform policies` | 线上叠层用的 ACR `:base` 是加策略文件**之前**推的，本地 `:base` 已含策略；同 tag 不同内容 | 叠层 Dockerfile 自带所需文件不依赖底镜像版本；拿到"本地能线上不能"先 diff 镜像内容（`docker run --entrypoint cat` 关键文件） |
| FC 超时切 WS | `/chrome` 连接固定在 120 s 被 1006 关闭；日志 `Function timed out after 120 seconds` | s.yaml `timeout: 120` 小于契约 `timeoutSec`(≤300)+冷启动 | `timeout: 600`；内存也从 1024 提到 2048（Chrome+TM 峰值 890 MB） |
| fc3-domain certConfig | `s <domain> plan/deploy` 报 `certConfig must contain certName, certificate and privateKey simultaneously` | 组件校验要三件套，本地没有证书私钥 | 整体不写 certConfig：组件只把 props 里有的字段放进 UpdateCustomDomain，证书保持不变（plan 的 `- certConfig` 是 diff 视图不是要删） |

另：主控自己起 `sleep 45` 等结果被工具拦，等后台任务用 `run_in_background` + 通知；`s deploy` 前会去 ACR 拿 token，本机代理 fake-ip 抖动就 `ETIMEDOUT`，重试即可。
