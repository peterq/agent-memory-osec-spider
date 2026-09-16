---
title: 失败经验：前端网关地址默认值写死"本地环境"下标
type: lesson
status: active
created_at: 2026-09-08T16:10:00+08:00
updated_at: 2026-09-16T09:30:00+08:00
priority: high
keywords:
  - gwEndpoint
  - gwAddrs
  - defaultGwAddr
  - useLocalStorage
  - 正在连接服务器
  - 本地环境
  - NC-JS
summary: 子应用把 gwEndpoint 默认值写死成本地地址导致线上首访连错；默认值必须由 location.hostname 推导
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/lessons/failure-ncjs构建脚本会自动上传OSS.md
---

# 失败经验：前端环境默认值写死本地

## 问题背景

NC-JS 两个连网关的子应用（`admin/spiderAdmin`、`admin/panShareDownload`）都用
`useLocalStorage('gwEndpoint', gwAddrs[1])` 决定连哪个网关。`gwAddrs`（定义在
`packages/catalyst/contract/rpc/grpc_rtc/rtc-rpc.ts`）第 0 项是正式环境、第 1 项是本地
`127.0.0.1`。开发时为了方便把默认值定成了本地项，随代码一路发到了生产。

## 失败表现

任何 localStorage 为空的浏览器（新设备、无痕、清过站点数据）访问生产域名，
页面**永远停在「正在连接服务器(本地环境)…」**，看不到登录门，必须自己发现顶栏
有个环境切换、手动切到「正式环境」才能继续。表面像"后台挂了"。

## 根本原因

1. 默认值是**硬编码下标**，与运行环境无关；开发便利被固化成了线上默认行为。
2. 缺陷来自 09-04 前端合并提交 `b1c6689`，一直没人用空 localStorage 访问过生产，
   所有人的浏览器里都已存着手动选好的值，**存量登录态掩盖了首次访问缺陷**。

## 规避方法

在 catalyst 里提供 `defaultGwAddr()`（`rtc-rpc.ts`），按 `location.hostname` 选：
`localhost` / `127.0.0.1` / `::1` → 本地环境，其余 → 正式环境；且**按 `name` 字段匹配**
（`GW_ADDR_NAME_PROD` / `GW_ADDR_NAME_LOCAL` 常量），不用下标，避免以后往 `gwAddrs`
中间插一项就再次漂移。两个子应用共用该函数。已存在的 localStorage 值仍然优先。
修复提交 NC-JS `7fb3721`。

## 下次行动建议

- 任何"环境选择/后端地址"类默认值，**必须由运行环境推导**，不能写死开发档位。
- 前端改动验收时，**至少跑一次清空 localStorage / 无痕的首次访问**；老浏览器里的
  存量本地状态会系统性地掩盖首次访问类缺陷。
- 同类默认值抽成公共函数放 `packages/catalyst`，不要在各子应用里各写一份。

## 适用边界

任何"用 localStorage 记住用户选择、同时需要一个合理初值"的前端配置项。
