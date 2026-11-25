---
title: "MEDUSA: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads论文笔记"
date: 2024-07-19
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/864296605/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["LLM 推理"]
tags: ["论文笔记", "投机解码"]
summary: "论文地址：https://arxiv.org/pdf/2401.10774 (FlashAttention作者Tri Dao也是作者之一)"
---

> 2024 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文地址：<https://arxiv.org/pdf/2401.10774> (FlashAttention作者Tri Dao也是作者之一)

speculative decoding的问题在于draft model一般需要预训练，预训练耗时长而且预训练数据集和original model的有差异会影响acceptance。

Medusa提出了一个新颖的优化做法，使用最后一层Transfomrer输出生成next k token的预测(Medusa Heads)，利用Tree Attention处理这些next k token的预测，最后确定是否接受。通过这种方式可以达到2.2到2.8的加速比。

![](/images/notes/medusa/01.jpg)

每个Medusa Head是个和LM Head一样结构、同样带残差连接、使用silu激活的单层feed-forward network。

![](/images/notes/medusa/02.jpg)

训练时w2k使用原始LM head的权重， w1k初始化为0。

Tree Attention只使用previous tokens生成的权重，后继token的权重通过类似causal mask加以屏蔽：

![](/images/notes/medusa/03.jpg)

我猜测是输出的向量序列最后softmax确定取哪个token。

很巧妙的思路，但过程中有很多超参需要确定，比如一次生成几个token(即确定Medusa head数)，每个位置取top几个prediction等，typical acceptance中同样也有超参，还有训练中有更多需要关注的。

MEDUSA-1是把original model的权重fronzen，只训练medusa heads。损失函数为：

![](/images/notes/medusa/04.jpg)

还可以使用量化版本减少显存(类似于QLORA)。

MEDUSA-2是把original model和medusa heads联合训练，损失函数为：

![](/images/notes/medusa/05.jpg)

backbone (well-trained)和medusa heads存在不同步，可以分别设置学习率。也可以两阶段训练，第一阶段训练出MEDUSA-1;第二阶段，使用wamup strategy联合训练(如先训练backbone几个epoch,然后联合训练；或者缓慢增加lambda0）。

拒绝采样由于是两次独立采样，拒绝率过高；medusa使用的是typical acceptance:

![](/images/notes/medusa/06.jpg)

使用自蒸馏数据进行训练(self-distillation)。这里有些内容没有仔细看。

wall-time加速效果(batch=1)在不同任务中有差异:

![](/images/notes/medusa/07.jpg)
