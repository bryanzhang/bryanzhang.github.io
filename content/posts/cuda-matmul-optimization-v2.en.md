---
title: "CUDA SGEMM Optimization V2: Beating cuBLAS by 25% on a T4"
date: 2024-08-14
migrated: 2026-11-11
original:
  platform: Douban
  url: "https://www.douban.com/note/865074422/"
  note: "English translation of the Chinese original."
draft: false
tags: ["CUDA", "GEMM", "Performance", "Kernel"]
summary: "No assembly, a T4, and a fixed shape (M=3840, K=2880, N=3840): SGEMM from naive to 25% faster than cuBLAS via shared memory, vectorization and 4x4 / 4x8 / 8x8 register tiling."
---

I finally implemented the whole thing end to end by hand. No assembly, and it hit the target: for one specific shape on a T4, it is 25% faster than cuBLAS. The shape is fixed at M=3840, K=2880, N=3840.

Code: <https://github.com/bryanzhang/cuda_matmul>

Main reference (in Chinese): <https://zhuanlan.zhihu.com/p/478846788>. In practice I did not follow it exactly.

GPU: T4.

**Baseline 1: cuBLAS**

```
M=3840, K=2880, N=3840, strategy=REDUCE_BANK_CONFLICTS, bs_m=32, bs_n=32, bs_k=32, enableProfiler=0, MatMul: Totally elapsed time in GPU was 2964.96 ms, 29.65 ms per operation
```

![ncu metrics for cuBLAS](/images/cuda-matmul-v2/1.webp)

**Baseline 2: naive**

```
M=3840, K=2880, N=3840, strategy=REDUCE_BANK_CONFLICTS, bs_m=32, bs_n=32, bs_k=32, enableProfiler=0, MatMul: Totally elapsed time in GPU was 25182.76 ms, 251.83 ms per operation
```

![ncu metrics for the naive kernel](/images/cuda-matmul-v2/2.webp)

A 10× gap.

**1. Shared memory**

```
M=3840, K=2880, N=3840, bs_m=32, bs_n=32, bs_k=32, enableProfiler=0, MatMul: Totally elapsed time in GPU was 6138.44 ms, 204.61 ms per operation
```

Only about 20% better than naive.

**2. Vectorization**

Use float2, and have each thread compute 4 results.

```
M=3840, K=2880, N=3840, bs_m=32, bs_n=32, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 2346.53 ms, 78.22 ms per operation
```

Vectorization plus loop unrolling gives a clear improvement.

**3. vectorize4x4**

Shrink the block to 16×16, but each thread computes 16 results (the total work per thread block is unchanged).

The main goal was to use float4; with a 32×32 block the shared memory would not fit. I'd attribute the gain to float4 raising the compute-to-memory ratio.

```
M=3840, K=2880, N=3840, bs_m=16, bs_n=16, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 1526.11 ms, 50.87 ms per operation
```

Transposing after the load and then doing the FMAs turned out slower, so that idea was dropped.

**4. vectorize4x8**

Keep the shared memory size unchanged (a T4 has at most 48 KB of shared memory), but unroll two small square tiles.

```
M=3840, K=2880, N=3840, bs_m=16, bs_n=16, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 1010.69 ms, 33.69 ms per operation
```

Here matrix A is transposed during the load. Very close to cuBLAS now.

![ncu metrics for vectorize4x8](/images/cuda-matmul-v2/3.webp)

**5. vectorize8x8**

Keep shared memory unchanged and unroll further into four 4×4 tiles, so each thread computes 8×8 results:

```
M=3840, K=2880, N=3840, bs_m=16, bs_n=16, bs_k=64, enableProfiler=0, MatMul: Totally elapsed time in GPU was 711.47 ms, 23.72 ms per operation
```

25% faster than cuBLAS:

![ncu metrics for vectorize8x8](/images/cuda-matmul-v2/4.webp)

> In theory, unrolling further into 3×3 or 4×4 groups of tiles could give even better results (or it could get slower as "no instruction" stalls increase). This is also a good way to understand super-grouping in Triton's matmul.
