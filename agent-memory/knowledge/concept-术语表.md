---
title: 术语与命名约定
type: knowledge
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-02T11:06:00+08:00
priority: medium
keywords: [术语, bnd, valid, version, client, enfi, osec, 命名]
summary: 代码里高频出现的缩写、字段含义与命名来历，避免误读
load: on-demand
related:
  - agent-memory/knowledge/api-rpc契约.md
---

# 术语与命名约定

## 网盘类型（`services/spider-common/spider_contract/spider_contract.go`）

| 常量 | 值 | 网盘 | 分享链接前缀 |
|---|---|---|---|
| `TypeBnd` | `bnd` | 百度网盘 | `https://pan.baidu.com/s/1<id>`（旧域名 `yun.baidu.com`） |
| `TypeAliShare` | `ali-share` | 阿里云盘 | `https://www.aliyundrive.com/s/<id>` |
| `TypeQuark` | `quark` | 夸克网盘 | `https://pan.quark.cn/s/<id>` |
| `TypeXunlei` | `xunleipan` | 迅雷云盘 | `https://pan.xunlei.com/s/<id>` |

`ParseShareLink(url) → (type, id)` 是识别入口；`TypeFromUrl` 只要类型。

## 前缀 / 缩写

- **bnd** = 百度网盘（BaiduNetDisk）。代码里 `bnd*` 一律指百度相关。
- **enfi** / **osec** / **PPIO** / **pplabs** / **1s(1second)**：历史组织名。
  - 磁盘目录用 `osec-*` 或 `enfi-*`；Go module 用 `github.com/1s/enfi-*`（`PPIO` → `1s` 已于 2026-09-02 迁完，
    STORAGE 例外，其 module 名就是裸的 `enfi-resource-storage`）。
  - 部署机器名 `osec-res1/res2/resdb/restest/resngix/jenkins`，远程用户 `pplabs`，远程目录 `/home/pplabs/<repo>`。
- **res** = resource；**dl** = download；**kw** = keyword；**gw** = gateway；**acc** = account。

## 资源字段语义

| 字段 | 含义 |
|---|---|
| `id` | `md5(url)`，ES 文档主键 |
| `version` | 文件清单指纹 `md5(排序后 originMd5+filename+fid 拼接)`，用于判重与增量 |
| `md5` / `originmd5` | 网盘侧文件哈希，`originmd5` 是网盘原始值 |
| `valid` | 链接有效性状态（0/1 等），由 `valid` 链路回写 |
| `type` | 网盘类型，见上表 |
| `user` | 分享者账号 ID，账号黑名单以 `<type>:<user>` 为 key |
| `client` | 提交该资源的爬虫节点名（`SetClientName` / `GetDefaultClientName`） |
| `refer` / `referer` | 资源来源页 |
| `meta` | `map<string,string>` 自由扩展，如 `bndPwdCookies` |
| `filename_ik_completion` / `filename_py_completion` | ES 中文分词 / 拼音补全字段，值就是 `filename` |
| `haspwd` / `pwd` | 分享是否带提取码及提取码 |

## 任务队列语义

- 三段式消费：`PopTask`（同时进入 pending）→ 周期 `Keepalive` → `TaskDone(success, failMsg, isPermanentFail, meta)`
- `seq`：任务序号，`ErrSeqIdNotMatch` 表示任务已被取消/重投，当前处理结果应丢弃
- `isPermanentFail = true` 表示不再重试（如命中账号黑名单、链接确认失效）
- `app_error.MarkPermanentError(err)`（来自 `1second/pan/common/business/app-error`）是标记永久失败的标准方式
