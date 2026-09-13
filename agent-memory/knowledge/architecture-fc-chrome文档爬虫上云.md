---
title: fc-chrome（阿里云 FC Chrome 运行环境）与云端金山文档爬虫的线上拓扑
type: knowledge
status: active
created_at: 2026-09-13T11:00:00+08:00
updated_at: 2026-09-13T12:00:00+08:00
priority: high
keywords: [fc-chrome, nc-app-prod-cdp3, Tampermonkey, kdoc.user.js, fc-resource-node-api.krzb.net, doc_crawler, 函数计算, NAS, CDP3DATA, extensions=, profile=]
questions:
  - 新版 FC Chrome 部署在哪、地址、健康检查
  - cdp3 的 NAS 目录/extensions=/profile= 怎么用
  - 共用 FC 域名 fc-resource-node-api.krzb.net 有哪些路由
summary: 2026-09-13 上线的 nc-app-prod-cdp3（14:30 起挂 NAS：CDP3DATA/CDP3TEMP、extensions=、profile=、每日定时清理）（COMMON fc-chrome，Chrome 153 + Tampermonkey 5.5.0 + 预热 profile）的地址、共用域名 /cdp3/* 路由、OSS 对象、镜像 tag 与各仓库回填点；inject=1 与 Tampermonkey 两条路径线上都已跑通真实文档
load: on-demand
related:
  - agent-memory/procedures/workflow-fc-chrome上线.md
  - agent-memory/lessons/failure-品牌版Chrome禁用load-extension与userScripts二次授权.md
  - agent-memory/lessons/failure-注入脚本用consolelog回传被页面自身替换吞掉.md
---

# fc-chrome 线上拓扑（2026-09-13）

## 组件与地址 [事实]
- **函数** `nc-app-prod-cdp3`（cn-hangzhou，custom-container，timeout 600 s，2048 MB/1 vCPU，角色 `fcnervecenterrole`）。代码 COMMON `fc-chrome/`（独立 go module，`s.yaml` 在同目录）。
  - 系统域名：公网 `https://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run`，VPC `…cn-hangzhou-vpc.fcapp.run`；auto 域名 `nc-app-prod-cdp3.fcv3.1074692547105102.cn-hangzhou.fc.devsapp.net`（HTTP）。
  - **正式入口（用户决定）**：共用自定义域名 `fc-resource-node-api.krzb.net` 新增路由 `/cdp3/*` → 本函数，重写 `wildcardRules /cdp3/* → /$1`。健康：`https://fc-resource-node-api.krzb.net/cdp3/health` → `{"ok":true,"chromeVersion":"Google Chrome 153…","tampermonkey":"5.5.0","profileSeed":true}`；WS：`wss://fc-resource-node-api.krzb.net/cdp3/chrome?inject=1&script=<url>`。
  - 该域名其余路由（勿动）：`/*`→资源节点 API 函数；`/chrome`→`nc-app-prod-cdp2`（旧 CDP，NC-JS `prod-v2`）；`/proxy` `/check`→`nc-app-prod-cdp-driver`；`/nc-app-image-render-api-test/*`→测试函数。路由配置正本 `agent-tasks/2026-09-13-fc-chrome-online/domain-krzb-s.yaml`（故意不含 certConfig）。
- **镜像**（ACR `registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome`）：`:base`（ubuntu24.04+chrome153+TM 解包，**无策略文件**，2026-09-13 06:45）→ `:base-seed`（叠 `image/Dockerfile.seed`：策略 JSON + 预热 profile）→ `:app-2026MMDDx`（叠 `bootstrap`）。线上 `app-20260913h`（09-13 14:30 起），见 `s.yaml`。
- **OSS** `osec-deploy-pub/fc-chrome/`：`extensions/tampermonkey.{zip,crx}`、`extensions/tampermonkey-update.xml`（企业策略 update_url）、`userscripts/kdoc.user.js`（云端脚本，userscripts 仓库 `pnpm build:cloud && pnpm upload:cloud`）。
- **云端脚本** userscripts `src/cloud/kdocCloud.ts`：`#taskNonce=` 触发、console `[[DOC_SPIDER]]` 协议（契约 `agent-tasks/2026-09-08-monitoring-and-doc-fc/05-doc-fc-contract.md` §3）。
- **回填点**：NC-JS `admin/login3rd/src/task/task.ts` `eps['prod-v3']`（默认仍 prod-v2）、`apps/cdp-driver/s.yaml` `CDP_ENDPOINT` 注释占位（未切换）、SPIDER `services/doc_crawler/doc_crawler.go applyDefault`（`fc_endpoint`=VPC 系统域名，`fc_endpoint_public`=共用域名 /cdp3）。

## NAS 数据目录与新选项 [事实 2026-09-13 14:30 上线, 镜像 app-20260913h]
- 函数进 VPC `vpc-bp1wdtkktehlgutkby11k`，挂 NAS `00acc494e8-fnw4`：根 → `/mnt/nas`，`/temp` → `/mnt/temp`。开发机同一 NAS 在 `~/mnt/nerve-center-nas/`（`systemctl --user start nerve-center-nas.service`）。
- `CDP3DATA=/mnt/nas/apps/cdp3`：`extensions/<name>/|<name>.crx(+<name>.pem)`、`profiles/<ns>/<name>.tar(+.lock)`、`asset-cache/`（NAS_CACHE_DIR）；`CDP3TEMP=/mnt/temp/cdp3` 由 timer 触发器 `cleanTempTimer` 每天 04:30 清 >24 h 条目。NAS 上 `apps/cdp3/README.md` 有说明。
- `/chrome` 新 query：`extensions=a,b`（策略强装）、`profile=<namespace>/<name>`（持久化；**客户端须先发 `Browser.close` 等响应再断开**）；新错误码 409 profile 被占、504 扩展没装上。`/health` 多了 `cdp3Data/cdp3Temp.writable`、`policyDirWritable`。
- 机制与坑：`decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md`、`lessons/success-cdp3策略强装扩展与NAS持久化profile.md`、`lessons/failure-FC实例在WebSocket断开后立即冻结.md`；验证工具 `fc-chrome/cmd/cdp3verify`。

## 两条脚本执行路径 [事实]
- **`inject=1`（CDP 主世界注入）**：线上经共用域名对真实文档 `https://www.kdocs.cn/l/cdXYaQ5EOakI` 全通：握手 5 s → start → progress → `result ok:true`（quark 链接列表），20 s。**doc-crawler 的可信默认通道。**
- **Tampermonkey 原生路径**（不带 inject）：品牌版 Chrome 不能 `--load-extension`，改企业策略 `ExtensionSettings force_installed` + 带外预热 profile（含 Chrome 138+ "Allow User Scripts" 开关）；线上 2026-09-13 11:41 终验通过（9 s 拿到 result）。曾经"装上不执行"的根因是脚本 `@match` 缺 SSO 首跳域名 `account.kdocs.cn`（见 `lessons/failure-品牌版Chrome禁用load-extension与userScripts二次授权.md`）。

## 状态
- [用户确认 2026-09-13] cdp-driver **暂不切**新实例（仍指 v2）；PC 端油猴调度器**不下线**，与云端并存。未做：SPIDER `doc_crawler` 部署主机待定；ACR `:base` 重推为含策略的版本（现靠叠层补）。
