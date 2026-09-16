# 角色 10：API —— 搜索接口深翻页护栏（v2/v3 同改，不部署）

## 背景
`/api/v2/search`、`/api/v3/search` 对 `page*pageSize > 10000` 的请求（机器人深翻页，如 `kw=test page=1525 pageSize=15`）会把 `from=22,875` 直接交给 ES，
撞上 `index.max_result_window=10000` 返回 `search_phase_execution_exception` → 接口 500（`code 50005`）。v2/v3 同样失败，是既有缺陷；
2026-09-16 两次把灰度分流器 `search_canary` 的 v3 错误率顶过 0.1% 阈值触发误回落（rollout §17）。用户要求根治：在 API 层拦截，不再让这类请求打到 ES。

## 仓库
`/home/peterq/dev/projects/1s/osec-resource-api`（module `github.com/1s/enfi-resource-api`）。

## 硬性约束
- 只改 controller 层参数校验（`controller/api.go` `SearchApi` 与 `controller/api_v3.go` `SearchApiV3`，以及 `EnfiSearchApi` 若同样透传 page），**不改** `services/search/*.go` 的查询实现。
- 判据与 ES 一致：`page*pageSize > 10000`（`maxResultWindow` 常量 10000，注释说明来源）。命中时返回 **HTTP 200 `{code:0,msg:"succeed",data:{resources:[],total:0}}`**（与正常空结果同形，前端翻页不报错；不要 400——调用方 `dashengpan_web` 对 4xx 会弹错）。走既有 `encryptData` 分支时也要同形处理。
- 日志：命中时用既有 `logData` 加 `"deepPage":true` 打一条 info（不是 error），便于统计机器人；**不要**让 `search_canary.Observe` 记成 error（返回 200 自然就不会）。
- 抽成纯函数 `isDeepPage(page, pageSize int) bool` 放 `controller/`，单测覆盖：边界 10000 不拦、10001 拦、page/pageSize 缺省值路径。
- 中文注释；不动 `search.go`/`search_v3.go`；不加 Co-Authored-By；commit 前缀 `fix(search)`；push master；**不部署**（主控拿到用户确认后 `./deploy.sh`）。

## 验证
```bash
cd /home/peterq/dev/projects/1s/osec-resource-api && go build ./... && go vet ./controller/... && go test ./controller/...
```

## 交付
≤300 字中文：改动文件（路径:行）、测试输出原文、commit hash、push 状态、未做项。
