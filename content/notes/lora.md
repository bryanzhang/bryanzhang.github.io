---
title: "LORA论文笔记"
date: 2023-07-10
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/851292112/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["模型与算法"]
tags: ["论文笔记", "微调"]
summary: "LORA: LOW-RANK ADAPTATION OF LARGE LANGUAGE MODELS: https://arxiv.org/pdf/2106.09685.pdf"
---

> 2023 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

LORA: LOW-RANK ADAPTATION OF LARGE LANGUAGE MODELS: <https://arxiv.org/pdf/2106.09685.pdf>

相比于finetuning，通过LoRA只需要0.01%的额外参数就可以达到不错的效果。

Aghajanyan et al. 2020显示过参数化(over-parametrized)模型实际上秩比较低，受此启发想到finetune的delta可能是低秩的，这就是LoRA的思想：

![](/images/notes/lora/01.webp)

优势：

1.参数少，可以对不同任务使用的A，B矩阵，因而任务切换和存储成本大大降低；

2.LoRA让训练变快3倍，因为不需要计算梯度以及维护优化器状态。

3.没有额外的推理延迟

4.可以和其他方法组合使用，例如prefix-tuning。

可以看看普通的Adapter方法(通常是每个Transformer block两个Adapater层)对推理延迟的影响，特别是在短序列、小batch中尤其明显：

![](/images/notes/lora/02.webp)

Prefix tuning论文中也提到难以优化，Prefix tuning也有个问题是消耗了context size，实际任务能用的长度变少了。

论文中的只是对注意力相关权重(wq,wk,wv,wo)使用LoRA，MLP、LayerNorm、biases应用LoRA还需要后续工作。

LoRA最大好处是大大减少内存和存储空间，训练时VRAM克减少2/3(r&lt;&lt;dmodel时)，GPT-3 175B训练速度相比finetune提升25%，因为绝大多数参数都不需要计算梯度。

LoRA也有局限：不同任务的input不能搞成一个batch进行推理。

多项指标好于其他方法，包括finetune：

![](/images/notes/lora/03.webp)

![](/images/notes/lora/04.webp)

![](/images/notes/lora/05.webp)

额外参数有限的情况下，应该同时adapter wq和wv，效果更好：

![](/images/notes/lora/06.webp)

wq、wv同时adapater时都只需要较小的秩，但单独adapter wq则需要较大的秩：

![](/images/notes/lora/07.webp)

当然，考虑有些场景，如下游任务使用的语言和预训练语言不同时，较大的秩效果当然好于较小的秩。

Grassman距离表明最top的奇异向量在A(r=8)和A(r=8)中才容易交叠，这就可以解释为何r=1就可以在GPT3很多下游任务中表现良好。

![](/images/notes/lora/08.webp)

类似观察，不同种子随机初始化的delta wq，delta wv，可以发现delta wq的秩高于wv：

![](/images/notes/lora/09.webp)

通过Frobenius范数看,delta wq vs wq相比随机矩阵vs wq有更高的相关性：

![](/images/notes/lora/10.webp)

delta w强化了w中某些feature，且只强化了W中某些学习到、但不加强的features。
