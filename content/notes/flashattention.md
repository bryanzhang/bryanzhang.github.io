---
title: "FLASHATTENTION: Fast and Memory-Efficient Exact Attention with IO-Awareness论文笔记"
date: 2023-07-04
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/851076190/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["LLM 推理"]
tags: ["论文笔记", "Attention", "CUDA"]
summary: "FlashAttention是context-size外推的重要技术。Transformer模型慢而且内存需求大，所需的时间、内存复杂性与序列长度为二次关系(quadratic……"
---

> 2023 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

地址：<https://proceedings.neurips.cc/paper_files/paper/2022/file/67d57c32e20fd0a7a302cb81d36e40d5-Paper-Conference.pdf>

FlashAttention是context-size外推的重要技术。Transformer模型慢而且内存需求大，所需的时间、内存复杂性与序列长度为二次关系(quadratic)。Approximate Attention方法虽然尝试牺牲模型质量换取时间复杂度，但通常真正时间不会有提速(wall-clock speedup)。论文认为这里忽略了IO对训练时间的影响，实际上计算提速总是快于IO提速(内存墙问题)。FlashAttention提出的方法通过分块技术(tilling)显著减少HBM到SRAM的IO，在BERT-large上(seq_len: 512)提速15%，GPT2(seq_len:1k)提速3倍。通过扩展context size，模型质量提升（GPT2提升 0.7的perplexity、长文本分类问题提升6.4分)，并成为第一个在Path-X挑战中获得好于随机性能的Transformer模型。此外FlashAttention还可以作为基本操作和sparse attention结合进一步优化速度。

一般训练中attention实现包含多个kernel，还不考虑mask、dropout等额外的elemntwise operations影响：

![](/images/notes/flashattention/01.jpg)

tilling技术说明：

![](/images/notes/flashattention/02.jpg)

这里softmax有个小小变化，需要扣减max，因此参数和标准attention训练出来会有点不一样，并方便去迭代计算：

![](/images/notes/flashattention/03.jpg)

![](/images/notes/flashattention/04.jpg)

除了tilling外，还有个S、P等中间结果不保存而在backward时重新计算类似于gradient checkpointing的技术，尽管增加了计算量但减少了HBM访问，最后速度反而更快了。

文章还有相关的论证分析。FlashAttention HBM访问次数为

![](/images/notes/flashattention/05.jpg)

而标准attention为：

![](/images/notes/flashattention/06.jpg)

耗时和内存影响对比：

![](/images/notes/flashattention/07.jpg)

我的感觉：recomputation是好的，但tilling感觉不是独特的，只要做kernel fusion应该都能提速不少？
