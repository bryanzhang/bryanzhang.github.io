---
title: "CUDA 矩阵乘法优化 V2"
date: 2024-08-14
migrated: 2026-11-11
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/865074422/"
  note: "内容未改动，仅将图片与链接本地化。"
draft: false
tags: ["CUDA", "GEMM", "性能优化", "kernel"]
summary: "不用汇编，在 T4 上把 SGEMM（M=3840, K=2880, N=3840）从 naive 一步步优化到超过 cuBLAS 25%：shared memory → 向量化 → 4x4 / 4x8 / 8x8 寄存器分块。"
---

终于亲手完整实现了一遍，没有用到汇编，也达到预期的性能指标，T4 卡上特定 shape 超 cuBLAS 25% 性能。shape 固定为 M=3840, K=2880, N=3840。

代码：<https://github.com/bryanzhang/cuda_matmul>

主要参考思路：<https://zhuanlan.zhihu.com/p/478846788>，实操时没有完全按照文中做法。

GPU 为 T4。

**Baseline 1：cuBLAS**

```
M=3840, K=2880, N=3840, strategy=REDUCE_BANK_CONFLICTS, bs_m=32, bs_n=32, bs_k=32, enableProfiler=0, MatMul: Totally elapsed time in GPU was 2964.96 ms, 29.65 ms per operation
```

![cuBLAS 的 ncu 指标](/images/cuda-matmul-v2/1.webp)

**Baseline 2：naive**

```
M=3840, K=2880, N=3840, strategy=REDUCE_BANK_CONFLICTS, bs_m=32, bs_n=32, bs_k=32, enableProfiler=0, MatMul: Totally elapsed time in GPU was 25182.76 ms, 251.83 ms per operation
```

![naive kernel 的 ncu 指标](/images/cuda-matmul-v2/2.webp)

10 倍的差距。

**1. 使用 shared memory**

```
M=3840, K=2880, N=3840, bs_m=32, bs_n=32, bs_k=32, enableProfiler=0, MatMul: Totally elapsed time in GPU was 6138.44 ms, 204.61 ms per operation
```

只是比 naive 略好 20% 而已。

**2. 向量化 vectorize**

使用 float2，并且每个线程计算 4 个结果。

```
M=3840, K=2880, N=3840, bs_m=32, bs_n=32, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 2346.53 ms, 78.22 ms per operation
```

向量化 + 循环展开，优化效果明显。

**3. vectorize4x4**

块大小减少为 16×16，但每个线程计算 16 个结果（整个线程块的计算量不变）。

主要是希望使用 float4，但如果块大小保持 32×32，共享内存吃不消。可以归功为 float4 提升了计算访存比吧。

```
M=3840, K=2880, N=3840, bs_m=16, bs_n=16, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 1526.11 ms, 50.87 ms per operation
```

load 之后发现转置之后再 fma 反而变慢，无效。

**4. vectorize4x8**

共享内存大小保持不变（T4 卡最大只有 48K 共享内存），但展开两个小方阵。

```
M=3840, K=2880, N=3840, bs_m=16, bs_n=16, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 1010.69 ms, 33.69 ms per operation
```

这里 a 矩阵 load 时就做转置。非常接近 cuBLAS 了。

![vectorize4x8 的 ncu 指标](/images/cuda-matmul-v2/3.webp)

**5. vectorize8x8**

保持共享内存大小不变，继续展开至 4 个 4×4 小矩阵，单线程计算 8×8 个结果：

```
M=3840, K=2880, N=3840, bs_m=16, bs_n=16, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 711.47 ms, 23.72 ms per operation
```

性能超过 cuBLAS 25%：

![vectorize8x8 的 ncu 指标](/images/cuda-matmul-v2/4.webp)

> 理论上如果继续展开到 3x3，4x4，还有可能取得更好的优化效果（也可能"无指令 stall"变多而变慢）。这样其实就能理解 Triton 矩阵乘法中的 super grouping 了。
