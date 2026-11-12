---
title: "SGLang vs vLLM：Qwen2.5-7B 在 H800 上的吞吐与延迟对比"
date: 2026-11-20
draft: true
tags: ["AI Infra", "SGLang", "vLLM", "推理"]
summary: "同一张 H800、同一个模型、同一组请求，SGLang 与 vLLM V1 在 batch × 输入长度扫描下的吞吐、TTFT、TPOT 对比，以及拐点出现的原因。"
math: true
---

> 草稿模板。所有数字跑完替换；没有数字的段落不发。

## 背景

想回答三个问题：

1. 同配置下两个引擎的吞吐和延迟差多少，差在哪一段。
2. decode 从 memory-bound 转为 compute-bound 的拐点 batch 是多少，和 roofline 估算是否一致。
3. `bench_serving` 报告的 decode 吞吐和 engine 日志里的数字为什么不一致。

## 环境

| 项目 | 值 |
|---|---|
| GPU | H800 80GB × 1 |
| 模型 | Qwen2.5-7B-Instruct，BF16 |
| SGLang | vX.Y.Z（commit `xxxxxxx`） |
| vLLM | vX.Y.Z（V1 engine） |
| 数据集 | ShareGPT 抽样 + 固定长度合成 |

## 命令

```bash
# SGLang
python -m sglang.launch_server --model-path Qwen/Qwen2.5-7B-Instruct --port 30000
python -m sglang.benchmark.serving --backend sglang --port 30000 \
  --dataset-name random --random-input-len 1024 --random-output-len 256 \
  --num-prompts 256 --max-concurrency 32

# vLLM
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000
python benchmarks/benchmark_serving.py --backend vllm --port 8000 \
  --dataset-name random --random-input-len 1024 --random-output-len 256 \
  --num-prompts 256 --max-concurrency 32
```

## Roofline 估算

H800：HBM 带宽约 3.35 TB/s，BF16 稠密算力约 990 TFLOPS。7B 模型权重 $\approx 15\,\text{GB}$。

单 token decode 在 batch=1 时每 step 至少读一遍权重：

$$
t_{\text{step}} \ge \frac{15\,\text{GB}}{3.35\,\text{TB/s}} \approx 4.5\,\text{ms}
\quad\Rightarrow\quad
\text{上限} \approx 220\ \text{tokens/s}
$$

每 token 计算量约 $2 \times 7\text{B} = 14\,\text{GFLOP}$，算力与带宽的平衡点：

$$
B^{*} \approx \frac{990\,\text{TFLOPS}}{3.35\,\text{TB/s}} \times \frac{15\,\text{GB}}{14\,\text{GFLOP}} \approx 300
$$

即 batch 300 左右之前 decode 都是 memory-bound，实测拐点应早于此（KV cache 读取、attention 开销、调度开销）。

## 结果

### 吞吐 vs batch（输入 1k，输出 256）

| batch | SGLang tokens/s | vLLM tokens/s | 差异 |
|---|---|---|---|
| 1 | | | |
| 8 | | | |
| 32 | | | |
| 64 | | | |

### TTFT / TPOT vs 输入长度（batch 32）

| 输入长度 | SGLang TTFT (ms) | vLLM TTFT (ms) | SGLang TPOT (ms) | vLLM TPOT (ms) |
|---|---|---|---|---|
| 128 | | | | |
| 1k | | | | |
| 4k | | | | |

（图：`/images/sglang-vllm-throughput.png`）

## 分析

1. 拐点：
2. 两引擎差异来源（调度策略 / chunked prefill 默认值 / CUDA graph 覆盖范围 / overlap scheduling）：
3. `bench_serving` 与 engine 日志吞吐不一致的根因：

## 结论

## 复现

仓库：`https://github.com/bryanzhang/inference-bench`（脚本、原始 CSV、绘图代码）。
