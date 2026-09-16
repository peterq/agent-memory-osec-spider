# 2026-09-16 飞书文档解析接入 —— 过程笔记与验证记录

## 需求（用户原话要点）
现有金山文档解析获取网盘链接，需增加飞书文档；示例 2 条 wiki(doc 类型)，还有多维表格类型，网上找链接实现；开发好后多找几个文档验证；其他功能在开发中需用 worktree，合并 master 前确认。

## 产出（三个 worktree，均未 push、未合并）
| 仓库 | worktree | 分支 | 提交 |
|---|---|---|---|
| userscripts | `/home/peterq/dev/projects/peterq/userscripts-wt-feishu` | `feat/feishu-cloud` | `bf4c36d` 云端脚本拆 runtime/kdoc/feishu + verify_cloud.py + 单测 |
| NC-JS | `/home/peterq/dev/projects/1s/ncjs-wt-feishu` | `feat/feishu-doc` | `c10ce3e` spiderAdmin 提交框识别飞书链接 + 单测 |
| SPIDER | `/home/peterq/dev/projects/1s/spider-wt-feishu` | `feat/feishu-doc` | `bc4b25f` doc_crawler 默认脚本地址改 doc-cloud.user.js |

上线还需（人工）：userscripts `pnpm build:cloud && pnpm upload:cloud`（会同时写 OSS 旧对象名 `kdoc.user.js`，doc-crawler 线上不改配置也能用新脚本）；NC-JS spiderAdmin 发布。

## 调研关键结论（正本提炼到 `agent-memory/knowledge/domain-飞书文档解析.md`）
- 匿名（游客）可读公开文档；页面自带内部接口带 cookie 即可调，比啃 DOM/redux 稳。
- docx：`GET /space/api/docx/pages/client_vars?id=<objToken>&mode=7&limit=N` 首片带 `next_cursors`，逐个 `cursor=` 拉；不带 mode 一次返回全部（大文档是否封顶未验证，故用分片）。`mode=4` 是同步块专用，会报 4000091。
- 多维表格：`GET /space/api/v1/bitable/<token>/clientvars?tableID=&recordLimit=3000&needBase=true`，`table`/`base` 是 gzip+base64（`H4sI` 开头，`encoding` 字段为 0 也如此）；表清单 `base.blocks` + `blockInfos`（有 `blockType` 的是仪表盘等）；`recordLimit` 上限 3000（800004006）；小表调 `ondemand/records` 会原样返回全表，`ondemandVer=2` 只对按需表有效。
- `wiki_info_map[token].objType`：22 docx / 8 多维表格 / 12 文件；`/space/api/meta/?type=<objType>&token=` 给 `edit_time`。
- 需登录的文档停在 `accounts.feishu.cn/accounts/page/login?…login_redirect_times=1`，用 `onIntermediatePage` 延时 10 s 确认后发永久失败。
- `tablesv3/` 匿名调用 "Failed to fetch"（疑似 302 到登录页跨域），不用它。
- 公开多维表格样例来自飞书官方模板库（`https://www.feishu.cn/content/base` 页面内链接）。

## 真实文档验证（本机 Chrome + `scripts/verify_cloud.py` 模拟 inject=1，原始记录在 `verify/*.json`）
| URL | 结果 | 链接 | 说明 |
|---|---|---|---|
| mi6gd8l8fvo.feishu.cn/wiki/PqdDwDNF…（示例 1） | ok feishuDocx | 8（夸克 5 迅雷 3） | 与 DOM `a[href]` 去重一致；docMtime 2023-12-29 |
| mi6gd8l8fvo.feishu.cn/wiki/MpO7wcfo…（示例 2） | ok | 48 夸克 | DOM 47 + 1 条在文本里 |
| docs.feishu.cn/article/wiki/UKoZwZBx…（短剧汁源） | ok | 1364 夸克 | 302 到租户域；8 次分片 1484 块 7.6 s；3 批 result |
| docs.feishu.cn/v/wiki/TXUJwa1F…/a4（AI 资源） | ok | 30（百度 28 阿里 2） | |
| docs.feishu.cn/article/wiki/BJppwx5Z… | ok | 2 | |
| mi6gd8l8fvo.feishu.cn/wiki/SEBJwmaC… | ok | 1 | |
| mi6gd8l8fvo.feishu.cn/docx/AjwNd9YF…（直连 docx） | ok | 8 | 与 wiki 形式 version 相同 |
| docs.feishu.cn/v/wiki/EVuawdO9…/ac、TcJjwVP1…/a3 | ok | 0 | 文档本身无网盘链接（DOM 亦 0） |
| larkcommunity.feishu.cn/base/HHgdb3W9…（模板） | ok feishuBitable | 0 | 2 表 118+5 行全部拉到；docMtime 2026-02-06 |
| bytedance.larkoffice.com/wiki/P13Dwren…（wiki 内多维表格） | ok | 0 | larkoffice 域；2 表 |
| langgptai.feishu.cn/wiki/KK5uw1Ya…（PDF） | 永久失败 | | objType=12 |
| www.feishu.cn/wiki/QXlKw5Yi…（已删） | 永久失败 | | code 4000007 |
| tcnqaj820g6y.feishu.cn/base/GJvibLPw…（需登录） | 永久失败 11.8 s | | 登录墙钩子 |
| www.kdocs.cn/l/cdXYaQ5EOakI（金山回归） | ok kdocSheet | 193 | SSO 4 跳后 10 s |

未覆盖：带网盘链接的公开多维表格（网上没找到）、>3000 行按需表的 `ondemand/records` 分页（按抓包的请求格式实现，未在真实按需表上跑过）、Tampermonkey 路径（线上 fc-chrome 未跑）。

## 已知风险 / 待办
- PC 端油猴调度器（`userscripts/src/plugins/scheduler`）从同一队列 `popTask`，不按域名过滤；它打开飞书任务不会有脚本回传，会保活超时失败后由网关重试。上线后若 PC 调度器仍在跑，需给它加"非 kdocs 任务跳过/放回"或只让 doc-crawler 消费。
- 并行的 `feat/qqdoc-cloud`（腾讯文档）若也改 `src/cloud/`，合并时以本分支的 runtime/站点拆分为准接入。
