# 过程追加（主控维护）

- 2026-09-16 派单：10/20/30/40/50/60/70/80/85 九个开发角色并行（sonnet），45（NC-JS 前端）待 40 交付契约后派。
- 合并顺序预案：COMMON 分支先（delete-breaker → valid-unify → health-observe → ci → secrets），每合一个 `go build`；再 SPIDER/API/STORAGE。合并前须用户确认。
- 已知重叠文件：API `services/valid/valid.go`/`valid_v3.go`（10 与 20）；SPIDER `config/gateway/gateway.go`、`services/gateway/gateway.go`（10/30/40）；API `config/config.go`（10/30/85）；两份下载测试文件（50 加标签、60 改内容）。

## 交付/验收进度
- ✅ 85 search-config：`api-wt-search-config` `7677fcf`，验收通过（search_canary 未接 featureflag 为授权简化；keywords.txt 与 PRD p5-recheck 对拍表逐行一致）。待用户确认合并。
