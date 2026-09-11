# 40-fcchrome —— 新版 FC Chrome 环境（支持扩展/油猴）+ 云端金山文档爬虫脚本

先读 `00-shared.md` 与 `05-doc-fc-contract.md`，再读本文件。
你负责**云端浏览器侧**：新 FC 项目、cdp-driver 切换、油猴脚本移植。
并行的角色 41 负责服务端 `doc-crawler` 进程，你们之间的接口以 `05-doc-fc-contract.md` 为准。

## 用户原话（本角色相关部分）

> 前置任务
> - 现有 chrome fc运行环境无插件, 创建一个新的fc实例. 文件放到 COMMON 仓库
>   - 支持启动参数传插件url(放入 oss 桶 osec-deploy-pub), 通过内网下载并缓存至/tmp或nas, 启动chrome时指定插件
>   - 油猴插件作为内置插件, 无需指定默认加载
>   - 支持传入油猴脚本url, 油猴启动时自动加载脚本
> - 原有 chrome fc 环境项目目录(来自其他项目的一个子工程): /home/peterq/dev/projects/1s/nerve-center/fc-entry
>   现在的 app/cdp-driver 就依赖了他, `ws://nc-app-prod-cdp-xmmmpvnmqb.cn-hangzhou.fcapp.run/chrome` .
>   把现有依赖改为新的实例
> - 金山文档基于油猴的爬虫 /home/peterq/dev/projects/peterq/userscripts/src/plugins/kdoc/kdocSpider.ts 也移植过来

## 交付物 1：新 FC Chrome 项目（落在 COMMON 仓库）

**落点：`/home/peterq/dev/projects/1s/enfi-resource-common/fc-chrome/`，自带独立 `go.mod`**
（module 名 `github.com/1s/enfi-resource-common/fc-chrome`）。

⚠️ **必须是嵌套的独立 module**：COMMON 的根 `go.mod` 被 SPIDER/STORAGE/API 三个仓库依赖，
不能因为一个 FC 函数就把 aliyun SDK / websocket 依赖塞进去。参考先例：
SPIDER 的 `tools/ujuso-captcha/` 就是独立 go.mod。写完在 COMMON 根目录跑 `go build ./...`
确认根 module 不受影响（嵌套 module 会被自动排除）。

### 参考实现（只读，禁止修改）

`/home/peterq/dev/projects/1s/nerve-center/fc-entry`（**该仓库有未提交改动，绝对不要碰它**）：

| 文件 | 提取什么 |
|---|---|
| `cmd/app_cdp/app_cdp.go` | 全部逻辑：`HandleHttp()` 路由(`:34-62`)、Chrome 启动参数(`:250-269`)、从 stderr 正则抓 ws 端点(`:148,:156`)、`/chrome` 的 WS 双向透传(`:300-374`)、临时 profile 与 `clearTmpDir()`(`:165`)、`updateEnv()` 每 100 次强制换实例(`:104`) |
| `fc-framework/*.go` | FC custom runtime 的最小框架（监听 `FC_SERVER_PORT`，默认 9000），**照抄进新项目**，不要 import nerve-center |
| `cmd/app_cdp/image/Dockerfile` | 基础镜像：ubuntu24.04 + google-chrome-stable + 中日泰字体 |
| `cmd/app_cdp/Dockerfile` | 部署镜像：基础镜像 + COPY bootstrap |
| `s.v3.yaml:56-102` | serverless-devs fc3 的资源描述（函数名/内存/超时/角色/环境变量/httpTrigger/自定义域名） |
| `Makefile:50-66` | build / deploy / local start 的命令形态 |
| `cmd/app_cdp/test.bash` | 本地用官方 runtime 镜像模拟 FC 的办法 |

### 必须实现的能力（细节见 `05-doc-fc-contract.md` §2）

1. **`--headless=new`**：老的 `--headless` **不支持扩展**，必须换成 `--headless=new`。
   同时**移除** `--disable-extensions` 与 `--disable-component-extensions-with-background-pages`
   （现有 `app_cdp.go:253-254` 带着它们）。
2. **扩展下载与缓存**：
   - 下载源限制在白名单域（环境变量 `ALLOWED_ASSET_HOSTS`，缺省 `osec-deploy-pub` 的 OSS 公网 + 内网域名）
   - **FC 内优先走内网**：检测到 `FC_CONTAINER_ID` 环境变量时，把 URL 里的
     `oss-cn-hangzhou.aliyuncs.com` 自动改写成 `oss-cn-hangzhou-internal.aliyuncs.com`
   - 缓存目录：`NAS_CACHE_DIR` 环境变量优先，否则 `/tmp/fc-chrome-assets`
   - 缓存 key = URL 的 sha256；缓存里放解包后的目录 + 一个 `.meta.json`（url/etag/大小/解包时间）
   - 支持 `.zip` 与 `.crx`（crx 前 16 字节是头，剥掉后就是 zip；**要处理 crx2 与 crx3 两种头格式**）
   - 解包要防 zip-slip（路径穿越）
   - 并发下载同一 URL 时用 singleflight/文件锁，避免重复解压
   - 缓存总量上限（默认 512MB，超了按 LRU 删）
3. **内置 Tampermonkey**：镜像构建时下载并解包到 `/opt/extensions/tampermonkey`，
   启动 Chrome 时默认带上（`noTm=1` 可关）。
   - 下载地址用 Dockerfile 的 `ARG TAMPERMONKEY_URL`，缺省指向
     `https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/extensions/tampermonkey.zip`
   - **该文件目前不存在，需要人工上传**：`ARG` 拿不到文件时构建要**只警告不失败**，
     运行时 `/health` 里 `tampermonkey` 返回 null
4. **自动装油猴脚本**：见 `05-doc-fc-contract.md` §5 的三条路径，兜底的 CDP 主世界注入必须实现并本地验证。
5. **失败要在 WS 握手前以 HTTP 错误返回**（现有实现的痛点）。
6. **`/health` 端点**。
7. 保留 `updateEnv()` 那套"每 N 次调用强制换实例"，但把 N 做成环境变量可配（缺省 100），
   并且**允许通过环境变量完全关掉**（本地调试时它会一直报错）。

### 部署脚手架（写脚本与文档，**不要执行**）

- `fc-chrome/Makefile`：`build` / `image` / `deploy` / `local`
- `fc-chrome/s.yaml`（serverless-devs fc3，edition 3.0.0）：新函数名用 **`nc-app-prod-cdp3`**，
  内存/超时/角色照抄旧的；httpTrigger anonymous + fc3-domain auto
- `fc-chrome/README.md`：镜像怎么建、怎么发、怎么本地跑、环境变量表、query 参数表、
  Tampermonkey 包怎么准备、**新实例上线后要改哪些调用方的 endpoint**

## 交付物 2：把 cdp-driver 的依赖改为新实例（可配置，不写死）

`/home/peterq/dev/projects/1s/nc-js/apps/cdp-driver/src/main.ts:10-13`
现在写死 `nc-app-prod-cdp-xmmmpvnmqb`。改成：

```ts
const cdpEp = process.env['CDP_ENDPOINT'] ??
  (process.env['FC_CONTAINER_ID'] ? '<vpc 缺省>' : '<公网缺省>')
```

- 缺省值**先保留现有旧域名**并加 TODO 注释说明"新实例 `nc-app-prod-cdp3` 上线后改这里或配环境变量"
- 同时在 `apps/cdp-driver/s.yaml` 的 `environmentVariables` 里加上 `CDP_ENDPOINT` 占位（注释掉或留空）
- 另一个调用方 `/home/peterq/dev/projects/1s/nc-js/admin/login3rd/src/task/task.ts:11-20` 的 `eps` 表里
  **加一条 `'prod-v3'`**（值留 TODO 占位），不要删除现有条目、不要改默认选中项
- ⚠️ 不要跑 `pnpm build`（会真实上传生产 OSS）；只跑 `pnpm -F <包> type-check` 或 `npx tsc --noEmit`

## 交付物 3：移植金山文档爬虫（云端版）

源：`/home/peterq/dev/projects/peterq/userscripts/`
（**该仓库有未提交改动：`src/App.vue`、`src/plugin/plugin.ts`、`vite.config.ts`、`src/adblock/`、`src/runner.js`。
你只新增文件，不要动这些，也不要 checkout/stash**）

- 解析逻辑正本：`src/plugins/kdoc/kdocUi.tsx`（476 行，`kdocSpider.ts` 只是 40 行的注册壳）
  - `copySheet()` `:100-182`：调 `window.APP` 的内部 SDK 遍历 sheet；`prepareBlock` 懒加载分块
    (`:67`)、`waitRow` 轮询 (`:77-84`)、`loadSheetDelayed` (`:86`)、
    **超链接 `sheet.getHyperlink()` 拼成 `文本(地址)`** (`:150-153`)、每 1000 单元格让出 CPU (`:157-160`)、
    连续 1000 行空则 break (`:136,:164`)
  - 就绪判定 `:213-224`：`window.__WPSENV__.office_type ∈ {s,k,d}`，取 `file_info.file.modify_time`
  - 隐藏 sheet：`hackSheet` `:287-296` 劫持 `getVisible`
  - 链接提取：`src/plugins/scheduler/spiderUtil.ts:9-12,39-61`（4 种网盘正则 + 前后 50 字符找提取码）
  - 版本号：`calVersion()` `:362-378` —— url 去重 → 排序 → `join('\n')` → **SHA-1**
- **新增一个云端构建 target**（不要改动现有那个面向 PC 的 target）：
  - 建议 `src/cloud/kdocCloud.ts` + `vite.cloud.config.ts` + `package.json` 加 `build:cloud`
  - 产出**单文件、无外链 require、无 Vue、无 gRPC/WebRTC**的 `.user.js`
    （现有 target 的 header 会 `require` jsdelivr 上的 Vue，云端不要）
  - `@match` 收窄为 `https://365.kdocs.cn/l/*` 与 `https://www.kdocs.cn/l/*`，`@run-at document-start`
  - 行为：读 `location.hash` 的 `#taskNonce=`；没有 nonce 就什么都不做（**不能影响人手动打开文档**）；
    有 nonce 就等页面就绪 → 解析 → 按 `05-doc-fc-contract.md` §3 的 console 协议回传
  - **不要**调 `commitResource2`、不要 `hostEnv`、不要 `GM_openInTab`、不要自关标签页
  - 上传脚本：`ossutil cp -f dist/kdoc-cloud.user.js oss://osec-deploy-pub/fc-chrome/userscripts/kdoc.user.js`
    —— **写进 package.json 但不要执行**（无凭据）

### 本地验证（这条必须真的跑）

用 `/home/peterq/dev/projects/1s/enfi-resource-common/scripts/agent-browser.sh` 起调试 Chrome
+ `scripts/cdp.py` 驱动（用法见 `agent-memory/procedures/workflow-带登录态的浏览器自动化.md`）：

1. 起一个本地 http server 提供构建好的 `.user.js`
2. 用 CDP `Page.addScriptToEvaluateOnNewDocument` 注入（模拟 §5 路径 3）
3. 打开一个**公开可访问的金山文档分享链接**（如果找不到公开样本，就用
   `/home/peterq/dev/projects/1s/osec-spider-go/services/online_doc/king_soft/temp/` 下抓下来的
   html 样本起本地页面做**降级验证**：至少验证"脚本能加载、能识别 nonce、能按协议输出 error 事件"）
4. 把 console 输出抓下来，证明协议格式正确

**没有真实金山文档样本时，不要假装验证通过**，如实写"仅验证了协议与加载路径，解析逻辑未联网验证"。

另外：被删除的老服务端实现可以当参考（纯 HTTP 版，因表格懒加载而走不通）：
`cd /home/peterq/dev/projects/1s/osec-spider-go && git show d0e7aac^:services/online_doc/king_soft/king_soft.go`

## 交付

分支：COMMON `feat/fc-chrome`，NC-JS `feat/fc-chrome`，userscripts `feat/kdoc-cloud`。

汇报里必须写清：
1. 新 FC 项目的文件清单与每个文件的职责
2. `cd fc-chrome && go build ./... && go vet ./...` 的真实输出；COMMON 根目录 `go build ./...` 仍然通过
3. Tampermonkey 三条安装路径你各实现到什么程度、哪条验证过、哪条没验证
4. 本地 Chrome 验证的实际过程与 console 输出原文
5. 需要人工做的事情清单（至少包含：Tampermonkey 包上传 OSS、镜像构建与推送 ACR、
   FC 函数部署、新域名回填到 cdp-driver / login3rd / doc-crawler 配置）
