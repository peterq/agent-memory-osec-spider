---
title: 失败经验：端到端验证复用了仍在托管旧目录的 http.server，fc-chrome 注入的是旧脚本
type: lesson
status: active
created_at: 2026-09-16T09:20:00+08:00
updated_at: 2026-09-18T10:50:00+08:00
priority: medium
keywords: [fc-chrome, 端到端验证, 缓存, http.server, inject, DOC_SPIDER, 无回传]
questions:
  - 新构建的云端脚本经 fc-chrome 注入后为什么一条 [[DOC_SPIDER]] 都没有
  - 端到端脚本"复用已在跑的服务"有什么坑
summary: 2026-09-16 验证腾讯文档脚本时 fc-chrome 路径无任何回传、直连 CDP 却全通——根因是 e2e 脚本"端口有响应就复用"复用了托管旧 dist-cloud 的 http.server，注入的是只认 kdocs 的旧脚本；修法是每次重启托管进程并给脚本 URL 加内容哈希
load: rarely
related:
  - agent-memory/knowledge/domain-腾讯文档表格解析.md
  - agent-memory/lessons/failure-注入脚本用consolelog回传被页面自身替换吞掉.md
---

## 问题背景
用 `scripts/docspider/e2e-local-fcchrome.sh` 在本机 fc-chrome 上跑新构建的云端脚本（新增 docs.qq.com 分支），页面自身的 console 日志都到了，却一条 `[[DOC_SPIDER]]`（连 `start`）都没有。

## 失败方法与表现
e2e 脚本为省事写成"托管端口已有响应就复用、fc-chrome 已在跑就复用"。此前刚用**同一个端口**托管主工作树的 `dist-cloud`（旧脚本）做过金山冒烟，于是新一轮实际注入的是旧脚本；旧脚本在 docs.qq.com 上 `isDocHost` 为 false 直接 return，表现为"完全静默"。fc-chrome 自身还有按 URL 键控的资产缓存，同 URL 也可能命中旧内容。

## 根本原因
验证链路里有两处"按地址复用"的状态（http.server 进程、fc-chrome 资产缓存），而脚本内容变了地址没变。

## 规避方法
1. 端到端脚本每次**重启**托管进程，不复用。
2. 脚本 URL 带内容哈希 `?v=<md5>` 做 cache-busting。
3. 出现"注入后无回传"先用 `scripts/docspider/cdp-inject-debug.py` 直接用本机 Chrome 注入同一份产物：能跑通就是链路/缓存问题，跑不通才是脚本问题（它还会打印 JS 异常，localverify 不打印）。

## 适用边界
任何"起一个本地服务托管产物再由另一进程拉取"的验证流程；线上 OSS 同名覆盖脚本时也要留意 CDN/客户端缓存。
