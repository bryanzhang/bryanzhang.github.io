---
title: "CPU 双调排序性能优化"
date: 2024-08-28
migrated: 2026-11-11
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/865510242/"
  note: "内容未改动，仅将链接本地化。"
draft: false
tags: ["SIMD", "排序", "性能优化", "CPU"]
summary: "用排序网络 + SSE/AVX + in-register sort 手写双调排序，n=8192 时从 158ms 一路优化到 0.0075ms，6 倍于 std::sort。"
---

双调排序的优点是纯粹通过排序网络实现，耗时稳定，利用 SIMD 和 CPU 洗牌指令，可以做到没有分支判断，而且是 in-place sorting，没有额外空间。之前看大部分的并行排序算法要么全部使用双调排序，要么部分采用，一直手痒着想实现一遍。

其中 in-register sort 的优化参考了论文：<https://www.vldb.org/pvldb/vol1/1454171.pdf>（我的笔记见：<https://www.douban.com/note/864782124/>）

手写一遍：<https://github.com/bryanzhang/cpu_bitonicsort>。

没有想象中复杂。甚至没使用 vtune 和 perf，最终实现 6 倍于 STL sort 的效果。

服务器为：Intel(R) Xeon(R) Platinum 8163 CPU @ 2.50GHz，支持 AVX2。

**0. 朴素的双调排序 vs 标准 C++/C 排序**

这一版的代码只有几行，是从网络上 copy 的代码。

```
n=8192, average time: 158.861 ms.
```

stl sort:

```
n=8192, average time: 0.439392 ms.
```

libc qsort:

```
n=8192, average time: 0.727875 ms.
```

可见 STL 还是明显占优的。

**1. O(nlogn) 的双调排序**

看代码分析出 base 的双调排序复杂度为 O(n²)，实际上初始序列为双调之后，后面的序列就都是双调，因此可以改写为 O(nlogn)。为方便起见，直接使用两个 qsort 把初始序列变为双调序列，性能已经逼近 qsort：

```
n=8192, average time: 0.836735 ms.
```

注意：大部分耗时集中在两个 qsort 调用上，这部分共 0.697014ms，有理由相信可以优化到比 STL sort 好。

后面先优化纯粹的双调排序部分，最后再尝试把 qsort 部分改写了（因为一处代码问题导致对耗时错误估计，qsort 部分改写工作明显拖后了）。

**2. 无递归实现**

纯双调排序部分，直接加速 5 倍：

```
n=8192, average time: 0.714325 ms.
```

**3. SIMD 加速**

使用 SSE2（128 位向量）加速。再加速 10 倍：

```
n=8192, average time: 0.700847 ms.
```

**4. 专门针对 8192 的 shape 进行优化**

基本无效，甚至可能变慢一点：

```
arr pointer: 0x56089dcf7ee0
n=8192, average time: 0.701218 ms.
```

**5. SIMD8（AVX 256 位向量化）加速**

快了 40%：

```
arr pointer: 0x560081506ee0
n=8192, average time: 0.695701 ms.
```

**6. SIMD16（AVX2 512 位向量化）加速**

快了 30%：

```
arr pointer: 0x5637e70a6f00
n=8192, average time: 0.695622 ms.
```

也做了循环手动展开的工作，结合 4 的工作，感觉这类优化在 CPU 中不大显著甚至反效果。

你觉得会提高指令并行度，有可能 O3 已经做了这个事。

使用指令预取也没有优化了，个人判断是数组足够小，完全可以直接放在 cache 中，所以没啥用（超大数组就需要了）。后面开始优化改写 qsort 部分。

**7. noqsort**

自己写个 make_bitonic 的函数代替两个 qsort 调用。make_bitonic 是 bottom-top，bitonic_sort 是 top-bottom。make_bitonic 中最小单元的排序使用经典的 in-register sort。最终的耗时：

```
arr pointer: 0x55bbeee09f00
n=8192, average time: 0.0105338 ms.
```

**8. inregister8x8**

in-register sort 由 4x4 改为 8x8，总时间再降低 30%：

```
arr pointer: 0x55a81d56cf00
n=8192, average time: 0.00750863 ms.
```

即便如此，感觉还有优化空间。in-register sort 使用 AVX（256 bits）做 8×8=64 的小块排序，改为 16×16（寄存器数量受限）应该有效果。对于升序还是降序排，使用大量 if 判断，应该能通过 blend 相关指令把分支去掉。涉及到 1bit digits 的计算用表方法还能优化。
