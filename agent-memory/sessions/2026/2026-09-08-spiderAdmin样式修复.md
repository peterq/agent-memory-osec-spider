---
title: 会话摘要：spiderAdmin 线上样式丢失与顶栏深色修复
type: session
status: active
created_at: 2026-09-08T07:20:00+08:00
updated_at: 2026-09-08T07:20:00+08:00
priority: medium
keywords:
  - spiderAdmin
  - NC-JS
  - qiankun
  - 样式丢失
  - header 深色
  - 生产部署
summary: 定位并修复 spiderAdmin 线上 body margin/布局失效(Vue mount 清空 qiankun 包裹层)与顶栏 #001529(antd 两级选择器), 已部署 OSS 并 push
load: on-demand
related:
  - agent-memory/lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md
  - agent-memory/knowledge/architecture-nc-js.md
---

# 会话摘要

## 完成事项

- 用无头 Chrome dump 线上 DOM，确认 spiderAdmin 被 qiankun 加载时 `<qiankun-head>` 与子应用 CSS 全部不在文档里；
  读 `@vue/runtime-dom` 源码确认 `app.mount()` 会 `textContent=''` 清空容器 → 根因是 catalyst `initMicroFeApp` 直接挂包裹层。
- 读 antdv 4.2.6 Layout 样式源码，确认 header 规则选择器为 `.ant-layout .ant-layout-header`，单类名 `.sa-header` 压不过。
- 修复三处：`packages/catalyst/ui/microFe/entry.ts`（挂到包裹层内 `#app`）、`AppLayout.tsx`（Layout token 白底）、
  `main.less`（header 选择器提到 0,3,0）。type-check 通过。
- 先用 `{deploy:false}` 构建核对产物 CSS，再还原配置正式 `pnpm build` 部署到 OSS（apps.json `buildAt 2026/9/8 07:12:05`）。
- 部署后再次 dump 线上 DOM：`<qiankun-head>` 保留、CSS 已内联、`html,body{margin:0}` 与新 header 规则均在、Vue 挂在 `#app` 内；
  前后截图对比 8px 白边消失。
- NC-JS 提交 `b93922d` 并 push；本地 qiankun 联调用的 SPA 静态服务器脚本落到 `admin/qiankun/scripts/serveDist.py`。

## 关键发现

- 见 `lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md`。
- 主应用 `loadApps()` 只在 `location.hostname === 'localhost'` 时读本地 `/apps.json`，用 `127.0.0.1` 会去拉生产 apps.json。
- `pkill -f '<脚本名>'` 会匹配到当前 bash 自身的命令行把自己杀掉（exit 144），要写成 `pkill -f '[s]pa_server.py'`。

## 后续行动

- panShareDownload / login3rd 共用同一入口，下次各自 build 时自动带上修复；如需立即生效需单独重发。
