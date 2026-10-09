# 可复查证据索引

当前自进化决定已确认：[原生简单设计与目标进度](../reviews/2026-10-09-reassessment/goals-progress-v2.md)。外部项目仅参考，不作为实施依赖；实现/业务验收未完成。

## 当前优先入口（2026-10-09）

[严格重审与目标进度](../reviews/2026-10-09-reassessment/README.md)。当前实施未满足全部目标；以下保留旧检查，不用汇总数量代替目标验收。


2026-10-09。所有 FAIL 与追加尝试保留；不同时间/代码版本按各自范围解释。

| 证据 | 实际含义 |
|---|---|
| [live-20261008T153103.json](live-20261008T153103.json) | 49 项真实 HTTP/节点/角色功能检查（资源事件前） |
| [governance-recovery-20261008T153325.json](governance-recovery-20261008T153325.json) | 18 项真实发布竞争、撤回、回退、离线、重启检查（资源事件前） |
| [browser-guarded-2026-10-08T17-06-57-896Z.json](browser-guarded-2026-10-08T17-06-57-896Z.json) | 资源护栏下三浏览器上下文、只读启动、远端资产和移动布局 |
| [guarded-hub-20261008T170041.json](guarded-hub-20261008T170041.json) | 资源护栏下六节点逐个唤醒、消费密钥拒绝写入、取消和恢复；37 项 |
| [final-edges-1791481451416686618.json](final-edges-1791481451416686618.json) | 最后代码的 native revision/依赖包、发布消费、幂等、丢回执恢复、项目权限 |
| [resource-controls-1791480527113427669.json](resource-controls-1791480527113427669.json) | 实际内核限额、子线程/子进程 CPU 亲和性、跨进程模型单并发 |
| [luna-guarded-1791480044434422462.json](luna-guarded-1791480044434422462.json) | 资源护栏内实际 Luna 调用 |
| [luna-routing-20261008T152931.json](luna-routing-20261008T152931.json) | 21 条合成标注分类题真实 Luna 结果 |
| [luna-hermes-retry-run.json](luna-hermes-retry-run.json) | 实际 Luna → Hermes/MCP/WeKnora → 报告；此前 429 失败另保留 |
| [luna-learning-proposal.json](luna-learning-proposal.json) | 实际 Luna 生成的合成证据候选，未自动发布 |

资源事件：[诊断](resource-diagnosis-20261009.json)、[重启前节点心跳](prereboot-node-memory-20261009.json)。受限 WeKnora 启动卡点：[栈证据](guarded-weknora-startup-stall.json)。

其它 live/guarded/browser JSON 中的 FAIL 原样保留；部分为验证器错误，部分为预算拒绝/就绪竞争/接口边界，均不得计作通过。运行日志、数据库、身份和全部连续采样保存在忽略的 `.local`；正式摘要/截图/矩阵在 Git。

私人交付：[内容提交与可见性核验](private-delivery-r1.json)。最终 metadata HEAD 以实际本地/远端核对为准。

2026-10-09研究已持久化：本地分类、Hermes/独立进化、社媒正反证据与版本账本见[当前重审入口](../reviews/2026-10-09-reassessment/README.md)；新模型/进化运行NOT_RUN，整体目标仍部分实现。

预算调整与质量研究：[3GiB kernel核对](../reviews/2026-10-09-reassessment/resource-budget-v3-applied.json)、[13项资源检查](../reviews/2026-10-09-reassessment/resource-budget-v3-checks.json)、[原生自进化业务质量门禁研究](../reviews/2026-10-09-reassessment/native-evolution-quality-gates-v1.md)。旧1GiB证据保留历史；门禁集成/业务评测NOT_RUN。

最新RCA路线：[最终根因监督与周期合入审查建议](../reviews/2026-10-09-reassessment/rca-gated-native-evolution-v2.md)、[项目规模与第一方资料现场](../reviews/2026-10-09-reassessment/rca-evolution-route-sources-v1.json)。RCA由用户报告存在；未读取内部数据或运行领域回放。

[多引擎/节点隔离源码归属](../reviews/2026-10-09-reassessment/isolation-implementation-analysis-v1.md)与[文件SHA/基线差异](../reviews/2026-10-09-reassessment/isolation-implementation-provenance-v1.json)：静态核对，未重跑运行验收；旧串行证据不证明当前同时双节点。

[同引擎跨VM/容器路由与产物分析](../reviews/2026-10-09-reassessment/multi-resource-routing-artifacts-v1.md)：静态现状与架构建议，跨VM注册/租约/汇聚/产物上传等NOT_RUN。

[公开架构/目标交付PR #1](https://github.com/zcimon57-svj/hermes-webui-engine-hub/pull/1)、[提交记录](architecture-pr-submission-20261009.json)、[检查结果](architecture-handoff-checks-20261009.json)、[公开检查](publication-safety-20261009.json)。PR/ref是最终合并权威；提交记录不证明业务验收。
