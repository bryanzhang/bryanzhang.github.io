---
title: "Dremel列存基本概念(parquet)"
date: 2022-08-23
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/836724924/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["系统与性能"]
tags: ["论文笔记", "列存"]
summary: "本来想阅读下parquet文件格式，结果看文档说使用了Dremel论文中的切碎和汇编算法（uses the record shredding and assembly algo……"
---

> 2022 年 8 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

本来想阅读下parquet文件格式，结果看文档说使用了Dremel论文中的切碎和汇编算法（uses the [record shredding and assembly algorithm](https://github.com/julienledem/redelm/wiki/The-striping-and-assembly-algorithms-from-the-Dremel-paper) described in the Dremel paper)。

因此简单读了下Dremel论文：《Dremel: Interactive Analysis of Web-Scale Datasets》：<https://storage.googleapis.com/pub-tools-public-publication-data/pdf/36632.pdf>。

精妙的地方没掌握，只看个大概。

关于Dremel：是google的交互式分析引擎，06年在google上线。论文提出了嵌入式数据上新颖的列式存储格式，可以把嵌入式记录拆解程列并重组，而且Dremel提供了类SQL查询语言，底层执行类似于分布式搜索，不需要像Pig，Hive那样要做一次MR任务转换。

嵌入式数据就是像protobuf这样的数据结构了，和json不一样，它有schema，数据定义是可以一个结构包含另一个结构，每个域可以用repeated,optional,required来修饰。这种嵌入式数据在分析中非常常用，描述能力很强。

![](/images/notes/dremel-parquet/01.webp)

论文提的列存格式里，有两个重要概念：Repetition Level和Definition Level。

![](/images/notes/dremel-parquet/02.webp)

a definition level specifying how many fields in p that could be undefined (because they are optional or repeated) are actually present in the record.

具体编码时，每个列由一系列的block组成，每个block中包含repetition level和definition level使用位编码，NULL和有些definition level无需编码。

![](/images/notes/dremel-parquet/03.webp)

有时间附录中的算法要好好读一读。。。

大概看了下parquet文件格式：<https://parquet.apache.org/docs/file-format/>，它可以在chunk中放入一些统计数据(例如最大最小值等)方便做分析时谓词下推。但如果要应用在线上kv场景中，除非是非常嵌入式的结构，否则不管是读取性能、还是更新性能上复用的意义都不是太大(高密度存储场景应该和Lucene的store差不多)。
