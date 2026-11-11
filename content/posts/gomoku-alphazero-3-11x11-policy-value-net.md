---
title: "手搓五子棋 AlphaZero (3)：11×11 策略值网络模型的 MCTS"
date: 2025-10-27
migrated: 2026-11-11
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/876852240/"
  note: "内容未改动，系列内链接改为站内链接。"
draft: false
series: ["手搓五子棋 AlphaZero"]
tags: ["AlphaZero", "MCTS", "强化学习", "自对弈", "性能优化"]
summary: "带策略值网络的 MCTS：单线程训练太慢、多线程不稳定、搁置一年后修 bug 重跑、扩到 64 通道 ResNet、单 OMP 线程推理 + fold BN 提速近 10 倍。最终 1 万次模拟稳压 150 万次纯 MCTS，16 核 CPU 2 秒一步达到中高级人类水平。"
---

{{< series-nav >}}

前情回顾：

- [手搓五子棋 AlphaZero (1)：MCTS 框架](/posts/gomoku-alphazero-1-mcts/)
- [手搓五子棋 AlphaZero (2)：MCTS 性能优化](/posts/gomoku-alphazero-2-mcts-performance/)

代码 GitHub 地址：<https://github.com/bryanzhang/gomoku_ai>，git tag 为 v0.3。带策略值网络模型的 MCTS，在 16 核 CPU 上可以 2 秒一步地走出中高级人类水平的棋力。

以下为开发调优历程：

**1. 单线程的模拟训练：**

单线程 10000 次的 rollout，对于单纯的 MCTS 是极快的，但对于带模型的 MCTS 意味着最多需要 10000 次的模型推理，单线程模拟耗时极高。模型训练 5 个小时，仅仅完成 14 次棋局模拟，14 次模型更新。

![单线程训练](/images/gomoku-alphazero/3-01.webp)

必须使用多线程！

**2. 多线程的模拟训练**

使用 20 个线程做模拟，rollout 次数提高到两万，模拟速度提升到 5 倍，但收敛速度有所降低，震荡更多：

![多线程训练曲线](/images/gomoku-alphazero/3-02.webp)

但训练非常不稳定，过了 24 小时仍在 4.9 左右。

改回单线程训练，发现初期收敛快，后面收敛很慢，过了 35.5 小时只收敛到 3.8 左右：

![单线程训练曲线](/images/gomoku-alphazero/3-03.webp)

一度想改为使用多个线程多个模拟器，模拟与训练分离方式进行，但搁置一年。

**3. 保留多线程 rollout，修复 bug 再跑（2026.08.01）：**

时隔近一年，用 Opus 5.0 很快发现几个 critical bug：

![发现的 bug](/images/gomoku-alphazero/3-04.webp)

用大模型快速做下修复，1500 轮、每轮改为 1000 的 rollout，loss 和 entropy 下降比之前好很多，从和人对弈情况看有一定改善但还不行：

![修复后训练曲线](/images/gomoku-alphazero/3-05.webp)

中间尝试把 Dirichlet 噪声放在根结点的扩展而不是选择，发现直接坍塌了：

![噪声位置改动后坍塌](/images/gomoku-alphazero/3-06.webp)

还是在多样性上出问题了，再回滚代码多线程。

![回滚后](/images/gomoku-alphazero/3-07.webp)

跑下评测脚本：

![评测结果](/images/gomoku-alphazero/3-08.webp)

尝试 sim-scaling：

![sim-scaling 1](/images/gomoku-alphazero/3-09.webp)

![sim-scaling 2](/images/gomoku-alphazero/3-10.webp)

2 万次的策略值网络模拟才稳压 10 万次的纯 MCTS！确实有效，但仍然不够理想！

考虑是模型的原因。

**4. 改为 64 个通道、残差连接：**

同时把经验回放池由 1 万放大到 5 万，发现 1500 局后的对战胜率只有 35%。

怀疑是经验回放池的问题。再次把经验回放池缩回 1 万：

![回放池缩回 1 万](/images/gomoku-alphazero/3-11.webp)

现在 1000 次策略值网络模拟就能和 50 万次纯 MCTS 打平：

![1000 次模拟 vs 50 万次纯 MCTS](/images/gomoku-alphazero/3-12.webp)

说明模型扩容是对的，现在希望训练 1 万局，看效果能否持续改善。但训练和对弈都太慢了。

**5. 性能优化 + 自对弈 1 万局：**

参考 Kimi K3 的建议：大部分耗时在推理上，改为单 OMP 线程推理 + CNN fold 掉 BN。速度快了近 10 倍！大约 20 小时训练完 1 万局（16 核 32G 机器），训练曲线和 eval 情况（和 50 万 sim 的纯 MCTS 对战 20 局评估胜率）：

![1 万局训练曲线与评估](/images/gomoku-alphazero/3-13.webp)

总体上棋力是越来越高了，但 entropy 和 loss 基本在 3000 局之后没有变化了。现在再挑选胜率在 90% 以上的四个模型进行循环赛，结果和上面的 win ratio 曲线基本一致：

![循环赛结果](/images/gomoku-alphazero/3-14.webp)

再拿这个最强的 policy_game_9000 模型模拟 4 万次和 150 万次模拟的纯 MCTS 对战，发现 20 战全胜！

即使只用 1 万次模拟也能稳压 150 万的纯 MCTS：

![1 万次模拟 vs 150 万次纯 MCTS](/images/gomoku-alphazero/3-15.webp)

基本是普通人类无法战胜的了，1 万次模拟 1 步只要大约 2 秒。实际和人类下几盘，水平也确实可以了。

下一步是 15×15 的五子棋了！（待续）

下一篇：[手搓五子棋 AlphaZero (4)：15×15 策略值网络](/posts/gomoku-alphazero-4-15x15-policy-value-net/)
