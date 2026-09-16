# 角色 30：API —— resType 参数校验前置（非法值返回 400 而非 500，v2/v3 同改，不部署）

## 背景
`/api/v2/search` 与 `/api/v3/search` 收到非法 `resType`（线上真实出现 `ali`、`xunlei`、`ali-share`，多为匿名调用方）时，
`SearchV2`/`SearchV3` 在 `services/search/search.go:300` / `search_v3.go:135` 返回 `api_error.ErrInvalidResType`，controller 统一按内部错误回 **500**。
两版一致，是既有缺陷；但灰度到 100% 后窗口里没有 v2 样本，这 2 个 500 让 `search_canary` 误判 v3 错误率 0.23% > 0.1% 而回落到 0%（2026-09-17 00:18）。
参数错误应回 4xx：既符合语义，也不会被 canary 计入错误率（它只统计 status>=500）。

## 要求
- 在 controller 层（`controller/api.go` `SearchApi`、`controller/api_v3.go` `SearchApiV3`）取到 `resType` 后立即校验：合法集合**从 `services/search/search.go` 与 `search_v3.go` 现有分支推导**（含空串与 `all`），两处必须一致；抽成 `controller/res_type.go` 的纯函数 `isValidResType(string) bool` + 常量切片，注释写明来源行号。
- 非法值：HTTP **400**，`util.Response{Code: 40002, Msg: "resType 无效"}`（新常量，放 `search_guard.go` 旁或同文件），`logData["invalidResType"]=resType` 记 info 日志；不调用 `canary.Decide`。
- **不改** `services/search/*.go`（那里的兜底 `ErrInvalidResType` 保留）。
- 单测：`TestIsValidResType` 覆盖合法全集、空串、`all`、`ali`/`xunlei`/`ali-share`/大小写不同的非法值。
- `go build ./... && go vet ./controller/... && go test ./controller/...`；commit 前缀 `fix(search)`；push master；**不部署**；不加 Co-Authored-By；中文注释。
交付 ≤200 字：改动文件、测试原文、commit、push。

## 补充（主控 09-17 01:50）
- 两版还有一处差异：`search.go:295` 在 `resType==""` 时默认 `baidu`，而 `search_v3.go:133` 没有这个默认，空值会走到 `ErrInvalidResType` → 500。
  在 controller 校验之前先把空串归一化为 `baidu`（v2/v3 同做），再传给 SearchV2/SearchV3，使两版对空值行为一致；单测补空串归一化用例。
- 合法集合以 `services/search` 里的 `resTypeMap` 键 + `all` 为准（把 map 的定义位置写进注释）。
