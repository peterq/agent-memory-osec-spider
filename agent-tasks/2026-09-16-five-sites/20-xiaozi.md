# 站点：pan.xiaozi.cc（小子云盘）—— 短名 `xiaozi`，子命令 `bbs_xiaozi`

worktree：`/home/peterq/dev/projects/1s/spider-wt-site-xiaozi`（分支 `feat/site-xiaozi`）。样板：`services/bbs/feikuai.tv.go`（数字 id 枚举 + 水位线）+ `fuxipan.com.go`（sitemap 全量）。

## 报告已知（不要重测）

- 详情页 `https://pan.xiaozi.cc/resource/<数字ID>`，自增 id，观测范围 357131~393821；quark 为主。
- sitemap index `/sitemap.xml` → `/sitemap/1.xml`（5 条导航页）、`/sitemap/2.xml`、`/sitemap/3.xml`（各 30000 条）；近 7 天新增 3206 条（sitemap lastmod 是整批统一日期，不能做逐条水位线）。
- 免登录直出链接；25 条抽样有效率 100%；代理池 IP 未被拒（初筛的 5 s 断连是本地代理抖动）。
- V2EX 标注「需公众号」与实测不符——PRD 里记一句，爬虫按免登录做，但要在解析里检测「公众号/验证码」文案并计数告警。

## 策略要求

- 全量：sitemap 2/3 枚举 `/resource/<id>`，`FullSweepGate=true`，`Engine.Wait()` 限速。
- 增量：id 水位线——记录已见最大 id，增量从 `max+1` 向上探测，连续 N 个（缺省 50）空页/404 判到顶（像 feikuai 的空洞率处理）；先确认 id 之上的页面是 404 还是兜底页（报告未写，**这一条要实测并写进 PRD**）。
- 联网测试：sitemap 抽 15 条 + 水位线上探 10 个 id，断言链接类型分布、去重、二轮 0 提交。
