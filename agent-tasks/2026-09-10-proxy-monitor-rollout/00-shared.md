# 2026-09-10 代理池监控上线：爬虫容器分批重部

## 背景
- 后台「代理池总览」全 0：读取侧（网关 `proxy_admin`，09-09 已重部）正常，上报侧未部署。
- 上报侧 = 爬虫进程里的 `illuminate/proxy-monitor`（09-09 `883daeb` 进 master）。所有爬虫容器都创建于 09-08 13:00~15:50，跑的是旧二进制。
- 主控已于 09-10 09:30 用 `./deploy.sh deploy proxy` 完成 `proxy` 服务（osec-jenkins）重部并核验通过：
  本地已构建好的二进制 `osec-spider-go/spider` md5 前 8 位 `8c394a6f`（master `fefbf10`，与线上网关 `883daeb` 仅差一个巡检脚本）。
  **不要重新构建**，直接复用这个二进制。
- OSS 统一配置与本地一致，`uploadConfigToOss` 会打印 `config unchanged, skip`，这是预期。

## 仓库与工具
- SPIDER 仓库：`/home/peterq/dev/projects/1s/osec-spider-go`（在此目录执行 deploy.sh，脚本用相对路径）。
- 部署脚本用法见 `agent-memory/procedures/workflow-部署.md`（COMMON 仓库）。本次用法：
  ```bash
  cd /home/peterq/dev/projects/1s/osec-spider-go
  ./deploy.sh call deployService <service> 2>&1 | sed -E 's/(ak|sk|password|pwd)=[^&" ]*/\1=***/gi; s#//[^@/ ]*@#//***@#g'
  ```
  `call deployService` 跳过构建，直接：比对 OSS 配置 → 各主机 md5 不同才 scp（`-C`）→ `docker rm -f` + `docker run`，末尾打印新容器 `Created` 时间。
- **输出必须经上面的 sed 打码**（`set -x` 会把 OSS ak/sk 打进 trace）。凭据不得出现在汇报里。

## 硬性约束
- **不要动 `gateway`**（P4 bootstrap 正在跑，网关不可重启）；不要动 `osec-resdb` 上任何容器（跑的是 2024/2025 年老二进制，命令已不存在，重部即起不来）。
- 一次只部一个 service，部完核验再下一个。核验清单（每台主机）：
  1. `sudo docker inspect -f '{{.Created}} {{.State.Status}} restarts={{.RestartCount}}' spider-<cmd>` —— Created 必须是今天 UTC 01:xx 之后，restarts=0。
  2. 等 60 秒后 `sudo docker logs spider-<cmd> 2>&1 | grep -ci 'panic\|fatal error'` 必须为 0。
  3. `sudo docker logs spider-<cmd> 2>&1 | grep -i 'proxy_monitor' | head -3`：
     - 无输出 = 初始化成功（成功不打日志，只有出错才打）；
     - 出现「proxy_monitor 未启用」= 该角色配置拿不到 `services.proxy.redis`，**记录下来继续**，不要改代码；
     - 出现 `flush pipeline exec error` = redis 写入失败，停下汇报。
  4. `md5sum /home/pplabs/enfi-spider-go/spider | cut -c1-8` 应为 `8c394a6f`。
- `dockerRun` 的 `docker rm -f` 曾两次静默失败（容器名冲突、旧容器继续跑）：**Created 时间没变就是没换**，手工 `sudo docker rm -f spider-<cmd>` 后 `bash /tmp/run.sh` 补救（run.sh 已在机上）。
- ssh 偶发 `Connection timed out`：核验命令重试 2 次再判失败。
- 禁止 `pkill -f`/`pgrep` 组合杀进程（会杀掉自己的 shell）。
- 不要转派给其他 Agent，自己做完。
