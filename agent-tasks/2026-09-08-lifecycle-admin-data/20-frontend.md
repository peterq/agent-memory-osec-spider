# 角色简报：NC-JS 前端

> 先读同目录 `00-shared.md`。本文件只写前端专属内容。

## 要新增的页面

在后台子应用 `admin/spiderAdmin` 的「资源生命周期」模块下新增 4 个**只读**页面：

| 页面 | 对应 rpc |
|---|---|
| 资源列表 | `listResources` |
| 分表统计 | `tableStats` |
| 事件流水 | `listEvents` |
| 表诊断 | `tableDiagnostics` |

TS 契约已生成在
`packages/catalyst/contract/rpc/scheduler/proto/lifecycle_rpc/lifecycle.ts`，
相关类型：`ListResourcesParam/Response`、`TableStatsParam/Response`、
`ListEventsParam/Response`、`TableDiagnosticsResponse`、`TableStat`、`DimBucket`、
`LcEventRow`、`TableDiagnostic`、`IndexReconcile`。

## 必读文件（读它们是为了拿到什么）

| 文件 | 要提取什么 |
|---|---|
| `admin/spiderAdmin/src/pages/lifecycle/` 下现有 5 个页面（`OverviewPage` / `ResourcePage` / `JobsPage` / `ParamsPage` / `LcDiagramsPage`） | 页面结构、表格、筛选栏、错误处理、加载态——新页面一律照这个写，不要另创风格 |
| `admin/spiderAdmin/src/pages/lifecycle/format.ts` | 已有 `RES_STATUS_LABEL` / `RES_INDEX_ROLE_LABEL` / `CHECK_RESULT_LABEL` / `TYPE_LABEL` / `fmtBytes` / `fmtCount` / `fmtTimeMs`，**复用不重写**；缺的枚举文案（event 类型、cycle status、诊断 kind）补进这个文件 |
| `admin/spiderAdmin/src/pages/lifecycle/LifecycleContext.ts`、`LcCtxProvider.tsx` | 页面怎么通过 `useLifecycleCtx()` 拿 `lifecycleRpc` / `modals` / `operator` |
| `admin/spiderAdmin/src/layout/AppLayout.tsx`、`layout/navState.ts` | 加菜单项 = 加页面：`MenuKeys`、菜单树、`LazyKeepAlive` 挂载；照现有 lifecycle 5 项的写法加 4 项 |
| `packages/catalyst/contract/rpc/spiderGw/lifecycleMock.ts` | 现有 lifecycle mock 客户端；**必须为 4 个新方法补 mock 数据**——后端尚未上线，Mock 开关是唯一的整页验证途径 |
| `admin/spiderAdmin/src/pages/lifecycle/__tests__/` | 现有测试写法，按它给新页面补测试 |

## 交互要求

### 资源列表页

- 筛选栏：「网盘类型」**必填**（后端不接受空 type，会直接报错）；另有分表槽 bucket（-1=全部 16 槽）、
  status、index_role、index_name、last_check_result、只看到期（dueOnly）、fail_count 下限、
  share_id、时间字段 + 范围、排序字段 + 升降序。
- 分页用 offset/limit。响应里的 `maxOffset` 要用来**禁用超限的翻页按钮并给出提示**（后端会直接报错）。
- `total` 为 `-1` 时不显示总数、只按 `hasMore` 控制下一页；另给一个「统计总数」按钮显式触发
  `withTotal=true`，并提示这是慢查询。
- 行内字段：id（可复制）、type、share_id、status、index_role、index_name、last_check_result、
  next_check_at、fail_count、file_count、total_size、ctime / utime。
- 点行跳到现有「资源查询」页并带上该 id 直接查详情——**复用现有页面，不重复实现详情**。
- 页脚小字展示 `scannedTables` 与 `costMs`，便于排查慢查询。

### 分表统计页

- 默认 `exact=false`（估算，快）；勾选「精确统计」才发 `exact=true`，并提示是慢查询。
- 维度切换用分段控件；表格按分表列出，附全体汇总。
- `dueBacklog` 为 `-1` 时显示「未统计」，不要显示 -1。

### 事件流水页

- `resId` 为空时**必须强制填时间范围**（后端要求走 `idx_created`）。前端提交前校验并给清晰提示，
  别让用户吃后端报错。

### 表诊断页

- 顶部汇总：期望表数 / 缺失表数 / schema 不符表数。
- 逐表列出，有问题的行标红。
- `suggestions` 单独一块，展示为可复制的命令列表，并明确写清「后台不执行，请人工在服务器执行」。
- `reconciles` 单独一张表：`diff` 非 0 标黄，`esDocs` 为 `-1` 显示「未取到」。

## 额外禁止事项

- 不改现有 5 个 lifecycle 页面的行为，不动 queue / doc / res 其他模块。
- 不重新生成 proto TS 契约（已生成好）。
- `pnpm build` 的禁令见 `00-shared.md` §4.4。

## 验证（全部通过才算完成）

```bash
cd /home/peterq/dev/projects/1s/nc-js
# 包名与脚本名以 admin/spiderAdmin/package.json 为准, 可能叫 type-check / typecheck / tsc
pnpm -F <spiderAdmin 包名> type-check
```
以及仓库已有的单元测试命令（看 package.json，通常是 vitest）。类型检查必须干净。

## 交付

见 `00-shared.md` 第 5 节。额外汇报：菜单结构长什么样、mock 数据覆盖了哪些场景、
type-check 与测试的**实际输出**。
