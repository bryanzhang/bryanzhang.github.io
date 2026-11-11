---
title: "Optimizing Bitonic Sort on the CPU: 6× Faster than std::sort"
date: 2024-08-28
migrated: 2026-11-11
original:
  platform: Douban
  url: "https://www.douban.com/note/865510242/"
  note: "English translation of the Chinese original."
draft: false
tags: ["SIMD", "Sorting", "Performance", "CPU"]
summary: "A hand-written bitonic sort with sorting networks, SSE/AVX and in-register sort: n=8192 goes from 158 ms to 0.0075 ms, 6× faster than std::sort."
---

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
