# 角色 20：API —— 深翻页护栏改版（用户 2026-09-16 14:2x 裁定）

在 `94d91f7`（`controller/deep_page.go`：page*pageSize>10000 返回空）基础上改成用户要求的三档规则。前端已把用户翻页限制在前 300 条，所以超过的都是异常访问。

## 规则（以 `rows = page*pageSize` 计）
1. **rows > 400 → 报错**：HTTP **400**，`util.Response{Code: 40001, Msg: "分页超出范围"}`（新加常量，别复用 50005；4xx 不会被 `search_canary.Observe` 计成错误，且不要调用 `canary.Decide`）。
2. **rows > 320 → 记录 uid 并计数**：`logData["deepPage"]=true` 并以 **warn** 级打日志（含 uid、ip、kw、page、pageSize、rows）；redis `INCR searchGuard:deepPage:<key>:<yyyyMMddHH>`，TTL 2h，`key` = uid；uid 为空或 `anonymous` 时用 `ip:<ip>`。**320 < rows ≤ 400 仍正常查询**（只记不拦）。
3. **同一 key 1 小时内 >10 次 → 疑似机器人告警**：计数从 10 跨到 11 时发一封（同 key 同小时只发一次；再跨 100 次时补发一次），POST JSON `{subject, htmlContent, source:"search-guard"}` 到 `config.Config.SearchCanary.NotifyUrl`（为空则只打日志），subject 形如 `[search-guard] 疑似机器人深翻页 uid=xxx 1h 内 N 次`，正文列 ip、最近一次 kw/page/pageSize、两版路径。发送放 goroutine，失败只记日志。
4. 原 `maxResultWindow=10000` 判据不再需要（400 已经拦在前面），删掉或保留为兜底注释均可，但**逻辑以 400 为准**。

## 实现要求
- 抽成 `controller/search_guard.go`：`type deepPageGuard struct{rds redis.Cmdable; notifyUrl string; now func() time.Time; post func(url string, body []byte) error}`，方法 `Check(uid, ip, kw string, page, pageSize int) (verdict int)`（0 正常 / 1 记录 / 2 拒绝），计数与告警在内部；纯判定函数 `classifyRows(rows int) int` 单测覆盖 300/320/321/400/401。
- redis 用 `config.GetRedis()`（与 canary 同实例）；redis 出错只记日志、不影响返回（护栏是旁路，不能拖垮搜索，参考记忆 `lessons/failure-旁路能力初始化拖垮主流程.md`）。
- v2 `SearchApi` 与 v3 `SearchApiV3` 同改；注入方式照 `canary` 字段（`controller/com-api.go`）。
- 单测：`classifyRows` 表驱动；`Check` 用 miniredis（仓库已有依赖）验证计数、TTL、跨 10 次只告警一次（fake post 记录调用次数）。
- 常量与规则写进 `controller/search_guard.go` 顶部注释；`services/search-canary/README.md` 末尾加一小节「深翻页护栏」说明三档规则与告警。
- 不改 `services/search/*.go`；中文注释；commit 前缀 `fix(search)`；push master；**不部署**。

## 验证
```bash
cd /home/peterq/dev/projects/1s/osec-resource-api && go build ./... && go vet ./controller/... && go test ./controller/...
```
交付 ≤300 字中文：改动文件、测试原文、commit、push、未做项。
