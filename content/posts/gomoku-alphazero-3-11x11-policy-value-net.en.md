---
title: "Hand-built Gomoku AlphaZero (3): MCTS with an 11×11 Policy-Value Network"
date: 2025-10-27
migrated: 2026-11-11
original:
  platform: Douban
  url: "https://www.douban.com/note/876852240/"
  note: "English translation of the Chinese original."
draft: false
series: ["Gomoku AlphaZero"]
tags: ["AlphaZero", "MCTS", "Reinforcement Learning", "Self-play", "Performance"]
summary: "MCTS with a policy-value network: single-threaded training too slow, multithreaded training unstable, shelved for a year, then bugs fixed, the net scaled to a 64-channel ResNet, and inference made ~10× faster with single-thread OMP and BN folding. 10k simulations now beat 1.5M-simulation pure MCTS; 2 s per move on a 16-core CPU at a strong human level."
---

{{< series-nav >}}

Previously:

- [Hand-built Gomoku AlphaZero (1): The MCTS Framework](/en/posts/gomoku-alphazero-1-mcts/)
- [Hand-built Gomoku AlphaZero (2): MCTS Performance Optimization](/en/posts/gomoku-alphazero-2-mcts-performance/)

Code: <https://github.com/bryanzhang/gomoku_ai>, git tag v0.3. MCTS with a policy-value network plays at an intermediate-to-advanced human level at 2 seconds per move on a 16-core CPU.

Here is how it got there:

**1. Single-threaded self-play training:**

10,000 single-threaded rollouts are extremely fast for pure MCTS, but with a model they mean up to 10,000 model inferences, so single-threaded simulation is very expensive. After 5 hours of training, only 14 games had been simulated and the model updated 14 times.

![Single-threaded training](/images/gomoku-alphazero/3-01.webp)

Multithreading is a must!

**2. Multithreaded self-play training**

With 20 simulation threads and 20,000 rollouts, simulation got 5× faster, but convergence slowed and oscillated more:

![Multithreaded training curve](/images/gomoku-alphazero/3-02.webp)

Training was very unstable: after 24 hours it was still around 4.9.

Going back to single-threaded training, it converged quickly at first and then very slowly, reaching only about 3.8 after 35.5 hours:

![Single-threaded training curve](/images/gomoku-alphazero/3-03.webp)

At one point I wanted to switch to multiple threads running multiple simulators, separating simulation from training, but the project sat on the shelf for a year.

**3. Keep multithreaded rollouts, fix bugs and rerun (2026-08-01):**

Almost a year later, Opus 5.0 quickly found several critical bugs:

![Bugs found](/images/gomoku-alphazero/3-04.webp)

After a quick fix with the LLM's help, 1,500 rounds at 1,000 rollouts each: loss and entropy fell much better than before, and play against humans improved somewhat, but it still wasn't good enough:

![Training curve after the fix](/images/gomoku-alphazero/3-05.webp)

Along the way I tried applying Dirichlet noise at root expansion instead of at selection, and training collapsed outright:

![Collapse after moving the noise](/images/gomoku-alphazero/3-06.webp)

Diversity was the problem again, so I rolled the multithreading code back.

![After the rollback](/images/gomoku-alphazero/3-07.webp)

Running the evaluation script:

![Evaluation](/images/gomoku-alphazero/3-08.webp)

Trying simulation scaling:

![Simulation scaling 1](/images/gomoku-alphazero/3-09.webp)

![Simulation scaling 2](/images/gomoku-alphazero/3-10.webp)

It took 20,000 policy-value simulations to reliably beat 100,000-simulation pure MCTS. It works, but it's still not good enough.

I suspected the model.

**4. 64 channels with residual connections:**

I also enlarged the replay buffer from 10k to 50k, and after 1,500 games the win rate was only 35%.

Suspecting the replay buffer, I shrank it back to 10k:

![Replay buffer back to 10k](/images/gomoku-alphazero/3-11.webp)

Now 1,000 policy-value simulations break even with 500,000-simulation pure MCTS:

![1k simulations vs. 500k pure MCTS](/images/gomoku-alphazero/3-12.webp)

So scaling up the model was right. The goal now was to train for 10,000 games and see whether it kept improving, but both training and play were too slow.

**5. Performance optimization + 10,000 self-play games:**

Following Kimi K3's suggestion: most of the time was in inference, so I switched to single-thread OMP inference and folded BN into the CNN. Nearly 10× faster! 10,000 games took about 20 hours (16 cores, 32 GB). Training curves and evaluation (20 games against 500k-simulation pure MCTS):

![Training and evaluation over 10k games](/images/gomoku-alphazero/3-13.webp)

Overall strength kept rising, but entropy and loss barely changed after about 3,000 games. A round-robin among the four models with win rates above 90% matched the win-ratio curve above:

![Round-robin results](/images/gomoku-alphazero/3-14.webp)

The strongest model, policy_game_9000, with 40,000 simulations went 20–0 against 1.5M-simulation pure MCTS!

Even with only 10,000 simulations it reliably beats 1.5M-simulation pure MCTS:

![10k simulations vs. 1.5M pure MCTS](/images/gomoku-alphazero/3-15.webp)

That's basically beyond ordinary human players. 10,000 simulations take about 2 seconds per move, and in a few games against humans it really does hold up.

Next up: 15×15 Gomoku! (To be continued.)

Next: [Hand-built Gomoku AlphaZero (4): 15×15 Policy-Value Network](/en/posts/gomoku-alphazero-4-15x15-policy-value-net/)
