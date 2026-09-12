# 新版 FC Chrome + 云端油猴脚本上线与集成测试 —— 共享上下文（2026-09-13）

## 背景
2026-09-08 已写完但**从未上线**的一批代码：COMMON 仓库 `fc-chrome/`（阿里云函数计算 custom-container 的 Chrome 运行环境，
支持按 URL 加载扩展、内置 Tampermonkey、自动装油猴脚本、CDP WebSocket 透传）+ userscripts 仓库云端金山文档爬虫脚本
（`src/cloud/kdocCloud.ts` → `dist-cloud/kdoc-cloud.user.js`）+ SPIDER `services/doc_crawler`（本轮**不部署**）。
上一轮留下 6 项"需人工"事项，**用户 2026-09-13 授权：ossutil / docker / serverless-devs(s) / aliyun 等运维工具全部可用，全部由 Agent 完成；
缺信息就搜阿里云官方文档**。目标：新 FC 部署上线、共用现有 FC 自定义域名加一条转发路径、跑通**线上**「新版 FC + 油猴脚本」集成测试。

## 必读（按顺序，都在 `/home/peterq/dev/projects/peterq/agent-memory-osec-spider/agent-tasks/2026-09-08-monitoring-and-doc-fc/`）
1. `05-doc-fc-contract.md` —— `/chrome` 参数、console 回传协议 `[[DOC_SPIDER]]<json>`、Tampermonkey 三条安装路径。
2. `40-fcchrome.md` §交付物 1/3 —— 当初的需求原文。
3. COMMON `fc-chrome/README.md` —— 文件清单、环境变量、本地验证做过什么、「需要人工做的事情」。

## 仓库与路径
| 简称 | 路径 | 本任务涉及 |
|---|---|---|
| COMMON | `/home/peterq/dev/projects/1s/enfi-resource-common` | `fc-chrome/`（Go 独立 module，有自己的 go.mod） |
| userscripts | `/home/peterq/dev/projects/peterq/userscripts` | `src/cloud/`、`vite.cloud.config.ts`、`package.json` 的 `build:cloud`/`upload:cloud`；**有未提交改动（`src/App.vue` `src/plugin/plugin.ts` `vite.config.ts` `src/adblock/` `src/runner.js` `src/tests/`），一律不动、不 stash、不 checkout** |
| NC-JS | `/home/peterq/dev/projects/1s/nc-js` | `apps/cdp-driver/src/main.ts` `apps/cdp-driver/s.yaml`、`admin/login3rd/src/task/task.ts` 的 `eps['prod-v3']` 回填 |
| SPIDER | `/home/peterq/dev/projects/1s/osec-spider-go` | `config/config.go` `DocCrawlerConfig` 缺省 `fc_endpoint` 回填（只改代码缺省值） |
| 旧 FC 参考 | `/home/peterq/dev/projects/1s/nerve-center/fc-entry`（**只读**） | `s.v3.yaml`、`cmd/app_cdp` |

## 现状（主控 2026-09-13 已核，不用重查）
- 本机工具：`ossutil`（`~/.ossutilconfig` 已配）、`docker` 29.7（`~/.docker/config.json` 已登录 `registry.cn-hangzhou.aliyuncs.com`）、
  `s` 3.1.1（`~/.s/access.yaml` 有别名 `shaka_osec` 与 `default`）、`aliyun` CLI 已安装但**未配置** profile；本机有 `/usr/bin/google-chrome-stable`。
- OSS `oss://osec-deploy-pub/fc-chrome/` 目前**为空**（Tampermonkey 包与云端脚本都还没上传）。
- 现有 FC 自定义域名：**`fc-resource-node-api.krzb.net`**（NC-JS `task.ts` 的 `prod-v2` 就是 `wss://fc-resource-node-api.krzb.net/chrome`），
  它不在任何仓库的 s.yaml 里——是控制台手工配的，**现有路由 `/*` 指向哪个函数必须先查出来再动**。
- 新函数名 `nc-app-prod-cdp3`，镜像 `registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:{base,app}`，region cn-hangzhou，账号 `1074692547105102`。
- 测试用金山文档：`https://www.kdocs.cn/l/cdXYaQ5EOakI`（userscripts `sumbitModal.vue` 里的示例链接）。
- `userscripts/dist-cloud/kdoc-cloud.user.js`（09-08 构建，10 KB）已存在。

## 硬性约束
- **域名方案是用户定的**：不新申请域名；在 `fc-resource-node-api.krzb.net` 上**新增**一条路径路由到 `nc-app-prod-cdp3`（建议 `/cdp3/*`），
  **现有 `/*` 路由及其目标函数不能变**。路径前缀要在到达函数前去掉（FC 3.0 域名 `rewriteConfig`），去不掉就在 `handler.go` 加 `PATH_PREFIX` 环境变量剥前缀——两者选一并写明。
- **凭据零泄露**：AK/SK/口令不得出现在命令回显、汇报、文档、commit 里；`s`/`ossutil` 用已配好的别名；需要 `aliyun` CLI 时用 `aliyun configure --profile ... --mode AK` 交互外的方式从 `~/.s/access.yaml` 同一 AK 配置（不要 cat 该文件到输出，用 `grep -c`/python 读入变量）。
- **不动生产在跑的东西**：不 deploy `nc-app-prod-cdp-driver`，不动 `nc-app-prod-cdp`/`cdp2`，不部署 SPIDER `doc_crawler`，NC-JS **禁止 `pnpm build`**（会真实上传生产 OSS），只跑 `type-check`/`tsc --noEmit`。
- 每一步的验证都要**真实执行**并贴关键输出（打码后）；做不到就写"未做 + 原因"，不要用推测代替。
- 禁止 Monitor / 禁止"起后台任务再等通知"；需要长驻进程（本地 fc-chrome server、静态文件服务）用 `nohup … &` 起、用完 `kill`，并在汇报里确认已清理。
- git：中文 commit，前缀沿用仓库习惯，不加 Co-Authored-By；只 `git add` 自己的文件（同仓库可能有别的 Agent），**用 `git commit -- <路径>` 带 pathspec**；完成后 push。
- 汇报 ≤500 字中文 + 一张"事项 → 结果/证据"表；写进本目录 `99-notes.md`（追加自己的小节），主控只读它。
