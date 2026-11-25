---
title: "Interleaving with Coroutines: A Practical Approach for Robust Index Joins笔记"
date: 2024-11-24
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/868048518/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["系统与性能"]
tags: ["协程", "数据库"]
summary: "相当不错的一篇文章，SAP HANA的论文。除了这个做法很不错，也具有相当的知识性。论文也不是太老，15、16年的样子。"
---

> 2024 年 11 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

地址： [content](https://infoscience.epfl.ch/server/api/core/bitstreams/30cd024c-8d63-471d-87bd-7e251ed88f0e/content)

相当不错的一篇文章，SAP HANA的论文。除了这个做法很不错，也具有相当的知识性。论文也不是太老，15、16年的样子。

dictionaries in column stores: 列存中普遍对value使用int型的code(自增)进行压缩。因此字典有两种操作：

![](/images/notes/interleaving-coroutines-index-joins/01.webp)

一般在数据库中有全量(Main)和增量(delta)两部分，locate分别对应到二分查找和CSB+-tree查找。

可以把in谓词也当做类似hash join的问题，涉及到很多memory access的问题：

![](/images/notes/interleaving-coroutines-index-joins/02.webp)

现象上是CPI随着数据量增长而显著增长：

![](/images/notes/interleaving-coroutines-index-joins/03.webp)

分析方法是TMAM（Top-down Microarchitecture Analysis)，有必要好好研究一下：

![](/images/notes/interleaving-coroutines-index-joins/04.webp)

二分查找可以通过条件移动指令(cmov)减少分支bad speculation带来的大量不必要指令发射。这里提到条件移动指令在数据都在L1 cache时更有效，但数据增长到2G时推断执行更好：

![](/images/notes/interleaving-coroutines-index-joins/05.webp)

结合5.4.1,大概能理解，因为cmov本质上是两个分支都执行，如果分支都在内存中，当然会增大延迟。

论文的最重点来了：

![](/images/notes/interleaving-coroutines-index-joins/06.webp)

![](/images/notes/interleaving-coroutines-index-joins/07.webp)

![](/images/notes/interleaving-coroutines-index-joins/08.webp)

使用无栈coroutine。编码上几乎没有任何额外成本，只是prefetch时增加个suspend，可以使用个interleave模板参数，这样一套代码就能收获两个版本。

这里还提到为啥度量复杂度为啥不使用essential complexity或者cyclomatic complexity。

从Figure 3和FIgure 4看出CORO略好于AMAC，GP效果最好。排序检索值之后可以提高局部性，但无法完全消除cache miss。

![](/images/notes/interleaving-coroutines-index-joins/09.webp)

GP为啥效果最好？因为单个instruction stream维持最少的状态，使用指令更少。

DISCUSSION & FUTURE WORK中提到的：

1。interleaving技术适用于任何有memory stall的数据或任务并行操作，如排序。

2。原则上不同数据结构、不同操作都可以使用该技术，但这时有可能instruction cache misses会成为新的瓶颈；

3。可以考虑硬件支持interleaving，比如coroutine切换时支持更多的hardware context，这样inputstream切换代价减少，有可能可以接近GP。

4。减少tlb miss，比如叶子结点为一个page。

5。考虑numa effect。

可以展开想一下，读的interleaving是好做的，读写interleaving、写写interleaving的就比较麻烦，需要有类似CAS的读写锁机制，需要对存储的数据结构有一定侵入了。
