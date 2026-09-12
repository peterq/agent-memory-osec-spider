# P5 准入阶段 A/B 开发 —— 共享上下文（2026-09-12）

## 背景（读完这一节就知道为什么要做）

资源 ES 索引生命周期改造（三索引 `res_lc_all` + MySQL 64 张分表 `res_lc_<type>_<NN>`）已完成 P4 全量迁入，
下一步 P5 是把搜索流量从 `/api/v2/search`（旧索引 `resource`）切到 `/api/v3/search`（新索引）。
09-12 前置对拍**未通过**，两个原因：

1. **旧链路判失效没同步到新链路**：旧链路（爬虫侧 `url_check` 4 台机 + API v2 `validShareLink`）判失效后只删旧索引
   `resource`，新索引与 `res_lc_*` 分表里那条资源仍是 `status=1`，导致 v3 首页 4% 坑位是死链。→ **阶段 A（D1）**
2. **bnd(百度) 类关键词 v3 慢 3~10×**（quark 反而快 3×），怀疑 `SearchV3` 对 `resType=baidu` 仍带 `has_child(file)` 子句，
   而百度资源基本没有 join 子文档（无 join 百度父 2,905 万 vs join 型仅 948），在 10 亿子文档的 `res_long_2026` 上是纯开销。→ **阶段 B（D3）**

正本计划：`/home/peterq/dev/projects/1s/osec-spider-go/PRD/res-lifecycle/p5-plan-2026-09-12.md`（§2 阶段 A、§3 阶段 B）。
实测数据：同目录 `rollout-2026-09-05.md` §13、`p5-precheck-2026-09-12.md`。

## 仓库

| 简称 | 路径 | module | 说明 |
|---|---|---|---|
| SPIDER | `/home/peterq/dev/projects/1s/osec-spider-go` | `github.com/1s/enfi-spider-go` | 网关（`services/gateway/`）、lifecycle 包 |
| API | `/home/peterq/dev/projects/1s/osec-resource-api` | `github.com/1s/enfi-resource-api` | v2/v3 搜索与 valid |
| COMMON | `/home/peterq/dev/projects/1s/enfi-resource-common` | 契约中心 | **本任务不改 COMMON**（不改 proto） |

go.mod 用 replace 指向本地 COMMON，`go build ./...` 直接可用。

## 硬性约束（违反即返工）

- **v2 永不受影响**：SPIDER 旧清理链路（`res_scheduler/clear_expire.go`）在 lifecycle 未启用/未注入时行为必须逐字节一致；
  API `services/search/search.go`（SearchV2）**不允许出现在 diff 里**。
- **不直接把旧链路判失效写成 lc `status=2`**：旧链路判定与 lc checker 是两套实现（见 SPIDER `services/gateway/lifecycle/README.md`），
  只允许"提前复检"（`next_check_at = now`），由 lc 自己的探测器复检后走既有 `clear.go`。
- 生产 ES/MySQL/Redis 凭据在 `_note/config/*.yaml`，**禁止把任何明文凭据写进代码、测试、文档、汇报**。
- 中文注释；错误用 `github.com/pkg/errors` 包装；沿用各包既有风格（先读同包相邻文件再写）。
- git：不加 `Co-Authored-By`；commit message 中文、前缀沿用仓库习惯（如 `fix(res-lifecycle): …` / `feat(valid): …`）。
  **完成后 commit 并 push 到 master**（用户要求），push 被拦则如实汇报。
- **禁止 Monitor / 禁止"起后台任务再等通知"**：所有命令前台跑完；单测不要跑超过 5 分钟的东西。
- **抽样即可**：任何联网/生产只读验证给出样本量（≤20 条），不要跑全量。
- 不要做生产部署（`deploy.sh`）、不要改生产配置、不要写生产 ES/DB——那是主控在验收后做的。

## 通用验证命令

```bash
cd /home/peterq/dev/projects/1s/osec-spider-go && go build ./... && go vet ./services/gateway/... 
cd /home/peterq/dev/projects/1s/osec-resource-api && go build ./... && go vet ./services/...
```

## 交付格式（所有角色通用）

汇报 ≤400 字中文：改了哪些文件（路径:行）、测试结果（命令 + 通过/失败原文）、commit hash、push 状态、
**明确列出未做/无法验证的项**。不要复述代码。
