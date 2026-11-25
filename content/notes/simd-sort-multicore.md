---
title: "Efficient Implementation of Sorting on Multi-Core SIMD CPU Architecture论文笔记"
date: 2024-08-04
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/864782124/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["系统与性能"]
tags: ["论文笔记", "SIMD", "排序"]
summary: "主要看其中的SIMD优化，一定数量内全部使用二路和四路归并。涉及到非常大量的数据，为了便于对数据只读写访问一次，还会涉及多路归并，暂时也不关注。只看较简单版本的SIMD加速。"
---

> 2024 年 8 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文：<https://www.vldb.org/pvldb/vol1/1454171.pdf>

主要看其中的SIMD优化，一定数量内全部使用二路和四路归并。涉及到非常大量的数据，为了便于对数据只读写访问一次，还会涉及多路归并，暂时也不关注。只看较简单版本的SIMD加速。

整体算法如下：

![](/images/notes/simd-sort-multicore/01.webp)

最小块的数据使用In-Register Sorting对各个lane进行排序：使用类似小方阵转置的做法。

![](/images/notes/simd-sort-multicore/02.webp)

四路归并相比二路归并，看SIMD指令的latency和throughput（intrics guide）可以减少指令执行的相互依赖，提高inter-funcitonal parallelism，另外使用更宽的bitonic merge network也是为了提高inter-funcitonal parallelism，文中使用16个元素的bitonic merge network：

![](/images/notes/simd-sort-multicore/03.webp)

关于使用odd-even network还是bitonic merge network考量：尽管odd-even比较次数更少，但需要使用较多数据移动和masking，综合开销不如bitonic merge。

bitonic merge主要指令是min，max和shuffle，如：

![](/images/notes/simd-sort-multicore/04.webp)

文中还提到使用sort（key，value）时对性能的影响。
