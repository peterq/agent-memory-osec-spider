---
title: 失败经验：qiankun 子应用把 Vue 挂到包裹层上, 线上静态 CSS 被 mount 清空
type: lesson
status: active
created_at: 2026-09-08T07:20:00+08:00
updated_at: 2026-09-08T07:20:00+08:00
priority: high
keywords:
  - NC-JS
  - qiankun
  - 微前端
  - initMicroFeApp
  - Vue mount
  - qiankun-head
  - 样式丢失
  - body margin
  - antd Layout header
  - "#001529"
  - 选择器特异性
  - 无头 Chrome 验证
summary: 子应用 Vue app.mount 直接挂 qiankun 包裹层会把 <qiankun-head> 内联的全部静态 CSS 删掉(只在线上/被 qiankun 加载时出现); antd Layout header 深色底是 .ant-layout .ant-layout-header 两级选择器压过单类名; 附无头 Chrome 核对法
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/lessons/failure-ncjs构建脚本会自动上传OSS.md
  - agent-memory/lessons/failure-antdv-Row-字符串style.md
  - agent-memory/sessions/2026/2026-09-08-spiderAdmin样式修复.md
---

# 失败经验：qiankun 子应用把 Vue 挂到包裹层上, 线上静态 CSS 被 mount 清空

## 问题背景

用户报 spiderAdmin 两个样式问题：
1. 线上 `https://1s.peterq.cn/spiderAdmin`：body margin 重置丢失（页面四周 8px 白边、布局不再 fixed 铺满）。
2. 线上与本地 `localhost:5173` 都出现：顶栏底色是 antd 缺省深色 `#001529`，而不是 `main.less` 里写的白色。

两个症状根因不同，一个只在 qiankun 下出现，一个到处出现。

## 根本原因

### 1. 线上样式整体丢失：Vue `app.mount()` 清空了 qiankun 包裹层

- qiankun 传给子应用 `mount(props)` 的 `props.container` 是它自己造的 `__qiankun_microapp_wrapper_for_xxx__`，
  innerHTML 是子应用 `index.html` 经 import-html-entry 处理后的完整模板：
  `<qiankun-head>`（**入口 html 里的 `<link rel=stylesheet>` 被抓下来内联成 `<style>` 放在这里**，
  子应用运行期 `document.head.appendChild(style)` 也会被 qiankun 改道到这里）+ `<div id="app">`。
- Vue 3 的 `app.mount(el)` 在渲染前会 `el.textContent = ''`（`runtime-dom` 源码可查）。
  `packages/catalyst/ui/microFe/entry.ts` 原来直接 `app.mount(container)`，
  等于**把 `<qiankun-head>` 连同 antd `reset.css`、`main.less` 全部删掉**。
- 独立运行（`pnpm dev` 直接开 5173）不经 qiankun，Vue 挂的是真 `#app`，样式在真 head 里，所以本地完全看不出来。
  线上 DOM 用无头 Chrome dump 出来一看：包裹层第一个子元素直接就是 `.sa-boot`，没有 `<qiankun-head>`，
  子应用 CSS 文件名在整个文档里一次都不出现——这是最直接的证据。
- 该 bug 自 2024-12 的 `initMicroFeApp` 起就存在，三个子应用共用；老子应用自定义 CSS 少、靠 antd CSS-in-JS 撑着，没人察觉。

### 2. 顶栏深色：antd Layout 的两级选择器压过单类名

- ant-design-vue 4 的 Layout 样式是 CSS-in-JS 运行期注入，header 规则写在 `.ant-layout` 之下，
  实际选择器是 **`.ant-layout .ant-layout-header`（特异性 0,2,0）**：`background:#001529; height:64px;
  padding-inline:50px; line-height:64px`。
- `main.less` 里的 `.sa-header`（0,1,0）无论出现在前还是后都压不过，所以 header 永远是深色、64px 高。
- 这类问题**与样式表加载顺序无关**，光调顺序（prependQueue / 内联位置）治不好。

## 修复

1. `entry.ts`：优先挂到包裹层**内部**与独立运行同名的根节点（`container.querySelector('#app')`），
   找不到再退回包裹层；`update` 钩子同理。NC-JS `b93922d`。
2. `AppLayout.tsx` 的 `ConfigProvider` 加 `components.Layout = { colorBgHeader:'#fff', colorBgBody:'#f5f6f8' }`
   （antdv 4.2.6 的 Layout 组件 token 只有 `colorBgHeader/colorBgBody/colorBgTrigger` 三个，
   `layoutHeaderHeight` 等是样式钩子内部派生量，从 token 改不了）；
   `main.less` 的选择器提为 `.sa-shell > .ant-layout-header.sa-header`（0,3,0）覆盖高度/内边距/行高。

## 规避方法 / 下次行动建议

- 写 qiankun 子应用入口时，**永远挂到 `props.container.querySelector('#app')`**，这是 qiankun 官方示例写法；
  直接挂 `props.container` 是经典错误。
- 覆盖 antd 4 组件缺省外观，先看它生成的选择器层级（`node_modules/ant-design-vue/es/<comp>/style/index.js`
  里 `[componentCls]: { [`${componentCls}-xxx`]: ... }` 的嵌套就是两级），能用 `ConfigProvider` 的组件 token 就用 token，
  否则选择器至少比它多一级。
- **"只在线上坏、本地好"的前端样式问题，先怀疑 qiankun 包裹层**，用无头 Chrome 一条命令拿到线上真实 DOM 对照：
  ```bash
  google-chrome --headless=new --no-sandbox --disable-gpu --window-size=1400,900 --virtual-time-budget=20000 \
    --dump-dom "https://1s.peterq.cn/spiderAdmin" > dom.html      # 看 <qiankun-head> 是否还在、CSS 是否内联
  google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=1400,900 \
    --virtual-time-budget=20000 --screenshot=x.png "https://1s.peterq.cn/spiderAdmin"   # 修复前后截图对比
  ```
  连接网关前的启动骨架屏就足够看出 body margin / fixed 是否生效；顶栏要连上网关才渲染，无头模式没有管理秘钥进不去，
  改选择器特异性这类确定性修复靠代码推理 + 构建产物 CSS 核对即可。
- 本地要在 qiankun 壳下联调子应用，不必起 wrangler：`python3 admin/qiankun/scripts/serveDist.py 8791`
  以 SPA 回退方式服务 `admin/qiankun/dist/`，然后开 `http://localhost:8791/spiderAdmin`
  （**必须用 `localhost` 而非 `127.0.0.1`**，主应用只在 hostname 为 localhost 时读本地 `/apps.json`）。
- 修 catalyst 共享入口后，**其它子应用（panShareDownload / login3rd）要等各自下一次 build 才生效**，本次只重发了 spiderAdmin。

## 适用边界

qiankun 2.x + `vite-plugin-qiankun` + Vue 3 的子应用；antd/antdv 4/5 的 CSS-in-JS 组件都有同类"嵌套选择器"特性。
