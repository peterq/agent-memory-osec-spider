---
title: 成功经验：配置 v2 上线准备阶段发现的两个衔接问题
type: lesson
status: archived
created_at: 2026-09-08T11:40:00+08:00
updated_at: 2026-09-12T23:20:00+08:00
priority: medium
keywords:
  - 配置v2
  - github_auth
  - spider.gateway.prod.yaml
  - spider.prod.yaml
  - oss.last
  - deploy.sh
  - uploadConfigToOss
summary: v1/v2 两份网关配置文件同名字段易贴错目标文件；README §2.7 首次上传前置步骤的表述与 uploadConfigToOss 实际代码逻辑相反
load: rarely
related:
  - agent-memory/current/tasks.md
  - osec-spider-go/PRD/config-v2/README.md
  - osec-spider-go/PRD/config-v2/rollout-runbook-2026-09-08.md
---

# 成功经验：配置 v2 上线准备阶段发现的两个衔接问题

## 问题

主控告知"用户已把 `github_auth` 节贴进 `_note/config/spider.prod.yaml` 的 `services.gateway`
下"，核对时用 python 结构化解析（不打印值）发现 `spider.prod.yaml` 里根本没有 `github_auth`
键——`config_show` 的输出看起来"有"这个节，是因为 `GithubAuthConfig.applyDefault()` 对
`Org`/`SessionTtl`/`RedirectUriPrefixes` 三个字段有缺省值回填，**父节点整个缺失时子字段的缺省值
和"父节点存在但三件套为空"在 `config_show` 的打码输出里长得一模一样**，光看 `config_show` 会误判
为"已配置但为空"而不是"根本没贴对地方"。

## 适用条件

任何"新配置节是否已被人工贴入某份 yaml"的核对场景，尤其该配置节里混有"有缺省值的字段"和
"无缺省值、留空才会告警/panic 的字段"（本例中 `Org`/`SessionTtl`/`RedirectUriPrefixes` 有默认值，
`ClientId`/`ClientSecret`/`SessionSecret` 没有）。

## 推荐做法

1. **不要只看 `config_show` 的打码输出判断"某节是否存在"**——它是反序列化后的 struct 转储，
   缺省值回填会掩盖"父节点缺失"和"父节点存在但字段为空"的区别。
2. 用 `python3 -c "import yaml; d=yaml.safe_load(open(...)); ... .get('X') is not None"` 直接对
   **原始 yaml 树**做键存在性判断，只打印布尔值/长度，不打印内容。
3. 本项目里 `services.gateway` 这份配置历史上有两份文件（v1 时代遗留的
   `_note/config/spider.gateway.prod.yaml` 顶层字段 = v2 `spider.prod.yaml` 的
   `services.gateway.*` 子字段，字段名逐字对应，见 `scripts/config_v2_build_prod_yaml.py`），
   人工手贴新字段时**天然容易贴到旧的那份文件**（本例正是如此）。发现后用 ruamel.yaml
   round-trip 读写做结构化合并（只搬运目标子树，不重新序列化整份文件），可以在不破坏原文件
   格式/注释的前提下补正。

## 原因

`applyDefault()` 类缺省值回填是"填未设置的字段"，而不是"填未设置的节"——按 Go 反射逐字段
判断零值时，父 struct 是否被真实解析出来过并不影响子字段的缺省值填充逻辑，两种情况在最终
输出里没有区别。

## 第二个问题：README §2.7 步骤 4 与实际代码相反

`PRD/config-v2/README.md`（2026-09-05 版）步骤 4 写"先 `cp spider.prod.yaml
oss.last.spider.prod.yaml` 生成首次上传基线，再 `./deploy.sh deploy <服务>`"，但
`deploy.sh` 的 `uploadConfigToOss` 首次上传分支的判断逻辑是: **本地 `oss.last.*` 存在
就判定"状态不一致"直接 `return 1` 报错退出**，上传成功后由脚本自己生成这份基线。按 README
原文操作会导致真正执行时第一步就报错退出。已在 README 与 `rollout-runbook-2026-09-08.md`
里订正：**不要**预先创建 `oss.last.*`，直接跑 `./deploy.sh deploy <服务>` 即可。

## 注意事项

- 涉及生产配置文件的任何核对，一律走"结构化解析 + 布尔/长度判断"，不 `cat`/打印原始内容，
  即使是"确认某字段非空"这种看似无害的检查也不要直接打印值。
- 修改 `_note/` 下的 yaml 时优先用 ruamel.yaml（`preserve_quotes=True`）而不是 pyyaml 的
  `safe_load`+`safe_dump`，后者会丢注释、可能重排 key 顺序，产生不必要的大 diff（虽然
  `_note/` 不进 git，但一份人工维护的配置文件保留可读性仍有价值）。

## 可迁移范围

本项目所有"文档写的操作步骤"与"脚本实际实现"存在版本差的场景都适用第二条经验——README/
PRD 类文档容易在代码迭代后过时，涉及生产操作的步骤，**执行前应对照当前代码逻辑重新走一遍
再动手，不要盲信文档**，尤其是"首次执行会怎样"这类分支，往往没有被日常操作覆盖到，最容易
残留过时表述。
