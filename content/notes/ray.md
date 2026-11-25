---
title: "Ray: A Distributed Framework for Emerging AI Applications论文笔记"
date: 2023-06-15
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/850298661/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["训练与分布式"]
tags: ["论文笔记", "分布式计算"]
summary: "原文链接：https://www.usenix.org/system/files/osdi18-moritz.pdf"
---

> 2023 年 6 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

原文链接：<https://www.usenix.org/system/files/osdi18-moritz.pdf>

下一代的AI应用将需要和环境持续地交互学习，而之前的通用框架(general-purpose)没法灵活、高效地把强化学习的训练，serving和仿真整合在一起，Ray应运而生，特别适合RL应用。

两个抽象特性：task-parallel和actor-based。

Task支持无状态计算，像RPC；Actor支持有状态计算。

![](/images/notes/ray/01.jpg)

典型的RL应用代码同时包含serving,simulation和training：

![](/images/notes/ray/02.jpg)

RL的计算框架需要满足以下要求：

1.细粒度、异构计算

2.灵活的计算模型

3.动态执行

要达到高资源利用率，框架需要能每秒处理数百万的task；框架不需要重新实现DNN训练或复杂仿真，而是能与现有系统无缝整合。

前面也提到，Ray的编程模型是task-parallel和actor-based。具体API为：

![](/images/notes/ray/03.jpg)

为了支持异构资源任务，允许开发者指定资源需求从而让ray scheduler可以高效管理资源。

计算图中存在两类节点：数据节点和Rpc节点，边有数据边和控制边。数据边描述数据节点与RPC节点的依赖关系，控制边捕获RPC节点的计算依赖关系(嵌套RPC)。还有第三种边：有状态边，描述Actor与Actor的状态依赖关系。有状态边有利于将Actor在无状态系统里实现，而且帮助我们构建世系血缘。基于血缘图可以重构丢失的数据。

用Ray实现原来的例子：

![](/images/notes/ray/04.jpg)

架构分为应用层和系统层(Application Layer & System Layer)。

应用层包括Driver、Worker和Actor进程。

系统层包括GCS(Global Control Store)、两级分布式调度器(Bottom-Up Distributed Scheduler)、内存分布式对象存储(In-Memory Distributed Object Store)，所有组件都是可水平扩展和容错的。

GCS：是元数据的KV存储，很多数据流系统把元数据存储在调度器中，对象传输都需要通过scheduler，Ray一开始就把元数据存储和scheduler解耦。GCS让每个组件都变得无状态，并容易基于此做debugging，profiling和可视化工具的建设。

Bottom-Up Distributed Scheduler: Spark,CIEL,Dryad都使用了中心化的调度器有考虑数据局部性但延迟在10ms级别，分布式调度器如work stealing,Sparrow, Canary却不考虑数据局部性或者有种种假设。Ray是两级调度，为了减少global scheduler负载，任务先提交到local scheduler，过载或无法满足资源需求时才提交到global scheduler。global scheduler找预估等待时间最少的节点，estimated waiting time包括：1) 节点排队时间; 2)数据传输时间(input size/bandwidth)。global scheduler的数据来自各节点心跳。如果global scheduler成为瓶颈，可以实例化更多global scheduler。

In-Memory Distributed Object Store：内存且是共享内存从而允许同节点的零拷贝，在任务执行前远程数据会replicate到本地(有些场景可能变慢了?),为了降低延迟尽可能把数据放在内存中实在放不下才放到磁盘并使用LRU策略。object store是immutable data，从而简化fault tolerance实现，对丢失的对象Ray通过血缘关系重新计算。为了简化实现，单个对象不支持切分存放在多个节点上，有类似需求可以应用层实现。

实现：大概4万行代码，72% C++(系统层)，28% Python(应用层)。GCS每个分片使用Redis实现,local scheduler会缓存各种信息，两层调度器都使用事件驱动实现。为了加速大对象传送，可使用多个TCP连接切片传输。

以下是一个例子，从中可以看到整个架构以及执行步骤：

![](/images/notes/ray/05.jpg)
