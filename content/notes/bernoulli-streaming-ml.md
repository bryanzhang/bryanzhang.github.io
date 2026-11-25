---
title: "论文笔记：Bernoulli, An Industrial Streaming System for Machine Learning with Structured Designs"
date: 2022-07-23
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/835074864/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "流式训练"]
summary: "论文地址：https://dlp-kdd.github.io/assets/pdf/DLP-KDD_2021_paper_10.pdf"
---

> 2022 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文地址：<https://dlp-kdd.github.io/assets/pdf/DLP-KDD_2021_paper_10.pdf>

链接上看出是DLP KDD 2021论文(3rd Workshop on Deep Learning Practice for High-Dimensional Sparse Data with KDD 2021)。这里的工程实践颇有启发。

系统命名为Bernoulli，是向物理学家伯努利致敬，伯努利对流体力学有重大贡献。从名字也可以看出系统和“流”息息相关。

Bernoulli系统在各个流程充分利用了工业数据的结构化特性，即：**结构化数据处理流水线，结构化样本，结构化模型训练，结构化在线服务。所谓的结构化，就是将数据拆解程结构之后，能发现诸多可复用之处，从而节约计算和存储。**

Bernoulli系统类似TFX(TensorFlow Extended)，但后者为通用化设计，Bernoulli专注于工业ML服务，注重模型新鲜度、关注数据之上的算法迭代，强调使用结构化特性复用资源。

在数据处理阶段，不同于任务级别的抽象，Bernoulli由基础数据单元(Data Unit)抽象出ML任务，从而复用资源。

![](/images/notes/bernoulli-streaming-ml/01.webp)

这里Feature Center是离线特征数据仓库，DataFlow中包含Sample Skeleton和实时特征，Sample Pool存放数十天的样本。Sample Pool样本存储中可以让公共的Data Unit只存放一次，例如一个请求对应的数十个item特征中context-level特征就只需要存放一次。

为了加速模型迭代，Bernoulli用模型银行框架(Model-Bank Framework)实现结构化训练。这里科普下典型的CTR模型结构，一般是多个embedding通过sum pooling等方式变成定长的向量，然后是全连接的MLP。

Embedding存储量大，MLP参数少；前者相似、通用，后者偏任务特化。因此区分出公共embedding和私有embedding，每个模型任务仅保留少量的私有embedding。有了结构化embedding之后，训练阶段public embedding就有了很好的初值，其他部分仍使用随机初始化，训练速度可大大加速。流式模型的冷启动问题也因public embedding而得以缓解。

![](/images/notes/bernoulli-streaming-ml/02.webp)

而online serving中，public embeddng同样可直接复用。由于实时更新全模型代价过高，Bernoulli采用将模型不同参数部分的更新异步化方式得到较好的资源和效果平衡，即：public embedding数天更新一次，MLP和private embedding则接近实时更新。这是基于观察到的事实：embedding有较强语义特性，对时间并不敏感，而MLP部分对时间高度敏感。

总体来说，这篇论文启发比较大，这种优化对系统全链条要求比较高，即特征的抽取式全域多服务共享的，还包含是否是实时特征等配置，也对流程规范度要求比较高。
