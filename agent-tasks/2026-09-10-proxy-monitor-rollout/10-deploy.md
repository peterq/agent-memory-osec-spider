# 角色：部署执行

按下列顺序逐个执行 `./deploy.sh call deployService <service>`，每个做完按 00-shared.md 核验清单核验后再下一个。
service 名 → 容器名(cmd) → 主机：

## 批次 1：osec-jenkins
| service | cmd | hosts |
|---|---|---|
| fuxipan | bbs_fuxipan | osec-jenkins |
| dyyjmax | bbs_dyyjmax | osec-jenkins |
| url_commit_check | devops_read_and_push_check_expire_queue | osec-jenkins |
| lifecycle_checker | lifecycle_checker | osec-jenkins |

## 批次 2：osec-resngix / osec-restest（restest 内存只剩 ~300MB，部完看 `free -m`）
| service | cmd | hosts |
|---|---|---|
| kuakes | bbs_kuakes | osec-resngix |
| misoso | bbs_misoso | osec-resngix |
| aliyun | v2aliLoadShare | osec-restest osec-resngix |
| xunlei | v2xlLoadShare | osec-restest osec-resngix osec-jenkins |
| url_check | devops_check_and_push_clear_queue | **只部 osec-restest osec-jenkins osec-resngix，排除 osec-resdb** |

`url_check` 的主机表里含 osec-resdb，必须用改过主机表的脚本副本执行（仍在仓库根目录运行）：
```bash
cd /home/peterq/dev/projects/1s/osec-spider-go
S=/tmp/claude-1000/-home-peterq-dev-projects-1s-enfi-resource-common/62448de8-68f9-458a-b93f-13d63e157ca9/scratchpad/deploy_urlcheck.sh
sed 's/serviceToHosts\["url_check"\]="osec-resdb /serviceToHosts["url_check"]="/' deploy.sh > $S
grep -n 'serviceToHosts\["url_check"\]' $S   # 确认不含 osec-resdb 再执行
bash $S call deployService url_check 2>&1 | sed -E 's/(ak|sk|password|pwd)=[^&" ]*/\1=***/gi; s#//[^@/ ]*@#//***@#g'
```

## 批次 3：osec-res1
| service | cmd |
|---|---|
| upyunso | keyword_upyunso |
| aipanso | keyword_aipanso |
| pansearch_me | keyword_pansearch_me |
| kkpans | bbs_kkpans |
| web_res_search | webResSearchEngine |
| web_res_download_url | webResDownloadUrl |
| dl_download | share_download_download |

## 批次 4：osec-res2
| service | cmd |
|---|---|
| funletu | keyword_funletu |
| juzi | keyword_juzi |
| xuebapan | keyword_xuebapan |
| feikuai | bbs_feikuai |
| dl_resolve | share_download_resolve_link |
| web_res_head | webResHeadUrl |

## 批次 5：res1 + res2 双机（队列 v2 消费者，一个 service 两台会先后重启，属预期）
| service | cmd |
|---|---|
| v2bndInputPwd | v2bndInputPwd |
| v2bndLoadShare | v2bndLoadShare |
| quark | v2quarkLoadShare |

## 收尾
全部完成后跑一次总核对并把结果写进本目录 `20-result.md`：
```bash
for h in osec-res1 osec-res2 osec-resngix osec-restest osec-jenkins; do echo "== $h"; ssh $h "md5sum /home/pplabs/enfi-spider-go/spider | cut -c1-8; sudo docker ps --format '{{.Names}} {{.CreatedAt}} {{.Status}}' | grep ^spider-"; done
```
判据：除 `spider-gateway` 外，上表所有容器 CreatedAt 都是 2026-09-10 09:3x 以后；无 Restarting。

## 交付
汇报只要：每个 service 的结果一行（成功/异常 + Created 时间）、出现过「proxy_monitor 未启用」的容器清单、
任何 panic/exec error、以及需要主控决策的问题。不要贴大段部署输出。
