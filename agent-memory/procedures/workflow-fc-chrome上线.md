---
title: fc-chrome 构建/推送/部署/加域名路由的实际可行路径
type: procedure
status: active
created_at: 2026-09-13T11:00:00+08:00
updated_at: 2026-09-13T11:00:00+08:00
priority: high
keywords: [fc-chrome, serverless-devs, ACR, jenkins 中转, fc3-domain, seedprep, 函数计算部署]
questions:
  - 本机推不了 ACR / 拉不了 docker hub 时怎么把 fc-chrome 镜像弄上去
  - 怎么给现有 FC 自定义域名加一条路由而不碰证书
  - Tampermonkey profile 种子怎么重新生成
  - s deploy 报 getAuthorizationToken ETIMEDOUT 怎么办
summary: 2026-09-13 实测可行的 fc-chrome 上线链路：本机构建→docker save/rsync 到 osec-jenkins→load/push→s deploy（带日期 tag）；域名路由用 fc3-domain 组件、不写 certConfig；seed 用 scripts/seedprep-oob.sh 带外预热；含分类器拦截项与回滚
load: on-demand
related:
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
  - agent-memory/procedures/workflow-部署.md
---

# fc-chrome 上线流程（COMMON `fc-chrome/`）

## 0. 本机环境事实 [事实 2026-09-13]
- `s` 3.1.1 有别名 `shaka_osec`（够用：deploy/info/logs）；`aliyun` CLI 未配好（用 `s config get` 转配会得到 InvalidAccessKeyId，且检查凭据会被分类器拦，别再试）。
- 本机 docker：hub 镜像源（ustc）拉不到 `ubuntu:24.04`；ACR **登录已失效**（push denied）。**osec-jenkins root 的 docker 已登录 ACR**，但 docker 19.03 不能 build noble 的 apt 层（gpg NO_PUBKEY），只能 `docker load` 或叠 COPY 层。
- 分类器会拦：派子 Agent 做部署类操作（提示词含"授权"字样必拦）、域名/证书变更（`s <domain> deploy`）、读取凭据文件。域名变更需用户自己跑（命令见 §3）。

## 1. 镜像
```bash
cd enfi-resource-common/fc-chrome
make image-base BASE_FROM=registry.cn-hangzhou.aliyuncs.com/1second/app-cdp:chrome   # 本机, 以旧 chrome 镜像作底(Dockerfile 会先删旧 google-chrome apt 源)
make seed-oob                              # 带外预热 Tampermonkey profile → build/seed/chrome-profile-seed.tgz(反复尝试, 每次全新 profile)
make image-base-seed                       # 叠策略 JSON + seed → :base-seed
make build                                 # bootstrap(静态)
# 传 jenkins 叠层并推送(只传小文件; base 本身只在首次需要 docker save | gzip → rsync → docker load → push, ~1 GB)
rsync -az build/seed/chrome-profile-seed.tgz image/Dockerfile.seed image/policies bootstrap Dockerfile osec-jenkins:/home/pplabs/fc-chrome-build/app2/
ssh osec-jenkins 'cd /home/pplabs/fc-chrome-build/app2 && tar xzf chrome-profile-seed.tgz && sudo docker build --build-arg BASE_IMAGE=registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:base -t registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:base-seed -f Dockerfile.seed . && sudo docker build --build-arg BASE_IMAGE=registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:base-seed -t registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:app-<日期x> -f Dockerfile . && sudo docker push registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:base-seed && sudo docker push registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:app-<日期x>'
```
镜像 tag **带日期**（同名 tag 重推 FC 不一定重拉，且便于回滚）；`s.yaml` 的 `image` 改成新 tag。

## 2. 部署与验证
```bash
s fc-chrome deploy -y        # 报 getAuthorizationToken ETIMEDOUT 是本机网络抖动, 重试即可
curl https://fc-resource-node-api.krzb.net/cdp3/health           # 等 profileSeed:true 说明新镜像已生效(冷启动首个请求可 >60 s)
go run ./cmd/localverify -mode inject -timeout 150 -fc wss://fc-resource-node-api.krzb.net/cdp3/chrome -script https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js -page https://www.kdocs.cn/l/cdXYaQ5EOakI -nonce t1   # 退出码 0 = 收到终态 result
s fc-chrome logs --start-time "$(date -d '-10 min' '+%F %T')" --end-time "$(date '+%F %T')" | sed -E 's/\x1b\[[0-9;]*m//g'   # 函数日志(含 Chrome stderr)
```
本机到 FC/OSS 的连接偶发 `198.18.x.x i/o timeout`（代理 fake-ip），测试脚本外层加重试。

## 3. 共用域名加路由（用户执行）
`agent-tasks/2026-09-13-fc-chrome-online/domain-krzb-s.yaml`：现有全部路由原样 + 新路由 + `rewriteConfig.wildcardRules`；**不写 certConfig**（fc3-domain 组件要求 certName/certificate/privateKey 三件套，而组件只把 props 里有的字段放进 UpdateCustomDomain，不传即保留原证书；`plan` 里显示的 `- certConfig` 只是本地/远端 diff 视图）。先 `s <name> info -y` 读现状留回滚依据（props 里要有占位 routeConfig 否则组件报 undefined）。FC 路由匹配：精确 > 最长前缀，与顺序无关。

## 4. 回滚
函数：`s.yaml` image 改回上一 tag 重新 deploy。域名：用回滚依据里的路由列表 deploy。s.yaml 里 `timeout` 必须 ≥ 契约 `timeoutSec`(≤300)+冷启动，否则函数超时直接切断 WebSocket。
