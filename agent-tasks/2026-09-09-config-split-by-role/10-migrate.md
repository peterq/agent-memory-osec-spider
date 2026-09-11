# 10-migrate —— 配置按进程拆代码: 调用点迁移

## 背景（用户 2026-09-09 纠正的原则）

"配置按服务拆分"指**拆代码**不是拆文件：每个进程角色有自己的根配置结构体与 `Get()`，
section 类型共享、组合不共享；`config.Config` 全局变量与 `config.Get()` **已删除**；
配置文件保持一份。主控已完成 hub 部分（**不要改这些**）：

- `config/config.go`：只剩 section 类型 + `Common` + `ProxySubConfig` + 无状态助手
  `NewSpiderGwConn(addr, service)` / `NewResSchedulerRpcClient(addr, service)`。
- `config/internal/loader`：惰性加载，进程内只允许一种角色，第二种角色 `Get()` 直接 panic。
- `config/common`：`common.Get()`（公共段：Redises/AliLog/OSS/S3/StorageGateway/NodeName）、`common.Hostname()`。
- 角色包（各自 `Get()`）：

| 角色包 | 谁用 | 根结构体里有什么 |
|---|---|---|
| `config/gateway` | `./spider gateway`、`lifecycle_init_tables/indexes`、以及**网关进程内**的所有包（`services/gateway/{queue_admin,proxy_admin,lifecycle,auth,res_scheduler,doc_scheduler,download_scheduler 的 service 部分,...}`） | Common + `Services.{Gateway, Share, QueueAdmin, Lifecycle, Proxy(ProxySubConfig)}`。**没有 SpiderGateway** |
| `config/crawler` | bbs_* / keyword_* / v2*LoadShare / share/aliyun/quark/xunlei 客户端 / `services/spider-common` / `resource`(见下) | Common + `SpiderGateway` + `Services.{Proxy(完整), Share, Keyword, Kkpans, Dyyjmax, Feikuai, Fuxipan, Haisou, Kuakes, Misoso}`；`MustSpiderGwConn` / `MustNewResSchedulerRpcClient` |
| `config/proxyprov` | `services/proxy-provider`（**主控已迁移，勿动**） | Common + `Services.Proxy` |
| `config/lifecyclechecker` | `services/lifecycle_checker` | Common + SpiderGateway + `Services.{LifecycleChecker, Keyword{Redis}, Proxy(Sub)}`；`MustSpiderGwConn` |
| `config/doccrawler` | `services/doc_crawler` | Common + SpiderGateway + `Services.{DocCrawler, Proxy(Sub)}`；`MustSpiderGwConn` |
| `config/devops` | `services/devops/**`（clear_expire、migrate_legacy_queues） | Common + SpiderGateway + `Services.{Keyword, Share, Proxy(Sub)}`；`MustNewResSchedulerRpcClient` |
| `config/downloader` | `services/gateway/download_scheduler/{download_worker,resolve_worker,push_resolve,web_res,pan_download/**}` —— 它们是**网关的客户端进程**，虽然目录在 gateway 下 | Common + SpiderGateway + `Services.Proxy(Sub)`；`MustSpiderGwConn` |

- `spider.go` 已拆成 `spider.go` / `commands_gateway.go`(`//go:build !crawler_only`) / `commands_crawler.go`(`//go:build !gateway_only`)。
- `db.Redis` 已改读 `common.Get().Redises`；`gw_config.Get()` 已改为 `gateway.Get().Services.Gateway`，
  `gw_config.Hostname` 从变量改成了**函数** `gw_config.Hostname()`。
- `proxy_provider.OnProxy(cb)` 现在**只能在 proxyprov 角色进程里调**；其它进程一律改用
  `proxy_provider.OnProxyWith(sub config.ProxySubConfig, cb)`，`sub` 从**自己角色**的配置取：
  crawler → `crawler.Get().Services.Proxy.Sub()`；gateway → `gateway.Get().Services.Proxy`；
  downloader/devops/lifecyclechecker/doccrawler → `xxx.Get().Services.Proxy`。

## 你的任务

把全仓剩余的 `config.Config` / `config.Get()` / `config.Hostname` / `config.MustSpiderGwConn` /
`config.MustNewResSchedulerRpcClient` / `proxy_provider.OnProxy(` / `gw_config.Hostname`(当值用)
调用点迁移到对应角色包，直到：

```bash
cd /home/peterq/dev/projects/1s/osec-spider-go
go build ./...                                    # 必须过
bash scripts/check_config_isolation.sh            # 必须过: -tags gateway_only 与 -tags crawler_only 各编一次 main
go vet ./config/... ./services/gateway/... ./services/doc_crawler/... ./resource/... ./db/...   # 只看你改的包, 存量告警如实报告
go test ./config/... ./db/... ./services/gateway/queue_admin/... ./services/gateway/proxy_admin/... ./services/doc_crawler/... ./illuminate/proxy-client/... ./illuminate/proxy-monitor/...
```

### 逐文件角色表（主控 grep 得出，按此迁移；没列到的文件如果也报错，按所在进程判断角色并在汇报里列出）

| 文件 | 原读取 | 改为 |
|---|---|---|
| `resource/baidu.go` | `Config.StorageGateway` | `common.Get().StorageGateway` |
| `resource/magnet.go` | `Config.OSSConfig.*`, `Config.S3Config` | `common.Get().OSSConfig` / `.S3Config` |
| `illuminate/proxy-monitor/monitor.go` | 只有注释提到 `config.Config.Services.Proxy.Redis` | 改注释措辞即可（该包不许 import config） |
| `services/bbs/*.go`（6 个） | `Services.<站点>`, `Services.Keyword.Redis`, `proxy_provider.OnProxy` | `crawler.Get().Services.<站点>` / `.Keyword.Redis`；`OnProxyWith(crawler.Get().Services.Proxy.Sub(), cb)` |
| `services/haisou/haisou.cc.go` | `Services.Haisou`, `Services.Keyword.Redis`, `MustNewResSchedulerRpcClient`, `OnProxy` | `crawler.*` |
| `services/keyword/**`（aipanso/upyunso/upyunso-detail/funletu/nmme/xuebapan/pansearch.me） | `Services.Proxy.Redis`, `MustNewResSchedulerRpcClient`, `OnProxy` | `crawler.*` |
| `services/v2/res_crawler/{ali,quark,xl,bnd}/*.go` | `Services.Share.Redis`, `SpiderGateway`, `MustNewResSchedulerRpcClient`, `OnProxy` | `crawler.*` |
| `services/aliyun-drive`、`services/quark`、`services/xunlei-pan`、`services/share` 里的 `OnProxy` | | `OnProxyWith(crawler.Get().Services.Proxy.Sub(), cb)` |
| `services/spider-common/spider-common.go` | `MustNewResSchedulerRpcClient` | `crawler.MustNewResSchedulerRpcClient` |
| `services/spider-common/debug_proxy_server.go`、`services/spider_util/dev_utils.go` 里若有 `OnProxy` | | `crawler.*`（开发工具，按爬虫角色） |
| `services/gateway/gateway.go` | `config.Get().Services.Gateway.*`, `config.Get().Services.Share.Redis`, `config.Hostname`, `config.MarkCurrentProcessAsGateway()` | `gateway.Get().Services.*`（注意 `services/gateway` 包名也叫 gateway，import 要起别名如 `gwconf`）；`common.Hostname()`；**删掉** `MarkCurrentProcessAsGateway()` 调用及其注释（该函数已不存在，隔离由类型保证） |
| `services/gateway/auth/github.go` | `config.Get().Services.Gateway.GithubAuth` | `gwconf.Get().Services.Gateway.GithubAuth`（或经 `gw_config.Get().GithubAuth`） |
| `services/gateway/queue_admin/{register.go,config.go}` | `config.Config.Services.QueueAdmin`, `gw_config.Get()` | `gwconf.Get().Services.QueueAdmin`；`gw_config.Get()` 不变 |
| `services/gateway/proxy_admin/redis_resolve.go` | `config.Config.Services.Proxy.Redis` | `gwconf.Get().Services.Proxy.Redis` |
| `services/gateway/lifecycle/{register.go,init_tables.go}` | `Services.Lifecycle`, `config.Get().Services.Gateway.{EsAddr,Mysql}`, `gw_config.Hostname` | `gwconf.Get().Services.Lifecycle`；`gw_config.Get().EsAddr/Mysql`；`gw_config.Hostname()` |
| `services/gateway/doc_scheduler/doc_scheduler.go` | `gw_config.Hostname` 当值 | `gw_config.Hostname()` |
| `services/gateway/valid/valid_service.go`、`download_scheduler_service.go` 及 `download_scheduler` 里**网关进程内**的 `OnProxy`/硬编码频道 | | `OnProxyWith(gwconf.Get().Services.Proxy, cb)` |
| `services/gateway/download_scheduler/{download_worker/download_mgr.go, resolve_worker/resolve_mgr.go, push_resolve/push_resolve.go, web_res/*.go, pan_download/bnd_download/bnd_resolver/bnd_resolver.go}` | `SpiderGateway`, `AliLog.Ak/Sk`, `OnProxy` | `downloader.Get().SpiderGateway` / `downloader.MustSpiderGwConn`；`common.Get().AliLog`；`OnProxyWith(downloader.Get().Services.Proxy, cb)` |
| `services/devops/clear_expire/*.go`、`services/devops/2609/migrate_legacy_queues/*.go` | `Services.Keyword`, `Services.Share.Redis`, `SpiderGateway`, `MustNewResSchedulerRpcClient`, `OnProxy` | `devops.*` |
| `services/lifecycle_checker/checker.go` | `Services.LifecycleChecker`, `Services.Keyword.Redis`, `MustSpiderGwConn`, `OnProxy` | `lifecyclechecker.*` |
| `services/doc_crawler/doc_crawler.go` | `Services.DocCrawler`, `MustSpiderGwConn` | `doccrawler.*` |
| `services/gateway/stub_server.go` | `gw_config.Get()` | 不变 |

### 硬性规则

1. **一个进程只能出现一种角色的 `Get()`**。判断标准是"这段代码在哪个子命令进程里跑"，不是目录：
   `services/gateway/download_scheduler/download_worker` 是 `share_download_download` 进程 → downloader 角色。
   如果同一个包既被网关进程也被别的进程用（例如 `services/gateway/valid` 被网关与 `lifecycle_checker`、`clear_expire` 共用），
   **它自己不能读任何角色配置**，改成由调用方把需要的值（`ProxySubConfig`、redis 名、地址）传进去。
2. `common.Get()` 只给"被多个角色共用的库包"用（`db`、`resource`、日志…），业务代码直接读自己角色。
3. 不要新增任何全局变量来"缓存配置"，直接调 `xxx.Get()`（它本身就是热更新快照，开销可忽略）。
4. 不改 yaml 键、不改任何 section 结构体、不改 `config/` 下主控写的文件（发现问题写进汇报）。
5. `services/proxy-provider/change_proxy_config.go` 是 gitignore 的凭据文件，主控已改好，**不要碰、不要 cat**。
6. **不要 git commit**（主控统一提交）；不要 checkout/stash；不要碰 `scripts/`、`_note/`。
7. 存量 `go vet` 告警与需要真实中间件的测试失败如实报告，不要顺手改。
8. 主检出 `/home/peterq/dev/projects/1s/osec-spider-go` 上跑着生产守护脚本 `scripts/lc_adaptive_rps.sh`（PID 1664230），
   只改 Go 源码，其它一律不动。

## 交付

汇报：改动文件清单（按角色分组）；`go build ./...`、`scripts/check_config_isolation.sh`、上面 vet/test 命令的真实输出；
被迫改成"由调用方传值"的共用包清单及理由；任何你拿不准角色的文件。
