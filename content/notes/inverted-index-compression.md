---
title: "Inverted Index Compression and Query Processing with Optimized Document Ordering论文笔记"
date: 2024-09-14
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/866037169/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "倒排索引"]
summary: "research gate链接：https://www.researchgate.net/publication/221023128_Inverted_index_compre……"
---

> 2024 年 9 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

research gate链接：<https://www.researchgate.net/publication/221023128_Inverted_index_compression_and_query_processing_with_optimized_document_ordering>

回顾下这篇WWW 09的论文。文章提出了NewPFD和OptPFD算法，但文章重点是各种调研和实验数据，文中也只是轻描淡写两小段说这两个改进：NewPFD是在PForDelta基础上，把exception的出现间隔从前部分编码中取出，把低位放入其中，exception 部分存放出现位置和高位，直观上也更简单高效，目前也是检索引擎上的主流编码，不过第一部分编码采用simple 16；OptPFD,opt应该是optimal,是满足time consuming约束下最小的索引NewPForDelta编码，参数是每个block的num_of_exception。

在TREC GOV2数据集上几个表格数据有较强的参考性，调研结论：

1。PForDelta类编码在解码速度和索引大小上明显站优。这里也对比了插值编码（interpolative coding）。

2。docID reordering之后，frequency部分压缩得明显更好了；

3。docID reordering之后，相比随机docID，索引大小至少减少50%；

4。frequency部分可先做MTF和MLN转换，可以减少索引大小，但解码速度慢太多了，实用性不够

最后提出混合索引模式的一种近似最优方法，类似于OptPFD方法，也是初始先给出最小索引，在耗时约束下逐步、贪心地调整各个block的编码：

![](/images/notes/inverted-index-compression/01.jpg)
