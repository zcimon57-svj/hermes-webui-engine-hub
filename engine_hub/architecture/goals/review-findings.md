# 详细审查发现与本轮修正

[评审入口](README.md) · [总图与流程](overview.md) · [决策表](decisions.md) · [来源与版本](research.md) · [证据矩阵](acceptance-matrix.md)

**审查时间：2026-10-09。** 范围为开放 PR #12、总账 #2、分项 #3–#11，以及固定主线 `6e6c4e897c62078ff1f14f072abe3fd7d7c461b3` 的相关实现。三条并行核查线分别检查隔离/权限/调度、路由/学习/资产、官方上游事实。本轮修正评审文档和 Issue，**下列运行问题没有因文档改写而修复**；未启动用户宿主、模型、Gateway、WeKnora 或业务服务。

## 评审资料原有问题

原六份目标文件每份约 3–3.6 KB，包含范围和问题提要，却缺少足以把方案串起来的局部架构、主要流程、数据权威和接口关系。Issue 主要列状态与检查框，PR 没有完整阅读路径。大量事实只能跳转历史分析或源码后自行拼接。本轮补充整体架构/流程、六份分目标详细设计、直接嵌图的 Issue、待决策项、验收解释与版本化来源；原业务状态和历史证据保留。

## 发现总表

以下“影响”是基于已读源码的工程判断；历史动态证据不因本次静态分析被重写。各项的动态复现和修复验收仍待实施。

| 编号 | 发现及影响 | 对应目标/Issue | 本轮文档修正与后续关闭条件 |
|---|---|---|---|
| [RF01](#rf01) | 运行查询可进入派发或取消路径；“GET 不重试”的注释未覆盖下游 | R01/R04/R05；#3/#6/#7 | 明确只读投影与 Manager 恢复器的分工；以带缺失 gateway 回执的持久 Run 验证读取不执行动作 |
| [RF02](#rf02) | 节点/Profile 目录分离未闭合执行脚本与管理身份隔离 | R01/R04/R06；#3/#6/#8 | 增加独立执行身份、挂载与凭据边界；脚本及其子进程负例须真实验证 |
| [RF03](#rf03) | 部分管理和资产消费检查只到 engine；scope 在跨模块传递中丢失 | R04/R06；#6/#8 | 给出对象范围矩阵与可信上下文；同引擎跨项目/owner 的列表、读取、执行负例须覆盖 |
| [RF04](#rf04) | 追问的 conversation shortcut 先于新 instance 判定 | R02；#4 | 明确同引擎换实例的冲突/重绑定语义；旧空间与新实例冲突不得静默继续 |
| [RF05](#rf05) | `evaluate` 只记录调用者提供的 passed；原生门控也不等于产品审核闭环 | R03；#5 | 实际评测与不可变回执、RCA和候选绑定、失败关闭、原生批准旁路纳入设计 |
| [RF06](#rf06) | 本地指针 CAS 与远端 HTTP 发布没有跨服务原子性 | R03/R06；#5/#8 | 增加发布意图、未知状态、对账、孤立文档可见性和幂等恢复；不以本地回滚声称撤销远端写 |
| [RF07](#rf07) | 批准缓存目前执行固定 probe；内容 publish 也不足以证明检索可用 | R06；#8 | 区分固定包消费、通用 Skill 加载、内容读回和检索就绪；独立列验收 |
| [RF08](#rf08) | 运行版本、参考源码、旧实验时间与当前容量结论易被混用 | R05/E01/E02/E03；#7/#9/#10/#11 | 固定版本账本，区分历史 PASS、本轮源码发现和未运行；不外推双节点/真实领域/内部上线 |

<a id="rf01"></a>

## RF01：读取路径包含运行控制副作用

**源码链：** [Hub.run 与注释](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/server.py#L98-L110) → [Manager.refresh](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/manager.py#L195-L205) → [GET run/report 的调用](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/manager.py#L283-L297)。当未终态 Run 缺少 `gateway_run` 时，`refresh` 调用 `dispatch`；取消标记存在时还会发送 stop。相同幂等键可以限制接收方重复受理，但不能把这些操作变成纯读取。

现有恢复意图是合理的，问题是触发路径与 Viewer/查询合同混在一起。[cancel](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/manager.py#L229-L242)设置取消意图后也会调用 refresh；缺少 gateway 回执时可能先派发再 stop，需要纳入同一控制边界。建议 GET 只返回持久记录或显式只读观察；实际派发、重试和 stop 由 Manager 受管恢复器执行并记审计，取消后禁止新的业务派发，未知旧尝试先核查。验收必须覆盖详情、报告下载、会话重建、重连和取消的交叉状态，而不是只检查 Hub 函数内没有 POST。更完整方案见 [R04](r04-access-control.md)和 [R05](r05-multi-node-and-artifacts.md)。

<a id="rf02"></a>

## RF02：批准标签、chmod 和 Profile 不建立完整执行隔离

[Companion.consume](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/companion.py#L75-L110)直接从伴随服务派生脚本进程。环境变量经过缩减，时间、地址空间和输出也受限，但运行身份及可见文件系统仍来自伴随服务。`chmod(0444/0555)` 和包摘要校验也不等于独立只读挂载、权限不可恢复或路径竞态已解决。

上游 Profile 文档明确说明它不提供沙箱；这一外部事实见[固定来源](research.md#sources-hermes-profile)。需要分别画出管理凭据、节点状态、执行脚本和批准快照的边界，覆盖父目录替换、符号链接、子进程和文件描述符继承。当前已通过的错误密钥/普通路径拒绝测试只支持那些 API 路径，不能替代执行层验证。详见 [R01](r01-isolation-and-ui.md)。

<a id="rf03"></a>

## RF03：授权范围不能在服务密钥处缩水

[Hub 节点状态路径](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/server.py#L291-L303)按能力和 engine 找节点；[资产服务消费检查](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/assets.py#L193-L219)区分管理/节点密钥及 engine，未表达完整用户 project/space/owner。配置和用户管理也有未完整覆盖的范围。

建议服务身份与用户/Run 作用域同时校验：节点密钥只证明“哪个节点”，可信上下文约束“为谁、哪个项目、哪些目标、哪次运行、哪些动作”。MCP OAuth 或 stdio 传输本身不会补出这些业务约束。详见 [R04 权限矩阵](r04-access-control.md)与 [R06 消费](r06-assets-and-local-skills.md)。

<a id="rf04"></a>

## RF04：同引擎换实例需要明确语义

[Router.select](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/routing.py#L26-L52)在 conversation engine 未改变时提前返回旧空间，新提交的 `instance` 在后面才解析。旧追问保持空间的测试不覆盖这一冲突。分类器现有范围也主要是四个 engine，返回的 `engine-ops` 不能证明任意项目/实例空间选择。

建议先识别显式业务绑定变化，再决定延续、澄清或新建安全会话；本地模型只从服务端给定候选中建议，不生成地址和权限。具体规则、样例和验收见 [R02](r02-local-routing.md)。

<a id="rf05"></a>

## RF05：治理状态不能替代真实学习质量

[ReleaseAuthority.evaluate](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/assets.py#L124-L133)接受 `passed/evidence` 并改变候选状态，没有执行领域回放。锁定 Hermes 的原生 write approval 默认和异常路径、`/approve` 重放也未绑定本项目的 RCA、候选 hash 和审核回执，见[源码调研](research.md#sources-hermes-learning)。

需要把“原生候选生成”“实际评测执行”“周期独立人审”“发布资格”分开，确保前台、后台与所有写入/批准旁路共同受管；模型自述成功或布尔值不能放行。候选内容、基线、RCA、题集或评测器变更后旧签收失效。详见 [R03](r03-native-evolution.md)。

<a id="rf06"></a>

## RF06：本地 CAS 成功不意味着远端发布原子提交

[approve](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/assets.py#L136-L166)在本地 `BEGIN IMMEDIATE` 期间依次写远端内容，然后写 release/current。若远端已提交但应答丢失，或两个文档中只有一个成功，本地事务回滚不能撤销远端副作用。当前由批准指针控制消费可限制部分影响，但后续直接混合检索不能绕过该指针可见性。

建议使用同一协调权威的持久发布意图与固定远端身份，逐项读回并记录不确定状态，核实后再 CAS 切换 current；孤立远端文档保持不可被正常检索消费，后续对账而非删除证据。必须覆盖候选变化、并发基线变化、部分成功、响应丢失与重启。方案并不假设 WeKnora 有原生跨文档 CAS。详见 [R06](r06-assets-and-local-skills.md)。

<a id="rf07"></a>

## RF07：固定包、通用 Skill 与检索就绪是不同验收对象

[validate_package](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/assets.py#L47-L61)要求固定 `scripts/probe.py` 和 `references/method.md`；Companion 固定读取并执行这些路径。它证明了这个包格式的消费路径，未证明任意受管 Skill 的选择、发现、依赖和执行。`GET consume` 还会运行脚本，必须显式区分描述/读取与执行接口。

WeKnora 邻近参考源码中的 manual publish 先保存状态，再异步处理索引，且 payload 没有原生 `expected_version` CAS 字段。运行镜像的精确行为仍须实测，不能由邻近源码定案。设计需要区分内容读回、索引就绪和按批准集合检索三步，详见 [R06](r06-assets-and-local-skills.md)和[版本说明](research.md#sources-weknora)。

<a id="rf08"></a>

## RF08：版本与证据时间必须成为评审上下文

[版本锁](../../versions.lock.json)分别记录了 WebUI/Hermes 精确 SHA、WeKnora 运行镜像摘要与邻近源码。WeKnora 的短运行来源标记在本次官方仓库查询中无法解析，不代表镜像不存在，也不能据此将邻近源码认作运行内容。MCP 本地手写适配的协议版本与最新 HTTP 授权规范也应区分。

[F03/F19 等历史验收](../../acceptance-local-r1.json)有特定资源和串行轮换边界；[新包络记录](../../reviews/2026-10-09-reassessment/resource-budget-v3-applied.json)是另一时间的配置/空组核对。单热 worker 的自动策略、手动最多两个节点、真实同时双节点验证是三回事。Luna 的 21 条合成题同样不证明本地生产模型或真实领域质量。

本轮提供[逐项 F01–F32 解释](acceptance-matrix.md)、[E02 模型与证据 Issue](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/10)和 [E03 资源 Issue](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/11)，保留旧记录而不提升完成状态。
