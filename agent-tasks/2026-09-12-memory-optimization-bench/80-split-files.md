# 任务 80：拆分超长文件 + 提炼 res_lc 会话（先读 01-shared-execute.md）

## 你能动的文件
`agent-memory/lessons/patterns-长周期生产巡检.md`、`agent-memory/knowledge/architecture-nc-js.md`、`agent-memory/procedures/workflow-部署.md`、`agent-memory/knowledge/architecture-api.md`、`agent-memory/knowledge/architecture-spider.md`，以及你在 knowledge/、lessons/、procedures/ 下**新建**的拆分文件。sessions 文件只读。

## 做法（目标：任何文件 ≤ 8,000 字符，`mem.py lint` 不再报「超长」）
1. `patterns-长周期生产巡检.md`（18k）：正文「经验」节 98 条按主题分组压成**可操作清单**（每条一行），留在原文件（≤ 6k）；「实测数据」节移到新文件 `knowledge/domain-bootstrap吞吐实测数据.md`；两边 related 互指。
2. `architecture-nc-js.md`（16k）：按主题拆成 2~3 个文件（例如 `architecture-nc-js.md` 只留分包布局/构建/部署；`architecture-nc-js-qiankun与后台页面.md` 放 qiankun 注册、新增后台页面写法、spiderAdmin；网关对接/鉴权一节如独立成文则命名 `architecture-nc-js-网关对接.md`）。原文件保留并变薄，开头给一段「本文件拆分说明 → 各文件」。
3. `workflow-部署.md`（12k）：把「配置 v2 上线」等一次性历史段落抽出到 `procedures/workflow-部署-历史补充.md`（load rarely），主文件只留常规部署流程、判断现役服务的唯一判据、安全提醒。
4. **提炼 res_lc 会话**：读 `sessions/2026/2026-09-08-res_lc数据纳入后台.md`，把长期有效的能力描述（后台怎么看分表数据、资源列表、分表统计、事件流水、表诊断，对应 API/proto 与前端页面）写进 `architecture-api.md`（接口侧）与 nc-js 拆分后放后台页面的那个文件（页面侧）各一节；keywords 补 `res_lc`、`分表`、`资源列表`、`事件流水`、`表诊断`。
5. `architecture-spider.md`（8.9k）：keywords 补「配置节、yaml、Duration、线上配置同步、缺省值」（正文已有相关内容，评测发现关键词缺失导致找不到）；如仍 > 8,000 字符，把最长的一节拆出去。
6. 每个新文件完整 Front Matter；每个被拆文件更新 summary/keywords/related/updated_at。全文内不得出现指向已不存在章节的引用（拆出去的要改成文件路径）。

## 交付
results-80.md：拆分前后各文件字数表、新文件列表、跨文件引用改动。
