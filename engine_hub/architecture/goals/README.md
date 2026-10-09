# 六个功能目标与三个执行要求：独立评审入口

**从这里开始评审：[PR #12](https://github.com/zcimon57-svj/hermes-webui-engine-hub/pull/12) · [目标/进度总账 #2](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/2)。**

2026-10-09 修订：本目录提供可直接评审的系统总图、六项目标设计、正常与失败流程、接口/数据权威、源码与官方依据、备选方案和验收条件。五个一级模块保持业务接入、Agent Manager、Agent Core、知识平台、MCP接口。

**当前仍为部分实现，架构待独立评审。** 本轮修正文档和Issue，不把发现写成已修复代码；PR #1 仅是历史基线，PR #12 保持打开供用户转发，目标Issue不因文档合入自动关闭。

## 建议阅读顺序

| 顺序 | 材料 | 评审者可以回答的问题 |
|---|---|---|
| 1 | [整体架构与端到端流程](overview.md) | 业务场景是什么？五模块怎样配合？现状和目标有什么差距？ |
| 2 | [本轮详细审查发现](review-findings.md) | 哪些表述和实现有矛盾？为什么影响完整验收？ |
| 3 | 下表的目标设计和Issue | 本目标的接口、权限、失败恢复、备选与验收是否合理？ |
| 4 | [具体决策表](decisions.md) | 哪些需要现在决定？建议与替代的代价是什么？ |
| 5 | [验收与历史证据解释](acceptance-matrix.md) | 旧PASS到底证明了什么？还缺哪些场景和输入？ |
| 6 | [官方调研与版本边界](research.md) / [执行要求](execution-requirements.md) | 上游事实可否支持本设计？交付、模型与资源约束是否闭合？ |

## 六项目标：文档与Issue双向导航

| 目标 | 详细架构 / Issue | 当前真实状态 | 本轮重点 |
|---|---|---|---|
| R01 多引擎隔离与统一UI | [设计](r01-isolation-and-ui.md) / [#3](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/3) | PARTIAL_ISOLATION_NOT_ACCEPTED | 实际复用边界、脚本管理身份、只读查询、同时隔离 |
| R02 本地分类和空间路由 | [设计](r02-local-routing.md) / [#4](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/4) | PARTIAL_LOCAL_CLASSIFIER_NOT_IMPLEMENTED | 授权候选、同引擎换实例、拒识、型号/质量/容量 |
| R03 原生受控学习与共享 | [设计](r03-native-evolution.md) / [#5](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/5) | PARTIAL_GOVERNANCE_ONLY | 所有写入口pending、独立RCA、真实评测、人审绑定 |
| R04 三角色与对象权限 | [设计](r04-access-control.md) / [#6](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/6) | BASIC_ROLES_VERIFIED_MANAGEMENT_PARTIAL | 管理面scope、委派、撤权、读路径副作用 |
| R05 同引擎多节点与产物 | [设计](r05-multi-node-and-artifacts.md) / [#7](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/7) | SIMULTANEOUS_TWO_NODE_PENDING | worker与target、同时双节点、attempt/产物、跨机阶段 |
| R06 远端资产与本地Skill | [设计](r06-assets-and-local-skills.md) / [#8](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/8) | VERSION_CHAIN_VERIFIED_GENERIC_ADAPTER_PARTIAL | 发布对账、通用加载、检索就绪、候选/缓存隔离 |

## 三项执行要求

| 要求 | 详细说明 / Issue | 当前状态与后续约束 |
|---|---|---|
| E01 派生仓与可核对交付 | [E01](execution-requirements.md#e01) / [#9](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/9) | 已有历史交付；公开已获用户授权；保留上游历史/许可证与失败证据，原PR持续评审 |
| E02 真实模型与本地生产分类 | [E02](execution-requirements.md#e02) / [#10](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/10) | 历史真实Luna证据保留；本地模型、真实领域和数据阈值未验 |
| E03 严格资源控制 | [E03](execution-requirements.md#e03) / [#11](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/11) | 事故/补救/空组配置读回保留；新负载、双节点与CPU降级限制须实际验证 |

## 评审反馈怎么写

请引用目标决策/验收编号或跨目标 `X01–X12`，给出认可、需修改或缺证据的结论及原因。设计认可、实现完成、领域/部署验收分开记录。所有图注明当前或拟议，接口字段有当前映射；没有取得的内部数据和没有运行的验证继续保留未知状态。

其他入口：[五模块索引](../README.md) · [历史目标进度](../../reviews/2026-10-09-reassessment/goals-progress-v2.md) · [版本锁](../../versions.lock.json) · [原始证据](../../evidence/INDEX.md) · [本轮检查记录](../../evidence/review-readiness-checks-20261009.json)。
