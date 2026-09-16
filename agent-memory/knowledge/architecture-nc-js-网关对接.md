---
title: NC-JS 架构：与 SPIDER 网关的对接方式与鉴权
type: knowledge
status: active
created_at: 2026-09-12T11:25:00+08:00
updated_at: 2026-09-16T17:10:00+08:00
priority: high
keywords:
  - WebRTC
  - gRPC
  - protobuf-ts
  - 网关对接
  - GitHub OAuth
  - 登录门
  - GwLoginGate
  - RtcToken
  - useGwClient
  - proto 生成
  - HealthRpc
summary: NC-JS 后台前端与 SPIDER gateway 之间没有 REST，只有 WebRTC DataChannel 上自实现的 gRPC 传输；鉴权已改 GitHub OAuth（代码已合并，未部署）；含 proto 生成脚本用法与已知坑
questions:
  - 前端怎么连后端，网关 IP 换了改哪
  - 前端 proto 怎么生成
  - 后台登录 GitHub OAuth 怎么接的，gwToken / RtcToken 兜底是什么
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/knowledge/architecture-nc-js-qiankun与后台页面.md
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/api-rpc契约.md
  - agent-memory/decisions/decision-2026-09-08-后台登录改为github-oauth.md
  - agent-memory/lessons/failure-握手回包附加字段被传输层丢弃.md
---

# NC-JS 架构：与 SPIDER 网关的对接方式与鉴权

本文件是 `architecture-nc-js.md` 拆分出的一部分。仓库定位/工程栈/分包布局/构建部署见
`architecture-nc-js.md`；qiankun 微前端机制与后台页面写法见 `architecture-nc-js-qiankun与后台页面.md`。

## 1. 传输方式

- [事实] **没有 REST、没有 axios、没有 baseURL/proxy 配置**。后台所有数据都走
  **WebRTC DataChannel 上自实现的 gRPC 传输**，直连 SPIDER gateway。
  - 传输实现：`packages/catalyst/contract/rpc/grpc_rtc/{rtc-rpc.ts,RtcTransport.ts,packet-stream.ts}`
  - 生产网关地址写死在 `rtc-rpc.ts`：`gwAddrs = [{名:'正式环境', ipList:['115.29.215.228']}, {名:'本地环境', ipList:['127.0.0.1']}]`，端口 `7542/udp`；页面右上角可切换，选择存 localStorage `gwEndpoint`
  - 做法是伪造一份固定的 SDP answer（ice-ufrag `osec-anti-spider-server`），客户端只发 offer 即可连通

## 2. 鉴权

- [事实 2026-09-08，已修复] **鉴权已改为 GitHub OAuth 登录**（限 1second 组织成员），
  代码已合并 push（SPIDER `41832ca` / NC-JS `5808d42` / COMMON `ac5cfc5`），**未部署**。
  旧的"握手只校验全局 RtcToken、403 时 prompt 输管理秘钥"机制**已不成立**——`RtcToken`
  仅作为可关闭的兜底（配置 `allow_rtc_token`，生产 `false`）。新机制：握手首帧可带
  `githubCode` 换取会话票据，网关 `services/gateway/gateway.go:rtcHandshake` 校验
  GitHub 授权 + 1second 组织成员身份后签发自定义紧凑会话票据；403 时统一带上
  `needLogin/githubClientId/githubAuthorizeUrl/githubScope/githubOrg/allowRtcToken`，
  由前端新增的登录门 `GwLoginGate` 弹出并跳转 GitHub 授权。`clientName` 用途不变
  （服务端日志区分调用方，长度须 > 3）。详见 `decisions/decision-2026-09-08-后台登录改为github-oauth.md`、
  `lessons/failure-握手回包附加字段被传输层丢弃.md`（**握手回包的附加字段不能直接靠
  RPC 错误通道传给前端，要走专门回调**）、`knowledge/reference-github-oauth配置.md`。

## 3. 入口 hook 与 RPC 清单

- [事实] 入口 hook：`useGwClient({ipList, uiInputToken, uiInputClientName, onCallError})`
  （`catalyst/contract/rpc/spiderGw/spidergw.ts`）一次返回
  `resSchedulerRpc / spiderRpc / docRpc / downloadRpc / queueAdminRpc / lifecycleRpc` 等 client
  + `initialized` / `usingMock` ref。连接建立前页面渲染 `Spin+Skeleton`，`initialized` 为 true 后再渲染正文。
  **[事实 2026-09-04 晚] 一个子应用只应建一条 RTC 连接**：`queue_admin` 并入网关后
  `queueAdminRpc` 也挂在这条 transport 上；文档爬虫的 `Scheduler` 类原来自建第二条连接，
  已改为由外壳把 client 传进去。`queueAdminMock` 开关打开时 `queueAdminRpc` 换成内存假数据客户端；
  `lifecycleRpc` 同理有 `lifecycleMock.ts`（见 `architecture-nc-js-qiankun与后台页面.md` §4）。

### 现有 RPC → 页面对应

| 子应用 | 用到的 RPC | 主要方法 |
|---|---|---|
| spiderAdmin(资源配置/黑名单) | `spider.resScheduler.ResSchedulerRpc` | `adminHashKeys` / `adminHashGetAll` / `adminHashAdd` / `adminHashRemove` |
| spiderAdmin(文档爬虫) | `spider.docScheduler.DocSchedulerRpc` | `getQueueLength` / `getQueuedUrls` / `getTaskBatch` / `queryDocPagination` / `deleteWaiting` / `setTaskPriority` / `submitDoc` |
| spiderAdmin(队列监控) | `spider.queueAdmin.QueueAdminRpc` | `overview` / `listTasks` / `getTask` / `getDetailSchemas` / `queueStats` / 批量重推与删除 / 日志与审计查询 |
| spiderAdmin(资源生命周期) | `spider.lifecycle.LifecycleRpc` | `Overview` / `QueryResource` / `ListResources` / `TableStats` / `ListEvents` / `TableDiagnostics` / `ListJobs`/`GetJob`/`CreateJob`/`ControlJob` / `GetParams`/`UpdateParams` 等，详见 `architecture-api.md` |
| panShareDownload | `DownloadSchedulerRpc` | `monitorConfig`(返回 grafana url+账号) / `listDownloadGroup` / `queryShareFilePagination` / `getDownloadGroupInfo` / 账号增删改 |
| spiderAdmin(健康监测, 2026-09-16 新增) | `spider.health.HealthRpc` | `accountHealth`/`recheckAccount`(账号池探测)、`siteHealth`/`setSiteDownlineCandidate`(站点成功率与下线候选) |
| 全部 | `spider.SpiderRpc` | `pong`(心跳/连通性) / `getDefaultClientName` / `setClientName` |

[事实 2026-09-16] 表里未列出的 `search_admin`(搜索监控) / `proxy_admin`(代理池) 同样已并入网关, 接入方式与上面几个一致(同一条 transport + 各自 mock 开关), 本表未逐一补全, 以代码 `spidergw.ts` 为准。

[事实] 浏览器里直连网盘接口时（panShareDownload 的百度网盘解析）会经过一个 CORS 代理
`https://fc-resource-node-api.krzb.net/proxy`（`admin/panShareDownload/src/pan/panUtil.ts`）。

## 4. proto 生成

- [事实] proto 生成：`packages/catalyst/scripts/devops/protc_gen.sh`（`pnpm -F @nc/catalyst gen:proto`），
  用 `protoc --ts_out`（protobuf-ts 2.9.4）从 **COMMON 的 `rpc/`** 生成到
  `catalyst/contract/rpc/scheduler/proto/`；另从 SPIDER 的
  `services/gateway/rtc-gateway/grpc_proxy/message.proto` 生成 RTC 帧结构。
- [事实 2026-09-04，已修复] `packages/catalyst/scripts/devops/protc_gen.sh` 的 `PROTO_ROOT`
  原指向已重命名的老路径（`pplabs/`），已改为默认指向 `/home/peterq/dev/projects/1s/enfi-resource-common/rpc`
  且支持环境变量覆盖；同时把 `queue_admin_rpc/queue_admin.proto` 加进了生成列表，`gen:proto` 已跑通；
  同一问题也存在于 8 个 proto 的 `go_package`（重命名前的 `github.com/PPIO/...`），已统一改为 `github.com/1s/...`
  （2026-09-08，见 `sessions/2026/2026-09-08-res_lc数据纳入后台.md`）；`protc_gen.sh` 也曾缺
  `node_modules/.bin` 的 PATH（protoc-gen-ts 找不到），已补。
  另 `panShareDownload` 的 `package.json` 里 `gen:proto` 指向自己的 `scripts/devops/protc_gen.sh`，
  **该文件不存在**（只有 catalyst 有，未处理）；`docSpiderScheduler` 的同类问题随目录删除一并消失。
- [事实 2026-09-04] 已生成的 `res_scheduler` TS 客户端与 COMMON 当前 proto **方法集一致**（11 个方法），
  队列 v2 没有改动 proto 的 service 定义，所以前端契约没有落后。
- **[经验 2026-09-08]** 契约类产物（proto 生成的 TS 代码）主控生成后要**当场提交**，否则子 Agent 面对
  工作区里来路不明的改动会困惑或重做（本次前端子 Agent 因此重新生成了一遍，结果正确但属重复劳动）。

## 5. 已知坑

- [事实] 生产网关 IP `115.29.215.228:7542` 硬编码在 `rtc-rpc.ts` 里，换机器要改代码重新发布前端。
</content>
