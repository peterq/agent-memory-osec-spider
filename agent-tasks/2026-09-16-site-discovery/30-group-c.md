# 分组 C —— 你要评估的站点

初筛（triage.py，经代理池，2026-09-16）已知信息写在括号里，别再重复做。

1. `https://www.qileso.com/`（首页 200，耗时 13.7 s；sitemap 10001 条（像分页上限，需核实真实总量）；首页无网盘链接；V2EX 汇总帖标注「免登录」）
2. `https://www.lzpanx.com/`（首页 200；sitemap 3000 条（整数，疑似截断，需核实）；首页无网盘链接；V2EX 标注「免登录」）
3. `https://xykmovie.com/`（首页 200；**首页直出 8 条 xunleipan 链接**；无 sitemap；影视站，需找详情页枚举方式（id 枚举/分类分页）并统计四种网盘构成）
4. `https://ddys.io/`（首页 200；sitemap 9192 条；首页无网盘链接；WebFetch 从另一出口访问返回 403，可能有 UA/地区/Cloudflare 判定，**一旦确认反爬就 `--require-proxy`**。低端影视站，重点判断详情页给的是网盘链接还是只有在线播放/磁力，若无网盘链接直接「不满足：类型」）

报告写到 `260916/qileso.com.md`、`260916/lzpanx.com.md`、`260916/xykmovie.com.md`、`260916/ddys.io.md`。
