---
title: 网盘链接有效性检测
type: knowledge
status: active
created_at: 2026-09-02T16:35:00+08:00
updated_at: 2026-09-16T09:10:00+08:00
priority: high
keywords:
  - panvalid
  - 有效性检测
  - validShareLink
  - 失效
  - 夸克
  - 阿里云盘
  - 业务码
  - 限流
  - 41031
summary: 两套有效性检测已于 2026-09-16 合并为 COMMON panvalid 一套实现（分支 feat/valid-unify，未合并 master）；本文件保留历史背景与各网盘判定要点，权威码表/差异表/联网自测方法见 panvalid/README.md
questions:
  - 链接失效检测怎么做，validShareLink 返回 -1 是什么意思
  - 夸克/阿里网盘判定不准怎么排查
  - 误删资源怎么避免
  - panvalid 是什么，和旧的两套实现什么关系
load: on-demand
related:
  - agent-memory/knowledge/architecture-api.md
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/lessons/success-网盘失效判定原则.md
  - agent-tasks/2026-09-16-ten-proposals/20-valid-unify.md
---

# 网盘链接有效性检测

## 0. 2026-09-16 合并为 panvalid（`[事实]`，未合并 master）

`agent-tasks/2026-09-16-ten-proposals/20-valid-unify.md` 把下面 §1~§3 描述的"两套独立实现"
合并成 COMMON 新包 `enfi-resource-common/panvalid`（分支 `feat/valid-unify`，三仓库
COMMON/SPIDER/API 都已提交，**尚未合并 master**，合并前需用户确认）。合并后:

- 业务码表集中在 `panvalid/codes.go`，唯一正本；夸克 `41031` 已补进正式码表
  （此前只靠 message 兜底正则命中，见 §2 末尾）。
- 阿里云盘统一成 API 原来那套单请求实现（`api.aliyundrive.com`），SPIDER 那条
  `bj29.api.aliyunpds.com` 3 次请求的链路已废弃（详见 §3 末尾"合并后"）。
- 迅雷: COMMON 内置默认码表（与旧 API 硬编码表一致），SPIDER 侧注入
  `services/xunlei-pan/share_status.go` 正本表保持同源（避免 panvalid 反向依赖 SPIDER）。
- SPIDER `services/gateway/valid/*` 与 API `services/valid/*` 都改成薄适配层
  （只负责把各自的代理池适配成 `panvalid.HTTPDoer`），原导出函数签名不变。
- **权威信息(码表全文、两边旧实现差异对照表、如何加新码、联网自测方法)以
  `enfi-resource-common/panvalid/README.md` 为准**；下面 §1~§4 是合并前的历史背景，
  仍可用来理解"为什么会有两套"及排查合并前的线上问题，但新码/新差异不要再往这里加。

## 1. 两套实现（合并前, 互相独立, 改一处要想清楚另一处要不要跟）

| 用途 | 代码位置 | 入口 |
|---|---|---|
| 对外查询接口（前端/其他部门） | `osec-resource-api/services/valid/` | `POST /v2/validShareLink`（`controller/api.go` `ValidShareLink`） |
| 存量资源过期清理 | `osec-spider-go/services/gateway/valid/` | `services/devops/clear_expire`（`ValidShareId`） |

- [事实] 两边都按 `spider_contract.ParseShareLink` 解析出 `typ + shareId`，
  再按 `bnd / ali-share / quark / xunleipan` 分派到各自的 checker。
- [事实] 两边都有 redis 缓存键 `shareValid:<typ>:<id>`，TTL 1 小时。
- [事实] **判定为失效会触发删除**：API 侧 `deleteInvalid` 直接删 ES 文档；
  SPIDER 侧推 `DeleteResourceTask`。所以「拿不准时必须返回 error，不能返回 false」。
- [事实] `ValidShareLink` 把 checker 的 error 映射成 `status = -1`，
  用户看到的"检测出问题"就是这个 -1。

## 2. 夸克（quark）

判定接口（一次请求即可）：

```
POST https://drive.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc
body: {"passcode":"", "pwd_id":"<shareId>"}
```

[事实] 响应里的 `code` 是数字业务码，比 `message` 文案稳定，判定以 `code` 为主、`message` 正则兜底：

| code | message | 判定 |
|---|---|---|
| 0 | ok | 有效（`data.stoken` 有值） |
| 41004 | 文件不存在 | 失效 |
| 41006 | 分享不存在 | 失效 |
| 41010 | 文件涉及违规内容 | 失效 |
| 41011 | 分享地址已失效 | 失效 |
| 41012 | 好友已取消了分享 | 失效 |
| 41031 | 分享者用户封禁链接查看受限（HTTP 403） | 失效（2026-09-03 site-discovery 评测 slowread.net 时实测发现，见下方 [事实]） |
| — | 含"提取码/访问码" | **有效**（分享还在，只是要密码） |

- [事实] 失效时 HTTP 状态码是 404，不是 200，所以不能靠 HTTP 状态码判定。
- [事实] 2026-09-02 线上故障的直接原因：`41004 文件不存在` 从没被识别过，
  15 条抽样里有 4 条命中，全部返回 -1。
- [事实] 2026-09-03 在 site-discovery 任务里评测 `slowread.net` 时，73 条抽样中有
  43 条（近六成！）命中新码 `41031 分享者用户封禁链接查看受限`（分享者账号被封，HTTP 403）。
  `site-discovery/tools/pancheck.py` 的 `QUARK_INVALID_CODES` 已经把它加进去按失效处理。
  交叉检查发现当时 `osec-resource-api/services/valid/quark-api.go` 和
  `osec-spider-go/services/gateway/valid/quark_checker.go` 的 `classifyQuarkShare`
  这两处生产代码**code 白名单里都没有 41031**，只靠各自的 `quarkInvalidMsgRegexp` 兜底正则
  硬编码"分享者用户封禁链接查看受限"这句文案兜底，依赖文案不变，很脆弱。
  **`[事实]` 2026-09-16 已随 §0 的 panvalid 合并把 41031 补进正式码表**（`panvalid/codes.go`），
  两处旧 checker 已废弃改为薄适配层。

## 3. 阿里云盘（ali-share）

两个域名是同一套后端，字段略有差异：

- `https://api.aliyundrive.com/adrive/v3/share_link/get_share_by_anonymous`
  → 返回 `share_title`、`has_pwd`、`file_infos[]`、`file_count`（API 侧用这个，一次请求）
- `https://bj29.api.aliyunpds.com/v2/share_link/get_by_anonymous`
  → 返回 `share_name`、`has_pwd`、`need_check_pwd`，**不返回 `file_infos`**（SPIDER 侧用这个，
  再走 `get_share_token` + `v2/file/list` 共 3 次请求）

失效业务码（`code` 字段，字符串）：

```
ShareLink.Cancelled       分享者已取消分享
ShareLink.Forbidden       分享被封禁
ShareLink.Expired         分享已过期
ShareLink.ContentInvalid  分享内容已失效（被举报/屏蔽），HTTP 400
NotFound.ShareLink        分享不存在
NotFound.Drive            分享者网盘不存在
```

两个必须知道的坑：

1. [事实] **`TooManyRequests`（HTTP 429）是限流，不是失效**。
   直连不挂代理时抽 15 条就能稳定复现 5 条。必须 `BlockProxy` + 退避重试，
   重试用尽再报 error，绝不能返回 false（会删 ES 数据）。
   限流也可能表现为**空 body**，JSON 解析失败要一并按限流重试。
2. [事实] **分享入口还在但内容已被删除/屏蔽**：
   `share_title` 有值、`file_count > 0`，但 `file_infos` 是空数组 `[]`。
   这种链接打开是死的，必须判失效。SPIDER 侧靠 `file/list` 返回 `items` 为空发现，
   API 侧靠 `file_infos` 为空发现（不用多发请求）。

3. [事实] `bj29.api.aliyunpds.com` 的 `need_check_pwd` **恒为 true**，不携带任何信息；
   真正表示"有密码"的是 `has_pwd`，无密码的分享则**不返回** `has_pwd` 字段。
   `alipan_checker.go` 里 `else if need_check_pwd { noPwd = true }` 的写法看着可疑，
   但结论正确（has_pwd 缺失 ⇒ 无密码），不要"顺手修"。

**`[事实]` 合并后(§0)**：panvalid 统一走 `api.aliyundrive.com` 单请求（API 原来那套），
SPIDER `bj29.api.aliyunpds.com` 那条 3 次请求(`get_share_by_anonymous` 判code → 换
`get_share_token` → `file/list` 查文件数)的链路已作废——两边业务码表本来就完全一致，
差异只在请求次数，少请求的一边更优。SPIDER `AliPanValidChecker.CheckValid2`(历史遗留,
供 `services/devops/2409/ali_download` 用)因此额外多做一次 `has_pwd` 探测请求来还原
"是否需要提取码"，其余调用方不受影响。

## 4. 联网自测

两个仓库各有一份环境变量开关的联网用例，跑的是同一批 15+15 条样本链接，
断言只看「不报 error」，有效与否打印出来人工核对：

```bash
cd osec-resource-api  && VALID_IT=1 go test ./services/valid/ -v -run TestLiveShareValid
cd osec-spider-go     && VALID_IT=1 go test ./services/gateway/valid/ -v -run TestLiveShareValid
```

- 文件：`services/valid/valid_live_test.go`、`services/gateway/valid/valid_live_test.go`。
- [注意] 样本链接会随时间失效，断言不要写死 valid 的数量。
