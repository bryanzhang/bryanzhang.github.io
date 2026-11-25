---
title: "DIN论文笔记"
date: 2023-07-17
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/851579138/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "CTR 预估", "用户行为序列"]
summary: "DIN serve了阿里妈妈展示广告的主要流量。base模型为经典的Embedding&MLP："
---

> 2023 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

标题：Deep Interest Network for Click-Through Rate Prediction

地址：<https://arxiv.org/pdf/1706.06978.pdf>

DIN serve了阿里妈妈展示广告的主要流量。

base模型为经典的Embedding&MLP：

![](/images/notes/din/01.jpg)

一般是所有的用户行为做pooling(sum/average)，DIN通过local attention unit计算权重，即target ad和历史点击item通过外积和mlp计算出权重：

![](/images/notes/din/02.jpg)

这里没有权重之和为1的限制，传统限制的方法会丢失信息。论文说尝试过LSTM无效果，探索使用序列模型方式是后续的研究方向。

训练技巧上，这篇论文引入两个技巧：

1) Mini-batch aware Regularation，本来需要把整个embedding表的L2范数都计算出来，但代价太高了，可以根据mini-batch的情况进行估算：

![](/images/notes/din/03.jpg)

2）Data Adaptive Activation Function，即PRELU -> Dice：

![](/images/notes/din/04.jpg)

![](/images/notes/din/05.jpg)

E[s]和Var[S]是mini-batch中数据的期望和方差。

文章还给出了可视化，感觉是个做可解释好的思路：

![](/images/notes/din/06.jpg)
