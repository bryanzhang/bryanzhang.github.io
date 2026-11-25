---
title: "ZeRO-Infinity: Breaking the GPU Memory Wall for Extreme Scale Deep Learning笔记"
date: 2023-06-06
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/849946226/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "ZeRO", "显存优化"]
summary: "链接：https://arxiv.org/pdf/2104.07857.pdf过去三年最大模型变大1000倍，但显存仅增加5倍。内存墙问题明显。"
---

> 2023 年 6 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

[链接](https://arxiv.org/pdf/2104.07857.pdf)：<https://arxiv.org/pdf/2104.07857.pdf>

过去三年最大模型变大1000倍，但显存仅增加5倍。内存墙问题明显。

而对于DGX-2来说，NVMe容量巨大，是显存总量的50倍，CPU内存的20倍。把所有模型状态都offload到NVme+CPU内存+显存的异构存储中，并把activation memory放到CPU内存中，同时把大算子拆成小块可顺序执行的小块(memory-centric tilling for work memory)，就能让训练的模型容量变大50倍。

但这样带来训练速度变慢的问题，本质上要满足传输带宽要求。

训练加速做法有：

1.Bandwidth-Centric Partitioning

对于参数和梯度来说，原来都是由一个数据并行的进程own，通过广播传送(broadcast-based)，这样只有一个PCIe在工作，把同层的这些参数分片到不同的内存块、NVMe、GPU设备上，通过all-gather方式通信就能让所有PCIe都工作起来，带宽自然更大。

2.Overlap Centric Design:

把GPU到GPU通信、NVMe到CPU、CPU到GPU通信交叠起来。这依赖一个动态的预取器(dynamic prefetcher)，它会追踪前向后向计算的数据读取顺序，提前预取，从而实现overlap。

3.Infinity Offload Engine

两个主要组件：

1) DeepNVMe： NVMe读写库支持批量、同步、异步读写操作，顺序读写可以实现接近设备峰值带宽，通过包括IO请求聚合、智能调度、避免数据拷贝、内存锁定等几个优化实现。

2) Pinned memory management layer：这个应该类似于CUDA中的pinned memory，可避免内存碎片、无额外拷贝可自动同步到NVMe，从而节约传输带宽。

还有易用性优化，读起来没啥感觉。

经过一系列优化可以用512个GPU训练32万亿参数量的模型，容量增加50倍，同时GPU利用率达到40%(40% of peak)。
