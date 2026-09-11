# 40-verify-fix —— 修 `bootstrapVerify` 首个索引失败即 return 的问题（Sonnet，只改代码不部署）

先读 00-shared.md §2 硬性约束（不 `git add -A`、不碰用户未提交的 `.vscode/launch.json`、不连生产）。

## 背景

SPIDER `services/gateway/lifecycle/bootstrap.go` 的 `bootstrapVerify`（约 1585~1645 行）按 `[cur, long]` 顺序对拍，
第一个索引超阈值就 `return` 错误，第二个索引从未对拍。2026-09-11 作业 id=8 实测：错误只报了 cur（0.107%），
long（0.146%）是人工补对拍才发现的，导致「repair → retry」方案差点连败两次。

## 要求

1. 两个索引**都对拍完**再决定结果：全部通过 → `prog.Message="校验通过: …"`；任一失败 → 错误信息里**列出所有超标索引**
   （每个带 DB/ES/差额/百分比），并把两个索引的对拍结果都写进 `prog.Message`（当前失败路径只写了到失败为止的 msgs）。
   保持阈值语义不变：绝对差 ≤`bootstrapVerifyAbsTolerance`(100) 免检，否则 >0.1% 失败；`dbCount==0` 跳过。
   错误仍用 `errors.Wrapf(ErrEsOperation, …)`，保留「**不切换任何别名**, 请跑 repair 定位」字样（README/巡检脚本依赖该措辞）。
2. 单测：找现有 `bootstrapVerify` 相关测试（`grep -rn bootstrapVerify services/gateway/lifecycle/*_test.go`），若有则补「cur 通过 long 失败」
   「两者都失败错误信息含两个索引」两例；若没有可注入的测试桩，至少为差额判定抽一个纯函数（例如 `verifyGap(dbCount, esCount) (gap float64, fail bool)`）
   并对其写表驱动单测。不要为了测试大改 `esOps`/`Dao` 接口。
3. 本地验证：`go build ./...`、`go test ./services/gateway/lifecycle/...`（单测应不依赖 MySQL/ES；若该包已有需要外部依赖的测试，用 `-run` 限定到你新增/相关的用例并说明）。
4. 提交：只 `git add` 改动的 go 文件，中文提交信息（如 `fix(res-lifecycle): bootstrapVerify 两索引都对拍后再汇总失败`），
   `git pull --rebase --autostash` 后 push master。**不部署、不重启网关**（下次网关重启随 master 生效）。
5. 在 `services/gateway/lifecycle/README.md` 若有描述 B5 校验的段落，补一句「两索引都对拍后汇总」；没有则不加。

## 交付

汇报：改动摘要、新增/修改的测试与运行结果、提交 hash。
