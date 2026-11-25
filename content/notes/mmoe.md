---
title: "Modeling Task Relastionships in Multi-task Learning with Multi-gate Mixture-of-Experts笔记"
date: 2023-04-04
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/847184273/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "多任务学习"]
summary: "论文地址：https://github.com/imsheridan/DeepRec/blob/master/MTL/%5BMMoE%5D%5BKDD%2018%5D%5BGo……"
---

> 2023 年 4 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文地址：<https://github.com/imsheridan/DeepRec/blob/master/MTL/%5BMMoE%5D%5BKDD%2018%5D%5BGoogle%5D%20Modeling%20Task%20Relationships%20in%20Multi-task%20Learning%20with%20Multi-gate%20Mixture-of-Experts.pdf> （这篇论文作者几乎全是华人啊)

象推荐系统，就需要多任务学习，纪要优化购买和浏览指标，也需要看留存和体验指标。

研究者报告多任务学习可以充分利用正则化和迁移学习提高模型预测能力。但基于DNN的多任务学习对数据分布以及任务相关性非常敏感。

最近的工作提出了不少模型技术处理任务差异的，但通常会增加很多额外的模型参数，这些参数会破坏模型质量，且计算量无法满足实际部署要求。

受MOE启发，这篇论文提出了Multi-gate Mixture-Of-Experts结构(MMoE)，可以避免每个任务增加过多额外参数。

一张图把MMOE结构都说明了：

![](/images/notes/mmoe/01.jpg)

MOE：

![](/images/notes/mmoe/02.jpg)

MOE结构最初的目标其实是希望降低多任务的计算，对于特定任务来说只需要计算一部分的专家网络结构就可以。

MMOE：

![](/images/notes/mmoe/03.jpg)

MMOE主要是为了捕获任务差异而不增加过多模型参数，它对每个专家网络都会有对应的门网络。

人工合成的数据在不同的皮尔逊相关系数下可以看到MMOE效果都显著好于MOE和Shared-Bottem（完全相关时效果MMOE=OMOE)：

![](/images/notes/mmoe/04.jpg)

可训练性(trainability)，或者说鲁棒性上MMOE优势同样明显。Trainablity说的是给予随机的初始化参数、不同随机种子，期望的最终模型performance效果（横轴应该是概率)（优化器用Adam Optimizer)

![](/images/notes/mmoe/05.jpg)

在实际的数据中，主要和L2-constrained、Cross-stich、Tensor-Factorization方法对比。超参使用类似高斯过程选取（应该类似贝叶斯优化?)。

case 1：UCI收入统计数据集(1994年)做两组不同皮尔逊相关性的多目标学习（相关性系数分别为0.1768,0.2373)。

![](/images/notes/mmoe/06.jpg)

各个指标上都最优接近最优。

case 2：Google大规模内容推荐：

两个优化目标：1)点击率、订阅时长；2)满意度相关指标，如like率。模型使用mini-batch SGD进行优化（batch size=1024)。线上使用的是shared-bottom。

离线指标全面占优：

![](/images/notes/mmoe/07.jpg)

在线指标，这一方面也有engagement metric相对satisfaction metric比重较大的缘故：

![](/images/notes/mmoe/08.jpg)

结语中最后提到，模型还有计算优化的潜力，可以只选择top k gate进行计算。

联想：

1.Bert+MMOE是否效果会明显提升？

2.用户画像通常要预测用户的多个属性，可能单一任务的样本较少，估计比较适合用MMOE多任务学习来提升效果。
