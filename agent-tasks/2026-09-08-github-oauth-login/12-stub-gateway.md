# 追加任务：本地联调用的桩网关（SPIDER）

## 为什么要它

GitHub 登录这条链路目前只做了单测和"绕开网关的 GitHub 侧联调"，**没有在真实浏览器里跑通过一次**
（前端 → RTC 握手 → 网关换票 → 会话票据 → 顶栏显示用户）。真网关要 redis/mysql/ES 才能起，
本地不具备。所以做一个只保留"RTC 握手 + 最小 SpiderRpc"的桩网关：
既是本次改造的验收手段，也是以后前端改登录/连接相关代码时的常备工具。

## 落点与实现要点

1. 新文件 `services/gateway/stub_server.go`（**必须在 `package gateway` 内**，这样才能复用
   未导出的真实握手实现 `(*service).rtcHandshake` —— 桩必须调真代码，不许复制一份握手逻辑）：
   - 导出 `func StartStub()`：
     - 构造 `gwService := &service{log: logger.Logger("spider-gateway-stub")}`
       （**不要**调 `service.init()`，它要连 redis）；
     - `rtcServer := grpc_proxy.NewRtcServiceProxy(gwService.rtcHandshake, <一个只打日志的 logRtcUnaryCall 替代品>)`
       —— 注意真实的 `s.logRtcUnaryCall` 用了 `s.log` 之外还接了阿里云日志，桩里不要 `initAliLog()`，
       自己写个简单的本地 log 函数即可；
     - `spider.RegisterSpiderRpcServer(rtcServer, gwService)`（前端初始化只用到 `Pong` /
       `GetDefaultClientName` / `SetClientName`，其余方法会因缺 redis 而 panic，这是预期内的，
       在函数注释里写清楚"桩只保证握手与连通性相关的少数方法可用"）；
     - `pc.NewServer(gw_config.Get().RtcListenPort, rtcServer.HandleConn)` 起 RTC 监听，
       然后阻塞住（`select {}`）；
     - 启动时打印：监听端口、`github_auth` 的 client_id（非机密，方便核对是不是 dev App）、
       org、allow_rtc_token，**不要打印任何 secret**。
2. 新文件 `tools/stubgw/main.go`：`package main`，只调 `gateway.StartStub()`；
   文件头注释写清用法：
   ```bash
   LOCAL_CONFIG_PATH=/绝对路径/stub.yaml go run ./tools/stubgw
   ```
   并说明它连 7542 端口、前端把网关切到"本地环境"即可。
3. 在 `PRD/config-v2/` 下加一个 `config.stub-gateway.example.yaml`：桩网关能跑起来的**最小**配置
   （`services.gateway` 的 `rtc_listen_port: 7542` + `github_auth` 四项，client_id 写 dev App 的
   `Ov23lih8tSerxYwqexP5`，secret 全写占位符），顶上注释说明"这是本地前端联调用的最小配置，
   不含任何真实凭据，真 secret 从 `_note/` 或运维处取，填进本机副本里、不要提交"。
4. 在 `PRD/config-v2/README.md`（如果有）或 `tools/stubgw/main.go` 注释里补一段说明，
   让后来的人搜得到这个工具。

## 验证

```bash
cd /home/peterq/dev/projects/1s/osec-spider-go
go build ./... && go vet ./services/gateway ./tools/stubgw
```
**不要**真的用带 secret 的配置去跑它（跑起来由主控做，主控手上有 dev App 的 secret）。

## 禁止

不要 commit / push；不要改本次已完成的握手逻辑（除非是修复第 5 节的返工要求）；
不要在任何提交进 git 的文件里写真实 client_secret / session_secret。
