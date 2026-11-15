---
title: "SGLang vs vLLM：单卡 A100 上的 90 组压测，差距从哪里来"
date: 2026-11-15
draft: false
tags: ["AI Infra", "SGLang", "vLLM", "推理", "性能分析"]
summary: "同一张 A100、同一个模型、同一个压测客户端。并发 32 以内两者相差不到 4%；之后的差距分别来自 SGLang 的 CUDA graph 上限、两边相反的 prefill 调度策略，以及 vLLM 混合批里 attention 对 KV 的重复读取。附 nsys profile 和对照实验。"
math: true
ShowToc: true
---

数据、脚本和完整分析：<https://github.com/bryanzhang/inference-bench>

## 结论先行

1. **并发 32 以内，两个引擎相差不到 4%。** batch 1 时 decode 都达到显存带宽理论上限的 73–76%。
2. **短输入、并发 ≥ 64 时 vLLM 快 33–49%**，原因是 SGLang 默认的 decode CUDA graph 只覆盖到 batch 32。超过之后每步多出约 10 ms 的 CPU 发射开销；输入越长，GPU 每步的活越重，这部分开销越容易被掩盖。
3. **长输入时 SGLang 快 8–36%。** 两边都开了 chunked prefill，但调度策略相反：SGLang 默认 prefill 优先、不混批；vLLM 默认 decode 优先、每步混入一块 prefill。
4. **vLLM 的混合步慢在 attention**：nsys 显示，混合批里 attention kernel 没有按 GQA 分组，对每个 decode 请求的 KV 读了约 7 遍。每个混合步因此多花约 50 ms，正好解释了长输入下的吞吐差距。调大 prefill 预算能把差距从 19% 缩小到 4%，代价是 TBT 尖峰变大。
5. **两个测量陷阱**：这个压测客户端的 ITL 在两个后端之间口径不同，跨引擎只能比 TPOT；直接平均 SGLang 日志里的 `gen throughput` 最多高估 3.5 倍。

## 1. 实验设置

| 项目 | 值 |
|---|---|
| GPU | NVIDIA A100-PCIE-40GB（1555 GB/s，BF16 312 TFLOPS，250 W），矩池云单卡 |
| 模型 | Qwen2.5-7B-Instruct，BF16 |
| SGLang | 0.5.24.dev1289（commit `977e769b`），FlashInfer attention |
| vLLM | 0.33.0（V1 engine），FlashAttention 2 attention |
| 负载 | 输入 128 / 1024 / 4096，输出固定 256，并发 1 / 8 / 32 / 64 / 128 |
| 客户端 | 两个引擎都用 `python -m sglang.benchmark.serving`，`random` 数据集（ShareGPT 文本），长度固定，ignore_eos |
| 重复 | 每组 3 次取中位数，共 90 次 |

几点说明：

- **只改两个参数**：显存比例统一设为 0.85，并关闭前缀缓存（随机 prompt 之间没有共享前缀）。其余全部用默认值，因为默认值本身就是要比较的对象。
- **闭环压测**：客户端始终保持固定数量的请求在跑，一条结束立刻补发下一条。请求数为 8 × 并发，最少 32 条。
- **数据有效**：90 次运行全部完成，每条请求的输入、输出长度都和设定一致。同一配置 3 次之间，吞吐的变异系数最大 1.64%，30 组配置里有 26 组不超过 0.1%。每个引擎扫描前后各跑一次固定的哨兵配置，前后相差 +0.1% 和 −0.2%，说明机器状态稳定。

## 2. 总体结果

输出吞吐（tokens/s），格式为"SGLang / vLLM"，括号里是 vLLM 相对 SGLang 的差异：

| 输入 \ 并发 | 1 | 8 | 32 | 64 | 128 |
|---|---|---|---|---|---|
| 128 | 83 / 80（−3.5%） | 640 / 630（−1.7%） | 2227 / 2183（−2.0%） | 2432 / 3622（**+49%**） | 4312 / 5720（**+33%**） |
| 1024 | 81 / 78（−3.8%） | 541 / 534（−1.2%） | 1361 / 1346（−1.1%） | 1530 / 1712（+12%） | 2111 / 1926（−8.8%） |
| 4096 | 75 / 72（−3.3%） | 347 / 346（−0.3%） | 566 / 524（−7.3%） | 619 / 500（**−19%**） | 637 / 469（**−26%**） |

![输出吞吐随并发的变化](/images/sglang-vs-vllm/throughput_vs_concurrency.png)

并发 32 以内，两边几乎一样。之后分成两种情况：短输入 vLLM 明显更快，长输入 SGLang 更快。下面分别解释。

## 3. 短输入的断崖：SGLang 的 decode CUDA graph 只覆盖到 batch 32

输入 128 时，SGLang 从并发 32 到 64，吞吐只涨了 9%（2227 → 2432），vLLM 则涨了 66%（2183 → 3622）。SGLang 的 TPOT 从 13.5 ms 跳到 24.5 ms。

SGLang 的服务端日志里，每个 decode 批次都标注了是否用了 CUDA graph：

- 并发 32 时，100% 的 decode 批次用了 CUDA graph；
- 并发 64 时，只有 1.9%。

这次 SGLang 默认录制的 decode CUDA graph 尺寸是 batch 1、2、4、8、12、16、24、32。batch 超过 32 后，每一步都要由 CPU 逐个发射几百个 kernel。vLLM 录到了 512，所以没有这个断崖。

**为什么只有短输入受影响？** 不用 CUDA graph 时，一步的耗时约等于"CPU 发射所有 kernel 的时间"和"GPU 计算时间"中较长的那个。从日志里能算出 SGLang 纯 decode 一步的耗时（方法见第 4 节）：

| SGLang 纯 decode 一步 | c32（有 CUDA graph） | c64（无） | c128（无） | vLLM c64（作参照） |
|---|---|---|---|---|
| 输入 128 | 13.2 ms | **24.0 ms** | **25.0 ms** | 15.4 ms |
| 输入 1024 | 14.4 ms | **23.8 ms** | **24.4 ms** | 18.6 ms |
| 输入 4096 | 18.5 ms | 27.2 ms | 30.0 ms | 29.9 ms |

- 没有 CUDA graph 时，输入 128 和 1024 下每步都固定在约 24 ms，和 batch 大小、上下文长度几乎无关。这正是"被 CPU 卡住"的特征：GPU 本身只需要 14–20 ms。
- 输入 4096 时，每步要读 15–19 GB 的 KV cache，GPU 本身就要 25 ms 以上，CPU 的开销被掩盖了。
- 另外，输入越长，prefill 在总工作量里的占比越大，decode 上的劣势也越不重要（第 5 节）。

这个结论有日志和数据规律两方面的证据，但还没有用 `--cuda-graph-max-bs 128` 做对照实验直接验证。

## 4. decode 效率：离带宽上限有多远

decode 每一步至少要把权重和所有正在运行请求的 KV 从显存读一遍：

$$
t_{\text{step}} \ge \frac{14.1\ \text{GB} + B \times L \times 56\ \text{KB}}{1.555\ \text{TB/s}}
$$

其中 $B$ 是 batch 大小，$L$ 是平均上下文长度。权重 14.1 GB 不含输入 embedding 表，因为它只按 token 查表，不需要整张读。Qwen2.5-7B 每个 token 的 KV 是 28 层 × 2 × 4 个 KV head × 128 维 × 2 字节 = 56 KB。

注意 KV 这一项：它是每个请求各自的数据，不能在 batch 内共享，所以输入长了以后，下限会随 batch 线性上升。输入 4096 时，每个请求的 KV 约 242 MB，58 个请求的 KV 就和整份权重一样大。

| 场景 | 理论下限 | 实测 | 达到下限的比例 |
|---|---|---|---|
| batch 1（输入 128） | 9.08 ms | SGLang 12.0 ms / vLLM 12.4 ms | 76% / 73% |
| SGLang，输入 4096，c32 | 14.1 ms | 18.5 ms | 76% |
| SGLang，输入 4096，c64 | 19.0 ms | 27.2 ms | 70% |
| SGLang，输入 4096，c128（实际 batch 81） | 21.7 ms | 30.0 ms | 72% |

带宽规格值 1555 GB/s 本身是跑不满的，一般来说即使是纯粹的读写测试，也只能达到 85–90%。所以 70–76% 已经接近实际可达上限。

**纯 decode 一步的耗时是怎么测的**：SGLang 每 40 个 decode 步打一行日志，包含当前的请求数和生成吞吐。我只挑两行之间没有夹 prefill 的区间，用"请求数 ÷ 生成吞吐"算出每步耗时。另一个更简单的近似是看 ITL 的中位数：输入 4096、c64 时，SGLang 的 ITL 中位数是 27.0 ms，和日志算出的 27.2 ms 几乎一样。

**为什么不能拿 TPOT 和这个下限比**：TPOT 是一个请求在第一个 token 之后的平均每 token 耗时，它包含了等其他请求做 prefill 的时间。输入 4096、c64 时，SGLang 的 TPOT 是 64.7 ms，但纯 decode 一步只要 27.2 ms，多出来的部分全是等待 prefill。

## 5. 长输入：两边都是 chunked prefill，调度策略却相反

"chunked prefill"只说明长 prompt 可以拆成几块、分几步算完。真正决定行为的是另外三件事：

| | SGLang（默认） | vLLM（默认） |
|---|---|---|
| 一步里能否同时算 prefill 和 decode | 不能（`enable_mixed_chunk=False`） | 能，每一步 = 所有 decode + 一块 prefill |
| 谁优先 | prefill 优先：能组出 prefill 批次就先跑它，decode 暂停 | decode 优先：先给每个 decode 请求分 1 个 token，剩下的预算给 prefill |
| 每步 prefill 多少 token | 最多 4096（`chunked_prefill_size`） | 2048 减去 decode 请求数（`max_num_batched_tokens`） |

SGLang 这一行，我核对了 `scheduler.py` 里的 `get_next_batch_to_run`，代码注释原文是 "Run prefill first if possible"。

以输入 4096、并发 64 的一个波次为例：

```
SGLang:  [P1][P2]……[P64]                       [D][D]……共 256 步
          每个约 0.31 s，共约 20 s，decode 全停      每步约 27 ms，共约 7 s

vLLM:    [64×D + P1 前半][64×D + P1 后半][64×D + P2 前半]……  中间夹着纯 decode 步 [D]
          带 prefill 的步约 220 ms                            纯 decode 步约 29 ms
```

带来的结果：

- **decode 是被暂停，还是每步变慢**：SGLang 里，一个请求出完第一个 token 后，平均要等约 10 秒，让其他请求做完 prefill。但这种长间隔每个请求只有一次，只占全部间隔的 0.4%，连 ITL p99（32.7 ms）都看不出来。vLLM 里 decode 从不暂停，但带 prefill 的那一步要 220 ms，ITL p99 是 228 ms。
- **吞吐**：长输入时 SGLang 更高，原因见第 6 节。
- **TTFT**：差距比实际情况被放大了，下面单独说明。

![TTFT 随并发的变化，实线 p50，虚线 p99](/images/sglang-vs-vllm/ttft_vs_concurrency.png)

| 输入 4096 | SGLang p50 | vLLM p50 | SGLang p99 | vLLM p99 |
|---|---|---|---|---|
| c32 | 5.04 s | 0.92 s | 9.75 s | 10.04 s |
| c64 | 9.92 s | 1.12 s | 19.49 s | 22.06 s |

只看中位数，vLLM 的 TTFT 低 5–9 倍。但这个差距很大一部分来自**闭环、长度固定**的压测方式：

- **SGLang 会形成同步的波次**：一批请求的 prefill 全部做完才开始 decode，于是同一步开始 decode。输出长度又固定，所以也在同一步结束。下一批 64 条请求因此同时到达，又要排队等彼此的 prefill。
- **vLLM 会自然错开**：decode 一直在跑，新请求一个接一个被接纳，开始和结束的时间都是错开的。补发的新请求也是零散到达的，每条只需要等自己那 2–3 步。
- **证据**：客户端按秒统计的峰值并发。SGLang 在 c32 和 c64 时分别是 64 和 128，正好是并发数的两倍，说明换批的那一秒里，旧的一批全部结束、新的一批全部开始；vLLM 只有 36 和 67。
- **p99 两边几乎一样**，约等于"并发数 × 单个请求的 prefill 时间（0.31 s）"。它由每次运行开头的第一个波次决定：那一刻两个引擎都要面对 C 条请求同时到达。

如果是真实流量（请求随机到达、长度不一），SGLang 的波次形成不了。按 prefill 优先的策略，新请求会马上做 prefill，TTFT 应该不比 vLLM 差。**代价是每来一条请求，所有正在 decode 的请求都要暂停约 0.3 秒。这一点这次没有测。**

## 6. vLLM 的混合步慢在哪：nsys profile

输入 4096、c64 时，vLLM 每个请求占用的 GPU 时间（256 ÷ 吞吐）是 0.512 秒，SGLang 是 0.413 秒。但 vLLM 的纯 decode 步并不慢：同一配置下，ITL 中位数 vLLM 是 29.9 ms，SGLang 是 27.0 ms。ITL 中位数基本落在纯 decode 步上，可以近似看作纯 decode 一步的耗时（第 4 节）。所以多出来的时间在混合步里。

我用 nsys 录了 vLLM 在这个配置下连续 80 步的 kernel，其中 50 个混合步、30 个纯 decode 步（各项取中位数）：

| | 每步总耗时 | attention | 矩阵乘 | 其他 | attention 的线程块网格 |
|---|---|---|---|---|---|
| 混合步（约 62 个 decode + 1 块约 2000 token 的 prefill） | 220.5 ms | **75.7 ms** | 135.0 ms | 9.0 ms | (13–32, 62–64, **28**) |
| 纯 decode 步（64 个 decode） | 28.8 ms | **14.4 ms** | 12.9 ms | 1.4 ms | (1, 64, **4**) |

关键在网格的第三维：

- **纯 decode 步是 4**：Qwen2.5-7B 的 28 个 query head 共用 4 个 KV head。kernel 按 KV head 分组，一组线程块同时算共用同一份 KV 的 7 个 query head，所以每份 KV 只读一次。从网格看，FlashAttention 2 只在整批 query 长度都为 1 时才启用这个优化。
- **混合步是 28**：批里有 prefill，这个优化关闭，每个 query head 单独开线程块，同一份 KV 被读约 7 遍。

算一笔账：

- 混合步里 prefill 部分的 attention，按计算量估约 10 ms，那么 decode 部分约 65 ms，是纯 decode 步的 4.5 倍。
- 64 个请求的 KV 约 15.5 GB，读 7 遍约 108 GB，按 A100 的带宽需要约 70 ms，和 65 ms 对得上。
- 旁证：不同混合步里 prefill 那块的工作量相差约 3 倍，但 attention 耗时一直稳定在 75–77 ms，说明主要耗时不在 prefill 部分。
- 每个请求要经过约 2 个混合步，每步多出约 50 ms，合计约 0.1 秒，正好等于 vLLM 比 SGLang 多花的 GPU 时间。

顺带排除两个猜测：混合步里 GPU 有 99.6% 的时间在执行 kernel，几乎没有空档，所以"混合步超过 512 token、用不上 CUDA graph"不影响这次的结果；矩阵乘 135 ms 算约 2048 个 token，约合 214 TFLOPS（峰值的 69%），属于正常水平。

**对照实验 1：调大 prefill 预算。** 如果损耗是"每个混合步都要以低效方式算一遍所有 decode 请求"，那么减少混合步的数量，差距就应该成比例缩小：

| vLLM `--max-num-batched-tokens` | c32 吞吐 | c64 吞吐 | c64 每个请求比 SGLang 多花的 GPU 时间 | 每个请求经过的混合步 | c64 TTFT p50 | c64 ITL p99 |
|---|---|---|---|---|---|---|
| 2048（默认） | 524 | 500 | +0.099 s | 约 2 个 | 1.12 s | 228 ms |
| 4096 | 547 | 559 | +0.045 s | 约 1 个 | 1.47 s | 371 ms |
| 8192 | 564 | 593 | +0.019 s | 约 0.5 个 | 2.39 s | 655 ms |
| SGLang（参照） | 566 | 619 | — | — | 9.92 s | 33 ms |

多花的时间和混合步的数量成正比，平均每个混合步约 45 ms，和 profile 测到的 attention 额外开销吻合。代价是带 prefill 的那一步变长：ITL p99 从 228 ms 涨到 655 ms，TTFT 中位数翻倍。默认配置下复测一次，吞吐 500.6，和原来的 499.9 一致。

**下一步可以验证的：把混合批拆成 decode 和 prefill 两次调用。** vLLM 的 FlashInfer 后端就是这么做的（`split_decodes_and_prefills`）：先把批重新排序，decode 部分用 decode kernel，prefill 部分用 prefill kernel。按上面的分析，用 `--attention-backend FLASHINFER` 在默认预算下重跑，吞吐应该接近 SGLang。这组对照实验还没有结果，补测后更新本文。

即使拆开，也解决不了所有问题：混合步里的 decode 请求仍要陪着 2000 个 token 的矩阵乘走完这一步（约 135 ms），TBT 尖峰依然存在；两个 kernel 先后执行，一个卡带宽、一个卡算力，资源没有重叠。要进一步改善，要么让 prefill 和 decode 在同一个 kernel 里并发（如 POD-Attention），要么做 PD 分离。

## 7. 两个测量陷阱

**ITL 和 TPOT。** 对单个请求来说，TPOT 就是它所有 ITL 的平均值。区别在于统计方式：TPOT 是每个请求一个样本；ITL 是把所有请求的所有间隔放在一起统计。前者反映整体生成速度，后者反映流式输出是否卡顿。

这次用的客户端还有一个坑：`--backend sglang` 会把一个推送块的间隔按 token 数均分，`--backend vllm` 则每个推送块只记一次。一个块里有多个 token 时，vLLM 的 ITL 样本会偏大、偏少。所以**跨引擎只比 TPOT**，ITL 只在同一个引擎内部看。

**SGLang 日志里的吞吐（[sgl-project/sglang#3050](https://github.com/sgl-project/sglang/issues/3050)）。** 日志每 40 个 decode 步打一行 `gen throughput`。直接对各行取平均，最多会高估 3.5 倍（输入 4096、c128：2243 vs 637 tok/s）。原因是每行对应固定的步数，而不是固定的时长：夹着 prefill 的那一段可能长达 21 秒，但它和 1 秒的纯 decode 段一样只算一行。按时间加权（总 token 数 ÷ 总时长）后，15 组配置和客户端吞吐之比都在 0.92–0.99 之间。

## 8. 局限

- 只测了一张 GPU、一个模型、一种输出长度；prompt 是随机文本，没有共享前缀。
- 闭环压测加固定长度，会让请求按波次同步到达（第 5 节）。更接近线上的做法，是按泊松分布随机发送、长度不固定，再看满足 SLO 时的吞吐。
- CUDA graph 的解释（第 3 节）没有做对照实验；vLLM 纯 decode 步的耗时是用 ITL 中位数估算的。
- SGLang 没有编译 Rust 扩展（用的是 Python 回退实现），前缀缓存也关闭了，预计影响很小。

## 复现

所有原始数据、服务端日志、nsys 报告和脚本都在 <https://github.com/bryanzhang/inference-bench>。版本：SGLang `977e769b`、vLLM 0.33.0、PyTorch 2.14（CUDA 13.0）、驱动 610.57.04。
