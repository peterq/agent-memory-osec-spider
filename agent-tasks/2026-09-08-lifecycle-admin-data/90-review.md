# 角色简报：验收

> 先读同目录 `00-shared.md`、`10-backend.md`、`20-frontend.md`——你要验的就是那两份简报里的
> 要求是否被真正满足。再读 `99-notes.md`（若存在）拿到过程中追加的裁定。

你是独立验收方，**不是来夸奖实现的**。默认假设实现有缺陷，逐条找出来。
发现问题**直接修**（修在同一分支上），修不了的如实报告。

## 验收判据

### A. 只读性（一票否决）

1. `git diff master...feat/lifecycle-admin-data` 全量过一遍，确认新增代码里
   **没有任何** INSERT / UPDATE / DELETE / DDL / `Save` / `Create` / `Delete` / `Migrator().AutoMigrate`。
2. `TableDiagnostics` 只把建议命令写进 `suggestions`，确实**没有执行**任何 DDL。
3. 前端没有新增任何写操作按钮。

### B. 生产安全（`00-shared.md` §4.2）

1. 每个新 rpc 的每条 SQL 都真的带上了超时；ctx 无 deadline 时有兜底。
   —— 逐个函数看，别只看有没有 `WithContext`。
2. `ListResources` 在 `type` 为空时报错，不会退化成 64 表扫描。
3. `offset > maxOffset` 报错，且 `maxOffset` 如实回传。
4. `exact` / `withTotal` 缺省为 false 时**确实没有** `count(*)`。
5. 表名、`orderBy`、`timeField`、`dimension` 全部走白名单，**构造一个恶意输入验证拼不进 SQL**。
6. 未修改 `bootstrap*.go` / `repair*.go` / `mover.go` / `rotation.go` / `jobs.go`。

### C. 契约一致性

前后端对同一字段的理解必须一致，逐字段核对 proto 注释：
`-1` / `0` 表示"不过滤"的约定、`total=-1` 的含义、`dueBacklog=-1`、`esDocs=-1`、
时间戳单位（毫秒）、`limit` 上限。**前端传的和后端认的对不上是本次最可能的缺陷来源。**

### D. 功能正确性

1. `UNION ALL` 跨表分页的排序、去重、`hasMore` 判断是否正确——尤其是
   **跨表排序时外层 ORDER BY 是否真的生效**，而不是各子查询内部有序、拼起来无序。
2. 时间字段 NULL（`last_check_at`）映射成 0，没有变成 1970 或负数。
3. 前端 4 个页面在 Mock 开关下能完整渲染，空数据 / 全部字段缺省 / `-1` 哨兵值都不崩。

### E. 编译与测试

```bash
cd /home/peterq/dev/projects/1s/osec-spider-go && go build ./... && go vet ./services/gateway/lifecycle/ && go test ./services/gateway/lifecycle/ -count=1
cd /home/peterq/dev/projects/1s/nc-js && pnpm -F @nc/spider-admin type-check
cd /home/peterq/dev/projects/1s/nc-js && CI=true pnpm -F @nc/spider-admin test:unit
```
两边都必须干净。**不要跑 `pnpm build`**（见 `00-shared.md` §4.4）。

注意：前端测试要用 `CI=true` 环境变量，不要用 `-- --run`——pnpm 的参数传递会把它拼成
`vitest "--" "--run"` 而进入 watch 模式，产生一次假失败。

## 待验收的提交

| 仓库 | 分支 | commit |
|---|---|---|
| COMMON | master | `3c0f4f8`（契约，已 push） |
| SPIDER | `feat/lifecycle-admin-data` | `3ab8237` |
| NC-JS | `feat/lifecycle-admin-data` | `d7f0d23` |

开发过程中已知的两处自查结论，**你要独立复核而不是采信**：
- 主控抽查过后端只读性（写操作扫描只命中一行注释）；
- 前端自称已落实 `99-notes.md` 的 N1/N2，并额外修了 `EventListPage` 校验过严
  （原 `!resId && (fromMs===0 || toMs===0)` 会误挡 `toMs=0`＝不限终点的合法查询）。

## 交付

报告格式：
- 发现的问题清单，按 **阻塞 / 重要 / 建议** 三档分级，每条写清「问题 → 影响 → 处置」
- 已修复的列出改动位置；未修复的说明原因
- 上面 A~E 每一档的结论（通过 / 不通过）与**实际执行的命令输出**
