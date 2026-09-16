# 分组 B —— 你要评估的站点

初筛（triage.py，经代理池，2026-09-16）已知信息写在括号里，别再重复做。

1. `https://www.wnsearch.top/`（首页 200；sitemap 11647 条；首页无网盘链接、无登录墙文案；V2EX 汇总帖标注「免登录」）
2. `https://www.zlxapp.top/`（首页 200 但耗时 22 s，站点可能慢或脆弱，**并发 ≤2、delay ≥1**；sitemap 10001 条（10001 很像分页上限，需核实真实总量）；首页无网盘链接；V2EX 标注「免登录」）
3. `https://dapanso.com/`（首页 200，耗时 11.8 s；**首页直出 17 条网盘链接：quark 15、xunleipan 1、bnd 1**；sitemap 仅 22 条，规模需另找证据（分页末页/最大 id/接口 total）；V2EX 标注「免登录」）
4. `https://jsnoteclub.com/`（首页 200；sitemap 190 条；首页无网盘链接。规模疑似偏小，快速判定即可）

报告写到 `260916/wnsearch.top.md`、`260916/zlxapp.top.md`、`260916/dapanso.com.md`、`260916/jsnoteclub.com.md`。
