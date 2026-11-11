---
title: "手搓五子棋 AlphaZero (2)：MCTS 性能优化"
date: 2025-09-20
migrated: 2026-11-11
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/876037477/"
  note: "内容未改动，系列内链接改为站内链接。"
draft: false
series: ["手搓五子棋 AlphaZero"]
tags: ["AlphaZero", "MCTS", "性能优化", "lock-free", "C++"]
summary: "map 改 vector、hazard pointer 无锁多线程 + virtual loss、多线程并行回收内存：16 核 20 线程下搜索耗时降到 1/7，落子耗时降到 1/10 以内，11×11 上 150 万次搜索 20–30 秒达到不错的业余水平。"
---

{{< series-nav >}}

上一篇：[手搓五子棋 AlphaZero (1)：MCTS 框架](/posts/gomoku-alphazero-1-mcts/)

代码 GitHub 地址：<https://github.com/bryanzhang/gomoku_ai>，git tag 为 v0.2。

**1. 改为使用 vector 保存扩展节点（原来用 map），便于做多线程无锁优化、向量化优化、减少内存使用（从而可扩充 rollout 次数）：**

优化前：

![优化前](/images/gomoku-alphazero/2-1.webp)

优化后：

![优化后](/images/gomoku-alphazero/2-2.webp)

**2. 多线程并行化优化：**

为了节省内存，将 concurrency、visits、score 压缩成一个八字节的原子变量上；使用 hazard pointer 做多线程无锁；使用 virtual loss 避免多个线程同时挤在相同节点上。（注：实现 hazard pointer 时甚至为了避免 CAS 的 ABA 问题，对指针叠加了计数处理，可能是没必要的）

这里 debug 耗了太多时间，甚至为了 debug，把 web_server 用 C++ 重新实现了一遍。16 核机器上开 20 个线程，并使用 jemalloc，耗时减少到接近原来 1/7：

![多线程后搜索耗时](/images/gomoku-alphazero/2-3.webp)

但发现此时 Play 落子耗时也相同数量级了：

![落子耗时](/images/gomoku-alphazero/2-4.webp)

主要工作是回收内存，但单线程内存回收太慢。

**3. 多线程并行回收内存：**

落子耗时减少到 1/10 以内：

![并行回收后落子耗时](/images/gomoku-alphazero/2-5.webp)

没有做向量化优化，因为感觉内存分配释放、缓存效率是更大瓶颈。

现在 11×11 上已经是很不错的业余水平，搜索 150 万次，耗时在 20～30 秒，可以轻松识别各种双打，除了对一些妙招没法取胜。但目前纯 MCTS，一个耗时较长，另一个扩展到 15×15 上肯定还是太菜。

![11×11 对弈](/images/gomoku-alphazero/2-6.webp)

下一步要训练模型了，希望单步耗时两秒可以下出纯 MCTS 25 秒耗时的水平，并在 15×15 上有不错的业余选手表现。（未完待续）

下一篇：[手搓五子棋 AlphaZero (3)：11×11 策略值网络模型的 MCTS](/posts/gomoku-alphazero-3-11x11-policy-value-net/)
