---
title: "From 119 ms to 29.5 ms: Redoing SGEMM on a T4"
date: 2026-11-20
migrated: 2026-11-23
original:
  platform: Douban
  url: "https://www.douban.com/topic/506284209/"
  note: "English translation of the Chinese original. This post replaces the 2024 post \"CUDA SGEMM Optimization V2\", whose claim of beating cuBLAS by 25% has been retracted."
draft: false
math: true
ShowToc: true
tags: ["CUDA", "GEMM", "Performance", "Kernel"]
summary: "Redoing FP32 SGEMM on a T4 (M=N=3840, K=2880) with element-wise verification: from 119.06 ms for the naive kernel to about 29.5 ms for v17, about 2% slower than cuBLAS. It also retracts the 2024 post's unverified claim of beating cuBLAS by 25%."
---

> This post replaces "CUDA SGEMM Optimization V2" from 2024. That post's claim of beating cuBLAS by 25% was never checked against correct output and has been retracted; see "First, retracting a pretty number" below.

On this T4, a hand-written FP32 matrix multiplication now runs at **29.55 ms per call, against 28.96 ms for cuBLAS**. Both are the mean of two rounds of the same interleaved test: for the same pair of matrices, the hand-written kernel takes only about **0.6 ms (2%)** longer, and every output element passed an element-wise check against cuBLAS.

The version I kept is v17: each thread block computes **128×256** outputs, reads B with `float4`, and splits the last ten output tiles along K so that otherwise idle SMs also do work. It takes about 9% less time than v16. A 128×128 version I tried later could fit two blocks per SM, but it was not faster.

Experiment log: November 2026 · M = 3840, N = 3840, K = 2880 · all tile sizes are written as M×N, in output elements.

For most of this work the GPU I used gave me no access to ncu (Nsight Compute), so the manual tuning lacked thorough analysis and its direction was somewhat random.

GitHub: <https://github.com/bryanzhang/cuda_matmul>

A summary of the optimizations that worked:

1. Moving from global memory to tiled computation in shared memory;
2. Increasing the work per thread to cut thread and block scheduling overhead;
3. Coalesced global memory I/O, and eliminating shared memory bank conflicts (padding, swizzling, transposing asub while loading);
4. Double buffering, using registers to overlap computation and I/O across threads and hide latency;
5. Tuning loop unrolling (e.g. `#pragma unroll 4`) to improve FFMA throughput, and keeping TILE_K moderate so that unrolled loops don't use too many registers;
6. Moderately enlarging the tile along M and N to cut I/O (too large means more registers and more expensive block synchronization);
7. Vectorized loads (`float4`) to reduce instruction issue and LSU pressure;
8. Optimizing the last, partial wave of thread blocks.

Super grouping did not help for this matrix shape. Likewise, explicitly reusing asub inside the kernel or implicitly caching bsub did not help either (they used too many registers and ran slower).

Total global memory I/O:

$$
4MNK\left(\frac{1}{BM}+\frac{1}{BN}\right)+4MN
$$

Shared memory I/O:

$$
4MNK\left[\left(\frac{1}{BM}+\frac{1}{BN}\right)+\left(\frac{1}{RM}+\frac{1}{RN}\right)\right]
$$

Here BM×BN is the output tile of one thread block, and RM×RN is the block of outputs each thread computes in registers; the factor 4 is the size of an FP32 element, so both results are in bytes.

On the T4, plugging different parameters into the roofline model gives compute-bound in almost every case.

## First, retracting a pretty number

The 2024 post ["CUDA SGEMM Optimization V2"](https://www.douban.com/note/865074422/) recorded how I wrote SGEMM with shared memory, vector loads and register tiling. At the end it compared the hand-written kernel's 23.72 ms with cuBLAS's 29.65 ms and concluded that its throughput was 25% higher. **That conclusion was wrong.** From `2_vectorize` onward, the old experiments never verified the output; the old 8×8 source snapshot even used `K` as the row stride of the row-major output `C[M][N]`. On this shape K=2880 and N=3840, so finishing the writes does not mean writing the right thing.

On November 20 I fixed the code, added result verification, and reran v0–v15. The naive version takes **119.06 ms**, the early 8×8 version **55.90 ms**, and cuBLAS in the same batch **28.99 ms**; all three pass verification. The performance comparisons below start from this batch of data.

This round computes `C = A × B` with plain FP32 multiply-adds. The test program first copies A and B to device memory and times with CUDA events; each program run reports the average of 100 multiplications, and after the last one compares all **14,745,600** outputs element-wise with `cublasSgemm`. The check rejects non-finite values and allows an absolute error of `1e-3 + 1e-4 × |reference|`. "Two rounds" below means two program runs, not two kernel launches.

## The first fifteen versions: where do you keep the data?

In the naive version each thread computes a single element of C. The same row of A and the same column of B are used over and over by neighboring threads, yet each thread issues its own loads. v1 moves small tiles of A and B into shared memory, and the time drops from 119.06 to 88.58 ms. v2 to v4 go one step further: they keep partial sums in registers, so that the same input takes part in several outputs' multiply-adds. Going from 2×2 to 4×8 outputs per thread, v4 reached 48.94 ms. `float2`/`float4` cut the number of load instructions, but these steps also changed data reuse, so the gains can't be credited to vectorization alone.

v5 was the first counterexample. Combining four 4×4 sub-blocks into 8×8 was meant to save a few more transfers, but the time went back from 48.94 to 55.90 ms, and the log shows 208 registers per thread. v6 shortened the tile along K and still didn't turn things around; v7 kept the 8×8 output, dropped the piecewise combination, brought registers down to 128 and got to 41.13 ms. v8 transposes A as it is loaded into shared memory and, combined with interleaved access, reached **33.71 ms**. Its 128×128 output tile later became the starting point for testing the "two resident blocks" idea.

Making the tile even larger has a price: at 256×256, v9 spills registers and the time jumps to 242.20 ms. v11 uses 512 threads to share one 128×256 tile; v12 keeps two sets of shared memory, one for the current K slice and one for the next; v13 splits the prefetch into stages so that global loads for the next slice overlap with computation on the current one. By v14 the time was 32.76 ms. v15 moved all prefetching up front at once and slowed down to 33.56 ms. So the later work branched from v14.

**Corrected results: v0–v15, version by version (ms per call)**

| Version | Main change | Time |
|---|---|---|
| v0 / v1 | naive / shared memory tiling | 119.06 / 88.58 |
| v2 / v3 | 2×2 per thread, float2 / 4×4 per thread, float4 | 69.77 / 50.33 |
| v4 / v5 | 4×8 reusing asub / four sub-blocks combined into 8×8 | 48.94 / 55.90 |
| v6 | TILE_K reduced to 16 / asub row width adjusted again | 54.97 / 53.73 |
| v7 / v8 | 8×8 register tile / transpose on load plus interleaved access | 41.13 / 33.71 |
| v9 / v10 | 256×256, heavy spilling / 128×256, staged reuse of asub | 242.20 / 39.99 |
| v11 / v12 | 512 threads share the outputs / shared memory double buffering | 36.14 / 35.20 |
| v13 / v14 / v15 | staged prefetch / float4 loads of A / all prefetch up front | 33.02 / 32.76 / 33.56 |

## v16: the conflicts disappeared, the milliseconds didn't move

v14 left a very specific problem: reading A from global memory already used aligned `float4` loads, but when the four components were transposed and written into `asub`, every scalar write had a two-way bank conflict. Could I keep the loads as they were and change only the addresses of this step?

Numbering 4-byte floats, the bank index on the T4 is the address modulo 32. The row stride of `asub` is 132, so `asub[4*lx+c][ly]` maps to `(16*lx + 4*c + ly) % 32`. For the same component `c`, `lx=0` and `lx=2` land in the same group of eight banks, and so do 1 and 3. The fix is to flip bit 3 of the column index only when `lx=2,3`, which shifts each of the two overlapping pairs by eight banks:

```cpp
// Write: lx = 0, 1 stay in place; lx = 2, 3 XOR the column index with 8
int col = ly ^ ((lx >> 1) << 3);
asub[buf][4 * lx + c][col] = component;

// Compute: swap positions in groups of 8 floats; the two float4 reads within a group stay aligned
int acol = 8 * (ty ^ (j >= 8));
// read from asub[cur][j][acol] and [acol + 4]
```

Enumerating the addresses warp by warp, each bank now receives one distinct word per write instead of two; registers went from 126 to 124 with no spills. But in the interleaved comparison, v14 took **32.39–32.77 ms** and v16 **32.74–32.76 ms**. Benchmarking these shared memory writes in isolation, the old and new mappings both take 128 cycles per round. What I can confirm is that the address conflicts are gone and the total time did not improve. The machine did not expose Nsight Compute performance counters, so the address derivation can't be presented as a counter measurement, let alone used to conclude that every two-way conflict is free.

## v17: filling the last ten tiles mattered more than fixing banks

v17 keeps v16's layout and changes two more things. The first is in the inner loop: the eight columns a thread is responsible for become two groups of four consecutive columns, so reading B in each K step goes from eight scalar shared memory loads to two `LDS.128`. Ordinary output tiles can also write C with `float4`. The second is at the grid level: split only the tiles that don't fill the last wave.

**Why split only ten tiles?** The output is exactly (3840/128) × (3840/256) = 30 × 15 = **450 tiles**. The T4 has 40 SMs, and this version fits one block per SM. The first 440 tiles fill eleven waves; if the remaining ten still each went to one block, only ten SMs would have work at the end.

Each of these ten output tiles is cut into four along K. Where one block used to run 180 K steps, four blocks now run 45 steps each, producing exactly 40 tail blocks. So **440 + 40 = 480** blocks are launched, and the output is still 450 tiles. Only the tail outputs are zeroed beforehand and combined with `atomicAdd`; that overhead is included in the timings.

**Measured separately, then together · T4, ms per call**

| Version | Change relative to v16 | Round 1 | Round 2 |
|---|---|---|---|
| v16 | baseline | 32.76 | 32.73 |
| v17a | only the B reads and C writes | 31.76 | 31.45 |
| v17b | only the tail-wave split-K | 31.32 | 31.31 |
| v17c | both combined, no explicit outer unroll factor | 30.78 | 30.80 |

The tail split has a side effect: the same kernel now runs either 180 or 45 steps, so the loop count is no longer a compile-time constant. In another set of comparisons, the combined version took 30.53–30.78 ms, unrolling twice explicitly gave 29.91–29.92 ms, and **unrolling four times gave 29.73–29.76 ms**. With `__launch_bounds__(512, 1)`, it compiles to 128 registers per thread with zero spills. This version was committed as v17. Compared with v16 at about 32.75 ms, the typical time is about 9% lower.

In one full verification before committing, 0 of the 14,745,600 elements were out of tolerance, and the maximum absolute error was 0.00317. The partial sums of the tail tiles change the order of the FP32 additions, so PASS here means agreement within numerical tolerance, not bit-for-bit identity with cuBLAS.

## Back to v8's 128×128: can two blocks beat one?

To fit two blocks per SM at the same time, v18 goes back to v8's 16×16 threads, each thread still computing 8×8 outputs. Both A and B are double-buffered; without padding, each block uses exactly `2 × 16 × (128 + 128) × 4 = 32 KiB` of shared memory. With the 64 KiB shared memory configuration, the T4 can hold two; the CUDA occupancy API indeed returns a limit of **2 blocks/SM**. This verifies the resident capacity, not the number of active blocks at every moment.

Now there are 30×30 = 900 output tiles; counting 80 resident slots, the last 20 can also each be split four ways along K. The key point: **two 256-thread blocks and one 512-thread block both add up to 16 warps per SM.** Two resident blocks give two blocks that synchronize independently, but they do not double the number of schedulable warps. Smaller tiles also have a cost: per 16-wide K step, the compute divided by the bytes loaded for A and B drops from 42.7 FLOP/byte at 128×256 to 32 at 128×128. This is the per-block reuse, not measured DRAM bandwidth.

**Final interleaved comparison · each cell is the average time of 100 multiplications (ms); every round passed verification**

| Version and layout | Output tile | Round 1 | Round 2 |
|---|---|---|---|
| v17 · committed | 128×256 | 29.48 | 29.78 |
| v18_u1 · each warp loads 8 rows of A, 4 float4 each | 128×128 | 30.29 | 30.01 |
| v18e_u1 · 16 rows, 2 float4 each | 128×128 | 30.90 | 30.59 |
| v18f_u1 · same as e, 4×8 layout within a warp | 128×128 | 31.58 | 31.37 |
| v18f_u4 · same as f, K loop unrolled four times | 128×128 | 31.62 | 31.30 |

u1 and u4 are the unroll factors of the outer K loop. Don't subtract minimums taken from different rounds: the fastest variant, v18_u1, was 0.81 and 0.23 ms slower than v17 in the same rounds.

One more counterexample didn't make it into the final table: having each of the 32 lanes fetch one `float4` from a different row of A writes back to asub without conflicts even without a swizzle, and compiles without register spills. But each global load then touches 32 sectors of 32 bytes and uses only 16 bytes of each; the earlier coalesced mapping needed only 16 sectors. This version ran at 33.92–33.94 ms. **Zero local memory spills and zero shared memory conflicts are no substitute for the end-to-end run time.** None of the v18 variants I tested won, so v17 stays.

## Comparing with cuBLAS, and one last optimization that didn't pay off

How does v5's reuse of four sub-blocks within one block differ from Triton's super grouping? The former reuses data already in shared memory within the same block; the latter (grouped program ordering) changes the order in which different output tiles are numbered, so that blocks scheduled close together are more likely to reuse the same slice of A or B in L2. **The committed v17 numbers tiles in row-major order, with no cross-block super grouping.**

**Tile order and the library baseline in the same experiment (ms per call)**

| Scheme | Round 1 | Round 2 |
|---|---|---|
| v17, row-major | 29.76 | 29.34 |
| groups of 4 rows, column order within a group | 29.52 | 29.85 |
| groups of 8 rows, column order within a group | 29.82 | 29.82 |
| cuBLAS SGEMM | 28.93 | 28.98 |

Grouping by 4 rows won one round and lost the other, and 8 rows showed no advantage either. The grouped versions also split the tail zeroing into several calls; these are end-to-end timings, and L2 hit rates can't be inferred from them alone. Only two conclusions can be written down: grouping gives no stable gain on this shape, and comparing the means of these two rounds, v17 takes about 29.55 ms and cuBLAS about 28.96 ms, so the hand-written kernel is about 2% slower.

The library kernel identified by Nsight Systems is `volta_sgemm_128x64_nn`; the median of its 100 kernel executions is 28.90 ms. It uses a 30×60 grid, 128 threads per block, 122 registers per thread and 12,544 bytes of static shared memory per block. The `volta` in its name doesn't change the fact that the hardware is a T4. The trace gives the library's launch configuration; whether that half millisecond comes from tiling, scheduling or memory access can't be told from the name alone.

As an order-of-magnitude check, this multiplication is `2MNK ≈ 84.93 GFLOP`, and 29.48 ms corresponds to about **2.88 TFLOP/s**. Estimating with the 585 MHz commonly seen in sampling, the FP32 peak of 40 SMs is about 3.00 TFLOP/s, which corresponds to about 28.36 ms. But higher clocks were also sampled, so this number only checks the order of magnitude; it is not a hard lower bound measured at a constant clock.

**The version I ended with is v17.** From the corrected 119.06 ms to about 29.5 ms, throughput is about four times the starting point. What actually won back the last few milliseconds was turning eight reads of B into two, letting the last ten tiles also use all the SMs, and recovering the loop unrolling lost after split-K. Eliminating bank conflicts, adding resident blocks and changing the tile order each answered an equally useful question: which changes look better but, on this card, are not worth pursuing further.

## The remaining 0.6 ms: can a smaller tile wait less?

If I go after cuBLAS again, I'll start with the clue it gives: `volta_sgemm_128x64_nn` uses **a small 128×64 tile, with only 4 warps per block**; a v17 block has 16 warps. v17's main loop executes `__syncthreads()` every time it moves to the next K slice. Warps that arrive early must wait for the last warp in the same block, even if only one set of data is still being moved.

My hypothesis is that a small block only has to wait for 4 warps each time; if other blocks are on the same SM, they can also issue instructions during that wait. That way, the waiting exposed by intra-block synchronization might be shorter. But small tiles also reduce data reuse, which is exactly what hurt v18. Nsight Systems confirmed cuBLAS's kernel name and launch configuration; **there is no evidence yet that attributes this 0.6 ms to synchronization**.

To test it, I could build a 128×64, 128-thread version, still with 8×8 outputs per thread, keeping v17's vectorized memory access and double buffering. First compare the main loop on a full-wave grid to rule out the effect of the tail split-K, then go back to the original size and time it interleaved with v17 and cuBLAS. If performance counters are available, also look at the share of cycles in which warps can't issue because they are waiting at a barrier: whether the small tile is faster, and if so whether it is really because of less waiting at barriers, are two questions worth answering separately.

## Records and versions

["CUDA SGEMM Optimization V2"](https://www.douban.com/note/865074422/): the early approach and the subject of this correction; its conclusion of beating cuBLAS by 25% has been retracted.

`ab83049` · `16_asub_swizzle.cu`; `820b002` · `17_float4_b_tail_splitk.cu`. The tables for v17a/b/c, grouping and v18 come from the logs of this round of interleaved runs.

Scope: Tesla T4 (SM 7.5), fixed and evenly divisible matrix sizes, FP32 CUDA cores; all numbers are milliseconds per matrix multiplication.

## References

On matrix multiplication optimization:

<https://www.douban.com/note/849253271>

<https://zhuanlan.zhihu.com/p/478846788>
