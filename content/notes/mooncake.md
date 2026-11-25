---
title: "Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving论文笔记"
date: 2024-07-14
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/864137153/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["LLM 推理"]
tags: ["论文笔记", "LLM Serving", "KV Cache", "PD 分离"]
summary: "最近这个似乎非常火，简单的说就是Prefill和Decoding完全分离部署，考虑SLO约束条件下实现吞吐、KVCache复用性的最优化。"
---

> 2024 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

原文：<https://arxiv.org/pdf/2407.00079>

最近这个似乎非常火，简单的说就是Prefill和Decoding完全分离部署，考虑SLO约束条件下实现吞吐、KVCache复用性的最优化。

![](/images/notes/mooncake/01.jpg)

分离部署的点这两个阶段特点非常鲜明，prefill可以并行化计算kvcache，SLO指标是TTFT，随序列增长略呈superlinear增长趋势；decoding阶段一次只能算一个token，SLO指标是TBT，可以continuous batching，TBT随batch大小呈现sublinear增长。Conduct进行每个请求的prefill和decoding的调度。以kvcache为中心，几个思路非常清晰，尽管系统实现不简单也有些模糊的地方。

主要做法：

1.多节点Prefill， 所谓的CPP(chunked pipeline parallelism)，砍成多个chunk分给多个节点做prefill，有点类似于训练阶段的pipeline parallelism；

2.layerwise prefill，好处是kvcache的传输和写入操作可以overlap latency；

3.prefill调度优化：调度时不止考虑load，还考虑prefix cache hit length以及KVCache blocks数量，这样既考虑到约束，也考虑最大程度复用kvcache，并据此推算是否能满足TTFT，否则early rejection。

4.cache负载均衡。如果prefill节点的kvcache总是被动更新，可能存在cache不均衡，cache无法充分使用。它这里有个巧妙做法是调度时找到了预估TTFT最优但prefix cache hit length非最优节点，把请求调度过去，同时把最长的prefix cache hit length的数据也传输到该节点上。

5.early rejection：

最简单的early rejection: prefill时估算能否满足TFTT，decoding估算能否满足TBT。

但这样可能存在完成prefill，decoding时被拒绝，那么prefill就白计算了。

更好的early rejection: prefill时也估算能否满足TBT。但如果以prefill当时状态来估算，容易导致负载波动(fluctuation)。所以需要预测完成prefill之后的时间点能否满足TBT。提到的系统做法(system level)是以平均值来预测，感觉精准度有限。
