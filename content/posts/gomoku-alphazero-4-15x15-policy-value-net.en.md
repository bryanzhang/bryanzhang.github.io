---
title: "Hand-built Gomoku AlphaZero (4): 15×15 Policy-Value Network"
date: 2026-08-13
migrated: 2026-11-11
original:
  platform: Douban
  url: "https://www.douban.com/topic/496923907/"
  note: "English translation of the Chinese original."
draft: false
series: ["Gomoku AlphaZero"]
tags: ["AlphaZero", "MCTS", "Reinforcement Learning", "Self-play", "ResNet"]
summary: "Scaling to 15×15: with the same network and playouts it went 20–0 against pure MCTS yet was easy for humans to beat; a 6-block ResNet with 2,000 playouts, trained for 65 hours, is now hard for humans to beat."
---

{{< series-nav >}}

Previously:

- [Hand-built Gomoku AlphaZero (1): The MCTS Framework](/en/posts/gomoku-alphazero-1-mcts/)
- [Hand-built Gomoku AlphaZero (2): MCTS Performance Optimization](/en/posts/gomoku-alphazero-2-mcts-performance/)
- [Hand-built Gomoku AlphaZero (3): MCTS with an 11×11 Policy-Value Network](/en/posts/gomoku-alphazero-3-11x11-policy-value-net/)

GitHub: <https://github.com/bryanzhang/gomoku_ai>

**1. Scale to 15×15 with the same network and playout count**

10,000 games took over 24 hours; the evaluation opponent was 500k-simulation model-free MCTS:

![15×15 training curve](/images/gomoku-alphazero/4-01.webp)

Five well-performing snapshots played each other:

![Snapshot matches 1](/images/gomoku-alphazero/4-02.webp)

![Snapshot matches 2](/images/gomoku-alphazero/4-03.webp)

9000 was the best. Against 1.5M-simulation pure MCTS:

![vs. 1.5M pure MCTS 1](/images/gomoku-alphazero/4-04.webp)

![vs. 1.5M pure MCTS 2](/images/gomoku-alphazero/4-05.webp)

20–0, yet in actual play it was easy to beat!

**2. A 6-block ResNet, playouts raised to 2,000:**

![ResNet training](/images/gomoku-alphazero/4-06.webp)

The evaluation opponent was the previous version at 10,000 simulations. 10,000 games took about 65 hours to train, and it only got to roughly break even with that opponent:

![ResNet evaluation curve](/images/gomoku-alphazero/4-07.webp)

A league among the five strongest models:

![League results 1](/images/gomoku-alphazero/4-08.webp)

![League results 2](/images/gomoku-alphazero/4-09.webp)

This version is already hard for humans to beat:

![Human vs. AI 1](/images/gomoku-alphazero/4-10.webp)

![Human vs. AI 2](/images/gomoku-alphazero/4-11.webp)
