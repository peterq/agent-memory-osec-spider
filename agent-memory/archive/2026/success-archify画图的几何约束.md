---
title: 成功经验：archify 画 lifecycle / architecture 图时的几何约束与修图顺序
type: lesson
status: archived
created_at: 2026-09-07T08:30:00+08:00
updated_at: 2026-09-12T23:20:00+08:00
priority: medium
keywords: [archify, lifecycle, architecture, viewBox, 宽高比, yOffset, via, labelDy, visual-check, 首屏不滚动]
summary: archify 渲染器的固定布局规则（lifecycle 三带坐标、事件列对齐主轨 2~4 列、阅读区自适应仅在宽高比≥1.55）以及一轮修到 showcase+visual-check 双过的做法
load: rarely
related:
  - agent-memory/sessions/2026/2026-09-07-资源生命周期架构图.md
---

# 成功经验

## 问题
用 archify 技能画图时，首轮候选通常有十几条标签压框/穿框诊断，且交付后 `visual-check` 报首屏溢出。

## 适用条件
archify v0.1 的 `lifecycle` 与 `architecture` 渲染器（`~/.claude/skills/archify`）。

## 推荐做法
1. **lifecycle 先按固定坐标设计，而不是先写状态再修**：主轨列中心 x=94/248/402/556/710，带 y=126/278/450；
   事件/终态带只有 3 列且对齐主轨第 2~4 列。主轨相邻状态间隙只有 36px，**主轨过渡不要写标签**（主轨由渲染器自动画）。
2. 需要"回到前面的状态"时用显式 `via` 走主轨上方通道（y≈64/76，避开带标题 y≈100），两条通道 x 至少差 8px，
   出口 stub ≥8px（状态边缘到第一个 via 点）。
3. 探测报错这类可恢复失败放事件带，回边用 `right-channel`+`channelX` 穿相邻状态的 36px 缝；终态用 `left-channel`。
4. **首屏不滚动**：viewer 只在 viewBox 宽高比 ≥1.55 时按视口高度缩阅读区；lifecycle 默认 980×660(1.48) 不触发。
   把终态状态用 `yOffset` 塞进事件带、viewBox 降到最小高 566 并加宽到 1040，即可在 1440×900 通过。
   architecture 类型溢出几像素时，把最上/最下一行 pos 各向内挪 20~30px 即可。
5. architecture 标签压框的诊断会直接给 `labelDy` 建议值，照抄即可；节点副标题过长会被缩到 6px 以下触发
   `desktop-readability`，缩短文案而不是加宽整图。
6. 顺序：`validate --quality showcase --json` 修到 0 错 → `deliver` → `visual-check` → 看截图目视复核。

## 注意事项
- lifecycle 没有 `terminal` lane 时第 03 带会渲染英文 "Outcomes"，给一个空的 terminal lane 写中文标签即可。
- `deliver` 失败会保留旧 HTML，此时不要跑 `visual-check`（查的是旧文件）。

## 可迁移范围
所有用 archify 出图的任务；渲染器版本升级后需复核坐标常量。
