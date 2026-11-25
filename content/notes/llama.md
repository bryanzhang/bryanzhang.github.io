---
title: "LLaMA论文笔记"
date: 2023-07-11
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/851352491/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["模型与算法"]
tags: ["论文笔记", "LLM"]
summary: "LLaMA: Open and Efficient Foundation Language Models：https://arxiv.org/pdf/2302.13971.pdf"
---

> 2023 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

LLaMA: Open and Efficient Foundation Language Models：<https://arxiv.org/pdf/2302.13971.pdf>

Meta AI今年2月的论文，引用数已经达到596。Alpaca源出于此，目前了解到企业内大量finetune要么基于LLaMA系列，要么是chatglm-6B。因此很值得关注学习。（github上有llama项目，但只有推理，没有预训练相关）

LLaMA使用了超过1T的token进行训练，并证明使用公开数据集而不是专有、私有的数据集也能获得很好的性能。LLaMA-13B在多数指标上打败了GPT-3，但只使用了不到1/10的参数，LLaMA-65B性能可以和最好的Chinchilla-70B、PaLM-540B相提并论。

Hoffman et al. 2022指出，给定计算资源限制，不是最大的模型拿到最好性能，而是使用更多数据的小一点的模型获得最好性能。Hoffman论文中scalling law只考虑了给定训练计算资源预算情况下如何确定模型和数据集大小而没有考虑推理阶段的预算。从推理角度说，给定一定的模型性能指标，最好的模型不是最快完成训练而是最快完成推理。Hoffman推荐10B模型使用200B tokens,但我们发现7B模型在大于1T token之后模型指标还会继续改善。

![](/images/notes/llama/01.webp)

训练数据主要使用了CommonCrawl、C4、Github、Wikipedia、Books、ArXiv、StackExchange。

模型架构上：

1.受GPT3启发，对transformer每层输入进行normalize而不是对输出进行normalize，使用RMSNorm方法。

2.受PaLM启发，使用SwiGLU而不是ReLU。

3.受GPTNeo启发，使用RoPE做位置编码。

优化器使用AdamW，cosine学习率调度，2000 warmup steps。

为了加速训练，使用了xformers库(部分FlashAttention做法)，如不保存attention权重、不计算要屏蔽的key/query分数。部分计算成本高的activations作保存activations做checkpointing加速，这需要在transformer的backward函数中手动实现而不是直接使用autograd。还有sequence parallism。

还使用了模型并行和序列并行降低内存使用。对activations计算和GPU通信作交叠。

LLaMA-65B 每个GPU 380 tokens/sec训练速度，1.4T token花了大约21天训练，用了2048张A100 80G的卡。

3、4、5章中有非常丰富、多维度的评测知识，未来如果需要可以详读。评测的任务包含了封闭式问题回答、阅读理解、数学推理、代码生成、指令微调、偏见&有害内容&误导。

最后提到碳排放，训练大约消耗了1015吨二氧化碳，相比之下，BLOOM是82顿。碳排放的单位衡量指标是Watt-hour(Wh)。

![](/images/notes/llama/02.webp)

PUE是利用率(Power Usage Effectiveness)。
