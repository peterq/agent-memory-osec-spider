---
title: API 查询服务结构
type: knowledge
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-02T10:50:00+08:00
priority: high
keywords: [API, osec-resource-api, gin, 路由, 限流, 黑名单, 搜索]
summary: osec-resource-api 的路由表、中间件链、依赖服务与后台管理模块
load: on-demand
related:
  - agent-memory/knowledge/architecture-系统总览.md
---

# API（`1s/osec-resource-api`，module `github.com/PPIO/enfi-resource-api`）

## 入口 `api-starter.go`

启动顺序：加载配置 → 起 cron（定时刷新 apitoken、违禁关键词）→ 初始化 ES → gin 路由 →
起 `:8089` Prometheus → 注册 `remoteservice`(连 SPIDER gateway) → `valid.NewValidService` → `controller.NewEnfiResourceApi` → `resource_admin.InitApplication` → 优雅退出。

配置文件查找顺序：环境变量 `CONFIG_FILE` → `./config_dev.yaml` → `./config.yaml`。

> `main()` 里有一段硬编码：主机名为 `asus` 时设置 `LOCAL_CONFIG_PATH` 指向 `_note/config.dev.yaml`（作者本机开发用）。

## 中间件链（全局，按顺序）

1. `Metric()` —— `http_request_duration_seconds` / `http_requests_total`
2. `auth.PrivateIpCheck()`
3. `gin.LoggerWithConfig` —— 日志走阿里 SLS（`logger`），跳过 `/api/health/check`
4. `cors`
5. `throttle.Throttle` —— 60s 窗口，配置 `limit_config.minute_rate`，key 为 `api.<clientIP>`

`blackStrategy`（仅挂在重接口上）：10s / 5m / 30m 三档限流，触发后 `throttle.AddBlackIp` 拉黑。
挂了 blackStrategy 的接口：`v2/search`、`v2/fileCtx`、`v2/detail`、`v2/recommend`、`enfi/search`、`enfi/detail`、`enfi/recommend`。

## 路由表

| 分组 | 路由 |
|---|---|
| `/api/v2` | `POST report`、`POST userSubmit`、`POST checkValid`、`POST queryValidAndPwd`、`GET search`、`POST validShareLink`、`GET fileCtx`、`GET detail`、`GET query`、`GET recommend`、`GET suggest`、`POST complaint`、`POST likes`、`POST dislikes` |
| `/api/v2/bt` | `GET detail`、`GET file`、`POST report`、`GET search`、`GET recommend`、`POST magnet` |
| `/api/enfi/` | `GET search`、`GET detail`、`GET query`、`GET recommend` |
| 其他 | `HEAD /api/health/check`、`GET /api/token/get`、`GET :8089/api/metrics` |

## 目录

```text
controller/     api.go(主接口)、bt-api.go(磁力/种子)、com-api.go(健康/token/加解密)、green-api.go(内容安全)
services/
  search/       ES 查询构造（search.go / model.go / bittorrent.go）
  valid/        链接有效性校验（bnd/quark/xunlei api）
  remoteservice/gRPC 客户端（连 SPIDER gateway），cmd/ 下有命令行工具
  apitoken/ blackip/ forbidden/ complaint/ report/ initdata/ parallel-control/ aliyun/
middleware/     auth（PrivateIpCheck）、throttle（限流+拉黑）
resource-admin/ 后台管理模块（InitApplication 注入 service）
resource-config/
api-error/      错误码
util/           GetClientIP 等
```

> `README.md` 内容与本服务无关（是微信服务号 lua 脚本需求文档的残留），不要当作 API 文档读。
