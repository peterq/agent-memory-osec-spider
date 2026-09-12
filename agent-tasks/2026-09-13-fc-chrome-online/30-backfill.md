# 角色 30：三处回填新 FC 地址（代码改动 + 类型检查，不部署）

## 已确定的地址
- 新函数 `nc-app-prod-cdp3` 系统域名：公网 `wss://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run/chrome`；VPC 内网 `wss://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou-vpc.fcapp.run/chrome`。
- 共用自定义域名（用户决定的正式入口，路由 `/cdp3/*` → 该函数并去前缀，**路由变更待用户执行**，见 `99-notes.md`「主控」）：`wss://fc-resource-node-api.krzb.net/cdp3/chrome`；健康 `https://fc-resource-node-api.krzb.net/cdp3/health`。
- 云端脚本：`https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js`。

## 改动
1. NC-JS `admin/login3rd/src/task/task.ts` `eps['prod-v3']` → `wss://fc-resource-node-api.krzb.net/cdp3/chrome`；注释写明系统域名备用地址；**默认选中项不变**。
2. NC-JS `apps/cdp-driver/s.yaml` 的 `CDP_ENDPOINT` 注释占位改为真实值（仍保持注释掉/不生效，只做记录），`src/main.ts` 的 TODO 注释更新为"新实例已上线，切换时改 CDP_ENDPOINT"——**不改缺省值**（生产健康检查仍指旧实例，切换由用户决定）。
   验证：`cd nc-js && pnpm -F <cdp-driver 包名> type-check` 或对应 `tsc --noEmit`；login3rd 同理。**禁止 `pnpm build`**。
3. SPIDER `config/config.go` `DocCrawlerConfig`：给 `FcEndpoint` 缺省 = VPC 内网 wss 地址、`FcEndpointPublic` 缺省 = 共用域名 `/cdp3/chrome`；缺省值填在该配置节现有的"缺省值/applyDefault/Get()"机制里（先看 `services/doc_crawler/doc_crawler.go` 怎么读这两个字段——若目前没有兜底逻辑就按仓库同类配置节（如 `Lifecycle`）的写法补一个），并更新注释里"尚未部署"的措辞。`go build ./... && go vet ./config/... ./services/doc_crawler/...`；`go test ./services/doc_crawler/... -count=1`。
4. 各仓库 `git commit -- <路径>` 并 push（中文提交信息，无 Co-Authored-By）。

## 交付
≤300 字写入 `99-notes.md`「角色 30」小节：三处改动的 `文件:行`、类型检查/构建命令与结果、commit hash。
