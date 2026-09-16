---
title: NC-JS 架构：qiankun 微前端机制与后台页面写法
type: knowledge
status: active
created_at: 2026-09-12T11:25:00+08:00
updated_at: 2026-09-16T17:10:00+08:00
priority: high
keywords: [qiankun, 微前端, spiderAdmin, 后台页面, 账号健康, 站点健康, 新增页面, 队列监控, 资源生命周期, 架构图页, res_lc, 分表, absThreshold]
summary: qiankun 主应用注册/子应用生命周期、本地开发流程；spiderAdmin 新增后台页面写法与落点（队列监控、资源生命周期各页、架构图页、res_lc 分表、账号健康/站点健康页）；页面/样式相关坑
questions:
  - 后台前端加一个页面该怎么加
  - qiankun 子应用 / apps.json 是什么
  - 后台哪里看 res_lc_* 分表数据
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/knowledge/architecture-nc-js-网关对接.md
  - agent-memory/knowledge/architecture-api.md
  - agent-memory/lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md
  - agent-memory/sessions/2026/2026-09-08-res_lc数据纳入后台.md
---

# NC-JS 架构：qiankun 微前端机制与后台页面写法

本文件是 `architecture-nc-js.md` 拆分出的一部分，聚焦"怎么把一个新后台页面加进 spiderAdmin"。
仓库定位/工程栈/分包布局/构建部署见 `architecture-nc-js.md`；网关对接与鉴权见 `architecture-nc-js-网关对接.md`。

## 1. qiankun 微前端机制

- [事实] 主应用 `admin/qiankun/index.html` 用 **CDN script 引入 qiankun 2.10.16 UMD**（非 npm 依赖），挂到
  `window.qiankun`；`src/comps/Main.tsx` 负责 `registerMicroApps` + `start({prefetch:true, singular:false})`。
- [事实] **子应用清单不写在代码里**，而是运行时 fetch 一个 `apps.json`：
  - 生产：`https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/frontend/admin-mfe/apps.json`
  - 本地（`location.hostname === 'localhost'`）：`/apps.json`
  - 条目结构 `AppEntry { name, entry, container:'#subapp-viewport', activeRule, title, homepage, description, icon?, buildAt? }`
- [事实] 子应用**不自己写 qiankun 生命周期**，统一：
  - `vite.config.ts` 里用 `mfe(appsFilePath, entry)`（来自 `@nc/build`），内部含 `vite-plugin-qiankun`
  - `src/main.ts` 里用 `initMicroFeApp({ createApp, container:'#app', registerModalCall? })`
  - 非 qiankun 环境（直接 `pnpm dev` 打开）会自动降级为独立应用挂载，可单独开发
- [事实] `activeRule` 与 `homepage` 都是同一个**路径前缀**，主应用没有菜单，导航靠悬浮球应用卡片 `location.href = homepage`。
- [事实] **跨子应用弹窗调用**是本仓特色：`openMfeModal(appName, fn, param)` 会 `loadMicroApp` 目标子应用、
  经 props `$callModal$` 传入调用，目标子应用用 `MfeModalRouter.registerModal(fn, Comp)` 响应并以 Promise
  返回结果；契约写在 `catalyst/ui/microFe/contract/*.ts`（例：`appLogin3rd.chrome({...})`）。

### 本地开发流程 [推断，未实跑]

1. `pnpm install`（根目录，pnpm workspace）
2. 主应用：`admin/qiankun` 先 `vite build` 出 `dist/`，再 `pnpm dev`（= `wrangler pages dev`，服务 `dist/`）
3. 子应用：`cd admin/<app> && pnpm dev`，`writeMfeEntry` 插件会把本机 dev server 地址写进
   `admin/qiankun/dist/apps.json`，主应用刷新即可加载
4. 只调子应用页面本身时可以不起主应用，直接 `pnpm dev` 独立跑（会走 `initMicroFeApp` 的降级分支）

## 2. 页面写法约定（可直接抄的代表性文件）

| 我要写 | 抄这个文件 |
|---|---|
| 子应用外壳（连网关+侧栏菜单+弹窗管理器+网关切换） | `spiderAdmin/src/layout/AppLayout.tsx`（最新最完整）或 `panShareDownload/src/ui/panShareDownloadUi.tsx`（多 Tab 老写法） |
| 子应用入口 | `spiderAdmin/src/main.ts` + `vite.config.ts` |
| **队列/任务列表页（分页+自动刷新+行内操作）** | `spiderAdmin/src/pages/doc/comps/queuedTasks.vue` |
| 普通分页表格页（TSX，含筛选/统计条） | `panShareDownload/src/ui/panShareDownloadFilelist.tsx`，或 `pages/lifecycle/ResourceListPage.tsx` |
| 卡片式导航页 + 打开弹窗 | `spiderAdmin/src/pages/res/RdsConfPage.tsx` |
| 弹窗内的增删改表格 | `spiderAdmin/src/modals/ModalConfItem.tsx` |
| 嵌 Grafana 看板 | `panShareDownload/src/ui/panShareDownloadMonitor.tsx` |
| 跨组件共享 rpc/状态（provide/inject） | `spiderAdmin/src/scheduler/Scheduler.ts`、`pages/queue/QueueCtxProvider.tsx`、`pages/lifecycle/LcCtxProvider.tsx` |
| 列表懒加载详情 / 只读体检类页面 | `catalyst/ui/vueutil/layzload.ts` 的 `BatchLoader` / `pages/lifecycle/TableDiagnosticsPage.tsx` |

约定要点：
- 组件用 `defineComponent({ props: xxxProps(), setup(props){ ... return () => <jsx/> } })`，
  props 用返回对象的函数（如 `rpcProps()`）导出复用，rpc client 经 props 往下传。
- 目录：`src/layout/`（外壳）、`src/pages/<模块>/`（页面）、`src/modals/`（弹窗）、`src/style/main.less`；
  别名 `@` → `./src`（老子应用把页面与弹窗混放在 `ui/`）。
- 自动刷新套路：`useDocumentVisibility()` + `useTimeoutToRef(5e3)` + `useWatchToPromise(...)` +
  `useDisposePromise()`，只在页签可见且当前 Tab 展示时轮询。
- 报错统一走 `useGwClient` 的 `onCallError` → `notification.error`，业务错误码见
  `scheduler.ts` 的 `ErrorCodes`（按需忽略，如 110101 NoMoreTask）。
- 弹窗一律 `ModalManager.useInit()` + `useModal(wrapModal(Comp,false))`，`emit('resolve'|'reject')`；
  简单输入用 `modals.prompt(...)`。
- proto 的 int64 在 TS 侧是 **BigInt**，传参 `BigInt(x)`，展示 `Number(x)`/`.toString()`。
- mock 只有队列监控、资源生命周期两套（`queueAdminMock.ts`/`lifecycleMock.ts`），其余 RPC 本地直连网关。

## 3. 新增后台页面的落点结论

> [事实] 队列/文档爬虫两个旧子应用已合并进 `admin/spiderAdmin`（详见 `architecture-nc-js.md` §3.1、
> `decisions/decision-2026-09-04-前端合并为spiderAdmin.md`）。

**要加一个爬虫/队列/调度/生命周期相关的后台页面，就是在 `spiderAdmin` 的左侧菜单里加一项**，
不要新建子应用（新建要额外占 OSS 目录、apps.json 条目与独立部署，收益为零）。

`admin/spiderAdmin/src/` 结构：

| 目录 | 内容 |
|---|---|
| `layout/AppLayout.tsx` | 外壳：唯一 RTC 连接、顶栏(环境切换/连接状态/Mock/clientName)、侧栏菜单、内容区分发 |
| `layout/navState.ts` | `MenuKeys` 枚举 + `activeMenuKey`/`siderCollapsed`（localStorage），**代替路由** |
| `layout/LazyKeepAlive.tsx` | 复刻 AntDV `<Tabs>`"首次访问才挂载、之后只隐藏"，保住分页/自动刷新状态 |
| `layout/Page.tsx`/`PageHeader.tsx` | 统一页头(标题+说明+extra 按钮) + 卡片式页体 |
| `pages/queue/` | 队列监控 4 页 + `QueueCtxProvider` + schema 渲染器/JSON 树/迷你折线图/任务详情抽屉 |
| `pages/res/RdsConfPage.tsx` | 资源调度配置项 |
| `pages/doc/comps/*.vue` | 文档爬虫三页（SFC，从旧子应用原样搬迁） |
| `pages/lifecycle/` | 资源生命周期各页（总览/资源列表/资源查询/分表统计/事件流水/作业/参数/表诊断/架构图，见 §4）+ `LcCtxProvider.tsx` |
| `scheduler/Scheduler.ts` | 文档爬虫状态中枢，**复用外壳 client，不自建连接** |
| `scripts/removeMfeApps.mjs` | 从生产 apps.json 摘除已下线子应用条目（默认 dry-run，`--yes` 才写） |

加页面：`navState.ts` 加 `MenuKeys` 项 → `<Menu>` 加一项 + `LazyKeepAlive` 插槽加 `<Page>`。
**没有路由表、没有菜单配置文件、没有权限配置**。队列监控的 schema 驱动渲染
（`pages/queue/SchemaRenderer.tsx`+`schema.ts`，按 `GetDetailSchemas` 下发 JSON 渲染、未知 widget 兜底 JSON 树）
是本仓唯一一份通用渲染机制，需要类似能力时复用。

### 3.1 架构图页与构建时同步（2026-09-07）

- [事实] `spiderAdmin`「资源生命周期」菜单组的「架构图」页（`MenuKeys.LcDiagrams`，`LcDiagramsPage.tsx`）：
  `Segmented` 切资源/服务端视角，`<iframe>` 内嵌 archify 产出的自包含 HTML。
- [事实 2026-09-10，NC-JS `6ce0b9b`] **OSS 上的 `.html` 不能直接 `<iframe src>`/`window.open`，会被响应头强制下载**：
  改为 `fetch` 取文本 → `iframe srcdoc` 渲染，「新窗口打开」改成 Blob URL。**凡是把 HTML 类静态产物放 OSS
  再嵌入的场景都沿用这一做法**，不要再试 `src` 直连。
- [事实] HTML 来源是 SPIDER `PRD/res-lifecycle/diagrams/*.html`，由 `scripts/syncDiagrams.mjs` 在
  `predev`/`prebuild` 钩子复制到 `src/assets/diagrams/`（纳入 git，源目录不存在只警告不失败，
  可用 `RES_LIFECYCLE_DIAGRAMS_DIR` 覆盖）。改图流程：改 SPIDER 的 JSON → `archify deliver` → 重新 build 前端。
- [事实] Vite 6 把 `'*.html?url'` 当普通静态资源处理，生产会被 `mfe()` 改写成 OSS 绝对地址；dev 模式仅在
  `<head>` 注入一行 qiankun 版 `/@vite/client`，srcdoc iframe 与父页同源，无害。

## 4. res_lc 分表数据后台页面（2026-09-08 新增，只读）

来源：`sessions/2026/2026-09-08-res_lc数据纳入后台.md`。后台此前只能按 url/id 精确查单条资源
（「资源查询」`MenuKeys.LcResource`），本次给「资源生命周期」菜单组（`grp-lc`）补齐 4 个**纯只读**
列表/诊断页面，对应网关 `LifecycleRpc` 的 4 个新方法（proto/RPC 细节见 `architecture-api.md`
「res_lc 分表数据只读能力」一节），4 页共用 `LcCtxProvider`（注入 `lifecycleRpc` + mock 开关）：

组件均在 `pages/lifecycle/` 下：

| MenuKeys | 页面 / 说明 | 组件文件 | 对应 RPC |
|---|---|---|---|
| `LcResList` | 资源列表：按类型/分表槽/状态筛选分页浏览 `res_lc_*` 行，可跳转「资源查询」看详情 | `ResourceListPage.tsx` | `ListResources` |
| `LcTableStats` | 分表统计：64 张表行数/占用空间与维度分布，默认估算，精确统计需显式勾选 | `TableStatsPage.tsx` | `TableStats` |
| `LcEvents` | 事件流水：`res_lc_event` 条件查询，`resId` 为空时必须指定时间范围 | `EventListPage.tsx` | `ListEvents` |
| `LcDiag` | 表诊断：67 表存在性/列/索引/大小体检 + DB↔ES 对拍，只读，建议命令仅供参考 | `TableDiagnosticsPage.tsx` | `TableDiagnostics` |

前端已知坑（验收方发现）：
- `status` 与 `dueOnly` 是独立筛选条件，同选「失效」+「只看到期」会拼出恒空查询且不报错，
  `ResourceListPage`/`TableStatsPage` 已加防呆（选中失效状态时锁定「只看到期」）。
- `TableDiagnostics` 的 `diff=-1`（未知态）曾被误标成"有差异"（mock 数据也写错未被测到）——
  **未知态必须单独渲染，不能并入"有差异"分支**。
- `TableDiagnostics` 的 DB↔ES 对拍数来自网关 `Service.Stats()` 的 ≤60 秒缓存快照（非实时全量 COUNT），
  页面展示了口径说明（`note` 字段），同类"体检"页面应沿用而非自己发起全量统计。

## 5. 分享链接总览与搜索监控页面（2026-09-16 新增）

| MenuKeys | 页面 | 组件 | RPC |
|---|---|---|---|
| `LcShareOverview` | 分享链接总览（资源生命周期组） | `pages/lifecycle/ShareOverviewPage.tsx` | `LifecycleRpc.ShareOverview` |
| `SearchOverview` | 搜索总览 + Top10 IP/uid（新组「搜索监控」`grp-search`） | `pages/search/SearchOverviewPage.tsx` | `SearchAdminRpc.Overview/Top` |
| `SearchKeywords` | 搜索词 Top1000（本地过滤、复制 CSV） | `pages/search/SearchKeywordsPage.tsx` | `SearchAdminRpc.Top(keyword)` |
| `SearchGuard` | 匿名搜索防护（状态/手动开关/参数热更新/事件） | `pages/search/SearchGuardPage.tsx` | `GuardStatus/SetAnonymous/UpdateGuardParams` |

共用 `pages/common/TimeRangeBar.tsx`（快捷档 + 自定义区间 + 桶粒度 + 自动刷新）；`searchAdminRpc` 由 `spidergw.ts useGwClient()` 创建，mock 开关 `searchAdminMock`（localStorage）+ 顶栏 Tag。`source=sls-scan`/`truncated`/`warnings` 都有可见提示（Top10 榜单独提示）。[待确认] 页面只跑过 mock 冒烟测试，未在浏览器实测真实网关。

## 5.1 账号健康 / 站点健康页面（2026-09-16 新增，提案 6/7）

| MenuKeys | 页面 | 组件 | RPC |
|---|---|---|---|
| `AccountHealth` | 账号健康（新组「健康监测」`grp-health`）：网盘转存账号探测列表 + 按类型筛选 + 手动重检 | `pages/health/AccountHealthPage.tsx` | `HealthRpc.AccountHealth/RecheckAccount` |
| `SiteHealth` | 站点健康：队列名/关键词站点近1h/24h成功率、连续零成功时长、确认知悉/忽略重置下线候选 | `pages/health/SiteHealthPage.tsx` | `HealthRpc.SiteHealth/SetSiteDownlineCandidate` |

`healthRpc` 同样在 `spidergw.ts useGwClient()` 里创建，mock 开关 `healthMock`（`spiderGw/health.ts` + `healthMock.ts`），顶栏「健康监测 Mock」紫色 Tag，与 lifecycle/searchAdmin 同款接入方式。两页均无自带时间范围选择，固定 15 秒自动刷新（`isShow` 门控）。写操作（重检/确认候选/忽略重置）都走 `useModalFactory()` 二次确认。`queue_admin_rpc.AlertRuleConfig` 同批新增 `absThreshold`（绝对阈值，无全局缺省，只能按队列覆盖开启），已加进 `pages/queue/AlertRulesPage.tsx` 的字段清单。TS 契约生成需临时把 `packages/catalyst/scripts/devops/protc_gen.sh` 的 proto 来源指向对应 COMMON worktree 并把 `health_rpc/health.proto` 加入生成列表（脚本改动不提交，只提交生成物）。**踩坑**：health.proto 里 `success1h`/`fail1h`/`success24h`/`fail24h` 字段被 protobuf-ts 转成 `success1H`/`fail1H`/`success24H`/`fail24H`（数字后接小写字母会被大写化），不是 `success1h` 原样。

## 6. 已知坑 / 待确认（页面 / 样式相关）

- [事实 2026-09-08，已修复] catalyst `initMicroFeApp` 曾把 Vue 挂在 qiankun 包裹层上导致线上样式全失效，已改挂 `#app`（NC-JS `b93922d`），**其它两个子应用要各自重新 build 才生效**。排查方法与细节见 `lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md`。
- [事实 2026-09-08] antdv 4 Layout 的 header/sider 选择器是两级 `.ant-layout .ant-layout-header`，单类名覆盖不了
  缺省深色 `#001529`；spiderAdmin 用 `ConfigProvider.components.Layout.colorBgHeader` + 三级选择器解决。
</content>

## 代码位置

- 共享库 `nc-js/packages/catalyst/`
