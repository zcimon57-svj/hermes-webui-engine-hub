# 资源预算与两种Skill进化机制：澄清 v2

2026-10-09；用户已允许调整1GiB预算，同时仍严禁打满资源。本轮核对现场和第一方固定版说明；未启动模型/服务、未安装或修改宿主/WSL配置。**建议预算3GiB；当前运行保护代码仍1GiB，尚未切换。** [机器可读建议与实测现场](resource-budget-v2.json)。

## 为什么建议3GiB

本次现场：WSL总7.65GiB、MemAvailable 5.32GiB；Windows总15.79GiB、可用2.20GiB；本项目slice记账0字节/0任务。Linux的可回收缓存不代表Windows已经拥有同量空闲，不能只看WSL available决定启动。

建议本任务总memory.max=3GiB、memory.high=2.5GiB、swap.max=0、TasksMax=192，继续单核亲和性和一个模型任务。它包含分类器、Hub、两个Hermes节点及伴随服务，不是每进程各3GiB。暂定分类器不超过2GiB、其余最多1GiB，合计不能突破shared cgroup；分配是容量建议，加载/推理/双节点实际峰值均NOT_RUN。

Laya多语322M FP32仅参数约1.20GiB（1.29GB），再加框架/激活，1GiB显然不足；3GiB可为受限上下文的单模型与两个轻节点提供测试余量，不能保证所有PyTorch加载方式适配。优先评估ONNX/低精度或小模型，峰值不适配则停止并保留证据；不自动扩为4/8GiB，也不靠swap容纳模型。

两个节点共用一个只做分类的服务，不各装一份模型。分类器按请求取得服务端授权候选，不保留跨请求业务对话；私有Memory、工作区、凭据与学习草稿继续按节点/项目隔离。模型常驻与分类并发均最多1，限制线程、输入长度、候选数和队列；权重准备/转换/分类/进化评测不得同时叠加。

宿主reserve建议Linux与Windows各2GiB，启动前还须加上新负载的保守预留；运行中低于reserve、测量失败或发生压力则拒绝新任务并停止本项目负载。**Windows当前仅约2.20GiB可用，接近2GiB保留线，不能启动新的重负载。** 硬上限是最大许可，不能当成当前可用额外内存。保护配置切换与kernel值验证须先于真正运行；本轮只形成可复核建议，没有宣称已实施新保护或模型能装下。

## “只实现Skill阶段”指这个独立仓的目标对象

用户理解正确：Hermes原生已有Skill学习/修改，还包括Memory积累及Curator维护，并不是等独立仓Phase5才会跨会话学习。我此前表述混淆了两个维度。

[独立仓README](https://github.com/NousResearch/hermes-agent-self-evolution/blob/0a929e3aa20e15cf04dc7c28492a7d41a5139125/README.md)自行列出：Phase1=SKILL.md，Implemented；Phase2=tool description、Phase3=system prompt、Phase4=tool implementation code、Phase5=continuous loop，Planned。**Implemented是作者的阶段标记，不代表本项目已跑通或领域效果通过。** 它不是说Hermes只有一部分Skill才会进化，更不是说Skill之后必须进化主模型权重。

## 两边都改Skill，区别在组织和评价方式

| 维度 | Hermes原生 | 独立self-evolution的Skill路径 |
|---|---|---|
| 常见触发 | 解决非平凡工作、用户纠正、会话后后台review、维护过程 | 显式选择某个Skill启动优化作业 |
| 如何产生修改 | Agent根据本次经验创建/修补流程，Memory辅助跨会话复用 | DSPy/GEPA尝试候选变体，利用训练/验证反馈选择，最后holdout评测 |
| 评价含义 | 保存/修补成功证明资产变化；本身不等于领域效果提升 | 测评题与分数驱动选择；题集/评分器是否真实可靠仍需验证 |
| 持续性 | 可以在日常使用中不断积累、修改并维护 | 一个作业内部可有多次迭代；长期监控与自动触发管线另属Phase5 |
| 本系统现状 | 当前lab尚未接入原生Memory/Skill写学习链 | 独立优化器尚未集成，正文回写/API等疑点未实测 |

[Hermes原生说明](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/website/docs/user-guide/features/skills.md)明确把Skill称为程序性记忆，与事实/偏好Memory配合，并支持会话后建议或暂存修改。这个原生长期学习能力，应与独立仓的Phase5完成状态分开判断。

例子：一次PG锁等待工单解决后，原生Hermes可以把排查流程保存为Skill，并在下次发现遗漏时修补。独立优化作业则把同一个流程放到一组标注工单中，比较多个候选步骤顺序及遗漏补救，选择表现较好者。这是不同的改进方式，不能仅因保存了新版本就断言它更好。

## “持续进化仍在规划”是自动组织这些优化作业

该独立仓[PLAN Phase5](https://github.com/NousResearch/hermes-agent-self-evolution/blob/0a929e3aa20e15cf04dc7c28492a7d41a5139125/PLAN.md)写的是：从真实使用监测成功率、工具选择、benchmark和用户纠正；给薄弱点排序；按定时/阈值自动选目标和启动优化；更新评测数据；生成PR等待人审。人工仍然审核合并，不是自动上线所有候选。

所以一个Skill作业迭代10次，或允许输入SessionDB，不足以证明已经实现“持续监测→自动选目标→触发优化→评测→提交审核”的长期系统。该标记仅指独立仓相应Phase的状态；不能外推为“原生Hermes没有持续学习”，也不能外推所有fork都未实现（本轮未逐个审查其98个PR/653个fork）。

对我们的R03而言，并不需要等待上游Phase2–5全部完成。可以保留原生私有学习，复用独立优化器，自己接有限反馈采集/实际评测/审核与CAS发布；批准后仅同引擎共享。仍需先解决脚本隔离和实际评测器，不能由LLM自评/客户端passed=true自动发布。现有[自进化分析](self-evolution-analysis-v1.md)里的实现疑点依然有效，但与“进化对象也是Skill”并不矛盾。
