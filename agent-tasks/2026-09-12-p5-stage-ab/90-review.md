# 角色 90：验收 —— 阶段 A/B 代码复核

只读 + 跑测试，不改业务代码（发现问题写清位置与修法，交主控/开发返工；格式性小错可直接改并说明）。

## 读什么
1. `00-shared.md`、`10-gateway-hook.md`、`20-api.md` —— 判据来源。
2. SPIDER：`git -C /home/peterq/dev/projects/1s/osec-spider-go log --oneline -5` 与对应 diff（`git show <hash>`）。
3. API：同上。

## 判据（逐条给 ✅/❌ 与证据）

### SPIDER 钩子
- [ ] hinter 为 nil 时 `HandleTask` 逐语句与改动前一致（对照 `git diff <base> -- services/gateway/res_scheduler/clear_expire.go`）。
- [ ] 钩子在 `AddInvalidResLink` **成功后**才调用；钩子失败/panic 不影响返回值。
- [ ] `AdvanceNextCheck` 的 SQL 带 `status=1 AND next_check_at > ?` 条件；分表名走 `LcTableName`。
- [ ] `!enabled()` 时空操作；类型不认识时空操作；限速配置有缺省 0=不限并在 `applyDefault` 处理。
- [ ] 事件常量长度 ≤24；指标注册在 `registerMetrics` 内。
- [ ] 不成环：追 `doClear` → `pushLegacyClear` → `HandleTask` → 钩子的实际代码路径，确认 status=2 时 skip。
- [ ] `gateway.go` 装配：`lifecycle.Register` 失败仍不阻断启动；hinter 注入有并发保护（消费者已在跑）。
- [ ] `go build ./... && go vet ./services/gateway/...` 通过；新增单测通过（贴命令与输出末尾）。
- [ ] lifecycle README 有新节。

### API
- [ ] `services/search/search.go` 不在 diff 里。
- [ ] `search_v3.go`（若改）只在 `resType=="baidu"` 分支去 `has_child`，`match`/`precise` 两条路径都处理；注释更新；单测覆盖 baidu/quark/all。
- [ ] profile 报告存在且表格完整、结论明确；请求次数 ≤40（看报告自述）。
- [ ] `valid.go`：`ReportInvalid` 在删旧索引成功后调用；`Source="api-v2-search"`；`EsAlreadyDeleted=false`；nil client 不 panic；失败只 warn。
- [ ] `go build ./... && go vet ./services/... && go test ./services/search/... ./services/valid/... -count=1` 通过。

### 通用
- [ ] 两仓库 `git status` 干净、已 push（`git status -sb` 显示无 ahead）。
- [ ] 无明文凭据进入代码/文档。

## 交付
≤400 字中文：逐条 ✅/❌ 表，❌ 项给 `文件:行` 与建议修法；最后一句"可部署 / 需返工"。
