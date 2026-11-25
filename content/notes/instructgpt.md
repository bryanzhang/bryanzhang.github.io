---
title: "Training language models to follow instructions with human feedback论文笔记"
date: 2023-03-01
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/845652722/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["模型与算法"]
tags: ["论文笔记", "RLHF"]
summary: "论文地址：https://arxiv.org/pdf/2203.02155.pdf"
---

> 2023 年 3 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

论文地址：<https://arxiv.org/pdf/2203.02155.pdf>

这篇论文介绍InstructGPT，论文看起来十分详细，有68页。主要读了1 introduction和3 Methods and experimental details，ppo和强化学习的具体方法后面还要详细研究下其他材料。感觉把InstructGPT大体框架摸清楚了。

Abstract

简单地把大模型参数量加大并不会让它们更好理解用户意图。比如大模型的输出可能是错误的(untruthful）、有害的(toxic)或对用户无帮助(helpful)。这些都称为和用户意图不对齐(not aligend)。论文提出的方法InstructGPT，基于GPT-3模型进行有监督微调(SFT)，在人工评估中1.3B的参数就能打败175B的GPT-3模型，在helpful损失有限情况下，toxic、untruthful维度都有明显改善。

1 Introduction

大模型输出往往编造事实，带偏见或内容有害，或者不遵循用户指令，是因为大模型目标只是预测下个token，可以说是目标不对齐(misaligned)。对比InstructGPT(1.3B)和原始GPT-3(175B)，几个发现是：

1.标注者明显更偏好InstructGPT输出。

2.InstructGPT在truthfulness上相比GPT-3有明显改善

3.InstructGPT在toxicity上相比GPT-3有少量改善，但对偏见无改善。

4.公开NLP数据集上，通过修改RLHF微调过程(使用PPO-ptx)可以最小化效果损失。

5.InstructGPT可以很容易泛化到训练集外的其他标注者。

6.公开NLP数据集不是InstructGPT的典型应用场景，指标略输。

7.通过RLHF微调InstructGPT泛化潜力巨大，在做代码摘要、回答问题甚至听从其他语言指令上都表现不错，尽管这些指令样本很少很少。

8.InstructGPT仍会犯低级错误，比如编造事实，不正面回答问题等。

3 Methods and experimental details

三个步骤：

1.收集数据(demonstration data)有监督训练出策略。

2.收集对比数据(pairs)，训练奖励模型(Reward Model)。

3.使用PPO算法和奖励模型优化策略。

SFT数据集是13K prompts，RM数据集是33K prompts，PPO数据集是31K prompts。数据量都很小，效果却这么棒，让人感叹大模型泛化能力之强。

验证数据和对比数据是通过Upwork和ScaleAI外包网站雇佣的40人外包产出的。按照对有害内容的识别能力、对人群偏好的敏感性对标准人员进行严格筛选测试(screening test)。训练阶段把helpful目标放在首位，指标评估阶段则把truthness和harmlessness放在更高优先级。整个项目阶段和外包人员密切协作，包括做上手培训(onboarding process)、任务会写详细的指令，并在共享聊天室回答外包人员疑问。（为了验证泛化能力还单独留出相同外包供应商、不做筛选测试的一组外包人员)

模型的三个阶段：

1.有监督微调(SFT,supervised fine-tuning)：使用验证数据在GPT-3上微调，使用16 epochs, cos学习率衰减、0.2dropout。

2.奖励建模(RM, Reward modeling)：把SFT最后一个非embedding层移掉加入RM，论文使用的是6B的RM（175B不够适合)。对于相同输入的模型产出K个输出(4 &lt;= K &lt;=9)，两两进行比较标注，将相同输入的所有的pair放在一个batch中训练，不仅可以减少计算而且不会过拟合。

3.强化学习：使用PPO算法，加入奖励、每个token的KL分散度惩罚、预训练梯度 (具体原理，还要好好搞清楚)：

![](/images/notes/instructgpt/01.webp)
