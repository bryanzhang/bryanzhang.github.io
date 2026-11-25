---
title: "SONG: Approximate Nearest Neighbor Search on GPU论文笔记"
date: 2024-07-19
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/864304942/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "向量检索", "GPU"]
summary: "18年百度美研的论文。hnsw/nsw上的朴素ANN算法类似于A*:大部分ANN算法95%耗费在距离计算上。"
---

> 2024 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

原文：<https://www.cs.rit.edu/~wjz/papers/conference/2020-icde-song.pdf>

18年百度美研的论文。

hnsw/nsw上的朴素ANN算法类似于A\*:

![](/images/notes/song-gpu-ann/01.jpg)

大部分ANN算法95%耗费在距离计算上。

主要做法：

1.解耦为三个阶段分别做并行化：candidate locating; bulk distance computing；data structure updating。为了最大化利用率，距离计算使用batch计算。

![](/images/notes/song-gpu-ann/02.jpg)

2.减少显存访问。

数据结构上：

1.使用fixed degree graph storage减少adjacency lists的额外操作。

2.query不止放到GPU，还搬到shared memory中加速访问。

3.并发控制：优先队列和哈希表只使用一个线程管理。

4.内存访问模式：candidate和dist每次分配fixed degree定长，比动态分配更高效。

5.哈希表(visited)选择：

\- 开放地址法：相比链表处理冲突，没有动态内存分配更高效。一个warp足以完成一次探测。

\- 使用BloomFilter：可以比哈希表少用很多内存，只增加一点额外计算。

6.q只需要使用top k个，因此使用min-max heap实现有界优先队列。在此之上：

\- 选择插入优化：如果距离大于队列中top k的最大距离则不插入。

\- 访问删除优化：如果一个节点不更新top k结果，则从visited中删除，如果使用bloom filter为了支持删除，使用Cuckoo Filter。

candidate locating中：

多个query的处理放在一个warp中提高利用率；并行扩展近邻，一定程度可能多耗费点算力。

bulk distance compuations: 32个线程组织在一起，访问连续的地址，提高缓存命中率。

OUT-OF-MEMORY datasets:

为了减少向量数据存储的开销，可以使用1-bit random projection近似计算。

最终可以取得相比CPU hnsw 50～180x 的优化。可惜没有代码。
