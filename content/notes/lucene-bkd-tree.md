---
title: "Lucene 6.6.0 BKD树"
date: 2019-02-18
migrated: 2026-11-27
original:
  platform: CSDN
  url: "https://blog.csdn.net/jollyjumper/article/details/87653303"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["源码阅读", "Lucene", "空间索引"]
summary: "相关接口使用可以看TestBKD.java。仔细读BKDReader，BKD树是一颗完全二叉树,每个节点在一个维度上进行划分."
---

> 2019 年 2 月基于 Lucene 6.6.0 源码的笔记，从 CSDN 原样迁移，没有重新核对，可能有疏漏。

相关接口使用可以看TestBKD.java。

仔细读BKDReader，BKD树是一颗完全二叉树,每个节点在一个维度上进行划分.

发现里面为了节约空间做了很多差量编码工作.其中的PackedIndexTree结构是这样的:

![](/images/notes/lucene-bkd-tree/01.png)

要知道这个结构是为了遍历树的，因此有pushLeft,pushRight,pop等操作,这里splitValuesStack可以看到冗余存了numDims维数据，但实际上就是为了在索引中只存splitValues差量的,因为可能很多数据都是不用改的，只是后面的suffix部分需要改,第一个差量字节还存在code那个int中也是为了省空间(参见PackedIndexTree的readNodeData方法).

在访问docvalues(比如精确的geo值时还要保存common prefix,以做到压缩读取.压缩读取的编码也是比较特别:

![](/images/notes/lucene-bkd-tree/02.png)

会有一个维度、一个字节的数据，在一个runlength里是共用的 (会不会某些情况有浪费啊),还提供了estimatePointCount接口，按叶子节点的最大数量来估计节点数量.

内存索引实现的时候因为要支持新增文档，为了避免子树旋转等重操作，这里会维护一个N,2N,4N,8N,...的森林，磁盘索引不需要森林.

bkd树的主要好处是：索引能小很多，但docvalues这里是有一些冗余存储，虽然有压缩.

![](/images/notes/lucene-bkd-tree/03.png)

小数据量的时候不如geo hash,感觉上应该是受制于大量的压缩，还有包括docvalues都需要重新读取的原因。
