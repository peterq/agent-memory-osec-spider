# 角色 40：NC-JS 前端 —— 分享链接总览 + 搜索监控三页

仓库：`/home/peterq/dev/projects/1s/nc-js`（分支 `feat/share-search-overview`）。只改 `admin/spiderAdmin/` 与 `packages/catalyst/contract/rpc/spiderGw/`。TS 契约已生成在 `packages/catalyst/contract/rpc/scheduler/proto/{lifecycle_rpc,search_admin_rpc}/`，**不要重新生成**。

## 必读

1. `00-shared.md` §4.5、§5（**禁止 `pnpm build`**）。
2. 两个 proto 的注释（字段含义、单位、上限）：`enfi-resource-common/rpc/spider/lifecycle_rpc/lifecycle.proto` 末尾「分享链接总览」、`search_admin_rpc/search_admin.proto`。
3. 范本：`admin/spiderAdmin/src/pages/proxy/ProxyOverviewPage.tsx`（窗口切换 + 自动刷新 + 卡片/表格）、`pages/lifecycle/TableStatsPage.tsx`（筛选 + 表格 + note 展示）、`pages/queue/MiniLineChart.tsx`、`pages/lifecycle/__tests__/smoke.test.tsx`、`packages/catalyst/contract/rpc/spiderGw/spidergw.ts`（`lifecycleRpc`/`proxyAdminRpc` 如何创建与返回）、`spiderGw/lifecycle.ts` + `lifecycleMock.ts`（mock 开关与 mock 客户端写法）、`layout/navState.ts`、`layout/AppLayout.tsx`（菜单与 LazyKeepAlive 插槽；`grp-lc`/`grp-proxy` 两段）。

## 要做的事

### A. RPC 客户端与 mock
- `spidergw.ts`：新增 `searchAdminRpc: ISearchAdminRpcClient`（`SearchAdminRpcClient(transport)`），mock 开关 `useSearchAdminMock()`（`spiderGw/searchAdmin.ts`，localStorage key `searchAdminMock`）+ `createMockSearchAdminClient()`（`searchAdminMock.ts`：可信的假数据——时序有起伏、Top 榜、防护状态含事件；`setAnonymous/updateGuardParams` 要改内存状态让页面可交互）。返回值里带 `searchAdminRpc, usingSearchAdminMock`，AppLayout 顶栏与 lifecycle 一样显示一个紫色 Mock Tag。
- `lifecycleMock.ts`：补 `shareOverview` 的 mock（按参数生成桶、byType、byClient、stock、note/warnings）。

### B. 页面（全部 TSX `defineComponent`，ant-design-vue）
公共：新建 `pages/common/TimeRangeBar.tsx`——快捷档（最近 1 小时 / 6 小时 / 今天 / 24 小时 / 7 天 / 30 天）+ 自定义 `RangePicker`（dayjs） + 桶粒度 `Segmented`（受控，父组件传可选项）+「刷新」+「自动刷新」开关（`useDocumentVisibility` 页面隐藏时停）。三个总览页共用。

1. **分享链接总览** `pages/lifecycle/ShareOverviewPage.tsx`，`MenuKeys.LcShareOverview = "lc-share-overview"`，放在「资源生命周期」组「总览」之后，图标 `LineChartOutlined`。
   - 顶部 TimeRangeBar + 类型 `Select`（全部/四种，用 `format.ts` 的 `TYPE_LABEL`）。
   - 指标卡：新增、内容更新、失效、检测总数（有效/失效/报错）、失效率 = checkInvalid/checked、ES 新增（并列，tooltip 说明口径差异）。
   - 折线图（MiniLineChart）：created/updated/invalid/checked 四条；下方按类型分组的小图或表格（每类型一行：各指标合计）。
   - 「新增来源」表：client / 新增数 / 占比，按新增降序；`client` 空串显示「(未知)」。
   - 存量表：type / active / invalid / dueBacklog。
   - `note` 用 `Alert type=info`，`warnings` 非空用 `Alert type=warning` 逐条列出。
2. **搜索总览** `pages/search/SearchOverviewPage.tsx`，新菜单组 `grp-search`「搜索监控」（放在「代理池」之后），`MenuKeys.SearchOverview = "search-overview"`，图标 `SearchOutlined`。
   - TimeRangeBar（桶 minute/hour/day）+ 入口 `Segmented`（全部/v2/v3）。
   - 指标卡：搜索量、v3 占比、错误率、p50/p90/p99/avg/max、IP 数、用户数、匿名占比、被拦截数、空结果率、慢查询数。
   - 折线图两张：请求量（count/v3Count/errorCount/anonymousCount）与延迟（p50/p90/p99）。
   - 同页下方两张表：**Top10 IP** 与 **Top10 uid**（各调一次 `top`，列：key / 次数 / 平均延迟 / 错误 / 空结果 / 不同 uid|ip 数 / 最近出现），uid 榜排除 anonymous（后端已排除，前端再兜底过滤）。
   - `source`/`truncated`/`note` 展示：`source=sls-scan` 或 `truncated` 时用 `Alert type=warning` 提示「数据为降级扫描结果，可能不完整」。
3. **搜索词 Top1000** `pages/search/SearchKeywordsPage.tsx`，`MenuKeys.SearchKeywords = "search-keywords"`，图标 `TagsOutlined`。
   - TimeRangeBar（无桶）+ 入口 + `limit` 选择（100/500/1000）+ 本地关键词过滤输入框（前端过滤已加载的列表）。
   - 表格分页（每页 50），列：排名 / 搜索词 / 次数 / 平均延迟 / 错误 / 空结果 / 不同 uid 数 / 最近出现；「复制为 CSV」按钮（`navigator.clipboard`）。
4. **匿名搜索防护** `pages/search/SearchGuardPage.tsx`，`MenuKeys.SearchGuard = "search-guard"`，图标 `SafetyOutlined`。
   - 状态卡：当前「开放/已关闭」大字 + 到期倒计时 + 原因/操作者；leader 主机、最近巡检时间、最近 p90、样本数、连续超阈值次数；10 秒自动刷新。
   - 操作：「立即关闭匿名搜索」（弹窗填时长分钟、原因，二次确认）/「立即开放」（二次确认）；`operator` 传当前登录用户名（AppLayout 里有 `currentUser`，通过 props 或 ctx 传进来；没有就传 `"admin"`）。
   - 参数表单：`GuardParams` 各字段（Switch/InputNumber），「保存」调 `updateGuardParams`（只传改动字段，`enabledSet/autoCloseSet` 按是否改动置 true），保存前二次确认。
   - 最近事件表：时间 / 类型（中文 Tag：auto_close 自动关闭、manual_close 手动关闭、manual_open 手动开放、auto_expire 到期自动开放、alert 告警、params_update 改参数）/ 详情 / 操作者 / p90 / 样本。
   - `note` 展示。

### C. 菜单与插槽
`navState.ts` 加 4 个 `MenuKeys`；`AppLayout.tsx` 加菜单项与 `LazyKeepAlive` 插槽（照 `grp-proxy` 的写法把 `searchAdminRpc` 通过 props 传给三个搜索页；分享链接总览页通过 `useLifecycleCtx()` 拿 `lifecycleRpc`）。

### D. 测试与检查
- `admin/spiderAdmin/src/pages/lifecycle/__tests__/shareOverview.test.tsx`、`pages/search/__tests__/smoke.test.tsx`：mock 客户端挂载四页，断言指标卡渲染、表格行数、`warnings`/`truncated` 提示出现、防护页「关闭」按钮弹出确认并调用 mock 的 `setAnonymous`。
- 命令（在 `admin/spiderAdmin` 下）：`pnpm exec vitest run`、`pnpm exec vue-tsc --noEmit -p tsconfig.app.json`（若项目 type-check 脚本名不同，看 `package.json` 用等价的 `type-check`，**绝不能跑 `build`**）、`pnpm lint`（若 lint 需要网络或很慢可跳过并说明）。
- BigInt：proto 的 int64 在 protobuf-ts 里是 `bigint`，图表/`Statistic` 前用 `Number()`，看 `format.ts` 现成的 `fmtCount/fmtTimeMs`。

## 交付（最终回复里写）
- 改动文件清单 + 提交哈希（分支 `feat/share-search-overview`，不 push）。
- 测试/type-check 命令与结果。
- 未做/待确认项。
