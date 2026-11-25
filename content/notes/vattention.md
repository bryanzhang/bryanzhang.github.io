---
title: "vAttention： Dynamic Memory Management for Serving LLMs without PagedAttention论文笔记"
date: 2024-08-06
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/864856678/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["LLM 推理"]
tags: ["论文笔记", "KV Cache", "显存管理"]
summary: "论文地址：https://arxiv.org/pdf/2405.04437微软印度研究院今年的论文。"
---

> 2024 年 8 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文地址：<https://arxiv.org/pdf/2405.04437>

微软印度研究院今年的论文。

KV-cache显存分配时面临挑战：1）KV-cache增长缓慢，一次迭代只增加一个；2）请求的解码长度无法提前知道。例如Yi-34B的窗口长度为200K，但sharegpt数据集平均对话长度只有415tokens，静态分配容易导致严重的内存碎片，影响batch size以及服务吞吐。PagedAttention因此产生，每次动态分配小块，近乎完美地解决了内存碎片问题，并因此成为事实标准，应用在TensorRT-LLM，HuggingFace TGI，LightLLM等主流系统上。

但PagedAttention使得KV-Cache从连续内存变为非连续内存，这带来一系列问题：

1。需要重写Attention相关GPU kernel。

2。CPU层面，增加了软件复杂度和冗余。需要进行用户空间内的块表管理，重新实现用户代码内的页分配（本来是OS/cuda的功能）。

3。带来额外性能开销：非连续内存给attention kernel增加了额外指令，额外的分支预测，据估计attention kernel慢了20%，CPU开销额外增加了10%。

论文提出vattention，将kvcache存在连续的虚拟内存中，不需要提前commit物理内存，因此可以将高性能的attention kernel直接应用上。

具体一点：不使用标准的cudaMalloc，而将虚拟内存和物理内存分配分离，先按最大需要预留虚拟内存，在需要使用时申请物理内存，cuda最大支持128TB虚拟内存，足以满足大量的kvcache需要。

挑战点&优化点：

1。cuMemCreate最少要分配2MB的物理内存页，浪费物理内存，带来碎片问题。=》修改Nvidia驱动支持64KB，128KB，256KB页大小。相关API、修改后的接口及延迟情况如下：

![](/images/notes/vattention/01.jpg)

2。内存分配API耗时很长 =》1）内存分配与计算overlap：后台线程在当前iteration分配下个iteration所需内存；2）延迟回收+主动提前分配：请求结束之后一般不回收内存而等着下个请求占据其空间（仅当可用显存少于10%时才主动回收）：

![](/images/notes/vattention/02.jpg)

评估显示Prefill阶段对吞吐优化明显，但Decode阶段几乎没优化。这可能是因为Prefill阶段计算密集，显存分配很容易overlap起来，Decode阶段更偏存储密集，显存分配延迟不容易overlap。

![](/images/notes/vattention/03.jpg)

![](/images/notes/vattention/04.jpg)

总体的makespan还是有明显优化：

![](/images/notes/vattention/05.jpg)

（注：FlashInfer和FlashAttention主要区别在于Block-Table格式，前者是简单查找表后者是压缩块表）
