# 部署结果（2026-09-10）

## 总核对

```
== osec-res1
8c394a6f
spider-v2quarkLoadShare 2026-09-10 09:56:24 +0800 CST Up 42 seconds
spider-v2bndLoadShare 2026-09-10 09:55:43 +0800 CST Up About a minute
spider-v2bndInputPwd 2026-09-10 09:55:11 +0800 CST Up About a minute
spider-share_download_download 2026-09-10 09:51:19 +0800 CST Up 5 minutes
spider-webResDownloadUrl 2026-09-10 09:50:56 +0800 CST Up 6 minutes
spider-webResSearchEngine 2026-09-10 09:50:18 +0800 CST Up 6 minutes
spider-bbs_kkpans 2026-09-10 09:49:54 +0800 CST Up 7 minutes
spider-keyword_pansearch_me 2026-09-10 09:49:24 +0800 CST Up 7 minutes
spider-keyword_aipanso 2026-09-10 09:49:00 +0800 CST Up 8 minutes
spider-keyword_upyunso 2026-09-10 09:48:17 +0800 CST Up 8 minutes
spider-gateway 2026-09-09 11:53:23 +0800 CST Up 22 hours   # 未动, 符合硬性约束

== osec-res2
8c394a6f
spider-v2quarkLoadShare 2026-09-10 09:56:30 +0800 CST Up 37 seconds
spider-v2bndLoadShare 2026-09-10 09:55:49 +0800 CST Up About a minute
spider-v2bndInputPwd 2026-09-10 09:55:17 +0800 CST Up About a minute
spider-webResHeadUrl 2026-09-10 09:54:45 +0800 CST Up 2 minutes
spider-share_download_resolve_link 2026-09-10 09:54:10 +0800 CST Up 2 minutes
spider-bbs_feikuai 2026-09-10 09:53:45 +0800 CST Up 3 minutes
spider-keyword_xuebapan 2026-09-10 09:53:06 +0800 CST Up 4 minutes
spider-keyword_juzi 2026-09-10 09:52:41 +0800 CST Up 4 minutes
spider-keyword_funletu 2026-09-10 09:52:03 +0800 CST Up 5 minutes
spider-gateway 2026-09-09 12:04:18 +0800 CST Up 22 hours   # 未动, 符合硬性约束

== osec-resngix
8c394a6f
spider-devops_check_and_push_clear_queue 2026-09-10 09:46:42 +0800 CST Up 10 minutes
spider-v2xlLoadShare 2026-09-10 09:44:57 +0800 CST Up 12 minutes
spider-v2aliLoadShare 2026-09-10 09:38:47 +0800 CST Up 18 minutes
spider-bbs_misoso 2026-09-10 09:38:03 +0800 CST Up 19 minutes
spider-bbs_kuakes 2026-09-10 09:37:37 +0800 CST Up 19 minutes

== osec-restest
8c394a6f
spider-devops_check_and_push_clear_queue 2026-09-10 09:46:31 +0800 CST Up 10 minutes
spider-v2xlLoadShare 2026-09-10 09:44:49 +0800 CST Up 12 minutes
spider-v2aliLoadShare 2026-09-10 09:38:39 +0800 CST Up 18 minutes

== osec-jenkins
8c394a6f
spider-devops_check_and_push_clear_queue 2026-09-10 09:46:36 +0800 CST Up 10 minutes
spider-v2xlLoadShare 2026-09-10 09:45:01 +0800 CST Up 12 minutes
spider-lifecycle_checker 2026-09-10 09:37:05 +0800 CST Up 20 minutes
spider-devops_read_and_push_check_expire_queue 2026-09-10 09:36:44 +0800 CST Up 20 minutes
spider-bbs_dyyjmax 2026-09-10 09:34:03 +0800 CST Up 23 minutes
spider-bbs_fuxipan 2026-09-10 09:33:35 +0800 CST Up 23 minutes
spider-proxy 2026-09-10 09:30:06 +0800 CST Up 27 minutes   # 09-10 09:30 主控已部署核验过, 本轮未动
```

判据核对：除 `spider-gateway` 外，所有容器 CreatedAt 均在 2026-09-10 09:3x 以后；均为 `Up`，无 `Restarting`。`osec-resdb` 全程未触碰（`url_check` 用改过主机表的脚本副本部署，已确认排除）。

## 逐 service 结果

全部 20 个 service（osec-jenkins 4 个 + osec-resngix/restest 5 个 + osec-res1 7 个 + osec-res2 6 个，其中 xunlei/url_check/aliyun/v2bndInputPwd/v2bndLoadShare/quark 为多主机部署，按主机计入下表容器数）均部署成功，md5 全部为 `8c394a6f`，restarts=0，60 秒后日志无 panic/fatal error，无 `proxy_monitor` 相关日志（即代理监控初始化成功）。

| 批次 | service | cmd | 主机 | 结果 |
|---|---|---|---|---|
| 1 | fuxipan | bbs_fuxipan | osec-jenkins | 成功 09:33:35 |
| 1 | dyyjmax | bbs_dyyjmax | osec-jenkins | 成功 09:34:03 |
| 1 | url_commit_check | devops_read_and_push_check_expire_queue | osec-jenkins | 成功 09:36:44 |
| 1 | lifecycle_checker | lifecycle_checker | osec-jenkins | 成功 09:37:05 |
| 2 | kuakes | bbs_kuakes | osec-resngix | 成功 09:37:37 |
| 2 | misoso | bbs_misoso | osec-resngix | 成功 09:38:03 |
| 2 | aliyun | v2aliLoadShare | osec-restest, osec-resngix | 成功 09:38:39 / 09:38:47 |
| 2 | xunlei | v2xlLoadShare | osec-restest, osec-resngix, osec-jenkins | 成功（osec-restest 两次 ssh 超时后重试成功）09:44:49 / 09:44:57 / 09:45:01 |
| 2 | url_check | devops_check_and_push_clear_queue | osec-restest, osec-jenkins, osec-resngix（已排除 osec-resdb） | 成功 09:46:31 / 09:46:36 / 09:46:42 |
| 3 | upyunso | keyword_upyunso | osec-res1 | 成功 09:48:17 |
| 3 | aipanso | keyword_aipanso | osec-res1 | 成功 09:49:00 |
| 3 | pansearch_me | keyword_pansearch_me | osec-res1 | 成功 09:49:24 |
| 3 | kkpans | bbs_kkpans | osec-res1 | 成功 09:49:54 |
| 3 | web_res_search | webResSearchEngine | osec-res1 | 成功 09:50:18 |
| 3 | web_res_download_url | webResDownloadUrl | osec-res1 | 成功 09:50:56 |
| 3 | dl_download | share_download_download | osec-res1 | 成功 09:51:19 |
| 4 | funletu | keyword_funletu | osec-res2 | 成功 09:52:03 |
| 4 | juzi | keyword_juzi | osec-res2 | 成功 09:52:41 |
| 4 | xuebapan | keyword_xuebapan | osec-res2 | 成功 09:53:06 |
| 4 | feikuai | bbs_feikuai | osec-res2 | 成功 09:53:45 |
| 4 | dl_resolve | share_download_resolve_link | osec-res2 | 成功 09:54:10 |
| 4 | web_res_head | webResHeadUrl | osec-res2 | 成功 09:54:45 |
| 5 | v2bndInputPwd | v2bndInputPwd | osec-res1, osec-res2 | 成功 09:55:11 / 09:55:17 |
| 5 | v2bndLoadShare | v2bndLoadShare | osec-res1, osec-res2 | 成功 09:55:43 / 09:55:49 |
| 5 | quark | v2quarkLoadShare | osec-res1, osec-res2 | 成功 09:56:24 / 09:56:30 |

## proxy_monitor 未启用清单

无。全部容器日志中未出现 `proxy_monitor` 相关行（成功不打日志），也未出现「未启用」或 `flush pipeline exec error`。

## panic / exec error

无。所有容器 `grep -ci 'panic\|fatal error'` 均为 0。

## 过程中的异常与处理

1. **kuakes/aliyun/upyunso/funletu 等首次部署到某主机时二进制不一致**：deploy.sh 自动检测 md5 不同并 `scp -C` 更新，属预期行为（这些主机此前未同步过 09-09 网关重部时的二进制）。
2. **xunlei 部署时 osec-restest 两次 ssh 超时**：
   - 第一次超时发生在 `docker pull` 步骤中途，脚本在 `docker rm -f` 之后、`docker run` 之前退出，导致 `spider-v2xlLoadShare` 容器被删除但未重建（osec-restest 一度无该容器运行）。
   - 立即用 `ssh -o ConnectTimeout=10 osec-restest "echo ok"` 探测确认是瞬时网络抖动，非持续故障。
   - 重新执行 `./deploy.sh call deployService xunlei` 后第二次仍在同一步骤超时；第三次执行成功，三台主机全部部署完成并核验通过。
   - 未使用任何 `pkill`/`docker rm` 手工补救，重跑 `deployService` 命令本身具备幂等性（`docker rm -f` 对不存在的容器只报错不影响后续 `docker run`）。
3. **restest 内存**：部署 aliyun 后 `free -m` 显示 available 207MB，部署 url_check 后回升到 335MB，全程无 OOM，两次部署容器均 restarts=0。

## 需要主控决策的问题

无。20 个 service 全部按计划部署完成并核验通过，`osec-resdb`、`gateway` 均未触碰。
