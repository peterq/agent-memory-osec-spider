---
title: 失败经验：重新部署网关时发现 ES 配置指向已下线集群，网关崩溃重启
type: lesson
status: active
created_at: 2026-09-04T15:10:00+08:00
updated_at: 2026-09-18T10:50:00+08:00
priority: high
keywords: [网关, gateway, ES, elasticsearch, 集群更换, 配置过期, 长期不重启, 上线前检查, es_addr, spider.gateway.prod.yaml]
summary: 线上网关自 1 月未重启，期间 ES 集群已更换；队列 v2 上线一重启就 panic。教训：长期不重启的服务会掩盖外部依赖变更，重启前先在目标主机验证配置里的每个外部地址
questions:
  - 网关起不来，报 no such host 怎么查
  - 重启网关前要检查什么
load: rarely
related:
  - agent-memory/sessions/2026/2026-09-04-队列v2改造.md
  - agent-memory/procedures/workflow-部署.md
  - agent-memory/current/risks.md
---

# 失败经验：网关重启暴露 ES 集群已更换

## 问题背景

2026-09-04 队列 v2 上线，`./deploy.sh gateway` 后 res1/res2 的 `spider-gateway` 立即进入 `Restarting` 循环：
`panic: dial tcp: lookup es-cn-nwy39sbcx000a7gww.elasticsearch.aliyuncs.com ... no such host`（`gateway.go initEs()`）。
旧网关容器已被 `docker rm -f`，**无法回滚**（旧二进制连的也是同一个死域名）。网关挂掉期间所有爬虫提交、
`v2bnd*` 消费全部中断。

## 根本原因

- 网关生产配置 `_note/config/spider.gateway.prod.yaml`（`_note` 是符号链接，**不在 git 里**）的 `es_addr` 还指向旧 ES 集群
  `es-cn-nwy39sbcx000a7gww`；STORAGE 线上 `config.yaml` 早已换到 `es-cn-vcg4txxrn00021s9s`（凭据相同）。
- 线上网关自 2026-01-10 起未重启，`initEs()` 只在启动时 ping，所以集群更换后一直没暴露。
- 新集群上没有 `enfi_resource_v6` 索引/别名，只有 `enfi_resource_v6_250822`（别名 `resource`），`es_resource_index` 也要跟着改。

## 失败表现

上线执行 Agent 按指令"网关没起来就停下"，正确地停在第 2 步并给出了 DNS 诊断，但把它归类为"主机 DNS 问题"——
实际是**配置过期**。主会话通过对比 STORAGE 线上配置里的 ES 主机名才定位。

## 规避方法

1. **重启/重新部署任何长期运行的有状态服务前，先在目标主机上验证配置里的每个外部地址**：
   `ssh <host> "getent hosts <es/mysql/redis 域名>; curl -s -o /dev/null -w '%{http_code}' <url>"`。
   网关的外部依赖：ES（`es_addr`）、MySQL、Redis、阿里日志。
2. **同一外部资源以其他仓库/服务的线上配置为准交叉核对**：STORAGE 的 `/home/pplabs/enfi-resource-storage/config.yaml`
   是 ES 地址的可靠来源（它一直在写）。比对凭据用 shell 变量 `[ "$a" = "$b" ]`，不要回显。
3. `_note/config/*.yaml` 不受版本控制，改完要在会话摘要里记下改了什么（不记凭据）。
4. 含凭据的文件主会话读写会被安全策略拦截，需要用户手改；把目标值与验证依据一次说清，减少往返。

## 下次行动建议

- `procedures/workflow-部署.md` 加"重启前外部依赖连通性检查"一节（已加）。
- 考虑让 `initEs()` 失败时不 panic 而是重试+告警，避免网关因单个依赖拉不起来（待用户决定）。
- API 仓库 `config.yaml` 的 ES 主机 `es-cn-oew1qf4gx000pr1ap` 也与 STORAGE 不一致，**待确认**是否同样过期。

## 适用边界

所有"很久没重启过"的线上进程：重启前假定其配置已腐化，逐项验证。
