---
title: "Hand-Writing Bitonic Sort on the CPU (Corrected and Re-measured in 2026)"
date: 2024-08-28
migrated: 2026-11-11
original:
  platform: Douban
  url: "https://www.douban.com/note/865510242/"
  note: "English translation of the Chinese original. A correction was added at the top on November 24, 2026."
draft: false
tags: ["SIMD", "Sorting", "Performance", "CPU"]
summary: "Notes from hand-writing a bitonic sort with sorting networks, SSE/AVX and in-register sorting. Corrected in November 2026: the original code never checked its output, so the claim of being 6× faster than std::sort is retracted; after fixing every version and verifying every output, version 8 sorts 8,192 ints about 15× faster than std::sort on a Xeon 6982P-C."
---

> **Correction (November 24, 2026):** the claim in this post that the code is 6× faster than std::sort is retracted. The original code never checked its output. With an element-wise check against std::sort, every version from version 2 (the non-recursive one) onward failed to sort; the later versions were fast because most of the comparisons never ran. The bugs: the merge loop processed only the first block at each level; every version skipped its last few merge levels; versions 7 and 8 skipped several merge stages while building the bitonic sequence; and version 8's 8×8 in-register sorting network and transpose were themselves wrong.
>
> All versions are now fixed, and every sort is checked element-wise against std::sort. Re-measured on an Alibaba Cloud Xeon 6982P-C (AVX-512): versions 1–6 are all slower than std::sort, because two qsort calls take most of the time; version 7 takes 0.0215 ms and version 8 0.0203 ms, about 14–15× faster than std::sort at 0.304 ms. For reference, Intel's x86-simd-sort takes 0.0162 ms with AVX-512. Full data and fixes are on [GitHub](https://github.com/bryanzhang/cpu_bitonicsort).
>
> The original 2024 post follows unchanged, for reference; its timings are no longer valid.

The appeal of bitonic sort is that it is a pure sorting network: its running time is stable, it can be made branch-free with SIMD and CPU shuffle instructions, and it sorts in place with no extra memory. Most parallel sorting algorithms I've read use bitonic sort either entirely or in part, and I'd long wanted to implement one myself.

The in-register sort optimization follows this paper: <https://www.vldb.org/pvldb/vol1/1454171.pdf> (my notes, in Chinese: <https://www.douban.com/note/864782124/>).

Hand-written implementation: <https://github.com/bryanzhang/cpu_bitonicsort>.

It was less complicated than I expected. I didn't even use VTune or perf, and ended up 6× faster than STL sort.

Server: Intel(R) Xeon(R) Platinum 8163 CPU @ 2.50GHz, with AVX2.

**0. Naive bitonic sort vs. the standard C++/C sorts**

This version is only a few lines, copied from the internet.

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

STL is clearly ahead.

**1. O(n log n) bitonic sort**

Reading the code, the baseline is O(n²). But once the initial sequence is bitonic, every subsequent sequence is bitonic too, so it can be rewritten as O(n log n). For convenience I first used two qsort calls to turn the input into a bitonic sequence; performance is already close to qsort:

```
n=8192, average time: 0.836735 ms.
```

Note: most of the time is in the two qsort calls, 0.697014 ms in total, so there's good reason to believe it can beat STL sort.

From here I first optimized the pure bitonic part and left rewriting the qsort part for last (a bug in my code led me to misjudge the timing, so the qsort rewrite was delayed considerably).

**2. Non-recursive implementation**

The pure bitonic part gets 5× faster:

```
n=8192, average time: 0.714325 ms.
```

**3. SIMD**

Using SSE2 (128-bit vectors), another 10×:

```
n=8192, average time: 0.700847 ms.
```

**4. Specializing for n=8192**

Basically no effect, maybe even slightly slower:

```
arr pointer: 0x56089dcf7ee0
n=8192, average time: 0.701218 ms.
```

**5. SIMD8 (AVX, 256-bit vectors)**

40% faster:

```
arr pointer: 0x560081506ee0
n=8192, average time: 0.695701 ms.
```

**6. SIMD16 (AVX2, 512-bit vectorization)**

30% faster:

```
arr pointer: 0x5637e70a6f00
n=8192, average time: 0.695622 ms.
```

I also tried manual loop unrolling. Together with step 4, my impression is that this kind of optimization is not very effective on CPUs and can even backfire.

You'd expect it to increase instruction-level parallelism, but -O3 has probably done that already.

Software prefetching didn't help either. My guess is the array is small enough to sit entirely in cache, so it's pointless here (a very large array would need it). Next I moved on to rewriting the qsort part.

**7. noqsort**

I wrote a make_bitonic function to replace the two qsort calls. make_bitonic works bottom-up and bitonic_sort works top-down. The smallest units in make_bitonic are sorted with the classic in-register sort. Final time:

```
arr pointer: 0x55bbeee09f00
n=8192, average time: 0.0105338 ms.
```

**8. inregister8x8**

Changing the in-register sort from 4×4 to 8×8 cuts total time by another 30%:

```
arr pointer: 0x55a81d56cf00
n=8192, average time: 0.00750863 ms.
```

Even so, I think there is still room. The in-register sort uses AVX (256 bits) to sort 8×8 = 64-element blocks; going to 16×16 (limited by the number of registers) should help. Choosing ascending vs. descending order uses a lot of if-statements, which blend instructions should be able to eliminate. The 1-bit digit computations could also be sped up with lookup tables.
