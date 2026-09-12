# 角色 10：SPIDER —— `tools/lc-recrawl` 限速投递工具

## 必读
1. `services/spider-common/spider-common.go` L28-110 —— `ResLink{Url,Pwd,Client,Refer}`、`NewResLinkCommitter()`、`CommitResLink()`（内部按需建网关连接；调用方标识取 `os.Args[1]`，注意 `go run ./tools/xxx` 时 `os.Args[1]` 是第一个 flag，看它怎么取、需不需要显式 `SetClientName`）。
2. `services/spider-common/spider_contract/spider_contract.go` —— `ShareLinkFromId(type, id)`（type 常量 `bnd`/`ali-share`/`quark`/`xunleipan`）。
3. `services/gateway/res_scheduler/pre_check.go` —— 预检消费者：`resDealAt:<typ>:<id>:<pwd>` 6 h 去重、下游 waiting≥2000 背压。理解这两点决定限速策略。
4. `tools/lc-check/main.go` —— `-trigger-check` 的读文件/去重/分批/dry-run/进度打印形态，**照它写**。
5. `services/devops/clear_expire/push_to_clear_form_json_log.go` —— devops 进程里怎么拿配置与网关连接（若 committer 需要配置）。
6. 网关连接地址：本机经 `ssh -f -N -L 18082:127.0.0.1:8082 osec-res2` 隧道；工具要有 `-addr` 或等价方式指定网关（看 committer 是从配置读还是可注入，不能改生产配置）。

## 交付 (1)：`tools/lc-recrawl/main.go`
- 输入：`-file <tsv>`，每行 `type<TAB>share_id<TAB>pwd`（pwd 可空；`#` 开头/空行忽略；去重保序）。这个 TSV 由主控用 `scripts/lc_false_invalid_export.sh` 产出，你不用管导出。
- `-rate <n/s>`（缺省 5）、`-limit <N>`（本次最多投递 N 条，缺省 0=不限）、`-offset <N>`/`-state <file>`（断点：每投递 1,000 条把已投递行号写进 state 文件，重跑自动续）、`-client <name>`（缺省 `lc-recrawl-2609`，进 `ResLink.Client`，便于 ES 里按 client 找回本批）、`-dry-run`（只打印将投递的条数/类型分布/前 5 条，不连网关）。
- 每条：`CommitResLink(&ResLink{Url: ShareLinkFromId(type, shareId), Pwd: pwd, Client: client})`；`resource.ErrDupTask`（已在预检队列）计 dup 不算失败；其他错误重试 3 次仍失败则写到 `<state>.failed`（原行）继续。
- 每 1,000 条打印一行进度：`pushed/dup/failed/elapsed/当前速率`；结束打印汇总。SIGINT 优雅退出并落 state。
- 顶部用法注释（中文）含隧道命令与示例。

## 交付 (2)：文档
`services/gateway/lifecycle/README.md` 末尾加「误删资源重爬（2026-09-12 事故恢复）」小节：TSV 来源、命令示例、节奏建议（quark 走代理池 `quark` 场景，额外 ≤3 万/h ≈ 10/s；ali `v2aliLoadShare` 20 并发很慢）、怎么核对恢复进度（`res_lc_event` `created`/`updated` 事件里 operator/detail 含 client 名？——看 `rpc_service.go` 上报是否记录 client；不记录就用 ES `resource` 按 `client` term 计数）、真失效的会怎样。

## 单测
- 解析 TSV（去重、跳过注释/空行、pwd 为空）与 `ShareLinkFromId` 组 url 的纯函数用例。
- 限速器/断点用纯函数或小接口测，不联网。

## dry-run 验证
造一个 5 行样例 TSV（假 share_id）跑 `-dry-run`，贴输出。**不要**去掉 dry-run 连网关。
