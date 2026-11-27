---
title: "Lock-Free Data Structures with Hazard Pointers笔记"
date: 2016-12-16
migrated: 2026-11-27
original:
  platform: CSDN
  url: "https://blog.csdn.net/jollyjumper/article/details/53700726"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["系统与性能"]
tags: ["论文笔记", "无锁", "并发"]
summary: "接上一篇文章，使用引用计数实现WRRM map最后却会变成Write-Rarely-Read-Many-But-Not-Too-Many Map。这篇文章引入hazard po……"
---

> 2016 年 12 月的阅读笔记，从 CSDN 原样迁移，没有重新核对，可能有疏漏。

#### Andrei Alexandrescu神文，地址在这里:<http://collaboration.cmc.ec.gc.ca/science/rpn/biblio/ddj/Website/articles/CUJ/2004/0412/0412alexandrescu/0412alexandrescu.html>

接[上一篇文章](https://blog.csdn.net/jollyjumper/article/details/53676130)，使用引用计数实现WRRM map最后却会变成Write-Rarely-Read-Many-But-Not-Too-Many Map。这篇文章引入hazard pointers,大意是每个读线程会在读取时获取一次hazard pointer保存在全局链表中，而更新线程则每次把旧的map放到Retire list中(Thread local)。当retire list中元素数量超过R时，扫描retire list,对于不在hazard pointer列表中的map才进行回收。

R取多少？较好的选择是(1+k)\*H,H是hazard pointer列表长度,k为常数，如1/4。hazard pointer list如果使用哈希表，每次scan的复杂度为O(R)。注意在look的acquire调用之后要recheck pMap_。

如果要让lookup操作变为wait free,可以使用陷阱技术(trap technique)(基于hazard pointer).

通用性较好,HRecType结构使用void\*,所有结构都可以只用一套hazard pointer list/retire list就可以。

读取线程不应在acquire之后release之前挂掉，会导致内存无法释放。

这让我想起java gc，同样不使用引用计数，对无锁内存池表示很感兴趣。多核编程帅呆了。
