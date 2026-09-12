---
title: 本地构建与验证流程
type: procedure
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords: [构建, go build, replace, 编译失败, 验证, protoc, go vet, 存量告警, module名, 验收口径]
summary: 四个仓库当前的可编译状态、编译命令、已知失败原因，以及编译/go vet 的验收口径，改代码前必读
questions:
  - 编译不过，依赖报错怎么排查
  - go mod tidy / replace 问题怎么处理
load: on-demand
related:
  - agent-memory/03-project-context.md
  - agent-memory/current/risks.md
---

# 本地构建与验证流程

## 结论速查（2026-09-02 收尾后实测）

**COMMON / SPIDER / API / STORAGE 四个仓库 `go build ./...` 全部通过。**

改动前的失败原因（已修复，留档备查）：module 名仍是 `PPIO/...` 而源码 import 已是 `1s/...`；
API、STORAGE 的 `replace` 指向不存在的 `../../pplabs/enfi-resource-common`；
SPIDER 有 2 个包存在存量编译错误。

## 编译命令

不要用 `cd`（复合命令里的 `cd` 在 Agent 会话中不稳定），统一用 `-C`：

```bash
go build -C /home/peterq/dev/projects/1s/osec-spider-go ./...
go build -C /home/peterq/dev/projects/1s/enfi-resource-common ./...
go build -C /home/peterq/dev/projects/1s/osec-resource-api ./...
go build -C /home/peterq/dev/projects/1s/enfi-resource-storage ./...
```

SPIDER 全量编译约 1～2 分钟，建议放后台或给足 timeout。

## 验收口径：编译与存量告警

- **判断"能不能编译"必须逐仓库实测**。Go 的目录型 `replace`（`=> ../xxx`）**不校验被替换模块自己声明的 module 名**，
  所以"下游仓库能编译"不能证明上游仓库的 `go.mod` module 声明是对的——`PPIO → 1s` 重命名时就是靠这一点才发现
  COMMON 的 module 名还是旧的。每个仓库都要单独跑一次 `go build ./...`。
- **SPIDER 有大量存量的 `go vet` 告警与测试失败**（`services/alipan`、`services/quark`、`services/gateway/*`、
  `services/devops/*` 等包）。验收新代码时**只看新增/改动的包**，存量问题如实报告但**不要顺手改**——
  顺手改会把无关改动混进本次提交，也超出验收范围。

## `PPIO → 1s` 重命名收尾做了什么（2026-09-02 已完成）

顺序很重要：**先 COMMON，再下游**，每改一个仓库立刻 `go build ./...` 验证。

1. COMMON：只改 `go.mod` 第 1 行 module 名 → `github.com/1s/enfi-resource-common`。源码 import 早已就位，改完即自洽。
2. API：module → `github.com/1s/enfi-resource-api`；`require` 与 `replace` 里的
   `PPIO/enfi-resource-common`、`PPIO/enfi-spider-go` 改为 `1s/*`，并把两条写死的绝对路径改为
   `../enfi-resource-common`、`../osec-spider-go`；失效的 `PPIO/pan-client-core` replace 改为
   实际用到的 `github.com/1second/pan-client-core => ../pan-client-core`。最后 `go mod edit -fmt` 整理 require 排序。
3. STORAGE：同样改 require+replace，然后**必须跑 `go mod tidy`**（只改 replace 会报 `updates to go.mod needed`）。
   tidy 的副作用：`go 1.22.0` → `go 1.23`，并顺带升了 aws-sdk-go(1.25→1.40)、logrus(1.6→1.8.1)、
   go-sql-driver/mysql、easyjson 等版本，`go.sum` 被大幅裁剪。原因是它现在真的依赖本地的 SPIDER 模块了。
   **STORAGE 上线前建议做一次运行时回归**，这几个库的升级不是纯粹的 no-op。
4. STORAGE 的 module 名保持 `enfi-resource-storage`（无域名前缀），源码 import 也是这个前缀，不在本次重命名范围内。

## 重新生成 protobuf

```bash
cd /home/peterq/dev/projects/1s/enfi-resource-common
make spider    # 注意：Makefile 里的 rpc/spider/rpc.proto 与实际 spider-gw.proto 不符，先核对
make storage
```
`gateway_v2` / `res_scheduler` / `doc_scheduler` / `download_scheduler` / `spider_task` 未纳入 Makefile，需手工 protoc。
生成后务必跑 `cmd/proto/replace-json.go` 修正 json tag，否则 ES 字段名会错。

## 测试

各仓库有零散 `*_test.go`（如 `rpc/storage/types_test.go`、SPIDER `services/gateway/**_test.go`、
API `test/`）。部分是连生产环境的（`spider_dao_prod_test.go`），**不要无差别跑 `go test ./...`**。
