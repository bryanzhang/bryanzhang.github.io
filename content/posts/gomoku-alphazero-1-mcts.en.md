---
title: "Hand-built Gomoku AlphaZero (1): The MCTS Framework"
date: 2025-09-15
migrated: 2026-11-11
original:
  platform: Douban
  url: "https://www.douban.com/note/875904332/"
  note: "English translation of the Chinese original."
draft: false
series: ["Gomoku AlphaZero"]
tags: ["AlphaZero", "MCTS", "Reinforcement Learning", "C++"]
summary: "Starting from pure MCTS: a C++ implementation wrapped with pybind11. 1,000 rollouts on 8×8 take 0.01–0.05 s; on 11×11, 200k rollouts play at a beginner level."
---

{{< series-nav >}}

Compared with SFT, reinforcement learning is notoriously hard to train and prone to collapse. I'd long wanted to build an AlphaZero by hand.
MCTS is the foundation. Its runtime performance (the agent uses it directly during training) and the AlphaZero-specific details are what matter.
First, without any training, MCTS alone should reach a decent amateur or even strong amateur level (it's a classic moment when game AI moved from minimax search to MCTS in the 2000s). Only then can we be sure the model will be trainable later.

A quick recap of MCTS:

1. Select → expand → simulate → back-propagate.
2. Selection balances exploration and exploitation with Q + PUCT. In pure MCTS, Q is the average score ((1·win_count − 1·lose_count + 0·draw_count) / n_visit); randomness only breaks ties when several nodes have the same Q + PUCT.
3. When expanding, don't expand all children's children too. The code gets simpler, but memory explodes.
4. PUCT = prior_p · UCT, UCT = C · sqrt(parent_visits) / (n_visits + 1). prior_p is the prior probability: the policy network output when a model is involved, a constant in pure MCTS. C is a constant balancing exploration and exploitation. UCT is an upper confidence bound; classic UCT takes the log inside sqrt(parent_visits), but AlphaGo/Zero drop the log based on empirical results.
5. Back-propagation for board games is simpler than in general RL: there is no gamma decay, you simply add or subtract the score on every ancestor node.

I based this on junxiao song's implementation on GitHub and did engineering optimizations.
The whole MCTS is in C++ for ease of optimization, wrapped as a Python module with pybind11. The board state is stored in two bitsets, expanded children in a map, and I had Kimi throw together a frontend. Code: <https://github.com/bryanzhang/gomoku_ai>, git tag v0.1.

With C++ and -O3, 1,000 rollouts on an 8×8 board take 0.01–0.05 s, at least 20× faster than a vectorized Python version. On an 11×11 board it plays roughly at the level of a young beginner: 200k rollouts take 8–15 s per move; it can play a game but sometimes misses double-threes:

![Pure MCTS on 11×11](/images/gomoku-alphazero/1-1.webp)

(To be continued.)

Next: [Hand-built Gomoku AlphaZero (2): MCTS Performance Optimization](/en/posts/gomoku-alphazero-2-mcts-performance/)
