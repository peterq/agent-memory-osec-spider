# 过程追加裁定（主控，所有站点子 agent 必读）

## 2026-09-16 11:50 裁定 1：联网测试与 probe 脚本必须走代理池（qileso 验收返工项，适用全部 5 站）

验收发现 qileso 的 `scripts/qileso_probe.py` 用 urllib 直连、`qileso.com_test.go` 里 `NeedDirect: true`，
开发期直连已触发过 429。仓库里存量 5 站的测试也是 `NeedDirect: true`，那是历史惯例，**本批不豁免**：

1. **联网测试**：`NeedDirect: false` + 正常订阅代理池（与生产入口同一条路径）。测试开始先等代理就绪（≤30 s）；
   等不到就 `t.Skip("代理池为空")`，**绝不退回直连**。样本保持小，允许部分请求因代理抖动失败（断言用比例/下限，不用 100%）。
2. **probe 脚本**：复用 COMMON 的代理池封装，不要自写 HTTP：
   ```python
   import sys
   sys.path.insert(0, "/home/peterq/dev/projects/1s/enfi-resource-common/site-discovery/tools")
   import httputil, proxypool
   ap = argparse.ArgumentParser(); proxypool.add_proxy_args(ap); a = ap.parse_args()
   pool, require = proxypool.pool_from_args(a)
   if pool is None or pool.wait_ready(1, timeout=a.proxy_wait) == 0: sys.exit(3)   # 拿不到代理直接失败
   s = httputil.new_session(25, pool=pool, require_proxy=True)
   code, body = httputil.fetch(s, url, 25)
   ```
   脚本默认即 `--require-proxy` 语义（不给 `--no-proxy` 留口子）。
3. 生产入口 `new<Site>Crawler()` 必须 `NeedDirect: false` + 订阅代理池，代码里不得有「拿不到代理就直连」的兜底。
4. 改完重新跑一遍联网测试（经代理）与 `probe`，把结果更新进 PRD「实测结果」，再提交。

## 2026-09-16 11:50 裁定 2：注册位置以仓库实际为准

子命令注册在 `commands_crawler.go`，配置挂载在 `config/crawler/crawler.go`（`Services.<Site>`），`spider.go` 不动。共享简报已同步修正。
