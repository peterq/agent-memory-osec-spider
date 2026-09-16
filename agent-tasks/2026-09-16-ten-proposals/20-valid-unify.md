# 角色 20：有效性检测合并为一套实现（提案 4）

短名 `valid-unify`。worktree：`common-wt-valid-unify`、`spider-wt-valid-unify`、`api-wt-valid-unify`（分支 `feat/valid-unify`）。

## 目标

API `services/valid/*` 与 SPIDER `services/gateway/valid/*` 两套独立的网盘有效性检测合并为 COMMON 一套；
业务码表集中；百度/迅雷去掉纯文案匹配，改按业务码/结构化字段判定，判不准返回错误而不是失效。

## 必读

1. `agent-memory/knowledge/domain-网盘有效性检测.md` 全文（两套实现位置、各网盘判定接口与码表）。
2. `agent-memory/lessons/success-网盘失效判定原则.md`；`agent-memory/knowledge/domain-迅雷分享爬取.md` §5（迅雷状态码共用码表已做在 SPIDER，找到并复用）。
3. SPIDER `services/gateway/valid/*.go`（含 `*_test.go`、`valid_live_test.go`）与 API `services/valid/*.go`：逐个网盘对照两边差异，**以更严格、有业务码的一边为准**；差异列成表放进 README。
4. `agent-memory/current/tasks.md` 中「夸克业务码 41031」「bnd/xunlei 纯文案匹配」两条待办。

## 设计

- COMMON 新包 `panvalid`：
  - `type Checker interface{ Check(ctx, Share{Type, ShareId, Pwd, Url}) (Result, error) }`，`Result{State: Valid|Invalid|Unknown, Code string, Reason string, Raw string(截断)}`；`Unknown` 必须伴随 error。
  - 每种网盘一个文件 `quark.go / alipan.go / bnd.go / xunlei.go` + `codes.go`（集中码表，含注释：码值、含义、来源、加入日期）。
  - HTTP 客户端、代理、UA、Cookie/凭据通过 `Options` 注入（接口类型），包内不读配置、不直连代理池，便于两边各自注入。
  - 表驱动单测：每网盘 ≥15 条响应样本（从两边现有测试与 `_test.go` 里的样本搬，缺的用真实响应结构造），覆盖 valid/invalid/unknown 三态；未知响应必须 `Unknown+error`。
  - `valid_live_test.go` 之类联网测试带 `//go:build live` 标签，默认不跑。
- SPIDER `services/gateway/valid/*`：改成薄适配层（注入代理池 http client 等）调用 COMMON；保留原导出函数签名，调用方零改动。
- API `services/valid/*-api.go`、`valid.go` 判定部分：同样改薄适配。**不要碰**删除 ES 的那几行（另一角色 `delete-breaker` 在改）。
- README `panvalid/README.md`：码表、两边原实现差异表、如何加新码、联网自测方法。

## 文件所有权

COMMON：`panvalid/**`。SPIDER：`services/gateway/valid/**`。API：`services/valid/{quark-api.go,bnd-api.go,xunlei-api.go}`、`valid.go`/`valid_v3.go` 中**仅判定逻辑**（阿里检测若在别处也归你）。

## 验证

三仓库 `go build ./...`；`go vet`/`go test` 覆盖 `panvalid`、SPIDER `services/gateway/valid`、API `services/valid`（不带 live 标签）。

## 交付

分支/提交、差异对照表、码表、测试输出、需要主控联网抽样复核的判定点（列出每网盘 3 个真实分享 id 的预期结果，主控用只读探针跑）。
