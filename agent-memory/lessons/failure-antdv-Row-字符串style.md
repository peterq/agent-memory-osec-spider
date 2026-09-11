---
title: 失败经验：给 ant-design-vue 的 Row 传字符串 style 会运行时报错
type: lesson
status: active
created_at: 2026-09-04T23:20:00+08:00
updated_at: 2026-09-04T23:20:00+08:00
priority: medium
keywords:
  - ant-design-vue
  - Row
  - style
  - CSSStyleDeclaration
  - Indexed property
  - NC-JS
  - spiderAdmin
summary: antdv 的 Row/Menu.Item/transButton 用 Object.assign 合并 attrs.style，传字符串会被展开成索引键并抛 "Failed to set an indexed property [0] on 'CSSStyleDeclaration'"
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
---

# 失败经验：antdv `Row` 的 `style` 不能传字符串

## 问题背景

`admin/spiderAdmin` 队列监控总览页运行时报：

```text
Uncaught (in promise) TypeError: Failed to set an indexed property [0] on 'CSSStyleDeclaration': Indexed property setter is not supported.
```

## 失败方法

在 TSX 里按 Vue 的通用写法给 antdv 组件传字符串 style：

```tsx
<Row gutter={[16, 16]} style="margin-top:16px;">
```

## 根本原因

[事实] 大多数 antdv 组件是把 `attrs.style` 放进**数组**再交给 Vue（`style: [ownStyle, attrs.style]`），
Vue 的 `normalizeStyle` 会用 `parseStringStyle` 把数组里的字符串解析成对象，所以字符串没问题。

但有 3 个组件是用 `Object.assign`（编译产物里的 `_extends`）合并的，
`Object.assign({}, "margin-top:16px;")` 会把字符串按字符展开成 `{0:"m",1:"a",...}`，
Vue `patchStyle` 再 `for...in` 遍历执行 `el.style["0"] = "m"` → 浏览器抛上面的错。
（ant-design-vue 4.2.6 实测，路径为 `es/` 下编译产物）

| 组件 | 位置 | 合并方式 |
|---|---|---|
| `Row` | `es/grid/Row.js:149` | `_extends(_extends({}, rowStyle.value), attrs.style)` ❌ |
| `Menu.Item` | `es/menu/src/MenuItem.js:205` | `_extends(..., directionStyle.value)` ❌ |
| `transButton`（内部） | `es/_util/transButton.js:114` | ❌ |
| `Col` / `Tag` / `Space` 等 | — | `[ownStyle, attrs.style]` ✅ 字符串安全 |

另一个迷惑点：报错前缀是 `Uncaught (in promise)`，因为 Vue 的更新是在微任务里跑的，
**异步刷新触发的重渲染中抛出的 patch 错误都会显示成 promise 未捕获**，看着不像渲染问题。

## 规避方法

给这几个组件（保险起见就是所有 antdv 组件）传 **对象** 形式的 style：

```tsx
<Row gutter={[16, 16]} style={{ marginTop: "16px" }}>
```

原生 DOM 元素（`div`/`span`/`b`）传字符串 style 永远安全，不用改。

## 下次行动建议

- 见到 `Failed to set an indexed property [N] on 'CSSStyleDeclaration'`，
  直接去查“哪个组件对 `attrs.style` 做了 `Object.assign`/展开”，
  在 `node_modules/ant-design-vue/es` 里 `grep -rn "attrs.style" | grep -i "extends\|assign"` 一次定位。
- TS 不会拦这个错（`style` 允许字符串），只能靠约定。

## 适用边界

ant-design-vue 4.x；其他库若有同样的 `Object.assign(style)` 写法同理。
