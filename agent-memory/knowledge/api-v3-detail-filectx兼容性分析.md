---
title: v3 detail/fileCtx 对 lc 索引结构的兼容性分析
type: knowledge
status: active
created_at: 2026-09-12T14:40:00+08:00
updated_at: 2026-09-15T15:50:00+08:00
priority: high
keywords: [v3 detail, fileCtx, res_lc_all, 生命周期, LocateIndex, addViews, size 字符串]
questions:
  - detail/fileCtx 能不能直接查 res_lc_all，要改哪
  - /api/v2/detail 为什么报 size 反序列化错误
summary: 结论——lc 索引结构与 v2 detail/fileCtx 的查询方式兼容（nested filelist、join file、fid/parent、routing 均保留），补 v3 只需换索引 + 去重 + 数字字段容错，并删掉已弃用的 addViews；无需改 mapping
load: on-demand
related:
  - agent-memory/decisions/decision-2026-09-04-资源索引生命周期改造方案.md
  - agent-memory/current/tasks.md
---

# v3 detail/fileCtx 对 lc 索引结构的兼容性分析（2026-09-12 代码核对）

## 结论
[事实] **结构兼容，可以补做，且不用改 mapping**。P6 关双写的硬性前置（PRD §12.2 第 6 条）在结构层面没有障碍，只是 API 侧的代码工作量（约 0.5 人日）。

## 逐项核对（API `services/search/search.go` vs SPIDER `PRD/res-lifecycle/es/template_res_short.json`）
| v2 依赖 | lc 索引现状 | 兼容 |
|---|---|---|
| `Detail`: `ids` 查父 + `nested(filelist)` inner_hits（百度资源文件清单） | 模板保留 `filelist: nested`，bootstrap `_reindex` 原样复制 `_source` | ✅ |
| `Detail`: `excludeFields("filelist")`、`isdir` 判定 | 字段名一致 | ✅ |
| `GetFileCtx`: `terms parent/fid` + `Routing(rid)` | `fid`/`parent` 为 keyword（无 `.keyword` 子字段，与 `enfi_resource_v7` 分支同形）；子文档 STORAGE 写入 `routing=父id`，reindex 保留 routing | ✅（须走 `fParent="parent"` 分支） |
| `addViews`: 对 `conf.IndexOfResource` 单文档 `Update` | 别名 `res_lc_all` 指向多索引，ES 拒绝单文档写 | ❌ **已弃用，v3 detail 直接删掉该路径**（见 `decisions/decision-2026-09-12-弃用文档更新类接口.md`） |

## 补 v3 时必须处理的 4 点
1. **索引换成 `conf.IndexOfLifecycle`**，`Detail` 结果按 `_id` 去重（搬迁窗口 cur/long 双命中，同 `search_v3.go:336` 的做法）；`GetFileCtx` 走 `parent`/`fid` 无 `.keyword` 分支。
2. **v3 `Detail` 不调 `addViews`**（[用户确认 2026-09-12] 频繁 update 造成已删文档堆积、磁盘不回收，此类接口已弃用）。
3. **数字字段容错**：`EnfiResource.Size/Expires int64` 遇字符串会 unmarshal 失败。lc 索引里 bootstrap 复制的存量 `_source` 仍是字符串（mapping `long` 只是索引时强转，`_source` 不变；只有 STORAGE 新写入经 `normalizeNumeric` 才是数字），**v2 `/api/v2/detail` 现网就在报这个错**。改成 `json.Number`/自定义 UnmarshalJSON 可同时修好 v2 与 v3。
4. **2 个 `:cur` 半区窗口**（父在 long、子在 cur，21,451 子）：`GetFileCtx` 用 `Routing(rid)` 在 `res_lc_all` 上查，会同时命中 cur 里的子，因此 fileCtx 不受影响；`Detail` 的 nested 路径也不受影响。

## 不在本分析范围
`query/recommend/suggest` 同属"暂不提供"清单（PRD §8.1），只是换索引；`report/likes/dislikes` 与 `addViews` 同为单文档 Update，**已随之弃用，不做 v3**。
