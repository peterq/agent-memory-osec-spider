# 站点发现任务（2026-09-16）—— 子 Agent 共享简报

你是「网盘资源站点发现」任务的调研子 agent。所有输出用中文。

## 背景

项目爬取网络上的网盘分享资源用于版权取证。只支持 4 种网盘：
`bnd`(pan.baidu.com/s/1xxx)、`ali-share`(www.aliyundrive.com|alipan.com/s/xxx)、
`quark`(pan.quark.cn/s/xxx)、`xunleipan`(pan.xunlei.com/s/xxx)。
UC 网盘/123 云盘/天翼/磁力不在采集范围，只做构成统计。

本工作流负责**筛出候选**（广度），不写 PRD、不写爬虫代码。

## 工作目录（worktree，所有产物写这里）

```
/home/peterq/dev/projects/1s/enfi-resource-common/.claude/worktrees/site-discovery-260916/site-discovery
```

- 工具在 `tools/`，报告写 `260916/<主域名>.md`。
- **不要 `cd` 到主仓库 `/home/peterq/dev/projects/1s/enfi-resource-common`（worktree 之外）**，也不要做任何 git 操作（commit/stash/checkout），主控统一处理。
- 不要修改 `tools/` 以外的项目代码；工具失效先修工具（改完跑 `selftest.py`），不要绕过工具手写一次性 HTTP/正则代码。

## 硬规则：抓分享链接一律走代理池（用户确认 2026-09-03）

- 代理同步进程与蜻蜓白名单进程**已由主控启动**，不要再跑 `proxypool.py start` 或 `dev_add_local_ip_to_qingting`（重复实例会让同一代理被重复推送）。
- **确认有反爬迹象（403/429/验证码/Cloudflare challenge/连接被 RST）的站点，后续所有请求必须带 `--require-proxy`**；拿不到代理脚本会退出码 3，此时停下来汇报，**绝不改成直连**。
- 未确认反爬的站点可默认模式（有代理用代理）跑；不要主动加 `--no-proxy`。

## 别把小站打崩（步骤 3.5）

- 无 CDN 的小站默认并发 ≤2、`--delay ≥1`，宁可慢。
- 出现连接超时/RST/520 而非 429 时，同样按限流处理并大幅降速复测，报告里分清「反爬」还是「站点脆弱」。
- 第 6 条验收要测「单 IP 每分钟能稳定出多少条去重分享链接」：固定低速串行跑 3~5 分钟取均值，≥10 条/分钟即通过。

## 必须使用的现成工具

```bash
cd /home/peterq/dev/projects/1s/enfi-resource-common/.claude/worktrees/site-discovery-260916/site-discovery/tools
python3 sitescan.py https://xxx.com/ --from-sitemap 500 --sample 60 --pages 60 --delay 0.5 --json /tmp/claude-1000/sd/<域名>.json
python3 sitescan.py https://xxx.com/ --pages 50 --path-filter '/detail|/thread' --delay 1 --json /tmp/claude-1000/sd/<域名>.json   # 无 sitemap 时 BFS
python3 -c "import json;print('\n'.join(l['url'] for l in json.load(open('/tmp/claude-1000/sd/<域名>.json'))['crawl']['links']))" > /tmp/claude-1000/sd/<域名>-links.txt
python3 pancheck.py --file /tmp/claude-1000/sd/<域名>-links.txt --concurrency 5 --json /tmp/claude-1000/sd/<域名>-valid.json
```

- 临时文件统一放 `/tmp/claude-1000/sd/`（先 `mkdir -p`），文件名带域名避免互相覆盖。
- `pancheck` 三态 valid/invalid/unknown，有效率 = valid/(valid+invalid)，unknown 不进分母但必须披露条数。
- 工具用法细节见 `tools/README.md`（`sitescan.py`/`pancheck.py` 两节）。

## 验收标准（6 条同时满足才算「满足」）

| # | 标准 | 判定口径 |
|---|---|---|
| 1 | 分享形式为本系统支持的网盘 | bnd/ali-share/quark/xunleipan 之一为主。UC/123/天翼/磁力不算 |
| 2 | 资源量足够多 | ≥3000 条，需证据（sitemap 条目数 / 接口 total / 最大 id / 分页末页推算） |
| 3 | 足够新，有持续入库 | 存在最近 7 天内新增的条目 |
| 4 | 链接有效率 ≥60% | 抽样 50~100 条，valid/(valid+invalid)；unknown 不进分母但披露条数 |
| 5 | 无需登录即可获取资源 | 不带 cookie 能拿到链接；「回复可见/登录可见/VIP」都算不满足 |
| 6 | 编写链接爬虫可行 | 可全量枚举，且单 IP 能稳定 ≥10 条分享链接/分钟；有 Cloudflare、高并发触发验证码**不构成否决** |

## 产出

1. 每站一份报告 → `260916/<主域名>.md`，结构：
   一句话结论（满足/不满足 + 卡在哪条）/ 站点概况（技术栈、详情页 URL 形态）/ 规模证据 /
   更新频率证据 / 网盘类型构成表 / 抽样有效性结果（样本量、valid/invalid/unknown）/
   爬取可行性（枚举方式、限流实测、单 IP 每分钟产出）/ 风险与待确认。
2. 最终回复给主控一段压缩摘要，每站一行：
   `域名 | 满足?(是/否/证据不足) | 主网盘类型 | 规模 | 有效率(样本量) | 一句话原因`

## 纪律

- 只访问公开页面，不碰 /admin /login /auth，不注册不登录。
- 数字必须有出处，禁止估猜；拿不到写「未能确认」。
- 一个站卡住超过 15 分钟（站点崩溃、代理耗尽），记录现状进报告并换下一个站，不要死磕。
