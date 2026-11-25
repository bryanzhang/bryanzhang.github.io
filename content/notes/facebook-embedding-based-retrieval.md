---
title: "Embedding-based Retrieval in Facebook Search笔记"
date: 2023-02-20
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/845222192/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "向量检索", "召回"]
summary: "points：1.损失函数(triplet loss function)：2.使用曝光不点击item作为负例比random负例效果差；使用点击item作为正样本和使用曝光做正样……"
---

> 2023 年 2 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

原文：<https://arxiv.org/pdf/2006.11632.pdf>，偏算法调优的内容多。工程上总体是双塔+online minibatch learning+混合检索。

points：

1.损失函数(triplet loss function)：

![](/images/notes/facebook-embedding-based-retrieval/01.webp)

2.使用曝光不点击item作为负例比random负例效果差；使用点击item作为正样本和使用曝光做正样本，最终召回率一样。因此选择点击做正样本，random做副样本。

3.unified embedding model比单纯的text embedding召回率提升16%以上，在fb垂直搜索中有文本特征、定位特征和社交特征。

4.文本特征使用character n-gram比word n-gram鲁棒性更好（如针对拼写错误的查询)。文本embedding在模糊匹配和选择匹配场景比传统布尔检索好。

5.定位特征，在query端游城市、区域、国家、语言，doc则还增加了相关的群组标签。

6.社交embedding通过图学习生成。

6.使用基于倒排ANN的两个好处：1)使用量化方法存储开销可以非常少；2)容易整合到现有的基于倒排的传统检索系统。

7.ANN参数调整的几个经验：1)模型变更后需要重现调参；2)量化方法应该使用OPQ而不是PCA；3)PQ_BYTES位数最好是d / 4。

8.fb中向量检索主要使用(nn_key, radius)语法而不是KNN，实现时是在nprobe个cluster中过滤相似度小于radius的item。

9.与布尔的混合检索：有助于提升拼写错误、选择性查询的效果。

10.对于明显搜索意图、精搜场景不使用向量检索；item端，只选择月活用户、最近事件、热门页面、热门群组才建立向量索引。

11.使用人工反馈打分方式改善训练数据，提升向量检索精度。

12.hard mining：负样本也要尽量选择靠近正样本的，让模型提高精度，在线对随机doc做hard ngegative mining可以很大程度提升召回率，离线做hard mining，反直觉的是ranking position 101:500的效果更好(而非最靠近正样本的)，混合easy和hard样本效果好，经验值是100:1；从hard到easy做迁移学习，效果好于从easy到hard的迁移学习。

13.使用曝光未点击item或离线hard minine做负样本，ranking表现比较好，但检索效果差。因此按hardness两阶段训练，第一阶段专注在召回率，第二阶段在相似item中做区分。两种方法都有效：weighted concatenation和cascade model。

14.weighted concatenation：曝光不点击做负样本效果最好，但量化后效果损失了，最好策略是使用离线HNM，在线效果略低于离线但召回率提升仍然明显。(感觉好处是两个模型，可以只产出一份向量)

15.cascade model：级联不如weighted concatenation，精确size越多效果越差，但如果在第二阶段使用离线HNM可以比baseline提高3.4%的召回率。另一种级联模式是使用text embedding做召回，universal embedding做精排，效果可大幅提升。
