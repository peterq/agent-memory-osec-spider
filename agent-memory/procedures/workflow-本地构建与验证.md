---
title: 本地构建与验证流程
type: procedure
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-16T14:30:00+08:00
priority: high
keywords: [CI, go build, launch.json, go vet, live标签, make proto, replace, 编译失败, 验证, 存量告警, 验收口径]
summary: 四仓库编译命令、VSCode 本地启动(launch.json)、CI(vet/test 白名单 + live 标签隔离连生产测试)、make proto 生成流程与验收口径
questions:
  - 编译不过，依赖报错怎么排查
  - CI 怎么跑，哪些测试会连生产
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

### VSCode 本地启动（launch.json，已入库）[事实 2026-09-16]

- SPIDER：`osec-spider-go/.vscode/launch.json`，每个子命令一条 configuration，env 用 `LOCAL_CONFIG_PATH` 指向 `config.local.yaml`。
- API：`osec-resource-api/.vscode/launch.json`（2026-09-16 新增），`api-starter` 一条启动服务、`tools search-regression` 一条跑搜索回归；不设环境变量，靠 `initConfig` 的查找顺序 `CONFIG_FILE → ./config_dev.yaml(已 gitignore) → ./config.yaml`。
- 多根工作区 `1s/resource-backend.code-workspace` 会汇总各文件夹的 launch.json，Run 面板按「配置名 (文件夹名)」区分。

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

## 重新生成 protobuf（2026-09-16 已修复，`make proto` 一条命令）

```bash
cd /home/peterq/dev/projects/1s/enfi-resource-common
make proto   # 依次跑 rpc/{common_message,storage,spider}/gen.sh, 覆盖全部 proto(含 spider 全部子目录)
```
旧的 `make spider`/`make storage` 目标路径对不上（引用不存在的 `rpc/spider/rpc.proto`）、用的还是
老式 `protoc-gen-go plugins=grpc` 语法（现代 protoc-gen-go 已不支持），已删除。修复时发现
`common_message.pb.go`、`rpc/storage/rpc.pb.go` 里内嵌的 proto 描述符字节仍是重命名前的
`PPIO/enfi-resource-common` 路径（`.proto` 源码里的 `go_package` 早改了，但这两个生成物一直没
跟着重新生成），已随 `make proto` 一并修正。依赖 `protoc`(建议 3.21.x) + `protoc-gen-go` v1.34.2 +
`protoc-gen-go-grpc` v1.3.0，版本要求见各 `rpc/<dir>/gen.sh` 头部注释。

## CI（2026-09-16 新增，提案 8）

四仓库都有 `.github/workflows/ci.yml` + 本地同款 `scripts/ci.sh`（`go build` + `go vet` + `go test`）。
`go vet`/`go test` 用「排除法白名单」：`scripts/vet-denylist.txt`、`scripts/test-denylist.txt` 分别
记录存量告警包、依赖本地基础设施(redis/mysql/桩服务)的存量失败包，新增包默认就要求无告警/能跑。

**发现的隐藏依赖**：SPIDER/API 的 `go.mod` 除了 `replace => ../enfi-resource-common`，还有
`replace github.com/1second/pan/common => ../pan/common`、
`replace github.com/1second/pan-client-core => ../pan-client-core`（都是私有仓库 `1second/pan`、
`1second/pan-client-core`），API 还多一个 `replace github.com/1s/enfi-spider-go => ../osec-spider-go`。
CI 里要把这些兄弟仓库也 checkout 到同级目录，对应 secret：`COMMON_REPO_TOKEN`、`PAN_REPO_TOKEN`、
`PAN_CLIENT_CORE_REPO_TOKEN`、`SPIDER_REPO_TOKEN`（同一个有权限的 token 可以复用）。COMMON 自己
的 `go.mod` 对 `github.com/1second/pan/common` 是普通版本化 require（无本地 replace），CI 里需要
`git config url insteadOf` + `GOPRIVATE` 让 `go mod download` 能带 token 拉私有模块。
SPIDER `go.mod` 另有两行指向本机绝对路径 `/home/peterq/.../fancy-go/...` 的死 replace（`go mod why`
确认无代码引用），不影响 CI，属于遗留脏数据未清理。

**测试隔离**：会连生产 ES/DB/网关或联网打第三方接口（百度网盘校验、bing 搜索代理、真实论坛抓取、
硬编码生产网关 IP、硬编码 AK/SK 调用生产 FC）的 `_test.go`，第一行统一加 `//go:build live`，默认
`go test` 不带该 tag。已知模式：`ConnectProdSpiderGw`/`UseProdSpiderGw`/`UseProdDb`（当天日期口令）、
`InitProdEs`、`PROD_DB` 环境变量、`_live_test.go`/`_prod_test.go` 文件名、`*_IT=1` 环境变量门控、
文件里出现真实第三方域名或硬编码云凭据——**光靠 grep 关键词会漏**（例如测试只调用业务方法、
真正的网络请求在被测代码里），最终以`go test ./...` 实测「有没有连接失败/耗时异常长」为准。

## 测试

各仓库有零散 `*_test.go`。会连生产/外网的已按上面的约定加 `//go:build live`，`go test ./...`
默认不会触发；仍有一部分是"本地基础设施缺失"导致的存量失败（非连生产），记录在各仓库
`scripts/test-denylist.txt`，跑 `bash scripts/ci.sh` 即可看到完整、可复现的结果。
