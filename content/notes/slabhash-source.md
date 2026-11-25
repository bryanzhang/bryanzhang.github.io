---
title: "SlabHash代码阅读"
date: 2024-07-25
migrated: 2026-11-25
original:
  platform: 豆瓣
  url: "https://www.douban.com/note/864493201/"
  note: "原样迁移，只把图片和外链本地化。"
draft: false
topics: ["系统与性能"]
tags: ["源码阅读", "GPU", "哈希表"]
summary: "SlabHash是高性能的GPU hashtable实现。代码仓库：https://github.com/owensgroup/SlabHash，自己的论文笔记：https:/……"
---

> 2024 年 7 月的学习笔记，从豆瓣原样迁移，没有重新核对，可能有疏漏。

SlabHash是高性能的GPU hashtable实现。

代码仓库：<https://github.com/owensgroup/SlabHash>，自己的论文笔记：<https://www.douban.com/note/864386673>

代码阅读步骤：

一.benchmark

二.gpu_slab_hash

三.GpuSlabHash

四.SlabAlloc

一.benchmark

先从benchmark.cu和experments.cuh看怎么使用：

singleton_experment是单线程测试，指定expected_chain_length(单个chain装载率)，指定key数量，query数量以及query_ratio(多少query是已有key)，批量随机生成key、value、query，然后构建hash_table、搜索：

![](/images/notes/slabhash-source/01.webp)

load_factor_bulk_experiment指定数量后，装载率动态调整(每个iter的expected_chain_length逐步增加)，然后也是build、search还会执行一次bulk_search，不大清楚这个bulk_search有啥特殊，看参数和search也是一样：

![](/images/notes/slabhash-source/02.webp)

build_search_bulk_experiment experment_chain_length不变，key数量会变之外，并调用hash_search_bulk：

![](/images/notes/slabhash-source/03.webp)

![](/images/notes/slabhash-source/04.webp)

concurrent_batched_op_load_factor_experment和load_factor_bulk_experiment类似，key数量确定，expected_chain_length增量变化，但是测试的是batch的insert、update的时间：

![](/images/notes/slabhash-source/05.webp)

二、gpu_slab_hash

好了，下面进入gpu_hash_table相关代码。简单的说，这个类对内部类进行包装，提供以CPU、同步的使用接口。构造函数：

![](/images/notes/slabhash-source/06.webp)

可以看出key,value等数组是直接通过cudaMalloc分配，而后续的slab则通过DynamicAllocator分配，真正的实现类似乎都在GpuSlabHash中，这两个一会再展开。

这里req_values_感觉更适合做模版参数，避免运行时去判断，比较好理解，纯粹的set就不需要保存value了，或者是需要key、value连续保存在一起的情况。

to_string直接代理调用slab_hash->to_string。

![](/images/notes/slabhash-source/07.webp)

hash_build做key、value数组host到显存的拷贝，以及调用slab_hash_->buildHash，并返回总耗时：

![](/images/notes/slabhash-source/08.webp)

hash_build_with_unique_keys大同小异：

![](/images/notes/slabhash-source/09.webp)

hash_search：把CPU的query拷贝到显存，对显存result数组进行初始化，然后调用search_individual，最后将结果数组拷贝回主机内存：

![](/images/notes/slabhash-source/10.webp)

hash_search_bulk大同小异，只不过内部调用的是slab_hash_->searchBulk:

![](/images/notes/slabhash-source/11.webp)

hash_count应该是多值map的计数？

![](/images/notes/slabhash-source/12.webp)

hash_delete对key进行删除：‘

![](/images/notes/slabhash-source/13.webp)

batched_operations是在一个大数组中指定batch_id和batch_size，调用slab_hash_->batchedOperation进行批量操作，同样也要进行reuslt数组相应位置初始化，host和device memory之间的拷贝：

![](/images/notes/slabhash-source/14.webp)

mesureLoadFactor直接调用slab_hash_的computeLoadFactor方法：

![](/images/notes/slabhash-source/15.webp)

三、GpuSlabHash

接着看GpuSlabHash，有两个模版类GpuSlabHash&lt;KeyT, ValueT, SlabHashTypeT::ConcurrentSet>和GpuSlabHash&lt;KeyT, ValueT, SlabHashTypeT::ConcurrentMap>，我们直接看GpuSlabHash&lt;KeyT, ValueT, SlabHashTypeT::ConcurrentMap>，在cmap_class.cuh中，构造函数中分配了d_table_设备内存指针，这里留意到identity_hash和gpu_context：

![](/images/notes/slabhash-source/16.webp)

对应的initParameters比较简单：

![](/images/notes/slabhash-source/17.webp)

接下来看几个主要方法(这里也看出目前代码没有实现flush即compact操作)：

![](/images/notes/slabhash-source/18.webp)

1.computeLoadFactor调用的是bucket_count_kernel，一看就是非常地道的__ballot_sync，__popc，__shfl_sync用法:

![](/images/notes/slabhash-source/19.webp)

通过ballot_sync和popc把每个线程的计数收集上来，再通过shfl_sync把next指针分发出去，继续统计，虽然有while的条件判断，但这里对warp执行性能影响几乎可以忽略，最后每个warp的pair数量和slab数量写回到缓存中。但是并没有再启动kernel再去规约这些值了而是单线程循环，如果要优化，可以再launch kernel，或者在前面那个kernel中选择部分warp继续规约。

2.build_table_kernel:关键是insertPair:

![](/images/notes/slabhash-source/20.webp)

关键点不是insert之后的CAS，而是查找空位时发动warp内所有线程(即使自己线程to_be_inserted=false也需要参与工作）去找空位，这样就很好地利用了shuffle，ballot同步原语以及coalesced memory read能力：

![](/images/notes/slabhash-source/21.webp)

这里也可以看出虽然是泛型，但也有很强的局限性，mykey和myval都按指针进行保存而不支持按值保存，另外指针也都按32位处理，因为还有标识位的使用实际还没法全部用到32位，在大显存上显然并不合适。真正应用还需要修改相关实现的。

3.buildBulkWithUniqueKeys：和insertPair类似，只是如果有重复key插入，不做替换而保留原来的kv。

4.searchIndividual:调用的是search_table的kernel:

search用这种方式比较好理解，它可以warp内并行去找， 相比于线程内找自己的数据它更好利用了coalesced memory read：

![](/images/notes/slabhash-source/22.webp)

5.searchBulk: 调用的是searchKeyBulk函数，似乎和searchKey差不多，只是它使用展开的循环而不是每次work_queu取ffs低位任务，直观上性能可能更好：

![](/images/notes/slabhash-source/23.webp)

6.deleteIndividual:和insertPair类似，只是用的不是atomicCAS而是atomicExch:

![](/images/notes/slabhash-source/24.webp)

7.batchedOperation:

比较好理解，可以并发地增删改，使用之前的几个函数：

![](/images/notes/slabhash-source/25.webp)

8.countIndividual:调用的count_key的kernel:

![](/images/notes/slabhash-source/26.webp)

内部是countKey函数，跟search类似。

四、SlabAlloc

SlabAlloc为submodule，仓库地址<https://github.com/owensgroup/SlabAlloc>，看起来只实现了lightweight版本，比较简单，没有展开。

lightweight是把superblock也分配在一起，这样很多操作通过位运算即可，地址中不同位段分别代表super_block_index、memory_block_index、memory_unit_index:

![](/images/notes/slabhash-source/27.webp)

SlabAlloc一如SlabHash那样通过ballot和shuffle、ffs等函数实现WCWS，这样即使是内存分配这么轻量的工作也可以把负载分摊到32个线程中，核心的两个函数在这里：

![](/images/notes/slabhash-source/28.webp)

![](/images/notes/slabhash-source/29.webp)
