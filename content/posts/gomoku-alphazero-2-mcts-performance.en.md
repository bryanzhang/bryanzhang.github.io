---
title: "Hand-built Gomoku AlphaZero (2): MCTS Performance Optimization"
date: 2025-09-20
migrated: 2026-11-11
original:
  platform: Douban
  url: "https://www.douban.com/note/876037477/"
  note: "English translation of the Chinese original."
draft: false
series: ["Gomoku AlphaZero"]
tags: ["AlphaZero", "MCTS", "Performance", "Lock-free", "C++"]
summary: "map → vector, lock-free multithreading with hazard pointers and virtual loss, parallel memory reclamation: with 20 threads on 16 cores, search time drops to ~1/7 and move time to under 1/10. 1.5M searches on 11×11 take 20–30 s and play at a solid amateur level."
---

{{< series-nav >}}

Previous: [Hand-built Gomoku AlphaZero (1): The MCTS Framework](/en/posts/gomoku-alphazero-1-mcts/)

Code: <https://github.com/bryanzhang/gomoku_ai>, git tag v0.2.

**1. Store expanded nodes in a vector instead of a map, to enable lock-free multithreading and vectorization and to reduce memory use (and thus allow more rollouts):**

Before:

![Before](/images/gomoku-alphazero/2-1.webp)

After:

![After](/images/gomoku-alphazero/2-2.webp)

**2. Multithreaded parallelization:**

To save memory, concurrency, visits and score are packed into a single 8-byte atomic. Hazard pointers make it lock-free, and virtual loss keeps multiple threads from piling onto the same node. (Note: when implementing hazard pointers I even added a counter to the pointer to avoid the CAS ABA problem, which was probably unnecessary.)

Debugging this took far too long; I even rewrote the web server in C++ just to debug it. With 20 threads on a 16-core machine plus jemalloc, the time drops to about 1/7 of the original:

![Search time after multithreading](/images/gomoku-alphazero/2-3.webp)

But then the time to play a move became the same order of magnitude:

![Move time](/images/gomoku-alphazero/2-4.webp)

Most of that time is memory reclamation, and single-threaded reclamation is too slow.

**3. Parallel memory reclamation:**

Move time drops to under 1/10:

![Move time after parallel reclamation](/images/gomoku-alphazero/2-5.webp)

I didn't vectorize, because memory allocation/deallocation and cache efficiency seemed to be the bigger bottlenecks.

On 11×11 it now plays at a solid amateur level: 1.5M searches take 20–30 s, it easily spots all kinds of double threats, and only fails to win against some clever moves. But this is still pure MCTS: it's slow, and on 15×15 it would certainly be too weak.

![Playing on 11×11](/images/gomoku-alphazero/2-6.webp)

Next step is training a model. The hope is that 2 seconds per move with a model can match what pure MCTS does in 25 seconds, and reach a decent amateur level on 15×15. (To be continued.)

Next: [Hand-built Gomoku AlphaZero (3): MCTS with an 11×11 Policy-Value Network](/en/posts/gomoku-alphazero-3-11x11-policy-value-net/)
