---
title: "Megatron-LM论文笔记"
date: 2023-04-22
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/847971488/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "模型并行"]
summary: "论文链接：https://arxiv.org/pdf/1909.08053.pdf"
---

> 2023 年 4 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文链接：<https://arxiv.org/pdf/1909.08053.pdf>

标题：Megatron-LM：Training Multi-Billion Parameter Language Models Using Model Parallelism

这篇论文感觉应该是发表在GPipe之后、Pipestream之前。

大模型内存占用很大需要额外的内存管理技术例如陈天奇论文中的activation checkpointing(又叫rematerialization)，类似ADAM优化器大量使用需要对每个参数存储动量和其他优化器状态，这些都给大模型训练带来了难度。GPipe等做法需要依赖特定的编译器、框架。这篇论文提出了根据transformer模型结构特定开发简单的层内模型并行实现，只需引入极少的pytorch通信原语调用不依赖特定框架和编译器，在512GPU上取得了76%的扩展效率。

额外地，原始的BERT结构在超过336M参数(BERT-LARGE)后出现performance degradation，论文首次提出通过对layernormalization对放置调整的方法解决了此问题。

1.模型并行方法：

将输入按列拆分：

![](/images/notes/megatron-lm/01.jpg)

![](/images/notes/megatron-lm/02.jpg)

![](/images/notes/megatron-lm/03.jpg)

一个的transformer layer中这样前向和后向分别增加两次All-Reduce通信即可。

另外，在输出阶段为了减少通信量，把并行GEM[Y1,Y2]的输出和交叉熵损失融合，传输标量损失而非logits可以显著提升并行效率。

2.Bert的结构调整：

![](/images/notes/megatron-lm/04.jpg)

3.训练的一些点：

数据集：174GB，使用LSH对jaccard相似度>0.7的文档做了dedup。

混合精度训练提升性能。
