---
title: 失败经验：osec-resdb 的 ES 端点指向已下线集群，fail-fast 才把哑故障暴露出来
type: lesson
status: active
created_at: 2026-09-05T12:20:00+08:00
updated_at: 2026-09-18T10:50:00+08:00
priority: high
keywords:
  - osec-resdb
  - es_endpoint
  - ES 集群更换
  - fail-fast
  - save-worker
  - 哑故障
  - 部署前置检查
summary: STORAGE worker 所在 osec-resdb 的 ES 地址指向已下线集群，旧代码静默失败；排查与修法见正文
load: rarely
related:
  - agent-memory/lessons/failure-网关重启暴露ES集群已更换.md
  - agent-memory/procedures/workflow-部署.md
  - agent-memory/sessions/2026/2026-09-05-生命周期P3上线.md
---

# 失败经验：osec-resdb 的 ES 端点指向已下线集群

## 问题背景

2026-09-05 P3 上线，要把带 `services.storage.lifecycle`（`enabled: true`）的 STORAGE 新二进制
部署到 osec-resdb 的 `worker`。计划里 worker 是**第一台**。

## 失败方法

直接按 `deploy.sh` 的流程 `mv storage storage.old` → `docker rm -f` → `docker run`。

## 失败表现

容器启动 5 秒后：

```
level=error msg="fail to connect to elastic search health check timeout: Head
  \"http://elastic:***@es-cn-nwy39…:9200\": dial tcp: lookup es-cn-nwy39… on 100.100.2.138:53: no such host"
level=fatal msg="生命周期新链路已启用, 但 ES 客户端初始化失败(检查 aliservice/awsservice 开关)"
  func="[enfi-resource-storage/services/lifecycle/wire.build:51]"
```

`--restart always` → 重启循环，服务实际不可用。

## 根本原因

- osec-resdb 的 `/home/pplabs/enfi-resource-storage/config.yaml` 里
  `services.storage.es_endpoint` 指向 **`es-cn-nwy39sbcx000a7gww`（已下线的旧集群，域名连 DNS 记录都没了）**；
  osec-res1 / osec-res2 指向现网的 `es-cn-vcg4txxrn00021s9s`（HTTP 200）。**同一服务不同机器配置不一致。**
- **旧代码是哑故障**：`db.Elastic()` 连不上只打 `level=error` 就返回 nil，
  `save-worker` 拿着 nil 客户端继续跑，每批数据都在 `elastic.Client.PerformRequest` 上 nil 指针 panic，
  被 `queue-task` 的 recover 兜住 → 队列消费"看起来正常"。该机 `worker.log` 已 **3.7 GB**，
  尾部 1 MB 里旧集群域名出现 358 次，说明**坏了很久没人发现**。
- 新代码的 `lcwire.build()` 对 `es == nil` 做 `logrus.Fatal`，**把哑故障变成显式故障**——设计正确，
  但踩在了一台配置早就坏了的机器上。

## 规避方法

1. **部署任何带 fail-fast 的版本前，逐台验证配置里的外部依赖**，不要因为"同一个服务"就假设各机配置一致：

   ```bash
   ssh <host> 'url=$(grep -m1 "es_endpoint:" /home/pplabs/enfi-resource-storage/config.yaml \
       | sed -E "s#.*\"(http[^\"]*)\".*#\1#"); url=${url%/}
     host=$(echo "$url" | sed -E "s#.*@([^:/]*).*#\1#")
     getent hosts "$host" >/dev/null && echo "DNS OK" || echo "DNS FAIL"
     curl -s -m 8 -o /dev/null -w "%{http_code}\n" "${url%/}/_cluster/health"'
   ```

   凭据只落 shell 变量，不回显。用 `printf %s "$url" | md5sum` 对比各机端点是否同一个。
2. **先部署风险最低、最容易回滚的那台**，不要把"第一台"定在最不熟悉的机器上。
3. 回滚三件套要在动手前就备好：`storage.old`（现役二进制）、`config.yaml.bak.<日期>`、原容器的 `docker inspect` 参数。

## 下次行动建议

- 本次回滚耗时 46 秒（`docker rm -f` → `mv storage.old storage` → `cat 备份 > config.yaml` → 重跑 `dockerRun`），
  照抄即可。新二进制/新配置**别删**，留成 `storage.lc` / `config.yaml.lc`，端点修好后直接换回，省一次传输。
- **哑故障排查法**：怀疑某台机器的某条链路早就坏了，先看它的日志文件大小和
  `tail -c 1M <log> | grep -c <可疑域名>`——长期刷同一条错误的巨大日志文件是最明显的信号。

## 适用边界

- 只适用于"宿主机本地 config.yaml、不由脚本分发"的服务（STORAGE / API / 爬虫的 `config.yaml`）。
  走 OSS 分发的网关配置是单份的，不存在各机不一致的问题（但仍可能整体指向已下线集群，
  见 `failure-网关重启暴露ES集群已更换.md`）。
