---
title: "ORCA论文笔记"
date: 2026-11-08
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/topic/505028820/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["LLM 推理"]
tags: ["论文笔记", "LLM Serving", "调度"]
summary: "简单看一下这篇2022年的老论文。相较于当时的Serving System和Execution Engine来说(如当时的Triton+FasterTransformer),主……"
---

> 2026 年 11 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

标题：ORCA：A Distributed Serving System for Transformer-Based Generative Models

地址：<https://www.usenix.org/system/files/osdi22-yu.pdf>

简单看一下这篇2022年的老论文。

相较于当时的Serving System和Execution Engine来说(如当时的Triton+FasterTransformer),主要是两个大的优化：

1) Request-Level Scheduling -> Iteration Scheduling: 这个可以使得整个调度气泡较小，整体吞吐延迟得到优化：

![](/images/notes/orca/01.jpg)

2) Selective Batching:

考虑到不同请求的输入序列长度、decode轮次的不同，序列tokenwise的Attetnion计算一批仅包含一个请求，其他的shape都比较确定都可以batch计算。

![](/images/notes/orca/02.jpg)

分布式架构上，一个worker进程对应一个inter-layer partition，这个worker进程控制多个GPU，这些GPU分别对应一个线程、对应这个inter-layer partition内的一个intra-layer partition。为了减少通信同步耗时，把控制信号都统一放在CPU上(如走gRPC)、数据传输都走GPU NCCL通信（FasterTransformer和Megatron-LM都混在一起使用GPU NCCL通信)。

调度算法上，First Come First Serve以保证公平，这个指的不是任何情况下先进请求的优先，而是先进来的请求必须确保iteration次数大于等于后进请求的iteration次数。调度器同样考虑预留token对GPU的消耗（也就是mini-SGLang中的inflight tokens)。batch size可以调整。调度器一次最多调度满worker数量的batch数，以保证最好情况把GPU跑满。

![](/images/notes/orca/03.jpg)
