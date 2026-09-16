---
title: 排查：代理池总览/场景明细无数据
type: procedure
status: active
created_at: 2026-09-10T09:30:00+08:00
updated_at: 2026-09-12T22:36:00+08:00
priority: medium
keywords: [proxy-admin-check, 代理池总览, proxy_admin, proxy-monitor, proxyMon, dataSource, 无数据, 全是0, 上报侧未部署, 容器创建时间, Scene, ClassifyResult]
summary: 后台代理池页全 0 时三步定位：网关 dataSource → 上报侧是否部署 → tools 探针
load: on-demand
related:
  - agent-memory/lessons/failure-旁路能力初始化拖垮主流程.md
  - agent-memory/current/tasks.md (上线待办：爬虫容器分批重部、proxy 服务重部)
  - agent-memory/procedures/workflow-部署.md
---

# 排查：代理池总览无数据

数据链路：上报侧（爬虫进程 + `proxy` 服务）`illuminate/proxy-monitor` 每分钟写 redis
`proxyMon:*` → 网关 `services/gateway/proxy_admin` 只读聚合 → 前端 spiderAdmin。
读写两侧用**同一个** redis 名 `services.proxy.redis`（生产 `db1` = 192.168.7.145:16379 db6）。

## 三步定位（按顺序，通常第 2 步就出结论）

1. **读取侧对不对**：网关日志里 `ProxyOverview` 的 `output.dataSource`。
   ```bash
   ssh osec-res2 "sudo docker logs --since 1h spider-gateway 2>&1 | grep ProxyOverview | tail -1"
   ```
   期望 `redises[db1]/proxyMon:`；若是 `gatewayRedis(...)` 说明网关那份配置缺 `services.proxy.redis`，读错库。
2. **上报侧有没有部署**：上报代码在 09-09 `883daeb` 才进 master，容器必须在其后创建。
   ```bash
   for h in osec-res1 osec-res2 osec-resngix osec-restest osec-jenkins; do
     ssh $h "md5sum /home/pplabs/enfi-spider-go/spider | cut -c1-8; sudo docker ps --format '{{.Names}} {{.CreatedAt}}' | grep ^spider-"
   done
   ```
   注意主机上的二进制可能已是新版（网关重部时覆盖），但**容器不重启仍跑旧进程**——以容器 `CreatedAt` 为准，不看文件 md5。
   `proxy` 服务在 osec-jenkins，日志行还是 `proxy-provider.go:272: publish` 即旧代码（新代码在 `proxy_provider_supply.go`）。
3. **上报侧初始化有没有被降级跳过**：新容器日志 grep `proxy_monitor`。
   出现「proxy_monitor 未启用」说明该角色配置拿不到 `services.proxy.redis`（见 `failure-旁路能力初始化拖垮主流程.md`）。

## 2026-09-10 09:20 首次排查结论

- [事实] 读取侧正常：双网关 `dataSource=redises[db1]/proxyMon:`，请求 ok，只是库里没 key。
- [事实] 上报侧**全部未部署**：所有爬虫容器与 `spider-proxy` 都创建于 09-08 13:00~15:50（早于 `883daeb`），
  `spider-proxy` 二进制 md5 `c405efb1`（= `6cf6157`），没有任何容器日志含 `proxy_monitor`。
- 结论：不是缺陷，是 `current/tasks.md` 上线待办中「爬虫容器分批重部」「proxy 服务重部」尚未执行。
  重部顺序建议：先 `proxy`（osec-jenkins，只影响供给侧打点，风险最低）→ 再分批爬虫。

## 已解决（2026-09-10 09:30~09:56）

`proxy` 服务 + 20 个爬虫 service 重部后，5 分钟窗口供给 push=170/去重 114，20 个场景全部上报，无「未启用」、无 exec error。

## 直接看数据：`tools/proxy-admin-check`

```bash
ssh -f -N -L 18086:127.0.0.1:8082 osec-res2
cd ~/dev/projects/1s/osec-spider-go && go run ./tools/proxy-admin-check -addr 127.0.0.1:18086 [-window 300] [-scene xxx]
```
不依赖前端轮询；网关日志里只有前端打开页面时才有 `ProxyOverview` 记录。

## 注意

- 扫 redis `proxyMon:*` 需要密码，auto 模式分类器会拦截"从配置文件取密码拼进 ssh 命令"；
  用网关日志的 `dataSource` + 全 -1/0 的返回即可等价判断"库里无 key"，不必直连 redis。

## 代码位置

- `illuminate/proxy-client/{hook.go,classify.go}`（只暴露 hook，不含上报逻辑；加新消费端只需在 `ProxyClient{}` 填 `Scene:`）
- `illuminate/proxy-monitor/`（独立包，消费端 `Init` 注册；分钟桶 + 延迟直方图 + HLL 去重）
- 契约 COMMON `rpc/spider/proxy_admin_rpc/`
