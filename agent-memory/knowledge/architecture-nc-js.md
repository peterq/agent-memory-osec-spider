---
title: NC-JS 前端仓库架构
type: knowledge
status: active
created_at: 2026-09-04T12:56:00+08:00
updated_at: 2026-09-10T08:20:00+08:00
priority: high
keywords:
  - qiankun-head
  - 样式丢失
  - NC-JS
  - 前端
  - qiankun
  - 微前端
  - Vue3
  - TSX
  - ant-design-vue
  - pnpm
  - vite
  - WebRTC
  - protobuf-ts
  - 后台页面
  - 队列监控
  - spiderAdmin
  - GitHub OAuth
  - 登录门
  - GwLoginGate
summary: NC-JS 前端 mono repo 的分包布局、架构图页与构建时同步、qiankun 微前端注册与部署机制、与 SPIDER 网关的 WebRTC gRPC 对接方式（鉴权已改 GitHub OAuth，未部署）、以及新增后台页面的标准写法与落点
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/api-rpc契约.md
  - agent-memory/00-overview.md
  - agent-memory/decisions/decision-2026-09-08-后台登录改为github-oauth.md
  - agent-memory/lessons/failure-握手回包附加字段被传输层丢弃.md
---

# NC-JS 前端仓库架构

磁盘路径：`/home/peterq/dev/projects/1s/nc-js`（记为 NC-JS）。初次调研 2026-09-04 上午；
同日晚完成两个子应用的合并改造（见 §3.1 与 §7）。

## 1. 仓库定位

- [事实] NC-JS 是 "nerve-center" JS/TS mono repo，不只服务本项目：`apps/cdp-driver`（阿里云函数计算上的
  headless chrome 服务）与本项目无关。**与网盘取证系统相关的全部在 `admin/`**。
- [事实] `admin/*` 是由 **qiankun 2.x** 管理的多个微前端子应用，统一构成"NC ADMIN"后台，
  用于管理爬虫任务、网盘账号与转存下载、爬虫调度配置。
- [事实] 后台前端**只连 SPIDER 的 gateway**，不调 API 仓库（`osec-resource-api`）的任何 HTTP 接口。

## 2. 工程栈

| 项 | 取值 |
|---|---|
| 包管理 | pnpm 8.15.6（`packageManager` 锁定），workspace = `apps/*`、`packages/*`、`admin/*` |
| Node | `engines.node >= 18`（多数子包 `@tsconfig/node22`） |
| 构建 | Vite 6 + `@vitejs/plugin-vue` + `@vitejs/plugin-vue-jsx` |
| 框架 | **Vue 3.5**，全 TypeScript |
| 写法 | **以 TSX 为主**（`defineComponent` + `setup` 返回 render 函数），少量 `.vue` SFC（`<script setup>`） |
| UI | **ant-design-vue 4.x** + `@ant-design/icons-vue`，样式用 less |
| 状态管理 | **无 pinia/vuex**。跨组件状态用 `provide/inject`（见 `spiderAdmin` 的 `Scheduler` 类、`QueueCtxProvider`）+ `@vueuse/core` 的 `useLocalStorage` |
| 路由 | **无 vue-router**。子应用内部靠 `<Tabs>`（旧）或左侧 `<Menu>` + 自维护 activeKey（`spiderAdmin`）切页，选择存 localStorage；"路由"由 qiankun 的 `activeRule` 路径前缀决定 |
| 测试 | vitest（根 `vitest.workspace.ts` 聚合各子应用配置） |
| Lint | eslint 9 flat config + oxlint + prettier（`semi:false, singleQuote:true, printWidth:100`） |
| CI | [事实] **没有任何 CI 配置**（无 `.github/` 等），构建与发布全靠本地命令 |

## 3. 分包布局

### 3.1 `admin/`（本项目相关）

| 目录 | 包名 | qiankun name / activeRule | 职责 | 后端 RPC |
|---|---|---|---|---|
| `admin/qiankun` | `@nc/admin-qiankun` | 主应用 | 加载 `apps.json` 注册全部子应用；右侧悬浮球展开应用卡片导航 | 无 |
| `admin/spiderAdmin` | `@nc/spider-admin` | `spiderAdmin` / `/spiderAdmin` | 「🕷️ 爬虫管理台」：左侧栏三组菜单 —— 队列监控(总览/队列详情/日志搜索/黑名单) + 资源配置(配置项) + 文档爬虫(爬取中/队列中/已收录) | `QueueAdminRpc` / `ResSchedulerRpc` / `DocSchedulerRpc` |
| `admin/panShareDownload` | `@nc/pan-share-download` | `panShareDownload` / `/pan-share-download` | 「网盘分享转存 oss 管理页」：Grafana 运行状态、转存文档列表、网盘账号管理 | `DownloadSchedulerRpc` |
| `admin/login3rd` | `@nc/login3rd` | `login3rd` / `/login3rd` | chrome 自动化平台，被别的子应用当作**弹窗服务**调用（扫码登录百度/阿里，取 cookie/token） | 走 CDP，不走网关 |
| `admin/test_data` | — | — | 两个 `*.hide.json/ts` 测试数据，已被 `.gitignore` 的 `*.hide.*` 排除 | — |

- **[事实 2026-09-04 晚] `docSpiderScheduler` 与 `resSpiderScheduler` 已合并成 `spiderAdmin`，
  两个旧目录已删除**（见 `decisions/decision-2026-09-04-前端合并为spiderAdmin.md`）。
  资源调度/队列/文档爬虫相关的新页面一律加到 `spiderAdmin` 的左侧菜单里。

### 3.2 `packages/`（共享包）

| 包 | 说明 |
|---|---|
| `packages/catalyst`（`@nc/catalyst`） | **核心共享库**：RPC 契约与传输、qiankun 接入、弹窗管理器、vue hooks、格式化工具。子应用几乎所有公共能力都来自这里 |
| `packages/build`（`@nc/build`） | 自研 vite 插件 `mfe()`：dev 时写 `apps.json`、build 时改产物 URL 并上传 OSS |
| `packages/fc-framework`、`fc-util`、`typescript-config`、`eslint-config` | 阿里云函数计算脚手架与共享配置，**与本项目无关** |

catalyst 关键目录：

```
packages/catalyst/
├── base/            event.ts / async.ts / algo.ts / formatter.ts(humanSize, err2str) / types.ts
├── ui/
│   ├── microFe/entry.ts        initMicroFeApp：子应用统一入口
│   ├── microFe/modals.ts       跨子应用弹窗调用（openMfeModal / MfeModalRouter / genMehtods）
│   ├── microFe/contract/       跨子应用调用的类型契约（目前只有 login3rd.ts）
│   ├── widget/ModalManager.tsx 函数式 Promise 化弹窗管理器（含中文注释，是本仓最讲究的一块）
│   ├── vueutil/hooks.ts        useWatchToPromise / useDisposePromise / useTimeoutToRef
│   ├── vueutil/layzload.ts     BatchLoader：列表里按需批量拉详情
│   └── icons/emoji.ts          Emoji 常量表
└── contract/rpc/
    ├── grpc_rtc/              WebRTC DataChannel 上的 gRPC 传输实现
    ├── spiderGw/spidergw.ts   useGwClient()：一次性拿到 5 个 rpc client(含 queueAdminRpc)
    ├── spiderGw/queueAdmin.ts 只剩 useQueueAdminMock() 一个 mock 开关
    ├── spiderGw/queueAdminMock.ts 内存态假数据客户端
    └── scheduler/proto/**     protobuf-ts 生成代码（来自 COMMON 的 .proto）
```

## 4. qiankun 微前端机制（重点）

- [事实] 主应用 `admin/qiankun/index.html` 用 **CDN script 引入 qiankun 2.10.16 UMD**（不是 npm 依赖），
  挂到 `window.qiankun`；`src/comps/Main.tsx` 负责 `registerMicroApps` + `start({prefetch:true, singular:false})`。
- [事实] **子应用清单不写在代码里**，而是运行时 fetch 一个 `apps.json`：
  - 生产：`https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/frontend/admin-mfe/apps.json`
  - 本地（`location.hostname === 'localhost'`）：`/apps.json`
  - 条目结构 `AppEntry { name, entry, container:'#subapp-viewport', activeRule, title, homepage, description, icon?, buildAt? }`
- [事实] 子应用**不自己写 qiankun 生命周期**，统一：
  - `vite.config.ts` 里用 `mfe(appsFilePath, entry)`（来自 `@nc/build`），内部含 `vite-plugin-qiankun`
  - `src/main.ts` 里用 `initMicroFeApp({ createApp, container:'#app', registerModalCall? })`
  - 非 qiankun 环境（直接 `pnpm dev` 打开）会自动降级为独立应用挂载，可单独开发
- [事实] `activeRule` 与 `homepage` 都是同一个**路径前缀**（如 `/pan-share-download`），主应用没有菜单，
  导航靠悬浮球里的应用卡片 `location.href = homepage`。
- [事实] **跨子应用弹窗调用**是本仓特色：`openMfeModal(appName, fn, param)` 会 `loadMicroApp` 目标子应用，
  通过 props `$callModal$` 传入调用，目标子应用用 `MfeModalRouter.registerModal(fn, Comp)` 响应，
  结果以 Promise 返回。契约写在 `catalyst/ui/microFe/contract/*.ts`（例：`appLogin3rd.chrome({...})`）。

### 本地开发流程 [推断，未实跑]

1. `pnpm install`（根目录，pnpm workspace）
2. 主应用：`admin/qiankun` 先 `vite build` 出 `dist/`，再 `pnpm dev`（= `wrangler pages dev`，服务 `dist/`）
3. 子应用：`cd admin/<app> && pnpm dev`，`writeMfeEntry` 插件会把本机 dev server 地址写进
   `admin/qiankun/dist/apps.json`，主应用刷新即可加载
4. 只调子应用页面本身时可以不起主应用，直接 `pnpm dev` 独立跑（会走 `initMicroFeApp` 的降级分支）

### 部署 [事实]

- 子应用：`pnpm build`（默认 production mode）→ `deployToOss` 插件把 `dist/` 用 **`ossutil`** 传到
  `oss://$OSS_DEPLOY_PUB_BUCKET/frontend/admin-mfe/<name>/`，并原子更新 OSS 上的 `apps.json`
  （改写 entry 为带 `?t=` 时间戳的 index.html）。
- 主应用：`admin/qiankun` 的 `pnpm deployProd` = `vite build && wrangler pages deploy`，
  发到 **Cloudflare Pages**（project `1s-nc-admin-qiankun`）。
- 凭据从 `$BUILD_ENV_FILE` 或默认 `~/dev/test.env` 读取（`OSS_ACCESS_KEY_ID/SECRET/OSS_DEPLOY_PUB_BUCKET`）。
  ⚠️ 该文件是明文密钥，**禁止**读入记忆文件或输出。
- 前置依赖：本机需装 `ossutil`、`wrangler` 并已登录。

## 5. 与后端如何对接（重点）

- [事实] **没有 REST、没有 axios、没有 baseURL/proxy 配置**。后台所有数据都走
  **WebRTC DataChannel 上自实现的 gRPC 传输**，直连 SPIDER gateway。
  - 传输实现：`packages/catalyst/contract/rpc/grpc_rtc/{rtc-rpc.ts,RtcTransport.ts,packet-stream.ts}`
  - 生产网关地址写死在 `rtc-rpc.ts`：`gwAddrs = [{名:'正式环境', ipList:['115.29.215.228']}, {名:'本地环境', ipList:['127.0.0.1']}]`，端口 `7542/udp`；页面右上角可切换，选择存 localStorage `gwEndpoint`
  - 做法是伪造一份固定的 SDP answer（ice-ufrag `osec-anti-spider-server`），客户端只发 offer 即可连通
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
- [事实] 入口 hook：`useGwClient({ipList, uiInputToken, uiInputClientName, onCallError})`
  （`catalyst/contract/rpc/spiderGw/spidergw.ts`）一次返回
  `resSchedulerRpc / spiderRpc / docRpc / downloadRpc / queueAdminRpc` 五个 client
  + `initialized` / `usingMock` ref。连接建立前页面渲染 `Spin+Skeleton`，`initialized` 为 true 后再渲染正文。
  **[事实 2026-09-04 晚] 一个子应用只应建一条 RTC 连接**：`queue_admin` 并入网关后
  `queueAdminRpc` 也挂在这条 transport 上；文档爬虫的 `Scheduler` 类原来自建第二条连接，
  已改为由外壳把 client 传进去。`queueAdminMock` 开关打开时 `queueAdminRpc` 换成内存假数据客户端。
- [事实] proto 生成：`packages/catalyst/scripts/devops/protc_gen.sh`（`pnpm -F @nc/catalyst gen:proto`），
  用 `protoc --ts_out`（protobuf-ts 2.9.4）从 **COMMON 的 `rpc/`** 生成到
  `catalyst/contract/rpc/scheduler/proto/`；另从 SPIDER 的
  `services/gateway/rtc-gateway/grpc_proxy/message.proto` 生成 RTC 帧结构。
  ⚠️ **脚本里的 `PROTO_ROOT` 还是重命名前的老路径 `/home/peterq/dev/projects/pplabs/enfi-resource-common/rpc`，
  现在应是 `/home/peterq/dev/projects/1s/enfi-resource-common/rpc`，直接跑会失败，需先改路径。**
- [事实 2026-09-04] 已生成的 `res_scheduler` TS 客户端与 COMMON 当前 proto **方法集一致**（11 个方法），
  队列 v2 没有改动 proto 的 service 定义，所以前端契约没有落后。

### 现有 RPC → 页面对应

| 子应用 | 用到的 RPC | 主要方法 |
|---|---|---|
| spiderAdmin(资源配置/黑名单) | `spider.resScheduler.ResSchedulerRpc` | `adminHashKeys` / `adminHashGetAll` / `adminHashAdd` / `adminHashRemove` |
| spiderAdmin(文档爬虫) | `spider.docScheduler.DocSchedulerRpc` | `getQueueLength` / `getQueuedUrls` / `getTaskBatch` / `queryDocPagination` / `deleteWaiting` / `setTaskPriority` / `submitDoc` |
| spiderAdmin(队列监控) | `spider.queueAdmin.QueueAdminRpc` | `overview` / `listTasks` / `getTask` / `getDetailSchemas` / `queueStats` / 批量重推与删除 / 日志与审计查询 |
| panShareDownload | `DownloadSchedulerRpc` | `monitorConfig`(返回 grafana url+账号) / `listDownloadGroup` / `queryShareFilePagination` / `getDownloadGroupInfo` / 账号增删改 |
| 全部 | `spider.SpiderRpc` | `pong`(心跳/连通性) / `getDefaultClientName` / `setClientName` |

[事实] 浏览器里直连网盘接口时（panShareDownload 的百度网盘解析）会经过一个 CORS 代理
`https://fc-resource-node-api.krzb.net/proxy`（`admin/panShareDownload/src/pan/panUtil.ts`）。

## 6. 页面写法约定（可直接抄的代表性文件）

| 我要写 | 抄这个文件 |
|---|---|
| 子应用外壳（连网关 + 侧栏菜单 + 弹窗管理器 + 网关切换） | `admin/spiderAdmin/src/layout/AppLayout.tsx`（最新最完整）或 `admin/panShareDownload/src/ui/panShareDownloadUi.tsx`（多 Tab 老写法） |
| 子应用入口 | `admin/spiderAdmin/src/main.ts` + `vite.config.ts` |
| **队列/任务列表页（分页 + 自动刷新 + 行内操作）** | `admin/spiderAdmin/src/pages/doc/comps/queuedTasks.vue` |
| 普通分页表格页（TSX 版，含筛选/统计条） | `admin/panShareDownload/src/ui/panShareDownloadFilelist.tsx` |
| 卡片式导航页 + 打开弹窗 | `admin/spiderAdmin/src/pages/res/RdsConfPage.tsx` |
| 弹窗内的增删改表格 | `admin/spiderAdmin/src/modals/ModalConfItem.tsx` |
| 嵌 Grafana 看板 | `admin/panShareDownload/src/ui/panShareDownloadMonitor.tsx` |
| 跨组件共享 rpc/状态（provide/inject） | `admin/spiderAdmin/src/scheduler/Scheduler.ts`、`src/pages/queue/QueueCtxProvider.tsx` |
| 列表懒加载详情 | `packages/catalyst/ui/vueutil/layzload.ts` 的 `BatchLoader` |

约定要点：
- 组件用 `defineComponent({ props: xxxProps(), setup(props){ ... return () => <jsx/> } })`；
  props 用一个返回对象的函数（如 `rpcProps()`）导出复用，rpc client 通过 props 往下传。
- 目录：`src/layout/`（外壳）、`src/pages/<模块>/`（页面）、`src/modals/`（弹窗）、
  `src/style/main.less`；别名 `@` → `./src`。（`panShareDownload` 等老子应用把页面与弹窗混放在 `ui/`。）
- 自动刷新固定套路：`useDocumentVisibility()` + `useTimeoutToRef(5e3)` + `useWatchToPromise(...)` +
  `useDisposePromise()`，只在页签可见且当前 Tab 展示时轮询（见 `queuedTasks.vue`）。
- 报错统一走 `useGwClient` 的 `onCallError` → `notification.error`，业务错误码在
  `catalyst/contract/rpc/scheduler/scheduler.ts` 的 `ErrorCodes`（110101 NoMoreTask 等）里按需忽略。
- 弹窗一律用 `ModalManager.useInit()` + `useModal(wrapModal(Comp,false))`，业务组件 `emit('resolve'|'reject')`；
  简单输入直接 `modals.prompt(...)`。
- proto 里的 int64 在 TS 侧是 **BigInt**，传参要 `BigInt(x)`，展示要 `Number(x)` / `.toString()`。
- mock 只有队列监控这一套（`catalyst/.../spiderGw/queueAdminMock.ts`，顶栏开关）；其余 RPC 无 mock，
  本地开发直接连"本地环境"网关（127.0.0.1:7542）或正式环境网关。

## 7. 新增后台页面的落点结论

> [事实 2026-09-04 晚] `docSpiderScheduler` + `resSpiderScheduler` 已合并成
> **`admin/spiderAdmin`**（`@nc/spider-admin`，activeRule/homepage `/spiderAdmin`），
> 旧两个目录已删除。见 `decisions/decision-2026-09-04-前端合并为spiderAdmin.md`。

**要加一个爬虫/队列/调度相关的后台页面，就是在 `spiderAdmin` 的左侧菜单里加一项**，
不要新建子应用（新建要额外占 OSS 目录、apps.json 条目与独立部署，收益为零）。

`admin/spiderAdmin/src/` 结构：

| 目录 | 内容 |
|---|---|
| `layout/AppLayout.tsx` | 外壳：建唯一一条 RTC 连接、顶栏(环境切换/连接状态/Mock 开关/clientName)、侧栏菜单、内容区分发 |
| `layout/navState.ts` | `MenuKeys` 枚举 + `activeMenuKey`/`siderCollapsed`（localStorage），**代替路由** |
| `layout/LazyKeepAlive.tsx` | 复刻 AntDV `<Tabs>` 的"首次访问才挂载、之后只隐藏"语义，保住分页/自动刷新状态 |
| `layout/Page.tsx` / `PageHeader.tsx` | 统一页头(标题+说明+extra 按钮) + 卡片式页体 |
| `pages/queue/` | 队列监控 4 页 + `QueueCtxProvider` + schema 渲染器 / JSON 树 / 迷你折线图 / 任务详情抽屉 |
| `pages/res/RdsConfPage.tsx` | 资源调度配置项 |
| `pages/doc/comps/*.vue` | 文档爬虫三页（SFC，从旧子应用原样搬迁） |
| `scheduler/Scheduler.ts` | 文档爬虫状态中枢，**复用外壳的 client，不自建连接** |
| `scripts/removeMfeApps.mjs` | 从生产 apps.json 摘除已下线子应用条目（默认 dry-run，`--yes` 才写） |

加页面的动作：`navState.ts` 加一个 `MenuKeys` 项 → `AppLayout.tsx` 的 `<Menu>` 加一项 +
`LazyKeepAlive` 的插槽里加一个 `<Page>`。**没有路由表、没有菜单配置文件、没有权限配置**。

**schema 驱动渲染**：本仓原本没有任何通用 schema 渲染机制，队列监控这套
（`pages/queue/SchemaRenderer.tsx` + `schema.ts`，按后端 `GetDetailSchemas` 下发的 JSON 注册表渲染、
未知 widget 兜底 JSON 树）是唯一一份，需要类似能力时复用它。

### 7.1 架构图页与构建时同步（2026-09-07）

- [事实] `spiderAdmin`「资源生命周期」菜单组新增「架构图」页（`MenuKeys.LcDiagrams`，`src/pages/lifecycle/LcDiagramsPage.tsx`）：
  `Segmented` 切换资源视角/服务端视角，`<iframe>` 内嵌 archify 产出的自包含 HTML，可新窗口打开。
- [事实 2026-09-10，NC-JS `6ce0b9b`] **OSS 上的 `.html` 不能直接 `<iframe src>` / `window.open`，会被响应头强制下载**
  （用户反馈）。页面已改为 `fetch` 取文本 → `iframe srcdoc` 渲染；「新窗口打开」改为把文本包成 Blob URL 再 open。
  按视角缓存文本、带 Spin/Alert。archify HTML 内的 `location.search`/`localStorage` 均有兜底，srcdoc 下正常。
  **凡是把 HTML 类静态产物放 OSS 再嵌入的场景都沿用这一做法**，不要再试 `src` 直连。
- [事实] HTML 来源是 SPIDER `PRD/res-lifecycle/diagrams/*.html`，由 `scripts/syncDiagrams.mjs` 在 `predev`/`prebuild`
  钩子（pnpm 默认执行 pre 脚本，已实测）复制到 `src/assets/diagrams/`（**纳入 git**，源目录不存在只警告不失败；
  可用 `RES_LIFECYCLE_DIAGRAMS_DIR` 覆盖源目录）。改图流程：改 SPIDER 的 JSON → `archify deliver` → 重新 build 前端。
- [事实] Vite 6 对 `import x from '*.html?url'` 按普通静态资源处理（原样拷贝到 `dist/assets/` 带 hash），
  `mfe()` 的 `renderBuiltUrl` 不按扩展名过滤，生产会改写成 OSS 绝对地址；`vite/client` 已含 `*?url` 声明无需补类型。
- [事实 2026-09-10 实测] dev 模式下 Vite 对该路径会走 transformIndexHtml，仅在 `<head>` 注入一行 qiankun 版
  `/@vite/client` import，其余原样；srcdoc iframe 与父页同源，该注入无害。生产 OSS 原样返回。

## 8. 已知坑 / 待确认

- [事实 2026-09-08，已修复] **catalyst `initMicroFeApp` 原来把 Vue 直接挂在 qiankun 包裹层上**，Vue `mount()` 清空容器会把
  `<qiankun-head>` 里内联的全部静态 CSS 删掉，线上（被 qiankun 加载时）body margin 重置、fixed 布局、自定义配色全部失效而本地正常。
  已改为挂到包裹层内的 `#app`（NC-JS `b93922d`），spiderAdmin 已重发，**其它两个子应用要各自重新 build 才生效**。
  排查/验证用无头 Chrome `--dump-dom`，本地 qiankun 壳用 `admin/qiankun/scripts/serveDist.py`。
  详见 `lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md`。
- [事实 2026-09-08] antdv 4 Layout 的 header/sider 规则选择器是 `.ant-layout .ant-layout-header`（两级），
  单类名覆盖不了缺省深色 `#001529`；spiderAdmin 用 `ConfigProvider.components.Layout.colorBgHeader` + 三级选择器解决。
- [事实 2026-09-04，已修复] `packages/catalyst/scripts/devops/protc_gen.sh` 的 `PROTO_ROOT`
  原指向已重命名的老路径（`pplabs/`），已改为默认指向 `/home/peterq/dev/projects/1s/enfi-resource-common/rpc`
  且支持环境变量覆盖；同时把 `queue_admin_rpc/queue_admin.proto` 加进了生成列表，`gen:proto` 已跑通。
  另 `panShareDownload` 的 `package.json` 里 `gen:proto` 指向自己的 `scripts/devops/protc_gen.sh`，
  **该文件不存在**（只有 catalyst 有，未处理）；`docSpiderScheduler` 的同类问题随目录删除一并消失。
- [事实 2026-09-04 晚] **`mfe()` 插件对 apps.json 只 upsert 不删**：下线一个子应用后，
  它的条目会一直留在生产 apps.json 里，要用 `admin/spiderAdmin/scripts/removeMfeApps.mjs` 人工摘除。
- [事实 2026-09-04] **NC-JS `admin/*` 子应用的标准 `pnpm build` 脚本默认会把 `dist/` 真实上传到生产
  OSS**（`@nc/build` 的 `mfe()` 插件默认 `deploy:true`，挂在不看 `mode` 的 `closeBundle`，
  且构建报错不代表没上传——Rollup 对"无法解析的 import"先当 warning、正常写完 bundle 才在最后
  聚合成失败）。**要本地验证构建，必须先给 `vite.config.ts` 里的 `mfe()` 传 `{ deploy: false }`**，
  验证完 `git checkout` 还原。详见 `lessons/failure-ncjs构建脚本会自动上传OSS.md`。
- [事实] `admin/qiankun` 没有 `build` script，只有 `dev`(wrangler pages dev，服务 `dist/`) 和
  `deployProd`(vite build && wrangler pages deploy)。首次本地开发需要手动 `npx vite build` 生成 `dist/`。
- [事实] 生产网关 IP `115.29.215.228:7542` 硬编码在 `rtc-rpc.ts` 里，换机器要改代码重新发布前端。
- [事实] 仓库根有 `output.txt`(94KB)、`tmp/`、`.wrangler/`、`ossutil_output/` 等历史垃圾，别当代码看。
- [待确认] NC ADMIN 生产访问域名是什么（Cloudflare Pages 项目名 `1s-nc-admin-qiankun`，
  代码里没写自定义域名；`admin.pan-backend-public.krzb.net` 只在注释里出现，疑似上一代后台）。
- [待确认] `pnpm install` 未执行、未跑构建，本文档所有"流程"结论均为读代码推断，未实测。
