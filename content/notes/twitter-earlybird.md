---
title: "Twitter实时搜索系统EarlyBird"
date: 2014-06-07
migrated: 2026-11-27
original:
  platform: CSDN
  url: "https://blog.csdn.net/jollyjumper/article/details/29218789"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "实时索引", "Lucene"]
summary: "twitter对存档的tweet使用lucene做全量索引,新发的推文则是实时索引，实时检索(10秒之内索引)。实时索引和检索系统叫EarlyBird。 感觉写得比较清楚简洁……"
---

> 2014 年 6 月的论文笔记，从 CSDN 原样迁移，没有重新核对，可能有疏漏。

twitter对存档的tweet使用lucene做全量索引,新发的推文则是实时索引，实时检索(10秒之内索引)。实时索引和检索系统叫EarlyBird。  
 感觉写得比较清楚简洁，只要这些信息足够真实可信，完全可以做实现参考。  
 我简单做了几个记录:   
 1)基于lucene + java,michael busch是lucene committer  
 2)词典直接用哈希表，因此不支持term的prefix,偏序查询,哈希表使用开放链址法实现,避免大量小对象gc开销  
 3)postings列表在optimize之前直接用数组,按照docid生序不压缩，因此查找可以直接二分查找不需要跳跃表结构.posting增长时分配空间以block为单位,分配空间按指数预留空间  
 4)12个segment11个是read-only,只有一个是可读可写的,一个segment中tweet数量超过8.4m时,segment经过optimize(不是lucene中的段合并，而是做压缩)变为read only.  
 5)11个只读段并发读不需要锁，唯一的可读可写段使用volatile关键字实现高效同步(jvm memory barrier)

个人感觉,twitter全量和增量分开的设计,全量可以只有删除操作,禁止段合并,避免了段合并的问题,new generation和old generation的大小可以在整个运行阶段保持稳定，有利于系统性能的平稳高效。

论文地址:   
 <http://www-users.cs.umn.edu/~gade/earlybird.pdf>
