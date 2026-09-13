---
title: 失败经验：FC 在 WebSocket 断开、调用结束后立刻冻结实例，断开后的清理/写回代码拿不到 CPU
type: lesson
status: active
created_at: 2026-09-13T14:40:00+08:00
updated_at: 2026-09-13T14:40:00+08:00
priority: high
keywords: [FC 冻结, WebSocket, Browser.close, 持久化 profile, 冻结实例, 断开即冻结, custom-container, instanceConcurrency]
questions:
  - FC 上 WebSocket 断开后 handler 收尾代码为什么不执行
  - fc-chrome profile= 为什么要求客户端先发 Browser.close
summary: 2026-09-13 线上实测：客户端断开 WebSocket 后 FC 视为调用结束并立刻冻结实例，handler 中 kill Chrome→写回 NAS 的代码停在原地（锁心跳 2 分钟不动）；解法是把收尾工作挪到连接存活期内——拦截客户端 CDP Browser.close 同步完成写回再回包，外加会话中周期快照兜底
load: on-demand
related:
  - agent-memory/decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
---

# FC 实例在 WebSocket 断开后立刻冻结

## 问题背景
fc-chrome `profile=` 持久化会话最初的设计：客户端断开 → `pipeAndWait` 返回 → `kill()` 里 Browser.close/等退出/tar 写回 NAS/释放锁。本地 docker 全通，线上第二次连接总是 409（锁被占）。

## 失败表现 [事实 2026-09-13]
- 线上锁文件的心跳停在断开那一刻，`/health` 唤不醒（instanceConcurrency=1 时新请求路由到别的实例），2 分钟后 NAS 上仍无 tar；实验 `profile=osec/freeze1`：会话后不再发请求，100 s 内既无 tar 也无心跳。
- 事后被别的请求唤醒时它会接着跑，留下 `<name>.tar.new-*` 半成品（再次冻结）——所以"断开后的代码"不是不执行，而是只在实例被唤醒的零碎时间片里执行。
- 另一个放大因素：`cp -a` 445 个文件到 NFS 要 31 s（每个文件操作 ~70 ms）；单 tar 顺序写 1~2 s。

## 根本原因
FC 以"HTTP 响应结束"判定调用结束；WebSocket 被 hijack 后，客户端断开（FC 网关会在 1~10 s 后关掉到容器的连接）即等于响应结束，实例随即冻结（cgroup freezer），handler 是否 return 无关。FC 3.0 没有 PreFreeze 回调可用。

## 规避方法（已实现）
1. **收尾工作必须在连接存活期内完成**：`wsproxy.go` 拦截客户端发来的顶层 CDP `Browser.close`（puppeteer/rod 的 `browser.close()` 就是它），在连接里同步做完 Chrome 正常关闭 → tar 写回 → 释放锁，再回包、关连接。线上 ack 0.3~0.6 s。
2. **周期快照兜底**（`PROFILE_SNAPSHOT_SEC`=20，有变化才写）：客户端直接断开最多丢 20 s。
3. **写回前校验锁仍归自己**：被冻结很久后醒来的实例，锁可能已被抢占并写入了更新状态，绝不能用本地旧副本覆盖。锁过期改 90 s（3 次心跳）让直接断开的锁尽快可回收。
4. 排查时用 `Runtime.evaluate` 之外的旁证：NAS 上锁文件的心跳时间戳是最直接的"实例有没有在跑"的证据。

## 适用边界
- 所有在 FC custom-container 上做长连接的服务：任何"断开后再做"的逻辑（清理、上报、写回）都不可靠，要么放到连接内，要么放到下一次调用开头。
- 一次性 profile 的清理（删 /tmp 目录）不受影响：下次调用开头 `clearTmpDir` 会补删。
