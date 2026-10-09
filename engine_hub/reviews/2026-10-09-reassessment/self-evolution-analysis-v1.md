# Hermes原生与独立自进化项目分析 v1

2026-10-09；SOURCE_REVIEWED / INTEGRATION_NOT_RUN。分析对应R03自动学习缺口与R06发布消费边界；[进度](goals-progress-v2.md)、[源码版本账本](research-sources-v1.json)。没有执行项目安装器、bootstrap、定时任务或模型优化。

## 先明确进化对象和当前状态

Memory积累偏好/事实、Skill沉淀或修改可复用流程、分类head训练、模型全量/LoRA权重训练是四种不同对象。Hermes原生记忆和Skill操作并不等于持续重训主模型。Laya/Kev负责概率决策，也不能生成新的Skill正文。反馈归集和草稿生成仍需Hermes所用的文本模型及实际评测器。

当前Hub已有private draft→candidate→人工评测标记→approve/CAS发布→WeKnora读回→下一Run消费/回退链。**自动采集/生成和真正的评测执行器尚未实现**。当前lab关闭memory_enabled/user_profile_enabled，仅mcp-ops工具集；不能把Hermes上游的能力记为本实现已启用的进化效果。

## 原生Hermes能做什么

固定Hermes源码SHA `345cd2b057a452236de401d3534b8502a7465e8d`，查看`tools/memory_tool.py`、`tools/skill_manager_tool.py:742`、`agent/curator.py`及`website/docs/user-guide/features/curator.md`。第一方入口：[Hermes Agent](https://github.com/NousResearch/hermes-agent)。

原生可在节点私有Home沉淀Memory、创建/修补Skill；Curator维护使用/闲置状态、归档和备份回滚，可选模型辅助合并。该固定版consolidate默认关闭，prune_builtins默认开启，Hub-installed资产不在其自动维护范围；这不是所有历史版本默认行为。若接入，正式远端批准资产应只读/pinned，禁止Curator自主改写或归档本轮Run固定版本。

Curator的模型合并可能消耗多轮调用，不能仅以“后台”二字判断资源便宜。需要绑定单个节点私有学习库、显式调用/时间/预算上限、无与正在进行的Run冲突。当前没有验证这些接入条件，也未打开Curator或原生写能力。

## 独立项目对比

Nous项目核对了核心源码；其余项目主要依据第一方README选读，未做完整源码审计。下表为核对到的说明/实现范围，所有运行与本系统适配均NOT_RUN。

| 项目 | 当前核对范围 | 如何用于本系统 / 不能推定的内容 |
|---|---|---|
| [NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) | README标记Phase1 Skill implemented；Tool/Prompt/Code/Continuous为planned。DSPy优化与LLM评测，不训练主模型权重 | 很可能是用户提到的独立项目；可借鉴Skill数据/优化概念，不能直接称已实现全部持续进化或通过内部任务 |
| [GEPA](https://github.com/gepa-ai/gepa) | 通用文本参数、执行反馈和多候选反思优化框架 | 建议优先原型的优化内核，显式把candidate文本与真实Run/evaluator相连；它不提供我们的授权、发布、WeKnora或持续采集产品链 |
| [Hermes Curator Evolver](https://github.com/pingchesu/hermes-curator-evolver) | 默认dry-run的本地会话证据/候选；模型无关采集、来源约束、验证与备份回滚；可选autorun | 可借鉴轻量collector和candidate存储；bootstrap会设置调度和受控本地写，不能在此任务盲跑。正式资产发布仍走Hub审核 |
| [Sentient EvoSkill](https://github.com/sentient-agi/EvoSkill) | 以benchmark驱动失败分析与新建/修改Skill，heldout选择，多个coding harness；无benchmark/continuous标为研究中 | 若优化完整Skill包而非单正文，是并行选型候选；Hermes不在本次已核对支持表中，需要自己的harness。跨模型论文结果不是我们数据库领域效果 |

许可记录：GEPA/Curator Evolver为MIT、EvoSkill Apache-2.0。Nous README/pyproject声明MIT，但本次树和GitHub元数据未发现独立LICENSE，保留包级许可核对项。规划中的Darwinian外部代码进化器不代表该仓现在已交付代码进化。

## Nous项目的静态实现疑点

固定SHA `0a929e3aa20e15cf04dc7c28492a7d41a5139125`，本轮阅读`evolution/skills/evolve_skill.py`、`skill_module.py`、`core/config.py`、`fitness.py`、`constraints.py`、`dataset_builder.py`；可按[固定源码](https://github.com/NousResearch/hermes-agent-self-evolution/tree/0a929e3aa20e15cf04dc7c28492a7d41a5139125/evolution)复核。

1. `SkillModule`把正文存成普通`self.skill_text`，forward把它作为InputField传入预测器；优化结束又从`optimized_module.skill_text`读回正文。未见把优化后的predictor instructions映射回该字段的代码。**优化输出是否变成新SKILL.md存在静态数据流缺口，未实测，不宣称已复现失败。**
2. GEPA调用用`max_steps`且未显式传反思模型；`optimizer_model`虽配置/打印，不能据此证明真的用于reflection。依赖只设置DSPy下限，具体API兼容性须锁版验收。
3. GEPA路径捕获所有Exception再fallback MIPROv2；提供商/配置/调用失败也可能被解释成GEPA unavailable。接入应记录并失败关闭，禁止未经约定改变优化器或预算。
4. 默认synthetic题集和LLM judge主要测DSPy包装回答，没有证明经过真实Hermes Gateway、MCP执行、权限和数据库领域回放。README中的PR/持续闭环目标也不能由写出evolved/metrics文件代替。

以上为接入前应验证/修正的点，不是要在本轮重做第三方框架。须先证明“候选字节实际变化→运行消费这些字节→真实评测评分→发布内容等于获胜候选”。增加行数、自评高分或优化器完成均不足以验收。

## 本系统适配建议：完整闭环，保持发布权威

```mermaid
flowchart LR
  A[节点私有Run证据与明确反馈] --> B[脱敏与来源作用域检查]
  B --> C[候选collector]
  C --> D[Hermes生成 / GEPA或EvoSkill优化]
  D --> E[隔离候选包]
  E --> F[真实Hermes与MCP回放评测]
  F --> G[领域holdout与安全负例]
  G --> H[人工批准与CAS发布]
  H --> I[WeKnora正式版本]
  I --> J[同引擎节点下一Run固定消费]
```

这是建议，尚未落地。不抽取跨引擎公共知识；Run证据、Memory、学习草稿保留节点/项目scope。collector记录失败类型、人工纠正、实际工具轨迹、源Run/报告版本及脱敏审计；噪声反馈和“不喜欢措辞”不能等同根因修复真值。同一Issue历史先按时间去重和拆分，不把holdout泄漏进生成提示。

候选必须为完整包：SKILL.md及scripts/references/templates等引用、manifest/hashes/依赖锁/来源权利/目标engine及scope。将真实工具失败和反例反馈给优化器；评测器返回实际通过/失败证据，不能接受客户端POST passed=true作为自动验收。heldout与安全负例不得用于不断调参。

生成者不能批准自己。正式版本由WeKnora发布链唯一管理；获批同引擎共享，私有草稿不共享；并发更新走CAS，撤销/回退可追溯，既有Run继续使用固定版本，下一Run取新版本。任何项目自动改写本地Home仅限私有草稿，禁止绕过远端正式审批。

资源约束沿用E03；一次仅一个生成/评测任务，有限候选、实际调用次数/时间/花费上限、取消与恢复日志，禁止默认无限循环或开启每日autorun。本地分类器与Agent生成模型使用不同职责和预算，不能误以为分类模型本地化后文本进化也已经离线。

## 责任、下一步和验收

Core维护者先修I01脚本/管理凭据隔离，再提供I03 collector→candidate→实际eval适配器。知识维护者锁定完整包/远端manifest；领域维护者给专家真值与holdout；Manager维护者提供取消、互斥、恢复和审核身份。

建议先比较原生Hermes受控候选输出与GEPA显式适配的单Skill原型，Curator Evolver仅接入采集，不自动发布；EvoSkill作为完整包路线对照；Nous项目保留研究对照，并先查清正文回写/API疑点。至少记录候选hash变化、实际Run消费hash、提升/退化/无提升/生成失败、非法权限/不可信反馈、超预算/取消、批准后两个同引擎节点消费、拒批不生效、回退及并发CAS冲突。

本轮上述运行验收全部NOT_RUN，领域效果也未证实。当前R03仍是治理骨架部分实现；分析完成不改变六目标整体PARTIAL判定。
