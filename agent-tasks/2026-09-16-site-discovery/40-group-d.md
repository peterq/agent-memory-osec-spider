# 分组 D —— 你要评估的站点

初筛（triage.py，经代理池，2026-09-16）已知信息写在括号里，别再重复做。

1. `https://www.fastsoso.cc/`（首页 200；sitemap 1058 条；首页无网盘链接；V2EX 汇总帖标注「免登录」。规模需另找证据，若 sitemap 即全量则规模不达标）
2. `https://www.haitunsou.com/`（首页 200；sitemap 581 条；首页无网盘链接；V2EX 标注「免登录」。同上，先核规模）
3. `https://panku8.com/`（首页 200 但耗时 23.6 s，**并发 ≤2、delay ≥1**；sitemap 600 条；首页无网盘链接；V2EX 标注「需登录」——重点验证第 5 条：不带 cookie 打开详情页能否直接看到网盘链接，若是登录/回复可见则直接「不满足：登录墙」并记录规模）

报告写到 `260916/fastsoso.cc.md`、`260916/haitunsou.com.md`、`260916/panku8.com.md`。
