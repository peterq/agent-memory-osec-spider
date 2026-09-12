# 任务 80 结果：拆分超长文件 + 提炼 res_lc 会话

## 做了什么

1. `lessons/patterns-长周期生产巡检.md`：98 条"经验"按 6 个主题（巡检操作规范/进度吞吐判断/限速守护冲突/数据一致性校验/配置上线/批量运维）压缩成可直接照做的清单，去掉了轮次编号与已被后续轮次推翻的中间结论，只保留当前最优做法；「实测数据」节整体移到新文件。
2. `knowledge/architecture-nc-js.md`：按主题拆成 3 个文件（仓库/构建部署、qiankun+页面、网关对接），原文件开头加了拆分说明。为补齐 res_lc 页面信息，去 `1s/nc-js` 仓库核实了实际组件文件名（`ResourceListPage.tsx` 等）、`MenuKeys`、菜单分组 `grp-lc`，未凭空杜撰。
3. `procedures/workflow-部署.md`：把 5 段"YYYY-MM-DD ×次网关重部/上线补充"的一次性历史记录整体移到新文件，主文件只留用法/主机映射/现役服务判据/主机选型/部署机制/配置分发/重启前依赖验证/安全提醒/auto 模式分类器（后两者判断为仍在生效的通用规则，保留在主文件）。
4. `knowledge/architecture-api.md`：新增「res_lc 分表数据只读能力」一节，去 `1s/nc-js` 仓库核实了实际 RPC 方法名（`ListResources`/`TableStats`/`ListEvents`/`TableDiagnostics`，均属 SPIDER 网关 `spider.lifecycle.LifecycleRpc`，非本服务路由，已在文中显著标注归属）；`architecture-nc-js-qiankun与后台页面.md` 对应新增「res_lc 分表数据后台页面」一节（页面/组件/RPC 对应表 + 前端已知坑）。keywords 补了 `res_lc`/`分表`/`资源列表`/`事件流水`/`表诊断`。
5. `knowledge/architecture-spider.md`：补了 keywords（配置节/yaml/Duration/线上配置同步/缺省值）；因加词后仍 >8000 字符，把最长的「队列约定」一节整体拆到新文件 `architecture-spider-队列约定.md`，原文件留一句指引 + `related` 互指。

## 拆分前后字数

| 文件 | 拆分前 | 拆分后 |
|---|---|---|
| `lessons/patterns-长周期生产巡检.md` | 18,396 | 6,909 |
| `knowledge/architecture-nc-js.md` | 16,223 | 6,408 |
| `procedures/workflow-部署.md` | 11,719 | 6,384 |
| `knowledge/architecture-api.md` | 2,416 | 4,221 |
| `knowledge/architecture-spider.md` | 8,942 | 6,915 |

## 新建文件列表（均 ≤8,000 字符，完整 Front Matter）

| 新文件 | 字数 | 内容 |
|---|---|---|
| `knowledge/domain-bootstrap吞吐实测数据.md` | 2,280 | 从 patterns 文件移出的「实测数据」节 |
| `knowledge/architecture-nc-js-qiankun与后台页面.md` | 7,980 | qiankun 机制、页面写法约定、新增页面落点、res_lc 4 个后台页面、页面/样式已知坑 |
| `knowledge/architecture-nc-js-网关对接.md` | 5,297 | WebRTC/gRPC 传输、GitHub OAuth 鉴权、RPC 清单、proto 生成、网关 IP 硬编码坑 |
| `procedures/workflow-部署-历史补充.md` | 6,508 | 5 段一次性上线/重部踩坑记录（load: rarely） |
| `knowledge/architecture-spider-队列约定.md` | 3,140 | 队列 v2 的队列名/去重键/消费者并发度/通用队列命名空间 |

## 跨文件引用改动

- `patterns-长周期生产巡检.md` ↔ `domain-bootstrap吞吐实测数据.md`：related 互指，正文各留一句指向对方。
- `architecture-nc-js.md` 开头新增"本文件拆分说明"，三份 nc-js 文件 related 互相指向，正文内 `§3.1`/`§4` 等引用逐一核对指向仍存在的小节。
- `workflow-部署.md` ↔ `workflow-部署-历史补充.md`：related 互指；主文件"部署机制"一节保留了已固化进 `deploy.sh` 的加固结论（`scp -C`、`docker rm -f` 重试+校验创建时间），细节留给历史文件。
- `architecture-spider.md` ↔ `architecture-spider-队列约定.md`：related 互指，「队列约定」小节标题保留、正文改成一句指引。
- `architecture-api.md` 新增 related 指向 `architecture-spider.md`、`architecture-nc-js-qiankun与后台页面.md`、res_lc 会话文件；`architecture-nc-js-qiankun与后台页面.md` 反向指回 `architecture-api.md`。

## 有疑问的取舍

- **架构-api.md 归属问题**：res_lc 的 4 个新方法实际是 SPIDER 网关 `LifecycleRpc` 的方法，不是 `osec-resource-api` 自己的路由。任务单明确要求写进 `architecture-api.md`「接口侧」，但为避免误导，我在该节开头加了一段"⚠️ 注意归属"说明其真实位置在网关侧，仅信息落点放在此文件。如果后续统一记忆结构时想把它挪去 `architecture-spider.md` 或队列约定文件旁边，需要相应agent处理。
- **00-overview.md / 01-index.md 存在过期引用**：如 `00-overview.md` 写"长周期生产巡检模式（98 条）"、`01-index.md` 写"architecture-nc-js.md §7"、"第 5 节"等，均已因本次拆分失效。按 01-shared-execute.md 的文件边界要求（"每个任务只能动自己任务单里列出的文件"），这两个文件不在我的任务单内，未做修改，留给负责索引/总览的 Agent 处理。
- `patterns-长周期生产巡检.md` 压缩后 6,909 字，略高于任务描述里的"≤6k"目标（硬性 lint 阈值是 8000，已满足），是在保留 98 条经验实质信息与"不丢判据"之间取舍后的结果；已把纯数值挪空，进一步压缩会开始损失可操作性判据，故未继续硬压到 6000 以下。
- `mem.py lint` 全量跑了一遍：无我改动文件的"超长"/"悬空引用"/"元数据缺失"问题；报告的 5 条问题均属其他文件（01-index.md 常驻超长、几个 sessions/procedures 的 updated_at 落后 git、索引过期），不在本任务范围。
</content>
