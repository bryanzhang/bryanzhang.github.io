---
title: "PipeDream: Generalized Pipeline Parallelism for DNN Training笔记"
date: 2023-04-14
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/847637704/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "Pipeline 并行"]
summary: "原文链接：https://www.microsoft.com/en-us/research/uploads/prod/2019/08/pipedream.pdf"
---

> 2023 年 4 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

原文链接：<https://www.microsoft.com/en-us/research/uploads/prod/2019/08/pipedream.pdf>

这篇2019年的论文是模型并行的集大成者，之前没想道可以这么搞，感觉太厉害了。

GPipe的论文老实说让人看了困惑，它只提出搞出多个mini-batch接近线性扩展的做法，还提出一种用时间换空间的做法，但并没有提供如何自动分片。PipeDream不仅漂亮解决了自动分片，而且还没有GPipe中最后同步的环节，它的做法非常通用，不同于GPipe只做模型并行，它还能针对慢的stage通过数据并行加速，可以通过给定的worker数、硬件拓扑自动、最优均衡分片，通过前后向的仔细调度能在确保学习效果情况下进一步缩短时间。

按它声称的，相比数据并行：图像分类上5.3倍加速，机器翻译3.1倍加速，语言模型上4.3倍加速，视频剪切3倍加速；相比GPipe这样的简单模型并行加速1.7倍；相比hybrid parallelism加速2.6到15倍。

它有一个profiling的阶段采集运行数据，基于profiler数据和硬件条件做stage切分：

![](/images/notes/pipedream/01.jpg)

核心是自动分片算法：

是一个动态规划算法，它需要对网络拓扑进行描述，是多层级的结构，需要输入带宽，不同层级数量：

![](/images/notes/pipedream/02.jpg)

转移方程：

![](/images/notes/pipedream/03.jpg)

![](/images/notes/pipedream/04.jpg)

初始化过程：

![](/images/notes/pipedream/05.jpg)

复杂度为：

![](/images/notes/pipedream/06.jpg)

，N为网络层数。实测这个DP算法运行时间都在8秒以内。还能算出哪些stage需要replication、多少replication的。

实际运行是这样：

![](/images/notes/pipedream/07.jpg)

可见负载跑得很不错了。

这里还有一个关键点是怎么避免读到过期的参数，更新参数是否需要像GPipe那样有个同步的Aggregate过程？通过weight stashing和vertical sync就能完美解决，中间过程无锁，而且理论上完全确保了Effective Learning，等同于数据并行效果：（默认实现不带vertical sync，减少元数据传输)

![](/images/notes/pipedream/08.jpg)

还有就是replication的stage mini-batch路由时需要带上minibatch ID，通过deterministic round roubin (1F1BRR)来确保FP和BP被路由到同个设备上。

内存节约有几种办法：

1.efficient encoding or compression of intermediate data [30]

2.m个batch的delta聚合到一个缓冲区；

3.rematerialization时间换空间。
