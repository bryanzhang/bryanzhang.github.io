---
title: "Fast implementation of DGEMM on Fermi GPU论文笔记"
date: 2023-05-21
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/849253271/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["系统与性能"]
tags: ["论文笔记", "CUDA", "GEMM"]
summary: "https://www.doc88.com/p-9901503599272.html"
---

> 2023 年 5 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

地址：

<https://www.doc88.com/p-9901503599272.html>

<https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=96501cb481db24649ce88639ba0a4943098ec013>

2011年中科院计算所和英伟达合作的论文。

一句话说，对双精度矩阵乘法(DGEMM)，通过总结GPU性能模型，在费米架构上对经典的矩阵分块算法选择最优分块参数。在此之上，使用128位内存操作、双缓存、指令调度优化。最终获得比cuBLAS更优的效果。

基本算法框架：

![](/images/notes/dgemm-fermi/01.webp)

分块对内存带宽的减少比例是：2/(1/bm+1/bn)。在使用内存确定情况下，bn=bm对内存带宽优化最好。给定GPU架构上的峰值band width，分块算法上的实际运行内存带宽有此约束：

![](/images/notes/dgemm-fermi/02.webp)

据此选出bm=bn=64,rx=ry=4,bk=16.（这里还根据实际的microbenchmark看出offset需要时128的倍数才最好)。

在此之上分析：

1.发现global memory操作时长接近于8倍共享内存时长，使用预取指令优化

![](/images/notes/dgemm-fermi/03.webp)

这样算法调整为：

![](/images/notes/dgemm-fermi/04.webp)

2.指令预取带来寄存器个数使用增加，多出的寄存器使用可能溢出到local memory造成性能下降，因此优化最好不增加或少增加寄存器使用个数。

3.经验表明浮点数指令占用比率大体能预测到峰值浮点数计算吞吐率。Algorithm 1中浮点数指令比例只能占到64%，如果使用128位内存操作则能提高到78%，但这将带来两路的bank-conflict，会影响性能。因此可行的优化是减少128位load/store指令的延迟影响。

主要优化点(Data-thread Mapping略去不说):

1.使用双缓存：

![](/images/notes/dgemm-fermi/05.webp)

2.指令调度优化：类似穷举的办法进行指令调度优化。

实验结果：

version1只基于algorithm3使用128位内存操作、不使用双缓存；version2使用双缓存；version3:指令调度优化把shared memory延迟隐藏;version4进一步指令调度优化，把global memory access延迟做优化。

![](/images/notes/dgemm-fermi/06.webp)

version4性能显著好于cublas3.2。

两个观察：

1.费米架构引入的cache hierachy减少了寄存器溢出影响。

2.性能优化中永远要先考虑global memory访问延迟影响，verson3和version4差距过于明显。

TODO：warp和bank-conflict要好好理解下。
