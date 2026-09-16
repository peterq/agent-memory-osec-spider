# 分组 A —— 你要评估的站点

初筛（triage.py，经代理池，2026-09-16）已知信息写在括号里，别再重复做。

1. `https://squark.cc.cd/`（首页 200；sitemap 18726 条；首页无网盘链接、无登录墙文案；WebFetch 看到公告「只分享最近热门影视资源，每日更新，无需注册登录」，提及夸克网盘。重点：找详情页 URL 形态、链接是否 SSR 直出还是二次接口）
2. `https://www.duanjuso.cc/`（首页 200；sitemap 50000 条（可能是 sitemap index 汇总，需核实是否真实条目）；首页无网盘链接；V2EX 汇总帖标注「免登录」，名字像短剧搜索站。重点：是否有可枚举的详情页而不是纯搜索）
3. `https://hunhepan.com/`（首页 200 但耗时 19.6 s；sitemap 1925 条；首页有 1 条 quark 链接；V2EX 标注「免登录」；WebFetch 看到「搜索全网网盘、磁力资源」、页面异步加载。重点：规模是否能超 3000、磁力占比）
4. `https://dm.xueximeng.com/`（首页 200；sitemap 180 条；首页无网盘链接。规模疑似偏小，快速判定即可，若 sitemap 就是全量则直接「不满足：规模」）

报告写到 `260916/squark.cc.cd.md`、`260916/duanjuso.cc.md`、`260916/hunhepan.com.md`、`260916/xueximeng.com.md`。
