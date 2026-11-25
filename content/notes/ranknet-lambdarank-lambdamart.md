---
title: "From RankNet to LambdaRank to LambdaMART: An Overview论文笔记"
date: 2023-04-01
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/847044087/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["论文笔记", "Learning to Rank"]
summary: "From RankNet to LambdaRank to LambdaMART: An Overview：https://www.microsoft.com/en-us/re……"
---

> 2023 年 4 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

From RankNet to LambdaRank to LambdaMART: An Overview：<https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/MSR-TR-2010-82.pdf>

MSR这篇2010年的论文回顾了RankNet，LambdaRank到LambdaMart的L2R历程，对我这样的算法小白还是非常不错的。

首先是最经典的RankNet，典型的pair-wised的损失函数，si和sj是得分函数，一层sigmoid输出概率，最底下是模型参数w：

![](/images/notes/ranknet-lambdarank-lambdamart/01.jpg)

损失函数为交叉熵：

![](/images/notes/ranknet-lambdarank-lambdamart/02.jpg)

使用SGD：

![](/images/notes/ranknet-lambdarank-lambdamart/03.jpg)

这样的话是每个ui,uj对做样本，数据量很大，考虑到用神经网络前向再后向，参数更新比较慢：

![](/images/notes/ranknet-lambdarank-lambdamart/04.jpg)

可以把一个query中涉及的url pair更新加到一起：

![](/images/notes/ranknet-lambdarank-lambdamart/05.jpg)

![](/images/notes/ranknet-lambdarank-lambdamart/06.jpg)

这样训练成本就可以从接近单query平均url数的二次方降到线性。

但把排序看做二分类无法充分反映不同排序位置对最终结果的影响，它只能看出相对的逆序数。NDCG，ERR等指标则可以反映用户侧排序位置的影响，并处理多级别的相关性，但NDCG、ERR不连续、不可导，难以优化：

![](/images/notes/ranknet-lambdarank-lambdamart/07.jpg)

![](/images/notes/ranknet-lambdarank-lambdamart/08.jpg)

NDCG取值在[0,1]，越大越好，NDCG更关注排在前面的结果。

ERR指标相关内容略去不表。

要优化NDCG、ERR等listwise指标，就引出LambdaRank。它的做法是SGD时，lambda值乘以delta NDCG (交换i,j两个url的排序位置对NDCG取值的delta)：

![](/images/notes/ranknet-lambdarank-lambdamart/09.jpg)

![](/images/notes/ranknet-lambdarank-lambdamart/10.jpg)

注意这里时argmax C。这里的C就不是RankNet中的交叉熵了，它现在是一个辅助变量了。

这样调整之后发现可以优化NDCG指标。因此LambdaRank是个经验优化而没有严格的数学证明。

不过直观上确实delta NDCG绝对值越小，代表迭代步长越不需要太大。（这里如果是|delta NDCG|平方，三次方是否也有效果呢？）

经验优化是靠实际的实验，通过随机选取不同方向的值和优化值比较，算出置信度的。

4.3中说通过庞加莱引理发现LambdaRank的损失函数实际上是RankNet的损失函数(交叉熵)乘上delta NDCG。

可以看出RankNet和LambdaRank广泛适用不同的模型，没有对底层使用的模型做假设。

LambaMart是MART(Multivariable Adaptive Regression Trees，多元自适应回归模型)和LambdaRank的结合，论文花了很多篇幅讲解MART推导过程，没有细看：

![](/images/notes/ranknet-lambdarank-lambdamart/11.jpg)

文章最后指出：LambdaRank遇到一个query更新所有模型权重，LambdaMART则一次使用所有数据但只更新一部分模型权重。
