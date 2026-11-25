---
title: "BytePS论文笔记"
date: 2021-05-06
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/802000320/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "参数服务器", "通信"]
summary: "零零散散看了这篇论文：A Unified Architecture for Accelerating Distributed DNN Training in Heterogen……"
---

> 2021 年 5 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

零零散散看了这篇论文：A Unified Architecture for Accelerating Distributed DNN Training in Heterogeneous GPU/CPU clusters，原文地址：<https://www.usenix.org/system/files/osdi20-jiang.pdf>，总体感觉思路很不错，但论文写得不够好(或者是太简洁)，好多地方需要猜。简单记录如下：

![](/images/notes/byteps/01.jpg)

文章都是针对同步训练模式，因为异步收敛慢，在有GPU资源和不错的网络条件情况下选择同步训练模式。

非常重要的是上面这个表格，如果有富余的CPU和带宽资源，PS架构性能会超过all reduce(通信时间相同)，但现存的架构设计太差(BytePS以前)，DNN训练性能记录全部都是AllReduce架构。

所以BytePS要基于PS架构，充分利用GPU机器上的CPU资源以及非同位部署的CPU资源，根据其数量分配好每个ps的最佳分片大小(其实是为了分配带宽)(有同学指出，单机上是all reduce)。推导出理论最佳的带宽分配：

![](/images/notes/byteps/02.jpg)

不过我推导出的是这样：

M(SS(CPU))=2(n-1)M/(kn-2k+n),

M(SS(CPU))=(1-k)M/(kn-2k+n)。

不知道是我计算的问题，还是论文本来存在问题呢。

这个只是解决了跨机器通信(inter-machine communication)的问题，在同机通信也做了优化，主要思想是每个PCIE Switch组先做张量聚合。

BytePS对网络和机器部署条件要求很高，两种部署方式：

1）PCIE-only拓扑：1个GPU机器有两个NUMA CPU用QPI连接，8个GPU分成两组用PCIE Switch连接，网卡为10万兆网卡并连到一个CPU的PCIE。PCIE link为3.0\*16(128Gbps理论带宽)，QPI>300Gbps；

2) NVLink-based拓扑：GPU基于NVLink,4个PCIE Switch,1个连两个GPU,GPU之间也用NVLink连接，每个GPU有1.2Tbps的带宽，远大于PCIE-only的拓扑。

优化器(optimizer)的工作是聚合梯度+更新参数，如果都在ps上面做，发现存在瓶颈，主要瓶颈是内存带宽，因此让cpu只做summation service，剩下的参数更新放到GPU上。架构为：

![](/images/notes/byteps/03.jpg)

那么这样就导致每一轮迭代时从CPU机器上拉参数时只能拉到梯度值，在GPU上要先做一遍参数更新，但发现overhead只有0.5%，可以接受。
