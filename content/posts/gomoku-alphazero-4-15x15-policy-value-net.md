---
title: "手搓五子棋 AlphaZero (4)：15×15 策略值网络"
date: 2026-08-13
migrated: 2026-11-11
original:
  platform: 豆瓣话题
  url: "https://www.douban.com/topic/496923907/"
  note: "内容未改动，系列内链接改为站内链接。"
draft: false
series: ["手搓五子棋 AlphaZero"]
tags: ["AlphaZero", "MCTS", "强化学习", "自对弈", "ResNet"]
summary: "扩到 15×15：网络和 playout 不变时 20 战全胜纯 MCTS 却不堪一击；改为 6 block ResNet、playout 2000，训练 65 小时后人类已经很难赢棋。"
---

{{< series-nav >}}

前情回顾：

- [手搓五子棋 AlphaZero (1)：MCTS 框架](/posts/gomoku-alphazero-1-mcts/)
- [手搓五子棋 AlphaZero (2)：MCTS 性能优化](/posts/gomoku-alphazero-2-mcts-performance/)
- [手搓五子棋 AlphaZero (3)：11×11 策略值网络模型的 MCTS](/posts/gomoku-alphazero-3-11x11-policy-value-net/)

GitHub 地址：<https://github.com/bryanzhang/gomoku_ai>

**1. 扩展到 15×15，网络和 playout 次数均不变**

1 万局跑了超过 24 小时，对手盘是 50 万次 model-free MCTS：

![15×15 训练曲线](/images/gomoku-alphazero/4-01.webp)

选取表现良好的 5 个快照，捉对厮杀：

![5 个快照对战 1](/images/gomoku-alphazero/4-02.webp)

![5 个快照对战 2](/images/gomoku-alphazero/4-03.webp)

9000 是最优模型。来和 150 万次纯 MCTS 做个对战：

![vs 150 万次纯 MCTS 1](/images/gomoku-alphazero/4-04.webp)

![vs 150 万次纯 MCTS 2](/images/gomoku-alphazero/4-05.webp)

20 战全胜，但实际棋力不堪一击！

**2. 改为 6 个 block 的 ResNet，playout 扩到 2000：**

![ResNet 版本训练](/images/gomoku-alphazero/4-06.webp)

评估对手盘是之前版本的 1 万次 simulation。一万局大概训练了 65 个小时，基本也只做到和对手盘打平：

![ResNet 版本评估曲线](/images/gomoku-alphazero/4-07.webp)

选最厉害的 5 个模型举行联赛：

![联赛结果 1](/images/gomoku-alphazero/4-08.webp)

![联赛结果 2](/images/gomoku-alphazero/4-09.webp)

这个版本人类已经很难赢棋了：

![人机对弈 1](/images/gomoku-alphazero/4-10.webp)

![人机对弈 2](/images/gomoku-alphazero/4-11.webp)
