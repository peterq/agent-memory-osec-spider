# 角色 20：API —— `services/valid/bnd-api.go` 百度判定与 SPIDER `classifyBndShare` 对齐

先读 00-shared.md（背景与硬性约束；本角色不涉及重爬投递，只改 API 仓库 `/home/peterq/dev/projects/1s/osec-resource-api`，module `github.com/1s/enfi-resource-api`）。

## 背景
API v2 `validShareLink` 走 `services/valid/bnd-api.go` 判百度分享有效性，判失效会删旧索引并 `ReportInvalid` 到 lc（不可逆）。
它现在用正则 `(不存在|违规|链接已过期)` 匹配**整页 HTML**，只对「部分文件违规」做了特判；文件名/描述含「不存在」等词就会误判。
SPIDER 09-12 已把同一判定改成业务码优先（`06ef50d`/`e16bd98`），两套实现必须同口径（记忆 `lessons/success-网盘失效判定原则.md`：看业务码不看文案，未知一律报错）。

## 必读
1. SPIDER `services/gateway/valid/bnd_checker.go` 的 `classifyBndShare` + `bndInvalidErrnos` + `bndInvalidMsgRegexp`（**逐字照搬判定顺序**）与 `bnd_checker_test.go`（真实页面片段，可直接复制到 API 测试）。
2. API `services/valid/bnd-api.go` 全文、`bnd-api_test.go`、`valid.go` 里 bnd 分支的调用方式与返回语义（`(bool, error)`；error 表示未知/探测失败，调用方不得当失效）。
3. API `services/valid/valid_v3.go` —— v3 是否复用同一 bnd 判定；若是，改一处即可。

## 交付
- `bnd-api.go`：抽出与 SPIDER 同名同语义的纯函数 `classifyBndShare(statusCode int, body string) (valid, known bool)`，`CheckValid` 只保留请求 + 调它 + 未知时 Warn 并返回 error；删掉旧正则的整页匹配与 `log.Println(body)`（整页打日志太大）。
- `bnd-api_test.go`：把 SPIDER 的 12 个用例（含「违规 tooltip 有效页」「链接不存在 errno 145」「need verify 未知」「只有违规文案未知」）搬过来；原有用例保留（若与新口径冲突，以新口径为准并在注释说明）。
- 不改 quark/xunlei；不改 `search*.go`。
- `go build ./... && go vet ./services/valid/ && go test ./services/valid/ -run Bnd`；commit 前缀 `fix(valid)`，push master。**不部署。**
