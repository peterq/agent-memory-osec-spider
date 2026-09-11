---
title: 失败经验：NC-JS 子应用标准 build 脚本会自动触发 OSS 部署
type: lesson
status: active
created_at: 2026-09-04T14:10:00+08:00
updated_at: 2026-09-04T14:10:00+08:00
priority: high
keywords:
  - NC-JS
  - pnpm build
  - mfe插件
  - OSS部署
  - vite-plugins
  - 队列监控
summary: admin/*子应用的标准 `pnpm build` 脚本默认会把 dist 上传到生产 OSS 并改写 apps.json, 验证构建前必须先用 { deploy:false } 关掉
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/sessions/2026/2026-09-04-队列监控前端开发.md
---

# 失败经验：NC-JS 子应用标准 build 脚本会自动触发 OSS 部署

## 问题

在 NC-JS(`../nc-js`) 里给 `admin/resSpiderScheduler` 加新 Tab 后，想验证构建是否通过，
直接跑了仓库里"标准"的构建命令：

```bash
pnpm -F @nc/resSpiderScheduler build
```

这个命令实际触发了到生产 OSS 的真实上传（`ossutil cp -r -f dist/ oss://.../frontend/admin-mfe/resSpiderScheduler`）
并改写了线上 `apps.json` 里该子应用的 entry（换成带 `?t=` 时间戳的新地址），
即使当次 vite 构建本身因为一个未解析的 import（`dayjs` 漏声明为直接依赖）而"失败"了。

## 根本原因

`admin/*/vite.config.ts` 都用 `packages/build` 的 `mfe(appsFilePath, entry)` 插件，
其内部 `deployToOss()` 子插件：

1. **默认 `deploy: true`**（`packages/build/src/vite-plugins/mfe.ts` 的 `defaultOptions()`），
   调用处（如 `admin/resSpiderScheduler/vite.config.ts`）几乎都没有传第三个参数覆盖它。
2. `deployToOss` 用 `apply: 'build'` 挂在 **`closeBundle` 钩子**，这个钩子在 `command==='build'`
   时**无条件执行**、不看 `mode`。唯一检查 `mode==='production'` 的地方是 `config()` 钩子（只用来
   设置 `renderBuiltUrl`），**不影响是否上传**。
3. 所以 `vite build --mode development` **挡不住上传**，唯一有效的开关是插件的
   `{ deploy: false }` 选项。
4. `vite build` 即使因为"打包内容有问题"（如未解析的 import）在最后报 *Build failed*，
   Rollup 对"无法解析的外部 import"是先当 warning 处理、正常写出 bundle、跑完
   `writeBundle`/`closeBundle`，最后才在聚合警告时把整个 `build()` promise 标记为失败。
   **`closeBundle`（也就是上传）已经在"失败"判定之前跑完了**——构建报错不代表没有部署。

## 影响评估（本次实际情况）

本次触发的上传把 `admin/resSpiderScheduler/dist/`（一份未纳入 git 的旧产物，
mtime 2026-01-13，构建失败没有覆盖它）重新 `cp -f` 到了 OSS，文件内容跟之前完全一样
（hash 文件名没变），只是 `apps.json` 里的 entry 时间戳被刷新。**没有引入新的坏代码**，
但依然是一次不该发生的真实生产写操作，且如果当时本地 dist 是新构建出的坏产物，
后果会是直接推坏生产后台页面。

## 正确做法

1. **只要还没准备好真正发布，验证构建前一律先在 `vite.config.ts` 里给 `mfe()` 传
   `{ deploy: false }`**（临时改，验证完用 `git checkout -- vite.config.ts` 或等价方式还原，
   不要把这个改动带进提交，除非任务就是要顺便修这个默认值）。
2. 验证通过后，`git diff` 确认 `vite.config.ts` 已经改回未修改状态再继续提交其它文件。
3. pnpm workspace 下每个子包必须自己声明用到的直接依赖（哪怕 catalyst 已经依赖了它），
   否则本地能跑但 CI/纯净安装会在 `vite build` 阶段报 "Rollup failed to resolve import"——
   这类报错本身不一定阻止 `closeBundle`/部署跑完，更要小心。
4. 如果已经不小心跑了一次没加 `{deploy:false}` 的 `build`：先看本地 `dist/` 的 mtime 是否
   在这次命令期间被刷新过（没刷新说明上传的是旧产物，一般无害）；确认好范围后如实告知用户，
   不要自行悄悄"补救"发起第二次真实部署。

## 适用范围

`admin/*` 全部子应用共用同一个 `@nc/build` 的 `mfe()` 插件，都有这个坑；
`admin/qiankun`（主应用）不用这个插件，走的是 `wrangler pages deploy`，不受此影响。
