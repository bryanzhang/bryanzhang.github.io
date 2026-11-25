---
title: "Luecene 9.9 PForUtil编码格式"
date: 2024-09-13
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/866012499/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["搜索推荐与检索"]
tags: ["倒排索引", "Lucene"]
summary: "源文件：./lucene/core/src/java/org/apache/lucene/codecs/lucene99/PForUtil.java"
---

> 2024 年 9 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

源文件：./lucene/core/src/java/org/apache/lucene/codecs/lucene99/PForUtil.java

源码包：[**https://dlcdn.apache.org/lucene/java/9.11.1/lucene-9.11.1-src.tgz**](https://dlcdn.apache.org/lucene/java/9.11.1/lucene-9.11.1-src.tgz)

查看encode方法：

![](/images/notes/lucene-pforutil/01.jpg)

一个block放128个int，最多7个exception。

非exception部分使用ForUtil按字节紧凑编码，exception部分一个数字需要两个byte，第一个byte存放位置，第二个byte存放高位部分。因为只能一个byte存放高位，所以patched部分（forutil）最少也需要占exception最大数字的位数-8。首个字节写入token，即numExceptions(3位）和需要的for编码位数；一个特殊状况是所有数字都相同、且最大数字不超过255时，token只带numException信息，ForUtil编码为0位，数字部分仅写入一个VLong，但exception仍正常写入（这里有些奇怪，就是为啥需要写多次相同数字呢？）。

![](/images/notes/lucene-pforutil/02.jpg)

![](/images/notes/lucene-pforutil/03.jpg)

另外两个重要接口是decode和skip就更简单一点了：

![](/images/notes/lucene-pforutil/04.jpg)

顺手再看下ForUtil.java, encode性能不是那么重要，只看decode吧：

![](/images/notes/lucene-pforutil/05.jpg)

再看下decode1，一次性读128位（2个long），

![](/images/notes/lucene-pforutil/06.jpg)

利用C2编译器自动进行SIMD加速：

![](/images/notes/lucene-pforutil/07.jpg)

按照这篇文章的说法：<https://www.cnblogs.com/AntonioSu/p/15124062.html>，这个实际上不是PFor，而是NewPFD了。
