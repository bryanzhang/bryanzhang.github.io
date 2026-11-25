---
title: "Mini-sglang源码阅读"
date: 2026-10-28
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/topic/503861912/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["LLM 推理"]
tags: ["源码阅读", "SGLang", "LLM Serving"]
summary: "仓库地址：https://github.com/sgl-project/mini-sglang"
---

> 2026 年 10 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

仓库地址：<https://github.com/sgl-project/mini-sglang>

仅阅读源码简单做些记录,零cc/codex分析，也没有实际运行代码追踪。主要自己做个简单的索引吧。

Mini-sglang is compact implementation of SGLang, designed to demystify the complexities of modern LLM serving systems.

commit为9a91cfafe754aa85daee49998176275667eb58f2。

**1.入口与前端逻辑：**

入口：python/minisgl/__main__.py。

![](/images/notes/mini-sglang-source/01.webp)

一路顺着进来，可以看到里面通过multiprocessing进行多进程通信处理，启动了多个tokenizer、world_size个调度进程、1个detokenizer：(world size这个命名比较容易让人想到tensor parallel的rank)

![](/images/notes/mini-sglang-source/02.webp)

进run_api_server，默认是启动了http server(FastAPI+uvicorn)进行处理的（当然也可以指定run_shell通过交互式命令处理,这部分不看)。api_server.py中可以看到主要是这几个接口：

/generate

/v1

/v1/chat/completions

/v1/models

run_api_server代码：

![](/images/notes/mini-sglang-source/03.webp)

关键入口是FrontendManager(_GLOBAL_STATE)，如主要的api接口都调用其send_one方法。后端(start_backend)则对应到调用scheduler进程、tokenizer进程和detokenizer进程。

重点看FrontendManager的new_user方法和send_one方法。前端比较简单，一个zmq发送队列和接收队列，发送队列、接收队列直接连接到后端tokenizer进程了：

![](/images/notes/mini-sglang-source/04.webp)

每个会话直接对应一个新的uid，更准确地说其实是session id了。从listen方法看，从后端进程接收到消息之后根据uid放入ack_map[uid]的列表中，同时设置event_map[uid]唤醒等待协程,listen()方法主要和wait_for_ack()方法配合，listen代码看tokenizer可能回应多个不同uid的消息(BatchFrontEndMsg)。wait_for_ack()方法产生一个generator，生成UserReply序列，生成器结束条件是最后一个ack带finished标志。

再看看api generate调用的FrontEndManager::stream_with_cancellation方法，同样是一个generator以支持流式输出(generator底下调的还是wait_for_ack)：

![](/images/notes/mini-sglang-source/05.webp)

**2.后端逻辑：**

正式进入后端环节，后端进程包括world_size个scheduler、一个DeTokenizer、num_tokenizer个tokenizer。

DeTokenizer和Tokenizer参数除了名称之外都一样，所以是否DeTokenizer是一个特殊的Tokenizer呢？是第num_tokenizer个tokenizer?看它们公共的执行函数tokenize_worker,就负责处理TokenizeMsg,DetokenizeMsg和AbortMsg。

- 对于TokenizeMsg,调用tokenize_manager.tokenize产生tensors,发送BatchBackendMsg(UserMsg)，应该是发送给调度器进程的；

- 对于DetokenizeMsg,调用detokenize_manager.detokenize,发送BatchFrontendMsg(UserReply)，发送给前端。

- 对于AbortMsg,直接发送BatchBackendMsg(AbortBackendMsg)，发给后端。

tokenize_worker加了@torch.inference_mode()标注，禁用梯度追踪及额外禁用版本计数器和视图追踪以达到较高性能的目的。

tokenize_manager实现比较简单，有个细节是消息文本的组装是在tokenize阶段做的，还不支持批量tokenize：

![](/images/notes/mini-sglang-source/06.webp)

主要的load_tokenizer方法看就是简单的transformers.AutoTokenizer:

![](/images/notes/mini-sglang-source/07.webp)

detokenize方法则调用了tokenizer.batch_decode方法。

调度器进程的回调函数为_run_scheduler,主要负责创建和销毁Scheduler、事件循环(run_forever)。

先看看它的父类，是个组合方法类SchedulerIOMixin，看注释主要提供的方法是：

![](/images/notes/mini-sglang-source/08.webp)

当tp_cpu_group: torch.distributed.ProcessGroup包含不止一个cpu时这些方法才有特殊性。这里的tp应该是tensor parallel，多少个gpu就对应到多少个cpu调度进程。以接收消息方法为例，主、从rank分别实现如下：

![](/images/notes/mini-sglang-source/09.webp)

主先广播数量，然后往消息队列中发送消息；从接收数量，然后读取这个数量的消息，所以是消息在ProcessGroup中广播。发送没有特殊性，不广播，因此只有主rank有操作。

事件循环run_loop_forever默认会走overlap_loop:

![](/images/notes/mini-sglang-source/10.webp)

其中_process_one_msg主要调用了prefill_manager.add_one_req

_schedule_next_batch先后调用了prefill_manager和decode_manager的同名方法（or的调用关系，prefill优先），然后再调_prepare_batch。这额就是chunked prefill的逻辑了。

可以看出不管是需要prefill还是decode的请求，内部都视为Batch，仅仅通过phase字段区分，这使得很多处理比较统一。看最后的_process_last_data，可以知道prefill之后的结果是最后进入prefix cache的，也可以看到发送DetokenizeMsg的处理，从_process_last_data中也可以判断decode每次也只是forward一个token，碰到eos token就做结束处理：

![](/images/notes/mini-sglang-source/11.webp)

**3.Engine:**

看engine代码，__init__部分，涉及到page数量计算，注意这里config.page_size对应的是一页(一个chunk)的kvcache缓存多少token，一个page对应完整一个模型、一个chunk序列的内存总量，计算如下，可以看到张量并行减少kvcache使用的逻辑：

![](/images/notes/mini-sglang-source/12.webp)

这里可见是不支持MLA的。MHAKVCache比较简单，内部就是一个大tensor，同时存KV。唯一要注意的是它存储时调了一个独立的kernel, store.cu，**具体为啥后面要看一下：**

![](/images/notes/mini-sglang-source/13.webp)

**不明白为啥需要dummy page和dummy request，另外就是为啥kvcache pool里只有一个请求的数据**:

![](/images/notes/mini-sglang-source/14.webp)

注意页表是在设备而不是host上面，一页对应的是一个token在整个模型中所需的kv cache大小，而不是一个chunk。

再看支持的Attention Backend有tensorrt-llm、flashattention、flashinfer:

![](/images/notes/mini-sglang-source/15.webp)

moe的后端只有FusedMOE:

![](/images/notes/mini-sglang-source/16.webp)

粗略看是两个融合算子实现，部分用到了triton:

![](/images/notes/mini-sglang-source/17.webp)

sampler也可以看到直接使用了flashinfer.sampling方法。

可以看到使用dummy request复制,针对配置的batch size进行图捕获，以加速后续执行，这里还升级到AttnBackend的prepare_for_capture、prepare_for_replay接口。当batch size不足时需要进行padding，序列不需要padding。Engine需要关注的只剩下forward方法，返回cpu、gpu存储以及事件：

![](/images/notes/mini-sglang-source/18.webp)

**4.PrefillManager、DecodeManager、CacheManger等：**

PrefillManger中留意这里有个inflight_tokens，即为decode阶段预留kvcache:

![](/images/notes/mini-sglang-source/19.webp)

TableManager是按照请求数来当slots:

![](/images/notes/mini-sglang-source/20.webp)

阅读下几十行的RadixPrefixCache(python实现, sglang中是rust高性能实现)，key是从parent延伸出来的input_ids子串，value则是页表(key在cpu,value在gpu)，通过引用计数来做驱逐判断，回收时先从空引用数的叶子开始回收，按最近访问时间戳顺序回收，因此是LRU。**当然RadixPrefixCache有个特殊的分裂节点操作还是蛮细节的(split_at)，为了避免单节点子串过长造成prefix不命中的问题**。

一个RadixCacheHandle即是一个RadixTreeNode。

CacheManager发现就那么回事，比较简单。另外从Scheduler、PrefillManger和DecodeManger中都看不出具体是prefill还是decode，都是简单的forward，原来是藏在attention后端基类HybridBackend去处理的：

![](/images/notes/mini-sglang-source/21.webp)

唯一有疑问的就是kvcache的页表同时在RadixPrefixCache的树节点和PageTable中同时保存了，空间上似乎有点浪费了。
