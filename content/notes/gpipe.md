---
title: "GPipe笔记"
date: 2023-04-06
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/847277642/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "Pipeline 并行"]
summary: "原文链接：https://arxiv.org/pdf/1811.06965.pdf"
---

> 2023 年 4 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

原文链接：<https://arxiv.org/pdf/1811.06965.pdf>

GPipe是为了更好的解决模型并行问题。

更大更深的模型带来更好的预测性能：

![](/images/notes/gpipe/01.jpg)

但有效的模型并行算法很难设计和实现，GPIpe library通过把模型垂直分为几个部分，从而允许扩展支持任意深度、超越单加速器(GPU)的内存限制。而且GPipe基础上还可以进行数据并行。

一副图就能解释GPipe如何工作，把模型按垂直方向分为K个部分，一个batch分为M个min-batch，就能获得多个加速器之间的并行，同步的update在所有min-batch完成之后进行：

![](/images/notes/gpipe/02.jpg)

为了减少内存使用，GPipe支持re-materialization。加速器前向计算时只保存输出到边界的激活函数，后向计算时重新计算复合的前向函数。尖峰的内存使用从O(N\*L)降到O(N+L/K \* N/M)。

同样还有一个bubble overhead，时间为O((k-1)/(M+K-1)，M越大，额外的开销越小，当M>=4\*K时bubble overhead可以忽略不计。这也部分因为后向时重新计算前向函数可以提前调度不需要等之前的梯度值。

但partitioning也受到参数不均衡的影响。

图表看出通过使用GPipe支持的模型参数大大增加（Transformer相对AmoebaNet各个部分更均衡，因而更接近按加速器数量的线性扩展）：

![](/images/notes/gpipe/03.jpg)

训练加速比同样如此：

![](/images/notes/gpipe/04.jpg)

即使GPU之间不使用NVLink而使用低速的PCI-E，同样能达到线性加速比：

![](/images/notes/gpipe/05.jpg)

通过GPipe在ImageNet 2012数据集上训练出来的AmoebaNet-B(18,512)迁移微调之后仍取得很好效果：

![](/images/notes/gpipe/06.jpg)

大语言模型中观察multilingual模型不同参数与baseline的对比(横轴为数据丰富性的语言排名)：

![](/images/notes/gpipe/07.jpg)

在此之上有几个经验发现：

1）模型越深，则对于缺少数据的语言提升越大

2) 模型越深，优化容易不收敛，解决办法是：1) 把transformer所有前向层数量减少；2) 把logit预测值做裁剪(不懂具体如何操作)。

3) batch越大，训练效果越好。使用了4M token的batch，这是当时已知的NMT模型中最大的batch size了，而且预计进一步加大还可以改善效果。

最后的Desgin Features and Trade-offs比较了几种模型并行方法。如Mesh-TensorFlow、Pipedream。

GPipe源码：<https://github.com/tensorflow/lingvo/blob/master/lingvo/core/gpipe.py>
