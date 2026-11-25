---
title: "Transformer Memory as a Differential Search Index论文笔记"
date: 2024-02-07
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/859182278/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "生成式检索"]
summary: "很有意思的一篇论文，传统上搜索是Retrieve and Rank使用倒排索引或者ANN索引，这篇论文提出的DSI(differential Search Index)则直接使……"
---

> 2024 年 2 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

很有意思的一篇论文，传统上搜索是Retrieve and Rank使用倒排索引或者ANN索引，这篇论文提出的DSI(differential Search Index)则直接使用LM做索引，理论上可以通过模型推理一次完成召回+排序。Hits@1指标大幅优于baseline的BM25和DEs，甚至zero-shot表现也优于BM25(没有任何query标注数据)。

DSI可以支持灵活的setup，相关选项在section 3中详细介绍。

3.1.1 索引策略：最终选择使用Inputs2Target

Inputs2Target(doc_tokens -> docid)

Targets2Inputs (docid->doc_tokens)

Bidirectional

Span Corruption

3.1.2 文档表示策略：最终选择Direct Indexing

Direct Indexing: 选择前L个token表示一个文档

Set Indexing: 去重、消除stopwords

Inverted Index: 随机挑选一个片段的token表示一个文档

3.2 Docids表示方法：选择Semantically Structured Identifier

Unstructured Atomic Identifiers： 用唯一整数表示一个文档，和LLM输出层很像，好处是最终可以softmax算出精确的topk。

Naively Structured String Identifiers: 使用字符串，这样不用存很大的embedding，topk转为用beam search求解。

Semantically Structured Identifiers: 通过语义层次聚类，使得优化更容易，论文中使用8层BERT生成embedding k-means层次聚类(c=100)

3.3 训练与优化方法：

一般这种场景，会使用交叉熵目标，采取pre-training(每篇文档(doc tokens, docid) pair地训练，然后用(query, docid) pair finetune。但这里却是使用index和retrieve的多任务学习，而且不同于普通多任务，retrieve完全依赖于indexing(听起来还是要先pre-training，只是fine-tune时多任务?)。

数据集使用NQ(Natural Questions)，包含提问和目标的wikipedia文档。

后记： 这个仓库提供了基于hf transformers的实现，代码极少，可以看到直接基于T5微调，能跑出zero-shot的指标，不过指标只能和BM25齐平：<https://github.com/ArvinZhuang/DSI-transformers> 猜测论文中参数可能不对(比如Direct Indexing中的L)。使用的是随机的文档id, 这样有个问题是验证集中怎么能命中文档ID呢？答案是验证集的docid集合包含在训练集的docid集合中,但测试集只包含question数据。实际场景中用unstructured atomic identifier不实用。
