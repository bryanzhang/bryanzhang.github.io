---
title: "Software-Hardware Co-design for Fast and Scalable Training of Deep Learning Recommendation Models论文笔"
date: 2024-01-05
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/858100600/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "推荐模型训练"]
summary: "作为torchrec实现主要参照的论文，还是挺值得说道的。硬件内容不多。系统叫Neo,硬件平台叫ZionEX，支撑了MODEL F 12T参数量模型训练，峰值吞吐达到1.7MQ……"
---

> 2024 年 1 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

原文: <https://arxiv.org/pdf/2104.05158.pdf>

作为torchrec实现主要参照的论文，还是挺值得说道的。硬件内容不多。

系统叫Neo,硬件平台叫ZionEX，支撑了MODEL F 12T参数量模型训练，峰值吞吐达到1.7MQPS。

**一、DLRM为什么在CPU异步训练上难扩展？**

staleness会放大，影响收敛和模型质量。因此GPU训练选择同步方式。

**二、并行模式：4D并行**

每个embedding表可以选择以下并行模式：

- table-wise：整表放在一个worker上

- row-wise：按row划分分片

- column-wise：按列分片

- data parallel: 每个worker上都保存embedding全量数据

可以跨硬件层级，组合不同的并行模式，比如节点之间table-wise，节点内各GPUrow-wise。

自动的分片放置策略有：

1.贪心法，最大分片优先放置；

2.KK差分法，理论上比贪心法更优

pipeline把通信藏进不依赖它的计算

![](/images/notes/dlrm-hardware-software-codesign/01.jpg)

**三、embedding融合kernel：**

- 前向融合多个embedding表的lookup

- 反向融合梯度计算与sparse optimizer

- 按row排序并聚合重复梯度，同row梯度给一个GPU block

**四、内存层级与压缩：**

不强制所有参数都存放在HBM，按热度支持三个层级：HBM，DRAM，SSD。

缓存用LRU/LFU实现，缓存哈希表一个key存32个entry，这样刚好可以一个warp并行访问，类似SlabHash: <https://www.douban.com/note/864386673>。使用FP16 embedding降低存储和通信压力。

支持Row-wise sparse AdaGrad，就是一行embedding共享一个adagrad状态，压缩存储。

传输时使用pinned memory提高主机和设备的传送速度。

**五、硬件上每 GPU配一张 NIC**
