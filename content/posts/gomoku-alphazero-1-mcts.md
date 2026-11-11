---
title: "手搓五子棋 AlphaZero (1)：MCTS 框架"
date: 2025-09-15
migrated: 2026-11-11
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/875904332/"
  note: "内容未改动，系列内链接改为站内链接。"
draft: false
series: ["手搓五子棋 AlphaZero"]
tags: ["AlphaZero", "MCTS", "强化学习", "C++"]
summary: "从纯 MCTS 开始：C++ 实现 + pybind11 封装，8×8 棋盘 1000 次 rollout 0.01–0.05s，11×11 上 20 万次 rollout 达到小学低年级水平。"
---

{{< series-nav >}}

相比于 SFT，强化学习是臭名昭著的难训练，很容易出现坍缩，一直想亲手搞个 AlphaZero。
MCTS 是基础，其运行性能（训练时 Agent 直接使用）、AlphaZero 上使用的特殊要点都是关键。
首先我们需要在没有训练的情况，利用 MCTS 达到业余中手甚至高手水平（想想 00 年代棋类 AI 算法由 min-max 搜索转向 MCTS 真是经典），这样才能确保后面模型可训练。

回顾一下 MCTS：

1. 选择（select）→ 扩展（expand）→ 模拟（simulate）→ 反向更新（back propagate）；
2. 选择时 Q+PUCT 做探索利用平衡，纯 MCTS 中 Q 值即平均得分（(1·win_count − 1·lose_count + 0·draw_count) / n_visit），随机仅当多个节点 Q+PUCT 值相同；
3. 扩展时需要注意别把所有子节点也扩展了，代码是简单了，内存要爆了；
4. PUCT = prior_p · UCT，UCT = C · sqrt(parent_visits) / (n_visits + 1)，prior_p 是先验概率，有模型参与时选用策略网络输出，纯 MCTS 中使用常数就可以，C 是个常系数平衡探索利用，UCT 是置信区间上界，实际上经典的 UCT 中 sqrt(parent_visits) 还要取对数，AlphaGo/Zero 中根据经验表现不取对数值；
5. 棋类反向更新比一般强化学习过程更简单，gamma 衰减系数为 0，直接扣减各个祖先节点上的得分即可。

参考 junxiao song 在 GitHub 的实现，做了工程优化。
整个 MCTS 使用 C++ 实现方便做优化，用 pybind11 封装成 Python 模块，使用两个 bitset 保存棋盘状态，用 map 保存扩展节点孩子，然后用 Kimi 随便写了个前端。代码 GitHub 地址：<https://github.com/bryanzhang/gomoku_ai>，git tag 为 v0.1。

C++ 开 O3 优化后，8×8 棋盘 1000 次 rollout 耗时 0.01s 到 0.05 秒，这个速度看起来比 Python 向量化优化后的版本要快至少 20 倍了。扩到 11×11 的棋盘，大体是个小学低年级的水平，rollout 20 万次，搜索耗时 8～15 秒，可以对弈但有时双三没识别出来：

![11×11 纯 MCTS 对弈](/images/gomoku-alphazero/1-1.webp)

（未完待续）

请看下篇：[手搓五子棋 AlphaZero (2)：MCTS 性能优化](/posts/gomoku-alphazero-2-mcts-performance/)
