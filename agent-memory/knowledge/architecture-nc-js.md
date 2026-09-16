---
title: NC-JS 前端仓库架构（总览：分包布局/工程栈/构建部署）
type: knowledge
status: active
created_at: 2026-09-04T12:56:00+08:00
updated_at: 2026-09-16T11:20:00+08:00
priority: high
keywords:
  - NC-JS
  - 前端
  - pnpm
  - vite
  - Vue3
  - TSX
  - ant-design-vue
  - 分包布局
  - 工程栈
  - OSS 部署
  - Cloudflare Pages
  - qiankun-head
  - 样式丢失
summary: NC-JS 前端 mono repo 的仓库定位、工程栈、分包布局（admin/*、packages/*）与构建/OSS/Cloudflare 部署机制；qiankun 微前端注册与后台页面写法见 architecture-nc-js-qiankun与后台页面.md，与 SPIDER 网关的对接与鉴权见 architecture-nc-js-网关对接.md
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js-qiankun与后台页面.md
  - agent-memory/knowledge/architecture-nc-js-网关对接.md
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/00-overview.md
---

# NC-JS 前端仓库架构

磁盘路径：`/home/peterq/dev/projects/1s/nc-js`（记为 NC-JS）。初次调研 2026-09-04 上午；
同日晚完成两个子应用的合并改造（见 §3.1）。

> **本文件拆分说明**：原单文件超长，已按主题拆成 3 个文件——
> 本文件只留仓库定位/工程栈/分包布局/构建与 OSS·Cloudflare 部署；
> qiankun 微前端注册机制、新增后台页面写法、spiderAdmin 页面约定 → `architecture-nc-js-qiankun与后台页面.md`；
> 与 SPIDER 网关的 WebRTC gRPC 对接方式、鉴权机制、proto 生成 → `architecture-nc-js-网关对接.md`。

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
| `admin/spiderAdmin` | `@nc/spider-admin` | `spiderAdmin` / `/spiderAdmin` | 「🕷️ 爬虫管理台」：左侧栏三组菜单 —— 队列监控(总览/队列详情/日志搜索/黑名单) + 资源配置(配置项) + 文档爬虫(爬取中/队列中/已收录)，另有「资源生命周期」菜单组（见 `architecture-nc-js-qiankun与后台页面.md`） | `QueueAdminRpc` / `ResSchedulerRpc` / `DocSchedulerRpc` / `LifecycleRpc` |
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
| `apps/doc-cloud-spider`（`@nc/doc-cloud-spider`） | **云端文档爬虫油猴脚本**（金山/飞书/腾讯文档），fc-chrome 注入、doc-crawler 消费；独立 vite+monkey 构建，`pnpm build/test/verify:*/upload`，2026-09-16 从个人仓库迁入 → `decisions/decision-2026-09-16-云端文档脚本迁入NC-JS.md` |

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
    ├── spiderGw/spidergw.ts   useGwClient()：一次性拿到 rpc client（详见 architecture-nc-js-网关对接.md）
    ├── spiderGw/queueAdmin.ts 只剩 useQueueAdminMock() 一个 mock 开关
    ├── spiderGw/queueAdminMock.ts 内存态假数据客户端
    └── scheduler/proto/**     protobuf-ts 生成代码（来自 COMMON 的 .proto，生成方式见网关对接文件）
```

## 4. 构建与 OSS / Cloudflare 部署

- 子应用：`pnpm build`（默认 production mode）→ `deployToOss` 插件把 `dist/` 用 **`ossutil`** 传到
  `oss://$OSS_DEPLOY_PUB_BUCKET/frontend/admin-mfe/<name>/`，并原子更新 OSS 上的 `apps.json`
  （改写 entry 为带 `?t=` 时间戳的 index.html）。
- 主应用：`admin/qiankun` 的 `pnpm deployProd` = `vite build && wrangler pages deploy`，
  发到 **Cloudflare Pages**（project `1s-nc-admin-qiankun`）；`admin/qiankun` **没有 `build` script**，
  只有 `dev`（wrangler pages dev，服务 `dist/`）和 `deployProd`，首次本地开发需要手动 `npx vite build` 生成 `dist/`。
- 凭据从 `$BUILD_ENV_FILE` 或默认 `~/dev/test.env` 读取（`OSS_ACCESS_KEY_ID/SECRET/OSS_DEPLOY_PUB_BUCKET`）。
  ⚠️ 该文件是明文密钥，**禁止**读入记忆文件或输出。
- 前置依赖：本机需装 `ossutil`、`wrangler` 并已登录。
- [事实] NC-JS 微前端发布的回滚手段是还原 OSS 上的 `index.html`，`apps.json` 的 entry 只是带 `?t=` 的缓存戳；
  `ossutil cp -r -f` 不会删旧 hash 资源，所以旧 `index.html` 还原即生效。**发布前必须快照两者**。

### 已知坑（构建/部署相关）

- [事实] **NC-JS `admin/*` 子应用的标准 `pnpm build` 脚本默认会把 `dist/` 真实上传到生产
  OSS**（`@nc/build` 的 `mfe()` 插件默认 `deploy:true`，挂在不看 `mode` 的 `closeBundle`，
  且构建报错不代表没上传——Rollup 对"无法解析的 import"先当 warning、正常写完 bundle 才在最后
  聚合成失败）。**要本地验证构建，必须先给 `vite.config.ts` 里的 `mfe()` 传 `{ deploy: false }`**，
  验证完 `git checkout` 还原。详见 `lessons/failure-ncjs构建脚本会自动上传OSS.md`。
- [事实] **`mfe()` 插件对 apps.json 只 upsert 不删**：下线一个子应用后，
  它的条目会一直留在生产 apps.json 里，要用 `admin/spiderAdmin/scripts/removeMfeApps.mjs` 人工摘除。
- [事实] 仓库根有 `output.txt`(94KB)、`tmp/`、`.wrangler/`、`ossutil_output/` 等历史垃圾，别当代码看。
- [待确认] NC ADMIN 生产访问域名是什么（Cloudflare Pages 项目名 `1s-nc-admin-qiankun`，
  代码里没写自定义域名；`admin.pan-backend-public.krzb.net` 只在注释里出现，疑似上一代后台）。
- [待确认] `pnpm install` 未执行、未跑构建，本文件所有"流程"结论均为读代码推断，未实测。
</content>
