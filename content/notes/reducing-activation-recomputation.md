---
title: "REDUCING ACTIVATION RECOMPUTATION IN LARGE TRANSFORMER MODELS论文笔记"
date: 2023-07-11
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/851358719/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "显存优化", "Megatron"]
summary: "REDUCING ACTIVATION RECOMPUTATION IN LARGE TRANSFORMER MODELS：https://proceedings.mlsys……"
---

> 2023 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

REDUCING ACTIVATION RECOMPUTATION IN LARGE TRANSFORMER MODELS：<https://proceedings.mlsys.org/paper_files/paper/2023/file/e851ca7b43815718fbbac8afb2246bf8-Paper-mlsys2023.pdf>

2022年的论文，LLaMA训练时使用了这篇论文的思路，工程实现的时候需要精读，感觉是质量很不错的论文。

两个思路：sequence parallelism和selctive recomputation。

activation memory消耗量巨大：

![](/images/notes/reducing-activation-recomputation/01.jpg)

文章非常耐心地分析了各种配置下的activation memory。

没有任何优化情况下：

![](/images/notes/reducing-activation-recomputation/02.jpg)

考虑Tensor Parallelism:

![](/images/notes/reducing-activation-recomputation/03.jpg)

很自然就想到对Layernorm以及最后的Dropout做sequence parallelism:

![](/images/notes/reducing-activation-recomputation/04.jpg)

这样是：

![](/images/notes/reducing-activation-recomputation/05.jpg)

再进一步按PipeDream做法继续模型并行，使用1F1B pipeline，第一个stage是：

![](/images/notes/reducing-activation-recomputation/06.jpg)

不同的microbatch还要乘以

![](/images/notes/reducing-activation-recomputation/07.jpg)

还有些额外的内存使用，较少，22B模型中占不到0.01%的总activation memroy:

![](/images/notes/reducing-activation-recomputation/08.jpg)

如果完全使用activation recomputation，总计算时间要增加30%到40%。

(5)中的5as/h包括Q,K,V值的计算、Q(K^T)矩阵乘法，softmax,softmax dropout, attention over V，占的内存大但计算量很小，因此对于很多大模型5as/h>34的，只需要增加少量recomputation计算，就能减少一半以上的内存，这样的话：

![](/images/notes/reducing-activation-recomputation/09.jpg)

（和(5)一样，PipeDream做法不同microbatch在此基础上要乘以一个数)。

在1T参数上，发现可以减少5倍的activation memory，同时比纯粹的activation recomputation减少90%的计算开销。
