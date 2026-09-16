---
title: 成功经验：解析在线文档优先调页面自带的内部接口，而不是啃 DOM 或前端内部对象
type: lesson
status: active
created_at: 2026-09-16T09:00:00+08:00
updated_at: 2026-09-16T09:00:00+08:00
priority: medium
keywords: [在线文档, 内部接口, performance.getEntriesByType, 飞书, 云端脚本, 调研方法]
questions:
  - 接入新的在线文档站点先看什么、怎么找分页接口
summary: 解析 SPA 文档站优先 fetch 页面自带接口：performance 资源列表 + 全局变量 + bundle 搜路径常量找到分页接口，比啃 DOM/redux 稳且快
load: on-demand
related:
  - agent-memory/knowledge/domain-飞书文档解析.md
  - agent-memory/procedures/workflow-新站点调研.md
---

# 成功经验：在线文档解析优先用页面自带接口

## 问题
要在注入到文档页的脚本里把整篇文档（可能上千块/上千行）的网盘链接抽干净。DOM 是虚拟化/懒渲染的，前端内部对象（redux store、fetch manager）字段名混淆且随版本漂移。

## 适用条件
目标站点是 SPA，页面加载时自己会调 JSON 接口取内容；脚本运行在页面主世界（同源，能带 cookie）。

## 推荐做法（本次实际步骤，约 2 小时）
1. `scripts/agent-browser.sh start` + `scripts/cdp.py eval`，在真实页面 `performance.getEntriesByType('resource')` 过滤 `/api/` 看页面调了哪些接口；`Object.keys(window)` 找 SSR 注入的全局（如 `DATA.clientVars`、`wiki_info_map`）。
2. 在页面里 `fetch` 这些接口，用 `walk(obj, depth)` 打形状不打全文，定位记录/块所在字段与分页字段（`has_more`/`next_cursors`/`recordsNum`）。
3. 分页参数不明时，`fetch(script.src).text()` 把前端 bundle 拉下来搜路径常量（如 `/ondemand/records`）和调用点上下文（`indexOf` 前后 700 字），比猜参数快得多。
4. 用小 `limit` 在小文档上把分页循环跑通（38 块 limit=5 → 8 次拉齐），再写脚本；脚本里接口失败退回 SSR 首片并带 warning。
5. 单测夹具直接从真实页面抓（`cdp.py eval 'JSON.stringify(...)'` 落盘），验证用 `verify_cloud.py` 模拟线上注入通道跑真实 URL。

## 原因
接口是页面自己在用的契约，比 DOM 结构/内部对象稳定；同源 fetch 自动带游客 cookie，无需登录；分页语义清楚可穷尽。

## 注意事项
- 共用调试浏览器时标签序号会漂移，`cdp.py --tab` 要用 target id。
- `DecompressionStream('gzip')` 可在页面里解 gzip+base64，不用引 pako；别信 `encoding` 字段，看前缀 `H4sI`。
- 有些接口匿名不可用（飞书 `tablesv3/` "Failed to fetch"），换用主接口里已带的数据。
- 未公开文档会停在登录页，脚本要能从"中间页"发终态，否则任务只能等超时。

## 可迁移范围
腾讯文档、语雀、Notion 等任何 SPA 文档站；也适用于资源站调研（`workflow-新站点调研.md` 的"找 JS bundle 接口"是同一思路）。
