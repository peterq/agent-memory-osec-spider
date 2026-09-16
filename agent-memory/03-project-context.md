---
title: 项目背景与仓库职责
type: context
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-16T11:20:00+08:00
priority: critical
keywords: [仓库, module, replace, 目录结构, 依赖, 职责, NC-JS, 前端]
summary: 五个仓库（4 个 Go + 1 个前端）的磁盘路径、module 名、职责、相互依赖与 go.mod replace 现状
questions:
  - 各仓库的职责分别是什么
  - go.mod replace 现状是怎样的
load: on-demand
related:
  - agent-memory/00-overview.md
  - agent-memory/knowledge/architecture-系统总览.md
  - agent-memory/procedures/workflow-本地构建与验证.md
---

# 项目背景与仓库职责

## 业务背景

风控技术部项目：爬取网络上公开的网盘分享资源（百度网盘、阿里云盘、夸克网盘、迅雷云盘），
把资源元数据与文件清单沉淀到 Elasticsearch，为后续**版权侵犯追责**提供证据；同时对外提供资源搜索接口。

- [用户确认 2026-09-02] **磁力/BT 已停止采集与入库**，只处理上述 4 种网盘类型；
  存量 ES 索引 `enfi_magnet_v3` 与 API 的 `/api/v2/bt` 查询接口保留。
  详见 `decisions/decision-2026-09-02-停止磁力资源采集.md`。

## 仓库一览

工作区根目录：`/home/peterq/dev/projects/1s/`

### COMMON —— `enfi-resource-common`（本仓库，主工作目录）
- [事实] 2026-09-12 起 `AGENTS.md`/`CLAUDE.md`/`agent-memory/`/`agent-tasks/` 实体迁至独立仓库 `/home/peterq/dev/projects/peterq/agent-memory-osec-spider`（远端 `git@github.com:peterq/agent-memory-osec-spider.git`，push 需用户授权放行），COMMON 内四者为绝对路径软链接；记忆变更须在该仓库内单独 commit，COMMON 不再随记忆变动。
- module：`github.com/1s/enfi-resource-common`
- 职责：跨仓库共享的 gRPC 契约（`.proto` + 生成代码）、通用工具、Agent 记忆宿主
- 关键目录：
  - `rpc/storage/`：存储服务契约（`StorageRpc`）
  - `rpc/spider/`：爬虫网关契约（`SpiderRpc` 及 4 个子调度器）
  - `rpc/common_message/`：通用消息类型（Empty/StringMessage/JsonObject…）
  - `rpc/illuminate/multi-server/`：自定义 gRPC resolver（多地址 round_robin）
  - `queue-task/`：基于 Redis 的通用任务队列服务框架（STORAGE 在用）
  - `prom/`：Prometheus 指标封装
  - `cmd/proto/`：protoc 生成后处理（去 `omitempty`、改 json tag）
  - `Makefile`：`make spider` / `make storage` 重新生成 pb 代码
- `agent-memory/`：本记忆目录

### SPIDER —— `osec-spider-go`
- module：`github.com/1s/enfi-spider-go`
- 职责：所有爬虫 + 爬虫网关（任务调度中枢）+ 下载/转存调度 + 有效性校验
- 入口：`spider.go`，单二进制多子命令（`./spider <cmd>`）
- 详见 `knowledge/architecture-spider.md`

### STORAGE —— `enfi-resource-storage`
- module：`enfi-resource-storage`（无域名前缀）
- 职责：接收爬虫提交的资源，异步写入 Elasticsearch / MySQL / MongoDB
- 入口：`storage.go`，子命令 `gateway` / `worker` / `reporter`
- 详见 `knowledge/architecture-storage.md`

### API —— `osec-resource-api`
- module：`github.com/1s/enfi-resource-api`
- 职责：给前端和其他部门提供资源查询/举报/有效性校验的 HTTP 接口（gin）
- 入口：`api-starter.go`
- 详见 `knowledge/architecture-api.md`

### NC-JS —— `nc-js`（前端 mono repo）
- 技术栈：pnpm workspace + Vite 6 + Vue 3（TSX 为主）+ ant-design-vue 4，非 Go 仓库
- 职责：内部后台管理页（qiankun 微前端主应用 + `admin/` 下 4 个子应用），管理爬虫任务、
  网盘账号与转存下载、爬虫调度配置
- 与后端的连接：**不走 REST**，用 WebRTC DataChannel 上自实现的 gRPC 直连 SPIDER gateway；
  proto TS 代码由 COMMON 的 `rpc/` 生成到 `packages/catalyst/contract/rpc/scheduler/proto/`
- `apps/doc-cloud-spider`：fc-chrome 注入的云端文档爬虫脚本（金山/飞书/腾讯文档），独立 vite 构建目标，2026-09-16 从个人仓库 userscripts 迁入（分支待合并）
- 详见 `knowledge/architecture-nc-js.md`

## 依赖关系

```text
SPIDER ──┐
         ├── 依赖 COMMON（rpc 契约）
STORAGE ─┤
API ─────┘
NC-JS ───── 依赖 COMMON（用 protoc 生成 TS 契约，非包依赖）

SPIDER ── gRPC ──> STORAGE（写资源）
API    ── gRPC ──> SPIDER gateway（有效性校验 / 用户提交）
API    ── 读 ──> Elasticsearch（搜索）
NC-JS  ── gRPC over WebRTC ──> SPIDER gateway（后台管理，:7542/udp）
```

外部私有依赖（均通过本地 `replace` 指向兄弟目录，已确认存在）：
- `github.com/1second/pan/common` → `/home/peterq/dev/projects/1s/pan/common`
- `github.com/1second/pan-client-core` → `/home/peterq/dev/projects/1s/pan-client-core`
- `github.com/fancy-go/utils` → `/home/peterq/dev/projects/fancy-go/utils`

## go.mod replace 现状（2026-09-02 收尾后，全部为相对路径且目标存在）

| 仓库 | replace |
|---|---|
| SPIDER | `github.com/1s/enfi-resource-common => ../enfi-resource-common` |
| API | `github.com/1s/enfi-resource-common => ../enfi-resource-common` |
| API | `github.com/1s/enfi-spider-go => ../osec-spider-go` |
| API | `github.com/1second/pan-client-core => ../pan-client-core` |
| STORAGE | `github.com/1s/enfi-resource-common => ../enfi-resource-common` |
| STORAGE | `github.com/1s/enfi-spider-go => ../osec-spider-go` |

> 约定：跨仓库 replace 一律写**相对路径**（原先 API 里有两条写死 `/home/peterq/...` 的绝对路径，已改为相对）。
> STORAGE `go.mod` 里还留着一行注释掉的 `//replace github.com/PPIO/enfi-go-util => ../../pplabs/enfi-go-util`，
> 是失效的历史残留（实际依赖是 `github.com/PPSub/enfi-go-util`），未删除。
- [事实 2026-09-13] 现网 `spider.prod.yaml` 已含 `services.lifecycle_checker.consumer_number_by_type: {bnd: 150}`（其余类型缺省 50）；`services.lifecycle` 节仍未分发，生命周期 `enabled` 靠 redis 热参数。
- [事实 2026-09-15] **API（res-api）生产配置 = 宿主机 `/home/pplabs/enfi-resource-api/config.yaml`（res1/res2 各一份，`CONFIG_FILE=config.yaml` 直接读文件，`OSS_CONFIG_URL` 只给 URL 型字段用）**；OSS `config/resource/search/config.prod.yaml`（11 行）是另一个服务的配置，改它对 res-api 无效。改配置：备份 → 追加 → `./deploy.sh restart 1/2`。
