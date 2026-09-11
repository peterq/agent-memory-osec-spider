---
title: 成功经验：爬虫保活(keepalive)只在 CommitResLink 成功时续期
type: lesson
status: active
created_at: 2026-09-03T21:30:00+08:00
updated_at: 2026-09-03T22:10:00+08:00
priority: high
keywords:
  - keepalive
  - 保活
  - CommitResLink
  - 爬虫存活告警
  - AfterFunc
  - nil channel
  - 定时器竞态
summary: 保活续期的唯一判据是"有新链接真正提交成功"，轮次成功不算；顺带修掉 keepalive 包读 nil channel 挂死的隐患
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/lessons/success-爬虫联网集成测试.md
---

# 成功经验：爬虫保活只认 CommitResLink 成功

## 问题

`illuminate/keepalive` 的作用是「爬虫多久没干活就告警」。
2026-09-03 前新写的 7 个爬虫（kkpans / dyyjmax / fuxipan / feikuai / kuakes / misoso / haisou）
都把 `p.alive()` 放在**轮次成功之后**（haisou 是 `st.found > 0` 时）调用。

这是错的：**很多站点会长期返回同一批老链接**，去重后一条新数据都没有，
轮次照样"成功"、`found` 照样大于 0，保活于是永远续期，
爬虫实际早已不产出任何资源却不会告警——保活失去意义。

## 适用条件

所有调用 `spider_common.CommitResLink` 的站点爬虫。

## 推荐做法

- [用户确认 2026-09-03] **保活只在 `CommitResLink` 返回 nil 时调用**。
  站点/轮次成功、抓到条目、找到链接，全都不算。
- `CommitResLink` 对重复任务返回的是 `resource.ErrDupTask`（非 nil），
  因此"老链接重复提交"天然不会续期，正是我们要的语义。
- 代码形状（各爬虫已统一成这样）：

  ```go
  st.lock.Lock()
  if err != nil { st.commitError++ } else { st.committed++ }
  st.lock.Unlock()
  if err == nil {
      p.alive()   // 只有真正入库了新链接才续期
  }
  ```

- 参考的存量正确实现：`services/keyword/keyword2024/www.yunso.net.go`
  （`resolveJumpLink` 返回 nil 才 `alive()`）。
  `www.pansearch.me.go`、`ali.gitcafe.ink.go` 仍是"提交前就 alive"，属存量遗留，未改。

## 顺带重写的 keepalive 包

`keepalive.New` 原来用 `time.AfterFunc` + 重置函数实现，重置函数里写的是：

```go
if !timeout.Stop() { <-timeout.C }   // ❌ 会永久阻塞
```

两个事实叠加成必现 bug：
1. `time.AfterFunc` 返回的 Timer **`C` 字段恒为 nil**（`time/sleep.go` 注释明写）；
2. 定时器一旦真的触发过（即发生过一次超时），`Stop()` 就返回 false（这与 `C` 是否为 nil 无关，
   `Stop` 只看定时器状态）。

于是走进 `<-timeout.C` 读 nil channel，**永久阻塞，把调用方的采集协程挂死**。
（顺带一提，这个 drain 写法在 Go 1.23 起对 chan-based timer 也已不需要。）
原来"每轮成功都调"时轮次间隔通常 < 1h 很难踩到；改成"提交成功才调"后，
长期无新数据 → 必然超时 → 首次有新数据时 `alive()` 挂死。

**加锁不是解法（走过的弯路）**：第一版修复给 `AfterFunc` 回调和重置函数加了一把
`sync.Mutex`，声称能挡住"回调晚于续期执行导致误报超时"。这是错的——
AfterFunc 到点是 `go f()`，**回调 goroutine 已经起来了**，它只是在等锁；
续期函数放锁后回调照样 `CAS(0 → now)` 把刚续期的状态标成超时。锁只推迟、不消除。
而并发调用者之间也不需要锁：`Timer.Stop/Reset` 与 `atomic.Store` 本身就是并发安全的。

**最终实现**：干脆去掉定时器。`timeoutAt` 唯一的消费者本来就是那个每分钟跑一次的
ticker goroutine，所以改成「续期 = 一次 `atomic.StoreInt64(&lastAliveAt, now)`，
ticker 里算 `time.Since(lastAlive) - duration` 判断是否超时」。
无锁、无阻塞路径、无竞态，告警文案与 30 分钟节流语义保持不变。
该包被多个存量爬虫共用，改动是纯收敛。

## 注意事项

- `alive()` 现在会被高并发 worker 调用，实现必须是无锁无阻塞的（当前是一次 atomic 写）。
- 保活函数不要放在持有统计锁的临界区里调用。

## 可迁移范围

所有新增站点爬虫；写新爬虫时直接照上面的代码形状写。
