---
title: "Attention Is All You Need论文笔记"
date: 2023-02-08
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/844687945/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["模型与算法"]
tags: ["论文笔记", "Transformer"]
summary: "最近ChatGPT比较火，大语言模型的基础是transformer，必须要了解一下。"
---

> 2023 年 2 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

最近ChatGPT比较火，大语言模型的基础是transformer，必须要了解一下。

论文地址：<https://proceedings.neurips.cc/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf>

Google Brain在这篇2017年论文中提出了Transformer。

1.Introduction

RNN的问题是训练并行度，特别是在序列越长、内存限制越多情况下。尽管通过一些技巧(factorization tricks and conditional computaiton)可以很大程度上改善，但序列计算的根本限制仍然存在。

注意力机制成文序列建模、转换模型(transduction model)很有吸引力的完整解决方案，尽管一部分用例中注意力机制和RNN共同使用。Transformer完全基于注意力机制而避免使用递归网络结构，大大提升了并行度，只需要在8张P100卡上训练12个小时就可以达到SOTA效果。

2.Background

为减少序列计算，出现了用CNN做构建基础的Extended Neural GPU、ByteNet、ConvS2S等模型，隐性表示(hidden representations)可以并行计算。但随着位置距离加大，计算成本在ConvS2S中线性增长、ByteNet中对数增长(是不是可以理解为随序列增长，模型复杂性显著提升?)，而Transformer只需要常数次计算。

自注意力(Self-attention)也称作内生注意力(Intra-attention)在阅读理解、文本摘要、文本蕴含(textual entailment)以及学习任务无关的句子表示上非常成功。端到端的记忆网络则基于递归的注意力机制而非序列对齐的递归结构在简单语言问答、语言模型任务上表现出色。

Tranformer是第一个完全依赖自注意力计算输入和输出表示的转移模型，而完全不使用序列对齐的递归或卷积。后面描述Transformer，再引出自注意力和模型优势的讨论。

3.Model Architecture

多数成功的序列转换模型都是用了编码器-解码器结构(encoder-decoder structure)。输入x: (x1,x2,...,xn)映射到表示层z:(z1,z2,...,zn)的是编码器，从z到输出序列y:(y1,y2,...,ym)的是解码器。

Transformer使用了编码器-解码器结构，堆叠了自注意力以及encoder、decoder之间的逐点全连接层。

![](/images/notes/attention-is-all-you-need/01.webp)

3.1 Encoder And Decoder Stacks

Encoder部分：N=6，即有六个大层，每个层有两个子层（Multi-Head Attion + Feed Forward），这里的layer normalization是LayerNorm(x + Sublayer(x))，encoder的输出为512维。

Decoder部分：同样N=6，但每层有三个子层，增加了一个从encoder中拿到输入做Multi-Head Attention的层，另外第一个子层为Masked Multi-Head Attention，屏蔽了序列后继部分的影响，确保预测只受前驱部分影响。

3.2 Attention

注意力函数(Attention Function)是(query, { k1 : v1，k2 : v2, ... })到output的映射，这里queyr,keys,values,output都是向量。output = weight \* value，而这些权重又是query和对应key函数计算出来的。

3.2 Scaled Dot-Product Attention

![](/images/notes/attention-is-all-you-need/02.webp)

假定query和keys维度都是dk，values维度是dv。

Scaled Dot-Product就是注意力是query和keys的点积，同时再乘上scaling factor 1/根号dk，可以翻译为缩放的点积注意力吧。

实际中多个query，keys，values会并行计算，所以就是Fig2的右图，相应的输入就是三个矩阵Q,K,V，缩放的点积注意力函数为：

![](/images/notes/attention-is-all-you-need/03.webp)

除了点积注意力函数，另一个最常用的注意力函数是累加注意力函数(additive attention)。Scaled Dot-Product就是在dot-product基础上乘上根号dk。additive attention使用一个feed-forward网络+一个隐层，理论上和dot-product具有相同的复杂性，但dot-product attetion更快、空间更少，因为它可以使用高度优化的矩阵乘法实现。

dot-product注意力在维度(dk)扩大后在softmax层产生过小的提督，为了抵消这种影响，所以乘上scaling factor。

3.2.2 Muliti-Head Attention

如Fig.2右边，并行进行注意力函数计算后产生多个输出值，然后再连接投影，产生最终输出值，这就是多头注意力。

多头注意力允许模型同时关注到不同位置不同表示子空间的信息，这是单头注意力做不到的。

![](/images/notes/attention-is-all-you-need/04.webp)

Transformer中是8个并行的attention。

3.2.3 Applications of Attention In our Model

三处地方使用了多头注意力：

1."encoder-decoder attention layer"： queries,keys,values都来自于编码器。

2.编码器中的自注意力层，keys,values,queries可以来自于编码器中之前的层

3.解码器中的自注意力层，keys，values，queries可以来自解码器当前位置及之前位置，对于解码器中的后面位置的信息，使用负无穷大加以屏蔽。

3.3 Position-wise Feed-Forward Networks

这个前馈网络前面是一个relu，后面只是线性计算，没有激活函数：

![](/images/notes/attention-is-all-you-need/05.webp)

输入输出都是512维，内部层都是2048维。

3.4 Embeddings and Softmax

整个模型把输入token序列和输出token序列都用学习好的embdding来表示，最终预测出下一个token。两个embedding层的参数以及softmax之前的线性变化参数是一样的，当然在隐层参数要乘以根号dmodel。

3.5 Positional Encoding

位置编码有几种：学习和固定。

这里使用固定编码，位置对应到正弦波上：

![](/images/notes/attention-is-all-you-need/06.webp)

实验使用学习的位置编码，效果差不多。使用正弦波版本因为它允许扩展到很长的序列上，长序列很可能在训练样本中并没有。

4 Why Selft-Attention

对于变长序列转换模型，为什么不使用递归或卷积结构，而使用Selft Attention呢？这主要考虑三个重要条件：单层计算复杂度，序列操作数以及最大路径长度：

![](/images/notes/attention-is-all-you-need/07.webp)

（这里其实不是很明白Maximum Path Length的含义)

另外，self attention其实有个副作用就是它的模型可解释性更强，不仅效果好，在具体任务中它会和句子的句法语法结构有更强联系。

后面的trainning和results就不做笔记了，可以直接翻阅。

几个问题需要解答：

1.自己对BPE编码的理解是否正确?

2.位置编码怎么理解?

3.多头的理解，如何屏蔽后继信息?

4.注意力体现在什么地方，序列长度变化对模型结构有何影响?

5.和CNN有什么区别?
