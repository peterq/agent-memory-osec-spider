# 站点：ddys.io（低端影视）—— 短名 `ddys`，子命令 `bbs_ddys`

worktree：`/home/peterq/dev/projects/1s/spider-wt-site-ddys`（分支 `feat/site-ddys`）。样板：`services/bbs/fuxipan.com.go`（sitemap 枚举 + 详情页）。

## 报告已知（不要重测）

- **已确认反爬**：非代理出口访问 403（UA/地区判定）；代理池访问正常但连接常被重置，需退避重试（`RemoteDisconnected`/超时按限流处理，指数退避，最多 4 次）。**任何情况下不得直连。**
- `robots.txt`：`Disallow: /go/ /search /api/ /activities /year/19*/`；sitemap 顶层 → `sitemap-static.xml`、`sitemap-movies-1.xml`、`sitemap-movies-2.xml`、`sitemap-community.xml`；详情页 `/movie/<slug>`，共 7237 条（实测）。
- **链接不是明文**：正文里 `onclick="trackAndOpenResource(id, 'view', atob('<base64>'), '')"`，真实分享链接在 base64 载荷里。Go 侧要先把所有 `atob('...')` 载荷 base64 解码再跑 `spider_contract` 正则（COMMON `site-discovery/tools/panlink.py` 的 `_decode_atob_payloads` 是 Python 参考实现）。
- 类型：quark 100% 页面含、bnd 79%、xunleipan 43%，无 ali；31 条抽样有效率 93.55%。每页通常 2 条链接。
- 吞吐：经代理串行 delay 1.5 s，成功段 13.6 条/分钟，零 403/429；失败全是代理侧。
- 调研工具的 `login_wall:true` 是文案误命中（页面有「登录」导航），不是真登录墙。

## 策略要求

- 全量：两个 movies sitemap → `/movie/<slug>`，串行或并发 ≤2，`MinRequestInterval` 缺省 1.5 s，`FullSweepGate=true`。
- 增量：sitemap `lastmod` 水位线（报告未验证可信度，实测并写进 PRD）；不可信则每轮重扫 `sitemap-movies-2.xml` 尾部 N 条。
- 联网测试：抽 12 个 `/movie/` 页，断言 atob 解码后 ≥1 条链接/页（允许 ≤30% 请求因代理失败）、类型分布、去重、二轮 0 提交。
