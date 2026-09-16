# 站点：www.duanjuso.cc（短剧搜）—— 短名 `duanjuso`，子命令 `bbs_duanjuso`

worktree：`/home/peterq/dev/projects/1s/spider-wt-site-duanjuso`（分支 `feat/site-duanjuso`）。样板：`services/bbs/fuxipan.com.go`（sitemap 分级枚举 + SSR 详情页）。

## 报告已知（不要重测）

- React SPA 壳；**详情页 `/doc/<25 位 cuid>` 后端 SSR 直出**，每页 1 条链接（`<meta description>` 与正文都有）。首页/搜索页是空壳，**不要 BFS 首页**。
- 全量：`sitemap-index → disk-1.xml … disk-31.xml`（约 150 万条，`lastmod` 停在 2026-08-07，sitemap 生成已停滞，只能当存量清单）。
- **增量用公开接口** `POST https://www.duanjuso.cc/v1/search/disk`（同源、免登录、无签名），JSON 体：
  `{"q":"txt","page":1,"size":20,"share_time":"week","order":"time"}`；字段 `q, page, size, share_time(week|month), share_year, order(time), type, exact, user, format, size_filter`；`share_time=day` 报「索引错误」。
  响应 `data.total`（**封顶 10000**）、`data.list[]`：`doc_id, disk_type(QUARK/BAIDU/ALIYUN…), disk_name, disk_pass, shared_time("2026-09-11 15:40:17"), link(明文分享链接)`。
  ⇒ 增量**不需要抓详情页**，直接用响应里的 `link` + `disk_pass`；用多关键词（`txt`、`完结`、`第`、`集`、`mp4`、`高清`…）× `share_time=week` × `order=time` 翻页，按 `doc_id` 去重（`Engine.Seen`），水位线记最新 `shared_time`。
- `GET /v1/disk/hot` 免参数可用；`/v1/disk/latest` 返回「非法请求」（需前端票据，不要追）。
- 类型混合 quark/bnd/ali；33 条抽样有效率 85.7%。
- 吞吐：单 IP 直连 46 条/分钟、零 403/429；经代理成功请求每页出链，失败全是代理超时。首页经代理偶发 `RemoteDisconnected`，详情页/接口正常。

## 策略要求

- 全量：sitemap 31 个子文件 → `/doc/<cuid>` 详情页，`Engine.Wait()` 限速（`MinRequestInterval` 缺省 1s），`FullSweepGate=true`。抽样对账：随机 3 个子 sitemap 各取 20 条。
- 增量：搜索接口关键词轮询（关键词列表放配置节，给缺省值），`IncrementalInterval` 缺省 30 分钟。
- 联网测试：搜索接口 2 个关键词 × 1 页 + 详情页 10 条，断言 `total>0`、每条有 `link`、去重后二轮提交 0。
