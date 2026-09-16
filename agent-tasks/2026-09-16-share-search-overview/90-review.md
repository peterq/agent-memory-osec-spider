# 角色 90：验收

先读 `00-shared.md`，再按下面清单逐项核对；每项给出「通过 / 不通过 + 证据（文件:行 或命令输出）」。只报告，不改代码（发现问题写清楚复现与建议，由主控决定返工）。

## 契约一致性
- [ ] Go / TS 生成物与 proto 一致（`enfi-resource-common` 工作树干净，`rpc/spider/gen.sh` 与 `nc-js/packages/catalyst/scripts/devops/protc_gen.sh` 均含 `search_admin_rpc/search_admin.proto`）。
- [ ] 所有实现的字段语义与 proto 注释一致（重点：`ShareCounts.checked = valid+invalid+error`；`SearchStats.v2Count + v3Count = count`；`distinctUids` 排除 anonymous；`GuardParams.enabledSet/autoCloseSet` 语义）。

## SPIDER lifecycle（主工作树 `osec-spider-go`，分支 `feat/share-search-overview`）
- [ ] 参数校验：跨度 >92 天、from>=to、非法 type/bucket 均返回 `ErrInvalidParam`。
- [ ] 桶补齐：区间内每个桶都有条目且按升序；day 桶按 Asia/Shanghai 0 点对齐。
- [ ] 事件聚合 SQL 参数化、走 `created_at` 范围；ES 查询有资源父文档过滤且 README 写了线上对拍命令。
- [ ] 计数器：三个 `onCheck*` 都传了 type；旧全局键与 `LastHour/LastDays` 行为未变（`alert.go`/`metrics.go` 测试仍绿）。
- [ ] 任一数据源失败只进 `warnings`，不整体失败；60s 缓存生效。
- [ ] `go build ./... && go vet ./services/gateway/lifecycle/... && go test ./services/gateway/lifecycle/...` 通过。

## SPIDER search_admin（worktree `osec-spider-go-wt-search`，分支 `feat/search-admin`）
- [ ] SLS 未配置 / SQL 不可用 / redis 出错三种情况下：网关能启动，RPC 返回明确错误或降级结果，不 panic。
- [ ] SQL 与扫描两条路径对同一组伪日志得到相同 `SearchStats`（有测试证明）。
- [ ] 巡检 leader-only；连续 `sustainPolls` 次才触发；去抖；`autoClose=false` 只发邮件；关闭键写法与 `00-shared.md` §4.2 完全一致（键名、JSON 字段、TTL）。
- [ ] `SetAnonymous`/`UpdateGuardParams` 写事件、发邮件；`GuardStatus` 在非 leader 实例也能返回最近巡检状态。
- [ ] 上限：Overview/Top 的时间跨度 ≤31 天、keyword limit ≤1000、ip/uid ≤100。
- [ ] `gateway.go` 注册失败只记日志；`config` 缺省值测试。
- [ ] `go build ./... && go vet ./services/gateway/search_admin/... && go test ./services/gateway/search_admin/... ./config/...` 通过。

## API（`osec-resource-api`，分支 `feat/search-guard`）
- [ ] `SearchApi` 与 `SearchApiV3` 都接了 guard；只拦 `uid == "anonymous"`；响应 403 / code 50008 / 文案「请登陆后再搜索」；`logData["guard"]="anonymous_closed"`。
- [ ] redis 出错 fail-open 且有限频日志；本地缓存生效；`enabled=false` 不查 redis。
- [ ] `go build ./... && go vet ./... && go test ./services/search-guard/... ./services/search-canary/...` 通过。

## NC-JS（分支 `feat/share-search-overview`，commit `c29d926`）—— 2026-09-16 验收完成
- [x] 4 个页面 + 菜单项 + LazyKeepAlive 插槽齐全；mock 开关与 Tag 工作；未跑过 `pnpm build`。
  证据：`layout/navState.ts` MenuKeys 含 LcShareOverview/SearchOverview/SearchKeywords/SearchGuard；`layout/AppLayout.tsx` 对应 4 个 `<Menu.Item>` + `LazyKeepAlive` 4 个插槽齐全；`searchAdmin.ts`（useSearchAdminMock）+`searchAdminMock.ts`（createMockSearchAdminClient 实现 overview/top/guardStatus/setAnonymous/updateGuardParams 全部 5 个方法）+`spidergw.ts:161-164`（usingSearchAdminMock 三元切换，写法与 usingLifecycleMock 一致）+顶栏"搜索监控 Mock"Tag/Switch。`git status` 干净，无 dist/OSS 改动。
- [x] BigInt 处理正确（type-check 通过，未见 `Cannot mix BigInt` 风险点）；`truncated/source=sls-scan/warnings` 有可见提示，但**有一处不够完整**：
  `SearchOverviewPage.tsx:130-132` 只展示 `state.data`（Overview 响应）自身的 source/truncated，**Top10 IP/uid 表格背后的 `top()` 调用各自也有独立的 source/truncated/note（search_admin.proto SearchTopResponse），未单独展示** —— 若 Overview 走 sls-sql 正常但 Top 降级为 sls-scan/truncated，用户看不到 Top10 数据不完整的提示。`ShareOverviewPage.tsx`/`SearchKeywordsPage.tsx` 均正确处理了各自响应的 note/warnings/source/truncated。建议：小改（非必须返工阻塞）—— SearchOverviewPage 的 `loadTop()` 也检查 `ipResp.truncated || uidResp.truncated || source==='sls-scan'` 并额外提示。
- [x] 防护页（`SearchGuardPage.tsx`）的关闭（`submitClose` 弹表单+`modals.alert`二次确认）/开放（`doOpen`）/保存参数（`saveParams`）均有 `modals.alert` 二次确认；`GUARD_EVENT_LABEL`（`pages/search/format.ts:48-55`）覆盖全部 6 种 `GuardEvent.kind`（auto_close/manual_close/manual_open/auto_expire/alert/params_update）中文标签，表格渲染用 `GUARD_EVENT_LABEL[text] || text` 兜底。
- [x] `pnpm exec vitest run`：5 个测试文件 15 个用例全部通过（`Test Files 5 passed, Tests 15 passed`，含新增 `shareOverview.test.tsx` 2 例、`pages/search/__tests__/smoke.test.tsx` 4 例）。`vue-tsc --build --force`：exit code 0，无报错。

## 汇总
- 按仓库列出：通过项数 / 不通过项 / 建议返工内容（按严重程度排序）。
