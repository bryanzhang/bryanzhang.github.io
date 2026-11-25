---
title: "GPTQ论文笔记与AutoGPTQ"
date: 2023-08-28
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/853282561/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["LLM 推理"]
tags: ["论文笔记", "量化"]
summary: "https://arxiv.org/pdf/2210.17323.pdfMaking LLMs lighter with AutoGPTQ and transformers:"
---

> 2023 年 8 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文：

<https://arxiv.org/pdf/2210.17323.pdf>

Making LLMs lighter with AutoGPTQ and transformers:

<https://huggingface.co/blog/gptq-integration>

还是奥地利科技学院(IST Austria)的Frantar等人在OBQ基础上进一步优化，可以说OBQ框架不变。

OBQ最大的问题是计算量仍然偏大，难以直接应用在大模型上。最关键的优化点是OBQ原来是每个Row分别贪心地选择量化位段，现在是整个权重矩阵不同Row选择同一个位段，配合Lazy Batch-Updates、Cholesky Reformulation等优化(细节就没看了)把计算量下降几个量级。

![](/images/notes/gptq-autogptq/01.jpg)

![](/images/notes/gptq-autogptq/02.jpg)

非常有用的量化方法，通过海塞矩阵优化量化权重，从而在效果基本没损失情况下把模型压缩到平均4bit左右，但原来论文中没有对矩阵计算进行优化，加速只是减少GPU通信量带来的，而AutoGPTQ则对A16W4做了kernel加速，预计还可以更进一步优化。(注：目前triton上还没有kernel优化)

评测一下，clone下<https://github.com/PanQiWei/AutoGPTQ>：

评测代码可以看到AutoGPTQ怎么正确使用，按之前测试的情况看AutoGPTQ的transformers博客用法很可能是错的。

```
# github代码中的示例使用已经out-of-date了
python3 examples/benchmark/perplexity.py --model_name TheBloke/open-llama-7b-open-instruct-GPTQ --model_basename model --use_safetensors --is_quantized
```

显存占用：4G左右

输出：

```
Perplexity: 7.9180
```

```
python3 examples/benchmark/perplexity.py --model_name VMware/open-llama-7B-open-instruct
```

显存占用：13717MiB / 32768MiB

输出：

```
Perplexity: 7.7450
```

Perplexity略涨一点。

生成速度测试，需要稍微改下generation_speed.py支持is_quantized参数

```
cd examples/benchmark/ && python3 generation_speed.py --model_name TheBloke/open-llama-7b-open-instruct-GPTQ --model_basename model --use_safetensors --is_quantized
```

输出：

```
generated 5120 tokens using 167.66178607940674 seconds, generation speed: 30.537668241080908tokens/s
```

```
python3 generation_speed.py --model_name VMware/open-llama-7B-open-instruct
```

输出：

```
generated 5120 tokens using 206.60652351379395 seconds, generation speed: 24.781405315394927tokens/s
```

在我的V100上快了25%!（按上面的数字算，快了约 23%。2026-11 注）
