---
title: 失败经验：copy_child 子文档计数校验用对称差，目标多出也被判不达标而整窗白跑
type: lesson
status: active
created_at: 2026-09-07T08:00:00+08:00
updated_at: 2026-09-12T23:15:00+08:00
priority: high
keywords: [bootstrap, copy_child, childCountOk, version_conflicts, 重跑, FailedSlices, 双写, url_check, 对称差]
summary: childCountOk 用 |src-dst| 判达标，但 cur 含双写、long 源侧被删，dst>src 是结构性的；重跑幂等补不回，白跑 2.5 h
load: on-demand
related:
  - agent-memory/lessons/patterns-长周期生产巡检.md
  - agent-memory/archive/2026/decision-2026-09-06-全量bootstrap动态rps守护续跑.md
---

# 失败经验：计数校验对称差误判

## 问题背景

全量 bootstrap 作业 id=8 copy_child 阶段（2026-09-06 晚~09-07），窗口体量到 5,000 万~1 亿。

## 失败表现（[事实]，第 7 轮巡检实测）

| 时间 | 窗口 | src | dst | 结果 |
|---|---|---|---|---|
| 20:03 | `child:t202402010000:cur` | 278,408 | 308,947（+11%） | 重跑 2 分钟仍不达标，进 FailedSlices |
| 22:58 | `child:t202403010000:long` | 54,919,896 | 55,242,299（+0.59%） | **重跑 5,492 万文档白跑 2.5 h**，15.4M version_conflicts / created 246 |
| 04:02 | `child:t202404010000:cur` | 199,419 | 447,255（+124%） | 重跑 1 分钟仍不达标，进 FailedSlices |

对照正常：07:45 `child:t202405010000:long` src 100,482,045 > dst 99,471,992（真缺 101 万），重跑有意义。

## 根本原因

`services/gateway/lifecycle/bootstrap.go` `childCountOk`（约 1347 行）判据 `|src-dst| > max(100, 0.1%·src)`，把 `dst > src` 也当不达标。`dst > src` 是结构性的：① `:cur` 目标 `res_short_202609` 含线上双写产生的、不属于本窗口源集合的子文档；② `:long` 复制期间源索引子文档被 url_check 删除，目标不跟删。重跑用同一幂等 reindex，只能得到 version_conflicts。

## 规避 / 修复

- 判据只看短缺 `src - dst`，`dst >= src` 直接通过：已修复 master `b5073cf` / hotfix `ca92fb3`（单测含三组生产实测数据），2026-09-07 08:35 用户确认第三次热修重部。
- [事实] FailedSlices 不影响作业终态（只 append，B5/finish 不消费），旧误报槽仅为展示残留。
- 巡检时看到同窗口第二次 reindex 且 version_conflicts ≈ total、created ≈ 0，即为白跑。

## 连带教训

- **在空转期（全 version_conflicts 重跑）给守护加档有采样偏差**：22:08~23:30 peak 从 10000 加到 18000 时集群几乎无真实写入，r 偏低；真实压力要到下一个新窗口才体现（所幸隔夜 r 4~9%，heap 仅 1 次硬熔断 45 秒自愈）。
- B5 verify 只对父文档对拍，不校验子文档；FailedSlices 的后果待代码核实。

## 续：结构性短缺同样触发无效重跑（2026-09-09 第 16 轮）

- [事实] `ca92fb3` 修了 dst>src 的误判后，`:long` 半区出现 dst<src 0.6%~5.6% 的短缺，仍触发整窗重跑；重跑为 `op_type=create`，全部 version_conflicts，前后计数逐字不变，纯浪费（26 窗、58% 时间）。
- [事实] 抽样源窗口 1000 个子文档 `_id` 在目标 1000/1000 存在——短缺是计数口径的结构性差异；[待确认] 疑似源索引同 `_id` 子文档挂不同父 routing，reindex 后合并。
- 修复方向：整窗重跑只在首次 reindex 未正常完成（取消/failures/处理数<total）时进行；正常完成的短缺记 `shortfallSlices` 供事后对账，不重跑、不记 failedSlices。
